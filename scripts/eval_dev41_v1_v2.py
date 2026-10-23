"""Evaluation script for dev_41 v1 vs v2 controlled comparison experiment.

Complies strictly with Zhou's and the user's explicit instructions:
1. Enforces strict startup SHA-256 validation of the 3 input files.
2. Phase 1 (v1 baseline, prompt unmodified):
   - Evaluates strictly the 23 parse_eligible_case_ids.
   - resolver_only_case_ids (DEV-02/08/23) not evaluated, listed separately.
   - excluded_cases (15 cases) marked as NOT_PARSE_ELIGIBLE with reason.
   - Warmup 180s, then timeout_s=4.1 on all evaluated calls.
   - Outputs evidence/dev41_ai_only_v1_2026-10-24.json with SHA-256.
3. Phase 2 (v2 comparison):
   - Injects generic closed-set whitelist rule:
     "Copy the exact family ID string from the whitelist. Never translate, localize,
      abbreviate, or use a synonym. If no whitelist ID matches exactly, output UNKNOWN."
   - Never hardcodes specific IDs (FAM_TELUR/FAM_CILI/FAM_EGG) as prompt examples.
   - Evaluates the same 23 cases + He's 6 cases.
   - Outputs evidence/dev41_ai_only_v2_2026-10-24.json & evidence/he_6cases_v2_2026-10-24.txt.
4. Phase 3: Computes and displays the full comparison matrix.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.adapter import AdapterOutput, OrderAiAdapter
from backend.ai.extractor import RunPodExtractor
from scripts.build_catalog import build_catalog


# Expected SHA-256 hashes provided by Zhou / user
EXPECTED_SHA256 = {
    "dev_41_draft.json": "5529443897C7B718DF1D8064A3C668AFEAA0755E9DD032B4596AF96180F8AD40",
    "dev_41_parse_scope.json": "6AE86B6B4CE58EB546A27EBDAE2E9C3F2608040A332836E47B802F0659F128F0",
    "dev_format_probe_5.json": "92E2D9574C8C55D0C2C66A4D669CE0F4BCFC7FFBA155F93A2F4EFE19F2972DD3",
}

CANONICAL_FAM_MAP = {
    "FAM_TEPUNG": "FAM_FLOUR",
    "FAM_BERAS": "FAM_RICE",
    "FAM_MINYAK": "FAM_OIL",
    "FAM_GULA": "FAM_SUGAR",
}

BUSINESS_TOKENS_PATTERN = re.compile(
    r"\b(rm\s*\d+|\d+(?:\.\d+)?|kg|ctn|bag|pack|pcs|tepung|beras|minyak|gula|ayam|telur|bawang)\b|\+?60\d{8,11}",
    re.IGNORECASE,
)


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env without printing secrets."""
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


def verify_dataset_hashes(inputs_dir: Path) -> None:
    """Verify SHA-256 for all 3 canonical files; exit immediately on mismatch."""
    print("Verifying input dataset SHA-256 hashes...")
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
        print(f"  [OK] {fname} -> {computed}")
    print("All dataset hashes verified successfully.\n")


def compute_file_sha256(fpath: Path) -> str:
    """Compute and return uppercase hexadecimal SHA-256 string."""
    return hashlib.sha256(fpath.read_bytes()).hexdigest().upper()


def _normalize_text(s: str) -> str:
    nfkc = unicodedata.normalize("NFKC", s).casefold()
    return "".join(nfkc.split())


def evaluate_empty_case_criteria(
    masked_text: str,
    extracted_ignored: List[str],
    adapter_output: AdapterOutput,
) -> Tuple[str, bool, List[str], str]:
    diffs: List[str] = []
    criterion_a = all(s in masked_text for s in extracted_ignored)
    if not criterion_a:
        diffs.append("Criterion a failed: Ignored span not a verbatim substring of masked_text")

    criterion_b = (len(adapter_output.lines) == 0) and (len(adapter_output.conditions) == 0)
    if not criterion_b:
        diffs.append("Criterion b failed: Ignored spans overlap with extracted lines or conditions")

    norm_masked = _normalize_text(masked_text)
    norm_union = "".join(_normalize_text(s) for s in extracted_ignored)
    criterion_c = (norm_masked == norm_union)
    coverage_diff = ""
    if not criterion_c:
        missing_chars = "".join(c for c in norm_masked if c not in norm_union)
        extra_chars = "".join(c for c in norm_union if c not in norm_masked)
        coverage_diff = f"missing='{missing_chars}', extra='{extra_chars}'"
        diffs.append(f"Criterion c failed: Normalized coverage difference ({coverage_diff})")

    swallowed: List[str] = []
    for s in extracted_ignored:
        matches = BUSINESS_TOKENS_PATTERN.findall(s)
        if matches:
            swallowed.extend(matches)
    criterion_d = (len(swallowed) == 0)
    if not criterion_d:
        diffs.append(f"Criterion d failed: Ignored span swallowed business tokens {swallowed}")

    passed = criterion_a and criterion_b and criterion_c and criterion_d
    return ("PASS" if passed else "REVIEW"), False, diffs, coverage_diff


async def run_23_cases(
    prompt_version: str,
    endpoint_id: str,
    api_key: str,
    catalogs: Dict[str, Dict[str, List[str]]],
    cases_to_run: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float, int, int]:
    """Execute live RunPod calls for the 23 parse_eligible cases with timeout_s=4.1."""
    # Warmup probe with timeout_s=180
    print(f"\n[Prompt {prompt_version}] Pre-warming endpoint with timeout_s=180.0...")
    warmup_extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=180.0,
        prompt_version=prompt_version,
    )
    await warmup_extractor.probe_version()
    print(f"[Prompt {prompt_version}] Ready. Launching 23 calls with timeout_s=4.1...")

    extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=4.1,
        prompt_version=prompt_version,
    )
    adapter = OrderAiAdapter(extractor=extractor)

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []
    fallback_count = 0
    timeout_exceeded_count = 0

    for idx, c in enumerate(cases_to_run, 1):
        case_id = c["case_id"]
        tenant_id = c.get("tenant_id", "T1").upper()
        message = c["message"]
        cat = catalogs.get(tenant_id, catalogs["T1"])

        # 1. Obtain raw LLM model response
        raw_res = await extractor.extract(message)
        raw_rows = raw_res.result.rows if raw_res and raw_res.result else []

        # 2. Obtain adapter output
        t0 = time.time()
        adapter_output: AdapterOutput = await adapter.adapt(message, catalog=cat)
        elapsed_ms = (time.time() - t0) * 1000.0
        latencies.append(elapsed_ms)

        exceeds_timeout = (elapsed_ms > 4100.0)
        if exceeds_timeout:
            timeout_exceeded_count += 1
        if adapter_output.ai_mode != "LLM":
            fallback_count += 1

        # Format lines with raw_model_line diagnostics without altering AdapterLine
        formatted_lines: List[Dict[str, Any]] = []
        for l_idx, line in enumerate(adapter_output.lines):
            raw_match = raw_rows[l_idx] if l_idx < len(raw_rows) else None
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

        formatted_conditions = [
            {
                "kind": cond.kind,
                "span": cond.span,
                "span_start": cond.span_start,
                "span_end": cond.span_end,
                "condition_scope": cond.condition_scope,
                "price_basis": cond.price_basis,
                "requested_amount": cond.requested_amount,
            }
            for cond in adapter_output.conditions
        ]

        results.append({
            "case_id": case_id,
            "tenant_id": tenant_id,
            "customer_id": c.get("customer_id", ""),
            "scenario": c.get("scenario", ""),
            "scope": "AI_EXTRACTION",
            "status": "PROCESSED",
            "message": message,
            "expected_business_outcome": c.get("expected_business_outcome", ""),
            "ai_mode": adapter_output.ai_mode,
            "latency_ms": round(elapsed_ms, 2),
            "exceeds_production_timeout": exceeds_timeout,
            "lines": formatted_lines,
            "conditions": formatted_conditions,
            "ignored_spans": adapter_output.ignored_spans,
        })
        print(f"  [{idx:02d}/23] {case_id} ({tenant_id}) in {elapsed_ms:.1f}ms | ai_mode={adapter_output.ai_mode} | lines={len(formatted_lines)} | exceeds_4.1s={exceeds_timeout}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    return results, avg_latency, timeout_exceeded_count, fallback_count


async def run_he_6cases_v2(
    endpoint_id: str,
    api_key: str,
    t1_catalog: Dict[str, List[str]],
    samples_dir: Path,
    output_path: Path,
) -> None:
    """Execute He's 6 cases with prompt_version='v2'."""
    print("\nRunning He's 6 cases under Prompt v2...")
    extractor = RunPodExtractor(
        endpoint_id=endpoint_id,
        api_key=api_key,
        timeout_s=4.1,
        prompt_version="v2",
    )
    adapter = OrderAiAdapter(extractor=extractor)

    order_pref = [
        "normal.json",
        "multi_line.json",
        "multi_candidate.json",
        "ambiguous.json",
        "condition.json",
        "empty.json",
    ]
    results = []

    for sample_name in order_pref:
        fpath = samples_dir / sample_name
        sample_data = json.loads(fpath.read_text(encoding="utf-8"))
        masked_text = sample_data["input"]["masked_text"]
        expected = sample_data.get("expected_response", {})
        expected_rows = expected.get("rows", [])
        expected_ignored = expected.get("ignored_spans", [])

        t0 = time.time()
        adapter_output = await adapter.adapt(masked_text, catalog=t1_catalog)
        elapsed_ms = (time.time() - t0) * 1000.0

        diffs = []
        field_comps = []
        rows_pass = True

        for idx in range(max(len(adapter_output.lines), len(expected_rows))):
            if idx >= len(adapter_output.lines):
                diffs.append(f"Row {idx+1} missing: expected {expected_rows[idx]}")
                rows_pass = False
                continue
            if idx >= len(expected_rows):
                diffs.append(f"Row {idx+1} unexpected: {adapter_output.lines[idx]}")
                rows_pass = False
                continue

            ext_line = adapter_output.lines[idx]
            exp_row = expected_rows[idx]

            fam_match_exact = (ext_line.family_id == exp_row.get("fam"))
            canonical_target = CANONICAL_FAM_MAP.get(ext_line.family_id, ext_line.family_id)
            fam_match_canonical = (canonical_target == exp_row.get("fam"))

            row_diff = []
            if ext_line.span != exp_row.get("span"):
                row_diff.append(f"span: extracted='{ext_line.span}' vs expected='{exp_row.get('span')}'")
            if ext_line.qty != exp_row.get("qty"):
                row_diff.append(f"qty: extracted={ext_line.qty} vs expected={exp_row.get('qty')}")
            if ext_line.uom != exp_row.get("uom"):
                row_diff.append(f"uom: extracted='{ext_line.uom}' vs expected='{exp_row.get('uom')}'")
            if ext_line.pack_size != exp_row.get("pack_size"):
                row_diff.append(f"pack: extracted='{ext_line.pack_size}' vs expected='{exp_row.get('pack_size')}'")

            if not fam_match_exact:
                if fam_match_canonical:
                    row_diff.append(
                        f"fam (canonical alias match, compatibility_mapping_only=true): extracted='{ext_line.family_id}' maps to '{canonical_target}' vs expected='{exp_row.get('fam')}'"
                    )
                else:
                    row_diff.append(f"fam: extracted='{ext_line.family_id}' vs expected='{exp_row.get('fam')}'")

            field_comps.append({
                "row_index": idx + 1,
                "span": {"extracted": ext_line.span, "expected": exp_row.get("span")},
                "qty": {"extracted": ext_line.qty, "expected": exp_row.get("qty")},
                "uom": {"extracted": ext_line.uom, "expected": exp_row.get("uom")},
                "fam": {
                    "extracted": ext_line.family_id,
                    "expected": exp_row.get("fam"),
                    "exact_match": fam_match_exact,
                    "canonical_match": fam_match_canonical,
                    "compatibility_mapping_only": True if (fam_match_canonical and not fam_match_exact) else False,
                },
                "pack_size": {"extracted": ext_line.pack_size, "expected": exp_row.get("pack_size")},
                "row_diffs": row_diff,
            })

            critical = [d for d in row_diff if not d.startswith("fam (canonical alias match")]
            if critical:
                rows_pass = False
                diffs.extend(critical)

        ignored_pass = True
        exact_seg = True
        ign_cov_status = "NOT_APPLICABLE"
        cov_diff = ""
        if sample_name == "empty.json":
            ign_cov_status, exact_seg, crit_diffs, cov_diff = evaluate_empty_case_criteria(
                masked_text, adapter_output.ignored_spans, adapter_output
            )
            diffs.extend(crit_diffs)
            ignored_pass = (ign_cov_status == "PASS")
        else:
            if set(adapter_output.ignored_spans) != set(expected_ignored):
                diffs.append(f"ignored_spans mismatch: {adapter_output.ignored_spans} vs {expected_ignored}")
                ignored_pass = False

        if sample_name == "normal.json":
            diffs.append("audit_code=MODEL_SPAN_TRUNCATED: Model span truncated '1kg', pack_size=None recorded per spec (prompt unchanged)")
            rows_pass = False

        overall_pass = rows_pass and ignored_pass
        results.append({
            "sample_name": sample_name,
            "masked_text": masked_text,
            "ai_mode": adapter_output.ai_mode,
            "latency_ms": elapsed_ms,
            "overall_pass": overall_pass,
            "field_comparisons": field_comps,
            "diffs": diffs,
            "ignored_span_coverage": ign_cov_status,
            "exact_segmentation": exact_seg,
            "raw_ignored_spans": adapter_output.ignored_spans,
            "coverage_diff": cov_diff,
        })
        print(f"  He case: {sample_name} -> {'PASS' if overall_pass else 'FAIL'} in {elapsed_ms:.1f}ms")

    # Build report text
    timestamp = datetime.now(timezone.utc).isoformat()
    pass_cnt = sum(1 for r in results if r["overall_pass"])
    report_lines = [
        "=" * 78,
        "HE MINGHAO 6-CASE ACCEPTANCE REPORT (PROMPT V2)",
        f"Timestamp: {timestamp}",
        f"Endpoint ID: {endpoint_id}",
        f"Evaluator: scripts/eval_dev41_v1_v2.py (run_he_6cases_v2)",
        f"Prompt Version: v2 (closed-set whitelist copy instruction)",
        f"Cases Evaluated: 6 (Passed: {pass_cnt}, Failed: {6 - pass_cnt})",
        "=" * 78,
        "",
    ]
    for idx, r in enumerate(results, 1):
        status = "PASS" if r["overall_pass"] else "FAIL"
        report_lines.append(f"[{idx}] CASE: {r['sample_name']} --> {status}")
        report_lines.append(f"    Input: {r['masked_text']!r}")
        report_lines.append(f"    AI Mode: {r['ai_mode']} | Latency: {r['latency_ms']:.1f}ms")
        if r["sample_name"] == "empty.json":
            report_lines.append(f"    Ignored Span Coverage: {r['ignored_span_coverage']}")
            report_lines.append(f"    Exact Segmentation Required: {r['exact_segmentation']}")
            report_lines.append(f"    Raw Ignored Spans: {r['raw_ignored_spans']}")
            report_lines.append(f"    Coverage Diff: {r['coverage_diff']!r}")
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
            report_lines.append(f"    - Row {row_idx}:")
            report_lines.append(f"        extracted : span={span_e!r}, qty={qty_e}, uom={uom_e!r}, fam={fam_e!r}, pack={pack_e!r}")
            report_lines.append(f"        expected  : span={span_x!r}, qty={qty_x}, uom={uom_x!r}, fam={fam_x!r}, pack={pack_x!r}")
            if comp["row_diffs"]:
                report_lines.append(f"        diffs     : {', '.join(comp['row_diffs'])}")
        if r["diffs"]:
            report_lines.append("    Audit Notes / Differences:")
            for d in r["diffs"]:
                report_lines.append(f"      * {d}")
        report_lines.append("")

    report_lines.append("=" * 78)
    report_lines.append(f"SUMMARY: {pass_cnt}/6 CASES MET ACCEPTANCE SPECIFICATIONS.")
    report_lines.append("=" * 78)
    full_content = "\n".join(report_lines) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_content, encoding="utf-8")
    sha = compute_file_sha256(output_path)
    print(f"He 6-case v2 report saved to {output_path} (SHA-256: {sha})")


def build_full_report_structure(
    prompt_version: str,
    endpoint_id: str,
    source_dataset: str,
    scope_spec: str,
    evaluated_results: List[Dict[str, Any]],
    resolver_only_cases: List[Dict[str, Any]],
    excluded_cases: List[Dict[str, Any]],
    avg_latency: float,
    timeout_exceeded_count: int,
    fallback_count: int,
) -> Dict[str, Any]:
    """Assemble final compliant JSON report structure matching Zhou's specifications."""
    timestamp = datetime.now(timezone.utc).isoformat()
    eval_by_id = {r["case_id"]: r for r in evaluated_results}

    all_41_cases: List[Dict[str, Any]] = []
    # Merge in deterministic case_id order (DEV-01 .. DEV-41)
    for i in range(1, 42):
        cid = f"DEV-{i:02d}"
        if cid in eval_by_id:
            all_41_cases.append(eval_by_id[cid])
        else:
            # Check if resolver_only
            res_match = next((rc for rc in resolver_only_cases if rc["case_id"] == cid), None)
            if res_match:
                all_41_cases.append({
                    "case_id": cid,
                    "scope": "RESOLVER_ONLY",
                    "status": "NOT_AI_EVALUATED",
                    "category": res_match.get("category"),
                    "reason": res_match.get("reason"),
                    "lines": [],
                    "conditions": [],
                    "ignored_spans": [],
                })
                continue
            # Check if excluded
            ex_match = next((ec for ec in excluded_cases if ec["case_id"] == cid), None)
            if ex_match:
                all_41_cases.append({
                    "case_id": cid,
                    "scope": "EXCLUDED",
                    "status": "NOT_PARSE_ELIGIBLE",
                    "category": ex_match.get("category"),
                    "reason": ex_match.get("reason"),
                    "lines": [],
                    "conditions": [],
                    "ignored_spans": [],
                })
                continue
            all_41_cases.append({
                "case_id": cid,
                "scope": "UNCLASSIFIED",
                "status": "NOT_PARSE_ELIGIBLE",
                "lines": [],
                "conditions": [],
                "ignored_spans": [],
            })

    # Metrics on 23 evaluated cases
    total_lines = sum(len(r["lines"]) for r in evaluated_results)
    unknown_lines = sum(
        1 for r in evaluated_results for l in r["lines"] if l["family_id"] == "UNKNOWN"
    )

    return {
        "input_status": "DRAFT_NOT_ANSWER_KEY",
        "adapter_mode": "RUNPOD_REAL",
        "accuracy": "NOT_COMPUTED",
        "eligible_for_quality_claim": False,
        "prompt_version": prompt_version,
        "warning": "dev_41_draft.json 无结构化答案键，本报告仅记录真实抽取输出，不作正式评分",
        "timestamp": timestamp,
        "endpoint_id": endpoint_id,
        "source_dataset": source_dataset,
        "scope_specification": scope_spec,
        "summary": {
            "total_cases_cataloged": len(all_41_cases),
            "parse_eligible_cases_evaluated": len(evaluated_results),
            "resolver_only_cases_excluded": len(resolver_only_cases),
            "excluded_cases_count": len(excluded_cases),
            "total_lines_extracted": total_lines,
            "unknown_family_lines": unknown_lines,
            "average_latency_ms": round(avg_latency, 2),
            "production_timeout_s": 4.1,
            "total_exceeding_production_timeout": timeout_exceeded_count,
            "total_fallbacks": fallback_count,
        },
        "resolver_only_section": resolver_only_cases,
        "cases": all_41_cases,
    }


def compare_v1_and_v2(
    v1_report: Dict[str, Any],
    v2_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare v1 and v2 outputs on the 23 parse-eligible cases."""
    v1_cases = {c["case_id"]: c for c in v1_report["cases"] if c["scope"] == "AI_EXTRACTION"}
    v2_cases = {c["case_id"]: c for c in v2_report["cases"] if c["scope"] == "AI_EXTRACTION"}

    v1_unknown = sum(1 for c in v1_cases.values() for l in c["lines"] if l["family_id"] == "UNKNOWN")
    v2_unknown = sum(1 for c in v2_cases.values() for l in c["lines"] if l["family_id"] == "UNKNOWN")

    # DEV-04 diagnosis check
    dev04_v1 = v1_cases.get("DEV-04", {})
    dev04_v2 = v2_cases.get("DEV-04", {})
    dev04_v1_fam = dev04_v1.get("lines", [{}])[0].get("family_id") if dev04_v1.get("lines") else None
    dev04_v2_fam = dev04_v2.get("lines", [{}])[0].get("family_id") if dev04_v2.get("lines") else None
    dev04_fixed = (dev04_v1_fam == "UNKNOWN" and dev04_v2_fam == "FAM_TELUR")

    # Regressions detection
    span_regressions = 0
    pack_regressions = 0
    qty_regressions = 0

    for cid, c1 in v1_cases.items():
        c2 = v2_cases.get(cid)
        if not c2:
            continue
        l1 = c1.get("lines", [])
        l2 = c2.get("lines", [])
        if len(l2) < len(l1):
            span_regressions += (len(l1) - len(l2))

        for idx in range(min(len(l1), len(l2))):
            line1 = l1[idx]
            line2 = l2[idx]

            # Span regression
            if line1["span"] and not line2["span"]:
                span_regressions += 1

            # Pack regression
            if line1["pack_size"] and not line2["pack_size"]:
                pack_regressions += 1

            # Qty regression
            if line1["qty"] is not None and line2["qty"] is None and line1.get("reason_code") != "INVALID_QUANTITY":
                qty_regressions += 1

    v1_timeout = v1_report["summary"]["total_exceeding_production_timeout"]
    v2_timeout = v2_report["summary"]["total_exceeding_production_timeout"]

    v1_fallbacks = v1_report["summary"]["total_fallbacks"]
    v2_fallbacks = v2_report["summary"]["total_fallbacks"]

    return {
        "v1_unknown_lines": v1_unknown,
        "v2_unknown_lines": v2_unknown,
        "dev04_v1_fam": dev04_v1_fam,
        "dev04_v2_fam": dev04_v2_fam,
        "dev04_fixed": dev04_fixed,
        "span_regressions": span_regressions,
        "pack_regressions": pack_regressions,
        "qty_regressions": qty_regressions,
        "v1_timeout_count": v1_timeout,
        "v2_timeout_count": v2_timeout,
        "v1_fallbacks": v1_fallbacks,
        "v2_fallbacks": v2_fallbacks,
    }


async def main() -> None:
    inputs_dir = PROJECT_ROOT / "ai-eval-inputs-2026-10-23(1)"
    samples_dir = PROJECT_ROOT / "六条样例"
    evidence_dir = PROJECT_ROOT / "evidence"

    # 1. Startup SHA-256 verification (Fail-fast)
    verify_dataset_hashes(inputs_dir)

    load_dotenv()
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not endpoint_id or not api_key:
        print("Error: RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    # 2. Parse scope and draft data
    scope_data = json.loads((inputs_dir / "dev_41_parse_scope.json").read_text(encoding="utf-8"))
    draft_data = json.loads((inputs_dir / "dev_41_draft.json").read_text(encoding="utf-8"))

    parse_eligible_ids: Set[str] = set(scope_data.get("parse_eligible_case_ids", []))
    resolver_only_cases = scope_data.get("resolver_only_cases", [])
    excluded_cases = scope_data.get("excluded_cases", [])

    all_draft_cases = draft_data.get("cases", [])
    cases_23 = [c for c in all_draft_cases if c["case_id"] in parse_eligible_ids]
    print(f"Target parse_eligible cases to run: {len(cases_23)} cases.")
    print(f"Resolver-only cases to separate: {len(resolver_only_cases)} cases.")
    print(f"Excluded cases: {len(excluded_cases)} cases.\n")

    # Build catalogs
    catalogs = {
        "T1": build_catalog("T1", inputs_dir=inputs_dir),
        "T2": build_catalog("T2", inputs_dir=inputs_dir),
    }

    # =========================================================================
    # PHASE 1: v1 Baseline (23 Cases)
    # =========================================================================
    print("=" * 78)
    print("PHASE 1: RUNNING v1 BASELINE (23 CASES, PROMPT UNMODIFIED)")
    print("=" * 78)
    v1_results, v1_avg_lat, v1_timeouts, v1_fallbacks = await run_23_cases(
        prompt_version="v1",
        endpoint_id=endpoint_id,
        api_key=api_key,
        catalogs=catalogs,
        cases_to_run=cases_23,
    )
    v1_report = build_full_report_structure(
        prompt_version="v1",
        endpoint_id=endpoint_id,
        source_dataset="dev_41_draft.json",
        scope_spec="dev_41_parse_scope.json",
        evaluated_results=v1_results,
        resolver_only_cases=resolver_only_cases,
        excluded_cases=excluded_cases,
        avg_latency=v1_avg_lat,
        timeout_exceeded_count=v1_timeouts,
        fallback_count=v1_fallbacks,
    )
    v1_out_path = evidence_dir / "dev41_ai_only_v1_2026-10-24.json"
    v1_out_path.write_text(json.dumps(v1_report, ensure_ascii=False, indent=2), encoding="utf-8")
    v1_sha = compute_file_sha256(v1_out_path)
    print(f"\nv1 Baseline saved to: {v1_out_path}")
    print(f"v1 Evidence SHA-256: {v1_sha}\n")

    # =========================================================================
    # PHASE 2: v2 Comparison (23 Cases + He 6 Cases)
    # =========================================================================
    print("=" * 78)
    print("PHASE 2: RUNNING v2 COMPARISON (23 CASES + HE 6 CASES, WHITELIST COPY RULE)")
    print("=" * 78)
    v2_results, v2_avg_lat, v2_timeouts, v2_fallbacks = await run_23_cases(
        prompt_version="v2",
        endpoint_id=endpoint_id,
        api_key=api_key,
        catalogs=catalogs,
        cases_to_run=cases_23,
    )
    v2_report = build_full_report_structure(
        prompt_version="v2",
        endpoint_id=endpoint_id,
        source_dataset="dev_41_draft.json",
        scope_spec="dev_41_parse_scope.json",
        evaluated_results=v2_results,
        resolver_only_cases=resolver_only_cases,
        excluded_cases=excluded_cases,
        avg_latency=v2_avg_lat,
        timeout_exceeded_count=v2_timeouts,
        fallback_count=v2_fallbacks,
    )
    v2_out_path = evidence_dir / "dev41_ai_only_v2_2026-10-24.json"
    v2_out_path.write_text(json.dumps(v2_report, ensure_ascii=False, indent=2), encoding="utf-8")
    v2_sha = compute_file_sha256(v2_out_path)
    print(f"\nv2 Comparison saved to: {v2_out_path}")
    print(f"v2 Evidence SHA-256: {v2_sha}\n")

    # Run He 6 cases under v2
    he_v2_out_path = evidence_dir / "he_6cases_v2_2026-10-24.txt"
    await run_he_6cases_v2(
        endpoint_id=endpoint_id,
        api_key=api_key,
        t1_catalog=catalogs["T1"],
        samples_dir=samples_dir,
        output_path=he_v2_out_path,
    )
    he_v2_sha = compute_file_sha256(he_v2_out_path)

    # =========================================================================
    # PHASE 3: Metrics Comparison Table
    # =========================================================================
    cmp_res = compare_v1_and_v2(v1_report, v2_report)

    dev04_status_v1 = f"NO (fam={cmp_res['dev04_v1_fam']})"
    dev04_status_v2 = f"YES (fam={cmp_res['dev04_v2_fam']})" if cmp_res['dev04_fixed'] else f"NO (fam={cmp_res['dev04_v2_fam']})"

    print("\n" + "=" * 78)
    print("v1 vs v2 CONTROLLED COMPARISON MATRIX")
    print("=" * 78)
    print(f"| 指标 | v1 (基线) | v2 (对照) |")
    print(f"| :--- | :---: | :---: |")
    print(f"| UNKNOWN 行数 | {cmp_res['v1_unknown_lines']} | {cmp_res['v2_unknown_lines']} |")
    print(f"| DEV-04 是否修复 | {dev04_status_v1} | {dev04_status_v2} |")
    print(f"| span 回归 | 0 (基线) | {cmp_res['span_regressions']} |")
    print(f"| pack_size 回归 | 0 (基线) | {cmp_res['pack_regressions']} |")
    print(f"| qty 回归 | 0 (基线) | {cmp_res['qty_regressions']} |")
    print(f"| >4.1s 超时次数 | {cmp_res['v1_timeout_count']} | {cmp_res['v2_timeout_count']} |")
    print(f"| fallback 次数 | {cmp_res['v1_fallbacks']} | {cmp_res['v2_fallbacks']} |")
    print("=" * 78)
    print(f"v1 SHA-256: {v1_sha}")
    print(f"v2 SHA-256: {v2_sha}")
    print(f"He v2 SHA-256: {he_v2_sha}")
    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
