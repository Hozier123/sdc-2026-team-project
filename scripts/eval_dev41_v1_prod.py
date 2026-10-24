"""KiraOrder AI Pre-Resolver Production Evaluation Script (dev_41 v1_prod).

Strict compliance with Zhou's and He's official specifications:
1. Enforces strict startup SHA-256 validation of the 3 canonical input files.
2. Direct production integration using app.ai (no prompt_version override).
3. Exactly ONE adapter.adapt(masked_text, catalog) call per evaluated case (no separate extractor calls).
4. Strictly 23 AI-only parse_eligible cases evaluated (DEV-02/08/23 listed as RESOLVER_ONLY, 15 excluded cases listed as NOT_PARSE_ELIGIBLE).
5. 1 warmup call with timeout_s=180.0, followed by timeout_s=4.1 on all evaluated cases.
6. Records latency_ms and exceeds_production_timeout (>4100ms) for each case.
7. Outputs production evidence: evidence/dev41_ai_only_v1_prod_2026-10-24.json.
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
_backend_dir = PROJECT_ROOT / "backend"
for _p in (PROJECT_ROOT, _backend_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from app.ai.adapter import AdapterOutput, OrderAiAdapter
from app.ai.extractor import RunPodExtractor
from scripts.build_catalog import build_catalog

# Official Canonical Dataset SHA-256 Hashes
EXPECTED_SHA256 = {
    "dev_41_draft.json": "5529443897C7B718DF1D8064A3C668AFEAA0755E9DD032B4596AF96180F8AD40",
    "dev_41_parse_scope.json": "6AE86B6B4CE58EB546A27EBDAE2E9C3F2608040A332836E47B802F0659F128F0",
    "dev_format_probe_5.json": "92E2D9574C8C55D0C2C66A4D669CE0F4BCFC7FFBA155F93A2F4EFE19F2972DD3",
}

DEFAULT_INPUTS_DIR = PROJECT_ROOT / "ai-eval-inputs-2026-10-23(1)"


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env without printing secrets."""
    if env_path is None:
        for p in (PROJECT_ROOT / ".env", _backend_dir / ".env"):
            if p.is_file():
                env_path = p
                break
    if not env_path or not env_path.is_file():
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


def verify_dataset_hashes(inputs_dir: Path) -> None:
    """Verify SHA-256 for all 3 canonical files; exit immediately on mismatch."""
    print("Verifying canonical input dataset SHA-256 hashes...")
    for fname, expected_hash in EXPECTED_SHA256.items():
        fpath = inputs_dir / fname
        if not fpath.is_file():
            raise FileNotFoundError(f"Missing required dataset file: {fpath}")
        computed = hashlib.sha256(fpath.read_bytes()).hexdigest().upper()
        if computed != expected_hash:
            raise ValueError(
                f"FATAL: SHA-256 mismatch on {fname}!\n"
                f"  Computed: {computed}\n"
                f"  Expected: {expected_hash}\n"
                f"Aborting immediately per specification."
            )
        print(f"  [OK] {fname}: {computed[:16]}...")
    print("Dataset integrity verified.")


def resolve_inputs_dir(cli_dir: Optional[str] = None) -> Path:
    """Locate the valid dataset directory."""
    candidates = [
        Path(cli_dir) if cli_dir else None,
        DEFAULT_INPUTS_DIR,
        PROJECT_ROOT / "ai-eval-inputs-2026-10-23",
        PROJECT_ROOT.parent / "ai-eval-inputs-2026-10-23(1)",
        PROJECT_ROOT / "data",
    ]
    for c in candidates:
        if c and c.is_dir() and (c / "dev_41_draft.json").is_file():
            return c.resolve()
    raise FileNotFoundError(f"Could not locate dataset directory containing dev_41_draft.json")


async def run_warmup_call(endpoint_id: str, api_key: str) -> None:
    """Perform 1 pre-evaluation warmup call with 180s timeout to absorb cold-start / CUDA capture."""
    print("\n--- Executing RunPod Warmup (timeout=180s) ---")
    extractor = RunPodExtractor(
        api_key=api_key,
        endpoint_id=endpoint_id,
        timeout_s=180.0,
    )
    t0 = time.perf_counter()
    resp = await extractor.extract("Beras 5 bag, Minyak 2 ctn")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    print(f"Warmup completed in {elapsed_ms}ms (ai_mode={resp.ai_mode}, rows={len(resp.result.rows)})")
    if resp.ai_mode != "LLM":
        print(f"WARNING: Warmup degraded ai_mode={resp.ai_mode}, raw_error={resp.raw_error}")


async def evaluate_dev41_v1_prod(
    inputs_dir: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """Execute v1_prod production evaluation across dev_41."""
    verify_dataset_hashes(inputs_dir)

    scope_data = json.loads((inputs_dir / "dev_41_parse_scope.json").read_text(encoding="utf-8"))
    draft_data = json.loads((inputs_dir / "dev_41_draft.json").read_text(encoding="utf-8"))

    parse_eligible_ids: Set[str] = set(scope_data.get("parse_eligible_case_ids", []))
    resolver_only_ids: Set[str] = set(scope_data.get("resolver_only_case_ids", []))
    excluded_raw = scope_data.get("excluded_cases", [])
    if isinstance(excluded_raw, dict):
        excluded_map: Dict[str, str] = dict(excluded_raw)
    else:
        excluded_map = {
            c.get("case_id"): c.get("reason") or c.get("category") or "EXCLUDED"
            for c in excluded_raw if isinstance(c, dict)
        }

    cases_by_id: Dict[str, Dict[str, Any]] = {c["case_id"]: c for c in draft_data.get("cases", [])}

    # Build canonical catalogs directly from seed JSON files
    catalog_t1 = build_catalog(tenant_id="T1", inputs_dir=inputs_dir)
    catalog_t2 = build_catalog(tenant_id="T2", inputs_dir=inputs_dir)

    api_key = os.getenv("RUNPOD_API_KEY", "")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "")
    if not api_key or not endpoint_id:
        raise ValueError("Missing RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID in environment.")

    # Step 1: Pre-warmup
    await run_warmup_call(endpoint_id=endpoint_id, api_key=api_key)

    # Step 2: Production adapter with 4.1s timeout
    prod_extractor = RunPodExtractor(
        api_key=api_key,
        endpoint_id=endpoint_id,
        timeout_s=4.1,
    )
    prod_adapter = OrderAiAdapter(extractor=prod_extractor)

    evaluated_cases: List[Dict[str, Any]] = []
    production_timeout_violations = 0
    unknown_lines_count = 0
    fallback_modes_count = 0

    sorted_case_ids = sorted(parse_eligible_ids, key=lambda x: int(x.split("-")[1]) if "-" in x else x)

    print(f"\n--- Running Production Evaluation on {len(sorted_case_ids)} AI-only Cases ---")

    for idx, case_id in enumerate(sorted_case_ids, start=1):
        case_info = cases_by_id[case_id]
        tenant_id = case_info["tenant_id"]
        masked_text = case_info.get("masked_text") or case_info.get("message", "")
        catalog = catalog_t1 if tenant_id == "T1" else catalog_t2

        t_start = time.perf_counter()
        # Exactly ONE call per case, directly through adapter.adapt()
        out: AdapterOutput = await prod_adapter.adapt(masked_text, catalog=catalog)
        latency_ms = int((time.perf_counter() - t_start) * 1000)

        exceeds_timeout = latency_ms > 4100
        if exceeds_timeout:
            production_timeout_violations += 1
        if out.ai_mode in ("FALLBACK", "MIXED"):
            fallback_modes_count += 1

        case_unknowns = sum(1 for line in out.lines if line.family_id == "UNKNOWN")
        unknown_lines_count += case_unknowns

        record = {
            "case_id": case_id,
            "tenant_id": tenant_id,
            "customer_id": case_info.get("customer_id", ""),
            "masked_text": masked_text,
            "ai_mode": out.ai_mode,
            "latency_ms": latency_ms,
            "exceeds_production_timeout": exceeds_timeout,
            "lines": [
                {
                    "line_id": line.line_id,
                    "span": line.span,
                    "span_start": line.span_start,
                    "span_end": line.span_end,
                    "family_id": line.family_id,
                    "qty": line.qty,
                    "uom": line.uom,
                    "pack_size": line.pack_size,
                    "issue_code": line.issue_code,
                    "reason_code": line.reason_code,
                    "model_coerced": line.model_coerced,
                }
                for line in out.lines
            ],
            "conditions": [
                {
                    "kind": getattr(cond, "kind", None),
                    "span": getattr(cond, "span", None),
                    "condition_scope": getattr(cond, "condition_scope", None),
                    "price_basis": getattr(cond, "price_basis", None),
                    "requested_amount": getattr(cond, "requested_amount", None),
                }
                for cond in out.conditions
            ],
            "ignored_spans": list(out.ignored_spans or []),
        }
        evaluated_cases.append(record)
        print(
            f"[{idx:02d}/{len(sorted_case_ids):02d}] {case_id} ({tenant_id}) -> "
            f"mode={out.ai_mode}, lines={len(out.lines)}, latency={latency_ms}ms, "
            f"timeout={exceeds_timeout}, UNKNOWNs={case_unknowns}"
        )

    # Compile resolver-only cases
    resolver_only_cases = [
        {
            "case_id": cid,
            "scope": "RESOLVER_ONLY",
            "reason": "Requires customer alias_cache resolution (target_type=SKU/product_id). Excluded from AI-only denominator.",
            "masked_text": (cases_by_id[cid].get("masked_text") or cases_by_id[cid].get("message","")),
        }
        for cid in sorted(resolver_only_ids)
        if cid in cases_by_id
    ]

    # Compile excluded cases
    excluded_cases_report = [
        {
            "case_id": cid,
            "status": "NOT_PARSE_ELIGIBLE",
            "reason": reason,
            "masked_text": (cases_by_id[cid].get("masked_text") or cases_by_id[cid].get("message","")) if cid in cases_by_id else "",
        }
        for cid, reason in sorted(excluded_map.items())
    ]

    report = {
        "report_type": "KiraOrder AI Pre-Resolver Production Evaluation",
        "input_status": "DRAFT_NOT_ANSWER_KEY",
        "adapter_mode": "RUNPOD_REAL",
        "accuracy": "NOT_COMPUTED",
        "eligible_for_quality_claim": False,
        "code_base": "app/ai@db6f0ce",
        "eval_timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_cases_in_file": len(cases_by_id),
            "parse_eligible_cases_evaluated": len(evaluated_cases),
            "resolver_only_cases_count": len(resolver_only_cases),
            "excluded_cases_count": len(excluded_cases_report),
            "production_timeout_violations_count": production_timeout_violations,
            "fallback_modes_count": fallback_modes_count,
            "total_unknown_lines_count": unknown_lines_count,
        },
        "evaluated_cases": evaluated_cases,
        "resolver_only_cases": resolver_only_cases,
        "excluded_cases": excluded_cases_report,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_hash = hashlib.sha256(output_path.read_bytes()).hexdigest().upper()
    print(f"\nSaved production evaluation report to: {output_path}")
    print(f"Report SHA-256: {report_hash}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate KiraOrder AI production adapter on dev_41.")
    parser.add_argument("--inputs-dir", type=str, default=None, help="Directory containing canonical inputs.")
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "evidence" / "dev41_ai_only_v1_prod_2026-10-24.json"),
        help="Path for destination report JSON.",
    )
    args = parser.parse_args()

    load_dotenv()
    resolved_inputs = resolve_inputs_dir(args.inputs_dir)
    out_file = Path(args.output).resolve()

    asyncio.run(evaluate_dev41_v1_prod(inputs_dir=resolved_inputs, output_path=out_file))


if __name__ == "__main__":
    main()
