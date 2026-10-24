# 非 canonical，仅回归用（待数据岗 Zhou 提供官方 dev_41.json 后通过 --dataset 参数替换）
"""AI Extraction Quality Evaluation Script for KiraOrder.

Evaluates OrderAiAdapter on end-to-end extraction quality using real RunPod Serverless LLM.
Computes:
- family_accuracy: Proportion of lines where extracted family_id matches ground truth.
- qty_accuracy: Proportion of lines where extracted quantity exactly matches ground truth.
- pack_size_accuracy: Proportion of lines where extracted pack_size matches ground truth.
- blocking_accuracy: Proportion of invalid lines (e.g. decimal, zero) correctly blocked with qty=None.
- false_blocking_rate: Proportion of valid lines mistakenly blocked with qty=None.

Outputs structured evaluation metrics to evidence/eval_dev_2026-10-23.json.
Exits with non-zero status if any degradation or failure occurs.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

# Project root setup
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
_backend_dir = PROJECT_ROOT / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.ai.adapter import AdapterOutput, OrderAiAdapter
from app.ai.extractor import RunPodExtractor

# ---------------------------------------------------------------------------
# Default Evaluation Catalog
# ---------------------------------------------------------------------------

DEFAULT_CATALOG: Dict[str, Sequence[str]] = {
    "FAM_FLOUR": ["tepung", "flour", "面粉", "tepung gandum"],
    "FAM_RICE": ["beras", "rice", "米", "beras wangi", "大米"],
    "FAM_OIL": ["minyak", "oil", "油", "minyak masak"],
    "FAM_SUGAR": ["gula", "sugar", "糖", "gula pasir", "白糖"],
}

# ---------------------------------------------------------------------------
# Built-in Regression Dataset (17 Multi-lingual Cases: MS / EN / ZH / Mixed)
# ---------------------------------------------------------------------------

BUILTIN_DATASET: List[Dict[str, Any]] = [
    {
        "id": "case_01_single_line_flour",
        "language": "ms",
        "text": "Tepung 5 ctn",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 5, "uom": "ctn", "pack_size": None, "blocked": False}
        ],
    },
    {
        "id": "case_02_multi_line_rice_oil",
        "language": "ms",
        "text": "Beras 10 bag\nMinyak 2 ctn",
        "expected_lines": [
            {"family_id": "FAM_RICE", "qty": 10, "uom": "bag", "pack_size": None, "blocked": False},
            {"family_id": "FAM_OIL", "qty": 2, "uom": "ctn", "pack_size": None, "blocked": False},
        ],
    },
    {
        "id": "case_03_comma_decimal_blocking",
        "language": "ms",
        "text": "Gula 1,5kg",
        "expected_lines": [
            {"family_id": "FAM_SUGAR", "qty": None, "uom": "kg", "pack_size": None, "blocked": True, "reason_code": "INVALID_QUANTITY"}
        ],
    },
    {
        "id": "case_04_dot_decimal_blocking",
        "language": "en",
        "text": "Tepung 5.5 ctn",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": None, "uom": "ctn", "pack_size": None, "blocked": True, "reason_code": "INVALID_QUANTITY"}
        ],
    },
    {
        "id": "case_05_fuzzy_alias_oil",
        "language": "ms",
        "text": "minyak masak 3 ctn",
        "expected_lines": [
            {"family_id": "FAM_OIL", "qty": 3, "uom": "ctn", "pack_size": None, "blocked": False}
        ],
    },
    {
        "id": "case_06_compound_pack_size_flour",
        "language": "en",
        "text": "Flour 10 ctn 1kg",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 10, "uom": "ctn", "pack_size": "1kg", "blocked": False}
        ],
    },
    {
        "id": "case_07_chinese_order_flour_rice",
        "language": "zh",
        "text": "5 箱面粉\n2 袋大米",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 5, "uom": "箱", "pack_size": None, "blocked": False},
            {"family_id": "FAM_RICE", "qty": 2, "uom": "袋", "pack_size": None, "blocked": False},
        ],
    },
    {
        "id": "case_08_mixed_notes_rice",
        "language": "mixed",
        "text": "Beras Wangi 10 ctn, send tomorrow",
        "expected_lines": [
            {"family_id": "FAM_RICE", "qty": 10, "uom": "ctn", "pack_size": None, "blocked": False}
        ],
    },
    {
        "id": "case_09_h5_price_condition_flour",
        "language": "mixed",
        "text": "Tepung 5 ctn, kalau RM95 boleh?",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 5, "uom": "ctn", "pack_size": None, "blocked": False}
        ],
        "expected_conditions": [{"kind": "PRICE"}],
    },
    {
        "id": "case_10_compound_pack_spec_flour",
        "language": "ms",
        "text": "Tepung 5kg x 2",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 2, "uom": "kg", "pack_size": "5kg", "blocked": False}
        ],
    },
    {
        "id": "case_11_zero_qty_blocking",
        "language": "ms",
        "text": "Gula 0 ctn",
        "expected_lines": [
            {"family_id": "FAM_SUGAR", "qty": None, "uom": "ctn", "pack_size": None, "blocked": True, "reason_code": "FIELD_NOT_EVIDENCED"}
        ],
    },
    {
        "id": "case_12_word_numeral_flour",
        "language": "ms",
        "text": "Tepung lima ctn",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 5, "uom": "ctn", "pack_size": None, "blocked": False}
        ],
    },
    {
        "id": "case_13_chinese_sugar",
        "language": "zh",
        "text": "白糖 3 箱",
        "expected_lines": [
            {"family_id": "FAM_SUGAR", "qty": 3, "uom": "箱", "pack_size": None, "blocked": False}
        ],
    },
    {
        "id": "case_14_numbered_list_flour_sugar",
        "language": "ms",
        "text": "1. Tepung 5kg Grade A, 2 ctn\n2. Gula 5 ctn",
        "expected_lines": [
            {"family_id": "FAM_FLOUR", "qty": 2, "uom": "ctn", "pack_size": "5kg", "blocked": False},
            {"family_id": "FAM_SUGAR", "qty": 5, "uom": "ctn", "pack_size": None, "blocked": False},
        ],
    },
    {
        "id": "case_15_allocation_condition_sugar",
        "language": "ms",
        "text": "Gula pasir 3 ctn, RM50 untuk semua",
        "expected_lines": [
            {"family_id": "FAM_SUGAR", "qty": 3, "uom": "ctn", "pack_size": None, "blocked": False}
        ],
        "expected_conditions": [{"kind": "PRICE"}],
    },
    {
        "id": "case_16_dot_decimal_rice_blocking",
        "language": "ms",
        "text": "Beras 5.5 ctn",
        "expected_lines": [
            {"family_id": "FAM_RICE", "qty": None, "uom": "ctn", "pack_size": None, "blocked": True, "reason_code": "INVALID_QUANTITY"}
        ],
    },
    {
        "id": "case_17_decimal_pack_size_oil",
        "language": "ms",
        "text": "Minyak 12 x 1.5L, 5 ctn",
        "expected_lines": [
            {"family_id": "FAM_OIL", "qty": 5, "uom": "ctn", "pack_size": "12 x 1.5L", "blocked": False}
        ],
    },
]


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load .env file into environment."""
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
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as err:
        print(f"Warning: Failed loading {env_path}: {err}", file=sys.stderr)


async def evaluate_dataset(
    dataset: List[Dict[str, Any]],
    catalog: Dict[str, Sequence[str]],
    extractor: RunPodExtractor,
) -> Dict[str, Any]:
    """Run extraction across dataset and compute comprehensive accuracy metrics."""
    adapter = OrderAiAdapter(extractor=extractor)

    total_expected_lines = 0
    total_extracted_lines = 0
    family_matches = 0
    qty_matches = 0
    pack_size_matches = 0

    total_expected_blocked = 0
    correctly_blocked = 0

    total_expected_valid = 0
    false_blocked = 0

    case_results: List[Dict[str, Any]] = []
    any_degraded = False

    for idx, case in enumerate(dataset, 1):
        case_id = case.get("id", f"case_{idx:02d}")
        text = case["text"]
        expected_lines = case.get("expected_lines", [])

        start_t = time.time()
        try:
            out: AdapterOutput = await adapter.adapt(text, catalog=catalog)
            lat_ms = (time.time() - start_t) * 1000.0
        except Exception as err:
            lat_ms = (time.time() - start_t) * 1000.0
            print(f"[{idx:02d}/{len(dataset):02d}] {case_id}: CRITICAL EXCEPTION: {err}", file=sys.stderr)
            any_degraded = True
            case_results.append({
                "case_id": case_id,
                "text": text,
                "status": "ERROR",
                "error": str(err),
                "latency_ms": lat_ms,
            })
            continue

        if out.ai_mode != "LLM":
            print(f"[{idx:02d}/{len(dataset):02d}] {case_id}: DEGRADATION DETECTED (ai_mode={out.ai_mode})", file=sys.stderr)
            any_degraded = True

        extracted_lines = out.lines
        total_expected_lines += len(expected_lines)
        total_extracted_lines += len(extracted_lines)

        case_line_evals: List[Dict[str, Any]] = []

        # Compare lines up to max count
        max_len = max(len(expected_lines), len(extracted_lines))
        for line_idx in range(max_len):
            exp_l = expected_lines[line_idx] if line_idx < len(expected_lines) else None
            ext_l = extracted_lines[line_idx] if line_idx < len(extracted_lines) else None

            fam_match = False
            qty_match = False
            pack_size_match = False
            block_match = False
            is_false_block = False

            if exp_l and ext_l:
                # Family check
                fam_match = (ext_l.family_id == exp_l["family_id"])
                if fam_match:
                    family_matches += 1

                # Pack size check
                exp_pack = exp_l.get("pack_size")
                ext_pack = ext_l.pack_size
                if exp_pack is None and ext_pack is None:
                    pack_size_match = True
                elif exp_pack is not None and ext_pack is not None:
                    pack_size_match = (exp_pack.strip().lower() == ext_pack.strip().lower())
                else:
                    pack_size_match = False

                if pack_size_match:
                    pack_size_matches += 1

                # Blocking & Quantity check
                if exp_l.get("blocked", False):
                    total_expected_blocked += 1
                    # Expected to be blocked (qty=None)
                    if ext_l.qty is None:
                        # If specific reason_code expected, check it
                        exp_reason = exp_l.get("reason_code")
                        correctly_blocked += 1
                        block_match = (exp_reason is None or ext_l.reason_code == exp_reason)
                        qty_match = True
                        qty_matches += 1
                    else:
                        qty_match = False
                else:
                    total_expected_valid += 1
                    # Expected valid quantity
                    if ext_l.qty is None:
                        false_blocked += 1
                        is_false_block = True
                        qty_match = False
                    elif ext_l.qty == exp_l.get("qty"):
                        qty_match = True
                        qty_matches += 1
                    else:
                        qty_match = False

            elif exp_l and not ext_l:
                # Missing extracted line
                if exp_l.get("blocked", False):
                    total_expected_blocked += 1
                else:
                    total_expected_valid += 1

            case_line_evals.append({
                "expected": exp_l,
                "extracted": {
                    "line_id": ext_l.line_id if ext_l else None,
                    "family_id": ext_l.family_id if ext_l else None,
                    "qty": ext_l.qty if ext_l else None,
                    "uom": ext_l.uom if ext_l else None,
                    "pack_size": ext_l.pack_size if ext_l else None,
                    "reason_code": ext_l.reason_code if ext_l else None,
                } if ext_l else None,
                "family_match": fam_match,
                "qty_match": qty_match,
                "pack_size_match": pack_size_match,
                "block_match": block_match,
                "false_blocked": is_false_block,
            })

        case_passed = all(
            l["family_match"] and l["qty_match"] and l["pack_size_match"] and not l["false_blocked"]
            for l in case_line_evals
        ) and out.ai_mode == "LLM"

        print(f"[{idx:02d}/{len(dataset):02d}] {case_id:<32} | Mode: {out.ai_mode:<8} | {'PASS' if case_passed else 'FAIL'} ({lat_ms:.1f}ms)")

        case_results.append({
            "case_id": case_id,
            "text": text,
            "ai_mode": out.ai_mode,
            "latency_ms": lat_ms,
            "status": "PASS" if case_passed else "FAIL",
            "lines": case_line_evals,
            "conditions": [
                {"kind": c.kind, "span": c.span, "requested_amount": c.requested_amount}
                for c in out.conditions
            ],
        })

    # Metric computations
    family_acc = (family_matches / total_expected_lines) if total_expected_lines > 0 else 0.0
    qty_acc = (qty_matches / total_expected_lines) if total_expected_lines > 0 else 0.0
    pack_size_acc = (pack_size_matches / total_expected_lines) if total_expected_lines > 0 else 0.0
    blocking_acc = (correctly_blocked / total_expected_blocked) if total_expected_blocked > 0 else 1.0
    false_block_rate = (false_blocked / total_expected_valid) if total_expected_valid > 0 else 0.0

    eval_summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(dataset),
        "total_expected_lines": total_expected_lines,
        "total_extracted_lines": total_extracted_lines,
        "metrics": {
            "family_accuracy": round(family_acc, 4),
            "qty_accuracy": round(qty_acc, 4),
            "pack_size_accuracy": round(pack_size_acc, 4),
            "blocking_accuracy": round(blocking_acc, 4),
            "false_blocking_rate": round(false_block_rate, 4),
        },
        "all_cases_pure_llm": not any_degraded,
        "results": case_results,
    }

    return eval_summary


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate KiraOrder AI extraction quality against test dataset.")
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to dataset JSON (e.g. dev_41.json). If omitted, built-in 16-case regression dataset is used.",
    )
    parser.add_argument("--timeout", type=float, default=180.0, help="RunPod request timeout in seconds.")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("RUNPOD_API_KEY", "").strip()
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()

    if not api_key or not endpoint_id:
        print("CRITICAL ERROR: RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set in .env", file=sys.stderr)
        return 1

    # Load dataset
    dataset_source = "builtin_dev_17 (non-canonical, regression only)"
    if args.dataset:
        ds_path = Path(args.dataset)
        if not ds_path.is_file():
            print(f"ERROR: Dataset file not found at: {ds_path}", file=sys.stderr)
            return 1
        with open(ds_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        dataset_source = str(ds_path)
    else:
        dataset = BUILTIN_DATASET

    print("=" * 72)
    print("      KiraOrder AI Extraction Quality Evaluation Suite")
    print("=" * 72)
    print(f"Dataset Source : {dataset_source}")
    print(f"Total Cases    : {len(dataset)}")
    print(f"Endpoint ID    : {endpoint_id}")
    print(f"Timeout        : {args.timeout}s")
    print("-" * 72)

    extractor = RunPodExtractor(api_key=api_key, endpoint_id=endpoint_id, timeout_s=args.timeout)
    summary = await evaluate_dataset(dataset, DEFAULT_CATALOG, extractor)
    summary["dataset_source"] = dataset_source

    metrics = summary["metrics"]
    print("-" * 72)
    print("Evaluation Results Summary:")
    print(f"  - Family Accuracy      : {metrics['family_accuracy'] * 100:.1f}%")
    print(f"  - Quantity Accuracy    : {metrics['qty_accuracy'] * 100:.1f}%")
    print(f"  - Pack Size Accuracy   : {metrics['pack_size_accuracy'] * 100:.1f}%")
    print(f"  - Blocking Accuracy    : {metrics['blocking_accuracy'] * 100:.1f}%")
    print(f"  - False Blocking Rate  : {metrics['false_blocking_rate'] * 100:.1f}%")
    print(f"  - Pure LLM (No degrade): {summary['all_cases_pure_llm']}")
    print("=" * 72)

    evidence_dir = PROJECT_ROOT / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "eval_dev_2026-10-23.json"
    evidence_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Detailed evaluation evidence written to: {evidence_file}")

    # Success criteria: family >= 0.90, qty >= 0.90, pack_size >= 0.90, blocking >= 0.90, no degradation
    is_success = (
        metrics["family_accuracy"] >= 0.90
        and metrics["qty_accuracy"] >= 0.90
        and metrics["pack_size_accuracy"] >= 0.90
        and metrics["blocking_accuracy"] >= 0.90
        and summary["all_cases_pure_llm"]
    )

    return 0 if is_success else 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
