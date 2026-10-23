"""Format Compatibility Probe Runner for KiraOrder dev_41 (5 Probe Cases).

Complies strictly with Zhou's data specifications and scope contracts:
- Uses dev_41_parse_scope.json to identify probe cases vs non-eligible cases.
- input_status = "DRAFT_NOT_ANSWER_KEY"
- adapter_mode = "RUNPOD_REAL"
- accuracy = "NOT_COMPUTED"
- eligible_for_quality_claim = false
- Strictly limits real RunPod calls to the 5 probe cases (DEV-01 .. DEV-05).
- Tenant catalog isolation: selects T1 or T2 catalog dynamically per case tenant_id.
- Wires in alias_cache (word-order insensitive matching with SKU -> Family resolution).
- Outputs structured evidence to evidence/dev_probe5_2026-10-24.json with SHA-256.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.adapter import AdapterOutput, OrderAiAdapter
from backend.ai.extractor import RunPodExtractor
from scripts.build_catalog import build_catalog


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env without logging secrets."""
    if env_path is None:
        env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                k = key.strip()
                v = val.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as err:
        print(f"Warning: Failed reading {env_path}: {err}", file=sys.stderr)


class AliasCacheResolver:
    """Customer-level alias cache resolver with word-order-insensitive matching."""

    def __init__(self, inputs_dir: Path) -> None:
        self.alias_entries: List[Dict[str, Any]] = []
        self.sku_to_family: Dict[str, str] = {}
        self._load_tenant_data(inputs_dir)

    def _load_tenant_data(self, inputs_dir: Path) -> None:
        for fname in ("tenant_sinaran.json", "tenant_kilat.json"):
            fpath = inputs_dir / fname
            if not fpath.is_file():
                continue
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                for prod in data.get("products", []):
                    pid = prod.get("product_id")
                    fid = prod.get("family_id")
                    if pid and fid:
                        self.sku_to_family[pid] = fid

                for ac in data.get("alias_cache", []):
                    if ac.get("active", True):
                        self.alias_entries.append(ac)
            except Exception as err:
                print(f"Warning loading {fname}: {err}", file=sys.stderr)

    def resolve_alias(
        self,
        tenant_id: str,
        customer_id: str,
        message: str,
    ) -> Optional[Dict[str, Any]]:
        """Attempt word-order-insensitive match against customer alias_cache."""
        t_id = tenant_id.strip().upper()
        c_id = customer_id.strip()

        # Filter candidate aliases by tenant and customer
        candidates = [
            ac for ac in self.alias_entries
            if ac.get("tenant_id", "").upper() == t_id and ac.get("customer_id", "") == c_id
        ]

        if not candidates:
            return None

        # Clean normalized message
        msg_clean = "".join(message.lower().split())

        for ac in candidates:
            phrase = ac.get("phrase", "")
            phrase_norm = ac.get("phrase_norm", "")
            target_phrase = phrase_norm if phrase_norm else phrase
            target_clean = "".join(target_phrase.lower().split())

            if not target_clean:
                continue

            # Word-order-insensitive / substring containment check
            # Check 1: direct contiguous clean substring
            # Check 2: all characters of target phrase present in message
            matched = False
            if target_clean in msg_clean:
                matched = True
            else:
                # Word-level / character set inclusion
                phrase_chars = set(target_clean)
                if phrase_chars and phrase_chars.issubset(set(msg_clean)):
                    matched = True

            if matched:
                sku_id = ac.get("product_id")
                target_type = ac.get("target_type")
                resolved_family = ac.get("family_id")

                if target_type == "SKU" and sku_id:
                    resolved_family = self.sku_to_family.get(sku_id, resolved_family)

                return {
                    "alias_id": ac.get("alias_id"),
                    "phrase": phrase,
                    "target_type": target_type,
                    "product_id": sku_id,
                    "family_id": resolved_family,
                    "match_type": "ALIAS_APPROX",
                }

        return None


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run dev_41 format compatibility probe strictly for Zhou's 5 probe cases."
    )
    parser.add_argument(
        "--inputs-dir",
        type=Path,
        default=PROJECT_ROOT / "ai-eval-inputs-2026-10-23(1)",
        help="Directory with dev_41_draft.json, dev_41_parse_scope.json, etc.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evidence" / "dev_probe5_2026-10-24.json",
        help="Path for output JSON evidence.",
    )
    args = parser.parse_args()

    load_dotenv()

    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not endpoint_id or not api_key:
        print("Error: RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    scope_file = args.inputs_dir / "dev_41_parse_scope.json"
    draft_file = args.inputs_dir / "dev_41_draft.json"

    if not scope_file.is_file() or not draft_file.is_file():
        print(f"Error: Required scope or draft file missing in {args.inputs_dir}", file=sys.stderr)
        sys.exit(1)

    scope_data = json.loads(scope_file.read_text(encoding="utf-8"))
    draft_data = json.loads(draft_file.read_text(encoding="utf-8"))

    probe_ids: Set[str] = set(scope_data.get("probe_case_ids", ["DEV-01", "DEV-02", "DEV-03", "DEV-04", "DEV-05"]))
    excluded_map: Dict[str, Dict[str, str]] = {
        ex["case_id"]: ex for ex in scope_data.get("excluded_cases", [])
    }
    alias_only_ids: Set[str] = set(scope_data.get("alias_only_case_ids", []))
    parse_eligible_ids: Set[str] = set(scope_data.get("parse_eligible_case_ids", []))

    all_cases: List[Dict[str, Any]] = draft_data.get("cases", [])
    print(f"Loaded {len(all_cases)} total cases from {draft_file.name}.")
    print(f"Probe case IDs to execute ({len(probe_ids)}): {sorted(probe_ids)}")

    # Initialize dynamic catalogs (T1 and T2 separated)
    print("Initializing isolated T1 & T2 catalogs...")
    catalogs = {
        "T1": build_catalog("T1", inputs_dir=args.inputs_dir),
        "T2": build_catalog("T2", inputs_dir=args.inputs_dir),
    }
    print(f"Catalogs ready: T1 ({len(catalogs['T1'])} families), T2 ({len(catalogs['T2'])} families).")

    # Initialize alias cache resolver
    alias_resolver = AliasCacheResolver(args.inputs_dir)
    print(f"AliasCacheResolver ready with {len(alias_resolver.alias_entries)} active alias entries.")

    extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=180.0,
    )
    adapter = OrderAiAdapter(extractor=extractor)

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []
    probe_call_count = 0

    print("=" * 72)
    print("STARTING RUNPOD CALLS STRICTLY FOR THE 5 PROBE CASES")
    print("=" * 72)

    for idx, c in enumerate(all_cases, 1):
        case_id = c.get("case_id", f"DEV-{idx:02d}")
        tenant_id = c.get("tenant_id", "T1").upper()
        customer_id = c.get("customer_id", "")
        message = c.get("message", "")
        scenario = c.get("scenario", "")

        is_probe = case_id in probe_ids

        if is_probe:
            probe_call_count += 1
            cat = catalogs.get(tenant_id, catalogs["T1"])
            print(f"[{probe_call_count}/5] Executing PROBE: {case_id} ({tenant_id}) | {message[:30]!r}...")

            t0 = time.time()
            adapter_output: AdapterOutput = await adapter.adapt(message, catalog=cat)
            elapsed_ms = (time.time() - t0) * 1000.0
            latencies.append(elapsed_ms)

            # Check alias cache resolution
            alias_match = alias_resolver.resolve_alias(tenant_id, customer_id, message)

            formatted_lines: List[Dict[str, Any]] = []
            for line in adapter_output.lines:
                fam = line.family_id
                match_type = "STANDARD_CATALOG"
                resolved_sku = None
                matched_alias_id = None

                if alias_match:
                    fam = alias_match.get("family_id") or fam
                    match_type = alias_match.get("match_type", "ALIAS_APPROX")
                    resolved_sku = alias_match.get("product_id")
                    matched_alias_id = alias_match.get("alias_id")
                elif fam == "UNKNOWN":
                    match_type = "ALIAS_NOT_MATCHED"

                formatted_lines.append({
                    "line_id": line.line_id,
                    "span": line.span,
                    "span_start": line.span_start,
                    "span_end": line.span_end,
                    "family_id": fam,
                    "qty": line.qty,
                    "uom": line.uom,
                    "pack_size": line.pack_size,
                    "match_source": line.match_source,
                    "match_type": match_type,
                    "matched_alias_id": matched_alias_id,
                    "resolved_sku_id": resolved_sku,
                    "issue_code": line.issue_code,
                    "reason_code": line.reason_code,
                })

            formatted_conditions: List[Dict[str, Any]] = []
            for cond in adapter_output.conditions:
                formatted_conditions.append({
                    "kind": cond.kind,
                    "span": cond.span,
                    "span_start": cond.span_start,
                    "span_end": cond.span_end,
                    "condition_scope": cond.condition_scope,
                    "price_basis": cond.price_basis,
                    "requested_amount": cond.requested_amount,
                })

            case_entry = {
                "case_id": case_id,
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "scenario": scenario,
                "message": message,
                "expected_business_outcome": c.get("expected_business_outcome", ""),
                "status": "PROBE_EXECUTED",
                "ai_mode": adapter_output.ai_mode,
                "latency_ms": round(elapsed_ms, 2),
                "alias_resolved": alias_match is not None,
                "lines": formatted_lines,
                "conditions": formatted_conditions,
                "ignored_spans": adapter_output.ignored_spans,
            }
            results.append(case_entry)
            print(f"       -> {case_id} DONE in {elapsed_ms:.1f}ms | ai_mode={adapter_output.ai_mode} | lines={len(formatted_lines)} | alias={alias_match is not None}")

        else:
            # Non-probe cases: populate metadata from scope without LLM execution
            exclusion_info = excluded_map.get(case_id)
            if exclusion_info:
                reason_category = exclusion_info.get("category", "EXCLUDED")
                reason_detail = exclusion_info.get("reason", "Excluded by scope specification")
            elif case_id in alias_only_ids:
                reason_category = "ALIAS_ONLY_CASE"
                reason_detail = "Case designated for alias-only workflow probe"
            elif case_id in parse_eligible_ids:
                reason_category = "DEFERRED_FROM_PROBE_5"
                reason_detail = "Eligible for parse but deferred during 5-case format compatibility probe"
            else:
                reason_category = "UNCLASSIFIED"
                reason_detail = "Not included in format probe 5"

            results.append({
                "case_id": case_id,
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "scenario": scenario,
                "message": message,
                "expected_business_outcome": c.get("expected_business_outcome", ""),
                "status": "NOT_PARSE_ELIGIBLE",
                "exclusion_category": reason_category,
                "exclusion_reason": reason_detail,
                "ai_mode": None,
                "latency_ms": None,
                "lines": [],
                "conditions": [],
                "ignored_spans": [],
            })

    # Strict compliance headers matching Zhou's specifications
    timestamp = datetime.now(timezone.utc).isoformat()
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    report = {
        "input_status": "DRAFT_NOT_ANSWER_KEY",
        "adapter_mode": "RUNPOD_REAL",
        "accuracy": "NOT_COMPUTED",
        "eligible_for_quality_claim": False,
        "warning": "dev_41_draft.json 无结构化答案键，本报告仅记录真实抽取输出，不作正式评分",
        "timestamp": timestamp,
        "endpoint_id": endpoint_id,
        "source_dataset": "dev_41_draft.json",
        "scope_specification": "dev_41_parse_scope.json",
        "format_probe_source": "dev_format_probe_5.json",
        "probe_case_count": probe_call_count,
        "total_cases_cataloged": len(results),
        "probe_summary": {
            "probe_cases_executed": probe_call_count,
            "non_probe_cases_stubbed": len(results) - probe_call_count,
            "average_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
            "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
        },
        "cases": results,
    }

    # Write evidence file
    args.output.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    args.output.write_bytes(json_bytes)

    # Compute SHA-256
    sha256_val = hashlib.sha256(json_bytes).hexdigest().upper()

    print("=" * 72)
    print("PROBE 5 EXTRACTION COMPLETE.")
    print(f"Report saved to: {args.output}")
    print(f"Evidence SHA-256: {sha256_val}")
    print(f"Probe calls made to RunPod: {probe_call_count}")
    print(f"Average latency for probe: {avg_latency:.1f}ms")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
