"""Evaluation script for dev_41_draft.json using live RunPod extraction.

Reads 41 draft evaluation cases, dynamically applies tenant-specific product catalogs
(T1: Sinaran Food Supply / T2: Kilat Cleaning Supplies), runs real over-the-wire
RunPod inference, and records extracted lines, conditions, and latency metrics.

COMPLIANCE METADATA (Zhou Specification):
- input_status = "DRAFT_NOT_ANSWER_KEY"
- adapter_mode = "RUNPOD_REAL"
- accuracy = "NOT_COMPUTED"
- eligible_for_quality_claim = false
- Dual-phase timeout: warmup with timeout_s=180.0, official calls with timeout_s=4.1.
- Records latency_ms and exceeds_production_timeout for each case.
- Adds raw_model_line diagnostic without modifying AdapterLine dataclass.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.adapter import AdapterOutput, OrderAiAdapter
from backend.ai.extractor import RunPodExtractor
from scripts.build_catalog import build_catalog


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load key-value pairs from .env without printing secrets."""
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


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract dev_41 draft dataset through live RunPod OrderAiAdapter."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "ai-eval-inputs-2026-10-23(1)" / "dev_41_draft.json",
        help="Path to dev_41_draft.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evidence" / "dev41_extract_2026-10-24.json",
        help="Output path for extraction report JSON.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of cases to process.",
    )
    args = parser.parse_args()

    load_dotenv()

    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not endpoint_id or not api_key:
        print("Error: RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    if not args.dataset.is_file():
        print(f"Error: Dataset file not found at {args.dataset}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading dataset: {args.dataset}...")
    dataset_raw: Dict[str, Any] = json.loads(args.dataset.read_text(encoding="utf-8"))
    cases: List[Dict[str, Any]] = dataset_raw.get("cases", [])
    if args.limit:
        cases = cases[: args.limit]
    print(f"Loaded {len(cases)} cases to process.")

    # Dynamically build catalogs for T1 and T2
    print("Building dynamic catalogs for T1 and T2...")
    catalogs = {
        "T1": build_catalog("T1"),
        "T2": build_catalog("T2"),
    }
    print(f"Catalogs initialized: T1={len(catalogs['T1'])} families, T2={len(catalogs['T2'])} families.")

    # Phase 1: Warmup probe with timeout_s=180.0
    print("Phase 1: Pre-warming endpoint with timeout_s=180.0...")
    warmup_extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=180.0,
    )
    await warmup_extractor.probe_version()
    print("Pre-warmup probe succeeded. Switching to production timeout_s=4.1...")

    # Phase 2: Production extractor with timeout_s=4.1
    extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=4.1,
    )
    adapter = OrderAiAdapter(extractor=extractor)

    results: List[Dict[str, Any]] = []
    mode_counts: Dict[str, int] = {}
    latencies: List[float] = []

    print("=" * 70)
    print("STARTING DEV_41 RUNPOD EXTRACTION (timeout_s=4.1)")
    print("=" * 70)

    for idx, c in enumerate(cases, 1):
        case_id = c.get("case_id", f"DEV-{idx:02d}")
        tenant_id = c.get("tenant_id", "T1").upper()
        customer_id = c.get("customer_id", "")
        message = c.get("message", "")
        scenario = c.get("scenario", "")

        cat = catalogs.get(tenant_id, catalogs["T1"])

        print(f"[{idx:02d}/{len(cases):02d}] {case_id} ({tenant_id}) | {message[:30]!r}...")

        # Obtain raw extraction first for raw_model_line diagnostics without altering AdapterLine
        raw_res = await extractor.extract(message)

        t0 = time.time()
        adapter_output: AdapterOutput = await adapter.adapt(message, catalog=cat)
        elapsed_ms = (time.time() - t0) * 1000.0

        latencies.append(elapsed_ms)
        mode = adapter_output.ai_mode
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        exceeds_timeout = elapsed_ms > 4100.0

        # Build raw model row mapping
        raw_rows = raw_res.result.rows if raw_res and raw_res.result else []

        # Format lines with raw_model_line diagnostic
        formatted_lines: List[Dict[str, Any]] = []
        for line_idx, line in enumerate(adapter_output.lines):
            raw_match = raw_rows[line_idx] if line_idx < len(raw_rows) else None
            raw_model_line = {
                "raw_span": raw_match.span if raw_match else None,
                "raw_fam": raw_match.fam if raw_match else None,
                "raw_qty": raw_match.qty if raw_match else None,
                "raw_uom": raw_match.uom if raw_match else None,
                "raw_pack_size": raw_match.pack_size if raw_match else None,
            }

            formatted_lines.append({
                "line_id": line.line_id,
                "span": line.span,
                "span_start": line.span_start,
                "span_end": line.span_end,
                "family_id": line.family_id,
                "qty": line.qty,
                "uom": line.uom,
                "pack_size": line.pack_size,
                "raw_model_line": raw_model_line,
                "match_source": line.match_source,
                "issue_code": line.issue_code,
                "reason_code": line.reason_code,
            })

        # Format conditions
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

        scope_val = "AI_EXTRACTION"
        if case_id in ("DEV-02", "DEV-08", "DEV-23"):
            scope_val = "RESOLVER_ONLY"

        status_val = "PROCESSED"
        if case_id in ("DEV-01", "DEV-05"):
            status_val = "DATA_ALIAS_MISSING"

        case_record = {
            "case_id": case_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "scenario": scenario,
            "scope": scope_val,
            "status": status_val,
            "message": message,
            "expected_business_outcome": c.get("expected_business_outcome", ""),
            "ai_mode": mode,
            "latency_ms": round(elapsed_ms, 2),
            "exceeds_production_timeout": exceeds_timeout,
            "lines": formatted_lines,
            "conditions": formatted_conditions,
            "ignored_spans": adapter_output.ignored_spans,
        }
        results.append(case_record)

        print(f"       -> ai_mode={mode} | lines={len(formatted_lines)} | conds={len(formatted_conditions)} | latency={elapsed_ms:.1f}ms | exceeds_timeout={exceeds_timeout}")

    # Build final report adhering strictly to requirements
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
        "source_dataset": str(args.dataset.name),
        "total_cases_evaluated": len(results),
        "summary": {
            "ai_mode_distribution": mode_counts,
            "average_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
            "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
            "total_lines_extracted": sum(len(r["lines"]) for r in results),
            "total_conditions_extracted": sum(len(r["conditions"]) for r in results),
            "total_exceeding_production_timeout": sum(1 for r in results if r["exceeds_production_timeout"]),
        },
        "cases": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 70)
    print(f"DEV_41 EXTRACTION COMPLETE.")
    print(f"Report saved to: {args.output}")
    print(f"Total processed: {len(results)} cases")
    print(f"AI Mode breakdown: {mode_counts}")
    print(f"Average latency: {avg_latency:.1f} ms")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
