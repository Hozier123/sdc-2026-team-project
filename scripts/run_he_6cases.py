r"""He Minghao 6-Case Acceptance Runner using live RunPod OrderAiAdapter.

Loads cases from '六条样例/*.json', constructs canonical T1 catalog from
tenant_sinaran.json, executes real end-to-end extraction through RunPod,
verifies span coordinate slice integrity against masked_text, and compares
extracted fields (span, qty, uom, fam, pack_size, ignored_spans) against
expected_response.

Usage:
    E:\anaconda\python.exe scripts/run_he_6cases.py [--limit 3] [--output evidence/he_6cases_2026-10-24.txt]
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
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.adapter import AdapterOutput, OrderAiAdapter
from backend.ai.extractor import RunPodExtractor
from scripts.build_catalog import build_catalog


# Canonical family synonym mapping between T1 database seed IDs and He's mock sample IDs
CANONICAL_FAM_MAP: Dict[str, str] = {
    "FAM_TEPUNG": "FAM_FLOUR",
    "FAM_BERAS": "FAM_RICE",
    "FAM_MINYAK": "FAM_OIL",
    "FAM_GULA": "FAM_SUGAR",
}


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


def load_samples(sample_dir: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """Load sample JSON files from directory in deterministic order."""
    # Preferred order of execution
    order_preference = [
        "normal.json",
        "multi_line.json",
        "multi_candidate.json",
        "ambiguous.json",
        "condition.json",
        "empty.json",
    ]
    files = list(sample_dir.glob("*.json"))
    file_map = {f.name: f for f in files}

    ordered_samples: List[Tuple[str, Dict[str, Any]]] = []
    for name in order_preference:
        if name in file_map:
            content = json.loads(file_map[name].read_text(encoding="utf-8"))
            ordered_samples.append((name, content))

    # Add any remaining
    for f in sorted(files):
        if f.name not in order_preference:
            content = json.loads(f.read_text(encoding="utf-8"))
            ordered_samples.append((f.name, content))

    return ordered_samples


def compare_single_case(
    sample_name: str,
    sample_data: Dict[str, Any],
    adapter_output: AdapterOutput,
) -> Dict[str, Any]:
    """Compare adapter output against sample expected_response."""
    input_data = sample_data.get("input", {})
    masked_text = input_data.get("masked_text", "")
    expected = sample_data.get("expected_response", {})
    expected_rows = expected.get("rows", [])
    expected_ignored = expected.get("ignored_spans", [])

    extracted_lines = adapter_output.lines
    extracted_ignored = adapter_output.ignored_spans

    diffs: List[str] = []
    field_comparisons: List[Dict[str, Any]] = []

    # 1. Verify span coordinate slicing integrity
    for idx, line in enumerate(extracted_lines):
        actual_slice = masked_text[line.span_start:line.span_end]
        if actual_slice != line.span:
            diffs.append(
                f"Row {idx+1} span coordinate mismatch: "
                f"masked_text[{line.span_start}:{line.span_end}]='{actual_slice}' != line.span='{line.span}'"
            )

    # 2. Compare row count
    if len(extracted_lines) != len(expected_rows):
        diffs.append(
            f"Row count mismatch: extracted {len(extracted_lines)} rows, expected {len(expected_rows)} rows"
        )

    # 3. Compare row-by-row
    rows_pass = True
    for idx in range(max(len(extracted_lines), len(expected_rows))):
        if idx >= len(extracted_lines):
            exp_row = expected_rows[idx]
            diffs.append(f"Row {idx+1} missing in extracted: expected {exp_row}")
            rows_pass = False
            continue
        if idx >= len(expected_rows):
            ext_line = extracted_lines[idx]
            diffs.append(f"Row {idx+1} unexpected in extracted: {ext_line}")
            rows_pass = False
            continue

        ext_line = extracted_lines[idx]
        exp_row = expected_rows[idx]

        row_diff: List[str] = []

        # span
        if ext_line.span != exp_row.get("span"):
            row_diff.append(f"span: extracted='{ext_line.span}' vs expected='{exp_row.get('span')}'")

        # qty
        if ext_line.qty != exp_row.get("qty"):
            row_diff.append(f"qty: extracted={ext_line.qty} vs expected={exp_row.get('qty')}")

        # uom
        if ext_line.uom != exp_row.get("uom"):
            row_diff.append(f"uom: extracted='{ext_line.uom}' vs expected='{exp_row.get('uom')}'")

        # pack_size
        if ext_line.pack_size != exp_row.get("pack_size"):
            row_diff.append(
                f"pack_size: extracted='{ext_line.pack_size}' vs expected='{exp_row.get('pack_size')}'"
            )

        # family_id
        fam_match_exact = ext_line.family_id == exp_row.get("fam")
        canonical_target = CANONICAL_FAM_MAP.get(ext_line.family_id, ext_line.family_id)
        fam_match_canonical = canonical_target == exp_row.get("fam")

        if not fam_match_exact:
            if fam_match_canonical:
                row_diff.append(
                    f"fam (canonical alias match): extracted='{ext_line.family_id}' maps to '{canonical_target}' vs expected='{exp_row.get('fam')}'"
                )
            else:
                row_diff.append(
                    f"fam: extracted='{ext_line.family_id}' vs expected='{exp_row.get('fam')}'"
                )

        field_comparisons.append({
            "row_index": idx + 1,
            "span": {"extracted": ext_line.span, "expected": exp_row.get("span")},
            "qty": {"extracted": ext_line.qty, "expected": exp_row.get("qty")},
            "uom": {"extracted": ext_line.uom, "expected": exp_row.get("uom")},
            "fam": {
                "extracted": ext_line.family_id,
                "expected": exp_row.get("fam"),
                "exact_match": fam_match_exact,
                "canonical_match": fam_match_canonical,
            },
            "pack_size": {"extracted": ext_line.pack_size, "expected": exp_row.get("pack_size")},
            "row_diffs": row_diff,
        })

        # Critical mismatch excludes benign family synonym differences between T1 canonical seed & mock sample
        critical_mismatch = [
            d for d in row_diff
            if not d.startswith("fam (canonical alias match)")
        ]
        if critical_mismatch:
            rows_pass = False
            for cm in critical_mismatch:
                diffs.append(f"Row {idx+1} mismatch: {cm}")

    # 4. Compare ignored_spans (as sets or presence)
    ignored_pass = True
    ext_ignored_set = set(extracted_ignored)
    exp_ignored_set = set(expected_ignored)
    if ext_ignored_set != exp_ignored_set:
        missing_ignored = exp_ignored_set - ext_ignored_set
        extra_ignored = ext_ignored_set - exp_ignored_set
        diff_str = []
        if missing_ignored:
            diff_str.append(f"missing {sorted(missing_ignored)}")
        if extra_ignored:
            diff_str.append(f"extra {sorted(extra_ignored)}")
        diffs.append(f"ignored_spans difference: {', '.join(diff_str)}")
        ignored_pass = False

    # Overall pass requires:
    # 1. No span coordinate slicing mismatches
    # 2. rows_pass is True (all row fields match, allowing canonical family equivalence)
    # 3. ignored_pass is True
    overall_pass = rows_pass and ignored_pass and (len([d for d in diffs if "span coordinate" in d]) == 0)

    return {
        "sample_name": sample_name,
        "masked_text": masked_text,
        "ai_mode": adapter_output.ai_mode,
        "overall_pass": overall_pass,
        "rows_pass": rows_pass,
        "ignored_pass": ignored_pass,
        "field_comparisons": field_comparisons,
        "diffs": diffs,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run He's 6 acceptance cases on live RunPod.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases to execute.")
    parser.add_argument("--samples-dir", type=Path, default=PROJECT_ROOT / "六条样例")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evidence" / "he_6cases_2026-10-24.txt",
        help="Path to output report.",
    )
    args = parser.parse_args()

    load_dotenv()

    # Preflight environment check
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not endpoint_id or not api_key:
        print("Error: RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Loading T1 catalog from tenant_sinaran.json...")
    catalog = build_catalog("T1")
    print(f"T1 Catalog loaded successfully ({len(catalog)} product families).")

    samples = load_samples(args.samples_dir)
    if args.limit:
        samples = samples[: args.limit]
    print(f"Loaded {len(samples)} cases to evaluate from {args.samples_dir}.")

    extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=180.0,
    )
    adapter = OrderAiAdapter(extractor=extractor)

    results: List[Dict[str, Any]] = []
    print("=" * 70)
    print("STARTING LIVE EVALUATION AGAINST RUNPOD ENDPOINT")
    print("=" * 70)

    for idx, (sample_name, sample_data) in enumerate(samples, 1):
        input_data = sample_data.get("input", {})
        masked_text = input_data.get("masked_text", "")
        print(f"\n[{idx}/{len(samples)}] Executing case: {sample_name}...")
        print(f"  Input: {masked_text!r}")

        t0 = time.time()
        adapter_output = await adapter.adapt(masked_text, catalog=catalog)
        elapsed_ms = (time.time() - t0) * 1000.0

        eval_res = compare_single_case(sample_name, sample_data, adapter_output)
        eval_res["latency_ms"] = elapsed_ms
        results.append(eval_res)

        status_str = "PASS" if eval_res["overall_pass"] else "FAIL"
        print(f"  Result: {status_str} | ai_mode={adapter_output.ai_mode} | latency={elapsed_ms:.1f}ms")
        if eval_res["diffs"]:
            print("  Differences/Notes:")
            for d in eval_res["diffs"]:
                print(f"    - {d}")

    # Build report text
    timestamp = datetime.now(timezone.utc).isoformat()
    pass_count = sum(1 for r in results if r["overall_pass"])
    fail_count = len(results) - pass_count

    lines: List[str] = [
        "=" * 78,
        "HE MINGHAO 6-CASE END-TO-END ACCEPTANCE REPORT",
        f"Timestamp: {timestamp}",
        f"Endpoint ID: {endpoint_id}",
        f"Evaluator: scripts/run_he_6cases.py",
        f"Catalog: T1 Sinaran Food Supply ({len(catalog)} families dynamically loaded)",
        f"Cases Evaluated: {len(results)} (Passed: {pass_count}, Failed: {fail_count})",
        "=" * 78,
        "",
    ]

    for idx, r in enumerate(results, 1):
        status_tag = "PASS" if r["overall_pass"] else "FAIL"
        lines.append(f"[{idx}] CASE: {r['sample_name']} --> {status_tag}")
        lines.append(f"    Input: {r['masked_text']!r}")
        lines.append(f"    AI Mode: {r['ai_mode']} | Latency: {r['latency_ms']:.1f}ms")
        lines.append(f"    Rows Extracted: {len(r['field_comparisons'])}")

        for comp in r["field_comparisons"]:
            row_idx = comp["row_index"]
            span_e = comp["span"]["extracted"]
            qty_e = comp["qty"]["extracted"]
            uom_e = comp["uom"]["extracted"]
            fam_e = comp["fam"]["extracted"]
            pack_e = comp["pack_size"]["extracted"]

            span_x = comp["span"]["expected"]
            qty_x = comp["qty"]["expected"]
            uom_x = comp["uom"]["expected"]
            fam_x = comp["fam"]["expected"]
            pack_x = comp["pack_size"]["expected"]

            lines.append(f"    - Row {row_idx}:")
            lines.append(f"        extracted : span={span_e!r}, qty={qty_e}, uom={uom_e!r}, fam={fam_e!r}, pack={pack_e!r}")
            lines.append(f"        expected  : span={span_x!r}, qty={qty_x}, uom={uom_x!r}, fam={fam_x!r}, pack={pack_x!r}")
            if comp["row_diffs"]:
                lines.append(f"        diffs     : {', '.join(comp['row_diffs'])}")

        if r["diffs"]:
            lines.append("    Audit Notes / Differences:")
            for d in r["diffs"]:
                lines.append(f"      * {d}")
        lines.append("")

    lines.append("=" * 78)
    lines.append(f"SUMMARY: {pass_count}/{len(results)} CASES MET ACCEPTANCE SPECIFICATIONS.")
    lines.append("=" * 78)

    report_content = "\n".join(lines) + "\n"

    # Always write to file
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report_content, encoding="utf-8")
    print(f"\nFull acceptance report written to: {args.output}")

    # Print summary to stdout
    print("\n" + report_content)


if __name__ == "__main__":
    asyncio.run(main())
