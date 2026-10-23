"""Run the six canonical AI contract samples through the in-process adapter.

This is a manual evidence tool, not a CI test. It reads the RunPod credentials
from ``.env`` through ``Settings`` and never prints the API key.

Usage (from ``backend/``)::

    python -m tools.run_ai_samples

    python -m tools.run_ai_samples --tenant T1 \
        --sample-dir ../docs/ai_contract/samples \
        --out ../evidence/ai-samples

Exit code is 0 only when all six samples return ``ai_mode=LLM`` with no errors.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.ai.adapter import OrderAiAdapter
from app.ai.catalog import load_family_catalog
from app.ai.extractor import RunPodExtractor
from app.config import REPO_ROOT, Settings
from app.db import connect

SAMPLE_NAMES = (
    "normal",
    "ambiguous",
    "condition",
    "empty",
    "multi_candidate",
    "multi_line",
)


def load_samples(sample_dir: Path) -> list[dict[str, Any]]:
    """Load exactly the six canonical samples, in fixed order."""
    samples: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in SAMPLE_NAMES:
        path = sample_dir / f"{name}.json"
        if not path.is_file():
            missing.append(str(path))
            continue
        sample = json.loads(path.read_text(encoding="utf-8"))
        sample["_sample_name"] = name
        samples.append(sample)
    if missing:
        raise FileNotFoundError("missing sample files: " + ", ".join(missing))
    return samples


async def run_samples(
    adapter: OrderAiAdapter,
    samples: Sequence[dict[str, Any]],
    catalog: dict[str, Sequence[str]],
) -> list[dict[str, Any]]:
    """Run all samples and capture actual output plus expected fixture."""
    results: list[dict[str, Any]] = []
    for sample in samples:
        input_data = sample["input"]
        started = time.perf_counter()
        try:
            output = await adapter.adapt(input_data["masked_text"], catalog)
            actual: dict[str, Any] | None = asdict(output)
            error: str | None = None
        except Exception as exc:  # evidence must record a failed sample, not abort all six
            actual = None
            error = f"{type(exc).__name__}: {exc}"
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        results.append(
            {
                "sample": sample.get("_sample_name"),
                "request_id": input_data.get("request_id"),
                "masked_text": input_data["masked_text"],
                "expected": sample.get("expected_response"),
                "actual": actual,
                "elapsed_ms": elapsed_ms,
                "error": error,
            }
        )
    return results


def summarize(results: Sequence[dict[str, Any]]) -> dict[str, int]:
    modes = [
        result["actual"]["ai_mode"]
        for result in results
        if result["actual"] is not None and result["error"] is None
    ]
    return {
        "total": len(results),
        "llm": modes.count("LLM"),
        "fallback": modes.count("FALLBACK"),
        "mixed": modes.count("MIXED"),
        "alias_only": modes.count("ALIAS_ONLY"),
        "errors": sum(1 for result in results if result["error"] is not None),
    }


def write_evidence(
    out_dir: Path,
    tenant: str,
    catalog: dict[str, Sequence[str]],
    results: Sequence[dict[str, Any]],
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"run-{generated}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tenant": tenant,
        "catalog_family_count": len(catalog),
        "summary": summarize(results),
        "samples": list(results),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="T1")
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "ai_contract" / "samples",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "evidence" / "ai-samples",
    )
    args = parser.parse_args(argv)

    settings = Settings()
    if settings.runpod_api_key is None or not settings.runpod_endpoint_id:
        print("ERROR: RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID are required")
        return 2

    samples = load_samples(args.sample_dir)
    with connect(settings) as conn:
        catalog = load_family_catalog(conn, args.tenant)
    if not catalog:
        print(f"ERROR: no family catalog for tenant {args.tenant}")
        return 2

    extractor = RunPodExtractor(
        api_key=settings.runpod_api_key.get_secret_value(),
        endpoint_id=settings.runpod_endpoint_id,
        timeout_s=settings.llm_timeout_s,
        model_name=settings.runpod_model_name,
    )
    adapter = OrderAiAdapter(extractor=extractor)
    results = asyncio.run(run_samples(adapter, samples, catalog))
    summary = summarize(results)
    evidence_path = write_evidence(args.out, args.tenant, catalog, results)

    print(f"evidence={evidence_path}")
    for result in results:
        actual = result["actual"] or {}
        print(
            f"{result['sample']} ai_mode={actual.get('ai_mode', 'ERROR')} "
            f"lines={len(actual.get('lines', []))} "
            f"conditions={len(actual.get('conditions', []))} "
            f"ignored_spans={len(actual.get('ignored_spans', []))} "
            f"elapsed_ms={result['elapsed_ms']}"
        )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["errors"] == 0 and summary["llm"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
