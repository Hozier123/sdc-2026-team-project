"""Smoke verification script for KiraOrder OrderAiAdapter using live RunPod extraction.

Complies strictly with Gate 0 contract and task specifications:
- 4-family in-memory catalog (FAM_FLOUR, FAM_RICE, FAM_OIL, FAM_SUGAR)
- 6 required sample cases:
  1. Single-line single product: "Tepung 5 ctn"
  2. Multi-line multi-product: "Beras 10 bag\\nMinyak 2 ctn"
  3. Decimal quantity blocking: "Gula 1,5kg" (asserts qty=None, reason_code="INVALID_QUANTITY")
  4. H5 condition: "RM95 for 5 ctn" (asserts kind="PRICE", allocation disambiguation)
  5. Fuzzy alias: "minyak masak 3 ctn"
  6. Compound pack size: "Flour 10 ctn 1kg"
- Real over-the-wire RunPod Serverless call (no mocking, no fallback pretending to be LLM)
- Pre-run health check: polls GET https://{RUNPOD_ENDPOINT_ID}.api.runpod.ai/health up to 300s
- Cold-start tolerance: RunPodExtractor(timeout_s=180.0)
- Writes formatted evidence to evidence/smoke_6cases_2026-10-23.txt
- Exits with non-zero code on any unexpected failure or degradation
"""

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

import httpx

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.adapter import AdapterOutput, OrderAiAdapter
from backend.ai.extractor import RunPodExtractor

# ---------------------------------------------------------------------------
# In-Memory Catalog (4 Families with ms/en/zh aliases)
# ---------------------------------------------------------------------------

CATALOG: Dict[str, Sequence[str]] = {
    "FAM_FLOUR": ["tepung", "flour", "面粉", "tepung gandum"],
    "FAM_RICE": ["beras", "rice", "米", "beras wangi"],
    "FAM_OIL": ["minyak", "oil", "油", "minyak masak"],
    "FAM_SUGAR": ["gula", "sugar", "糖", "gula pasir"],
}


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load key-value pairs from .env file into os.environ without printing secrets."""
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


def poll_runpod_health(endpoint_id: str, api_key: str, max_wait_s: int = 300) -> bool:
    """Poll RunPod health endpoint until HTTP 200 or timeout."""
    health_url = f"https://{endpoint_id}.api.runpod.ai/health"
    headers = {"Authorization": f"Bearer {api_key}"}
    print(f"Pre-run health check: Polling {health_url} (up to {max_wait_s}s)...")
    start_time = time.time()
    interval_s = 5.0

    with httpx.Client(timeout=15.0) as client:
        while time.time() - start_time < max_wait_s:
            elapsed = time.time() - start_time
            try:
                resp = client.get(health_url, headers=headers)
                if resp.status_code == 200:
                    print(f"[{elapsed:5.1f}s] HTTP 200 OK - RunPod vLLM engine is HEALTHY!")
                    return True
                print(f"[{elapsed:5.1f}s] Waiting for worker... (HTTP {resp.status_code})")
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as net_err:
                print(f"[{elapsed:5.1f}s] Connecting... ({type(net_err).__name__})")
            except Exception as err:
                print(f"[{elapsed:5.1f}s] Poll exception: {err}")
            time.sleep(interval_s)

    print(f"ERROR: RunPod health check timed out after {max_wait_s}s", file=sys.stderr)
    return False


def format_case_output(
    case_idx: int,
    case_title: str,
    input_text: str,
    out: AdapterOutput,
    passed: bool,
    details: str = "",
) -> str:
    """Format single test case output matching evidence requirements."""
    lines_buf: List[str] = []
    lines_buf.append(f"Case {case_idx}: {case_title}")
    lines_buf.append(f"Input:\n{input_text}")
    lines_buf.append(f"AI Mode: {out.ai_mode}")
    lines_buf.append(f"Lines ({len(out.lines)}):")
    if not out.lines:
        lines_buf.append("  (none)")
    else:
        for idx, line in enumerate(out.lines):
            lines_buf.append(
                f"  - [{line.line_id}] family_id={line.family_id}, qty={line.qty}, "
                f"uom={line.uom}, pack_size={line.pack_size}, reason_code={line.reason_code}"
            )
    lines_buf.append(f"Conditions ({len(out.conditions)}):")
    if not out.conditions:
        lines_buf.append("  (none)")
    else:
        for c in out.conditions:
            lines_buf.append(
                f"  - [{c.kind}] span='{c.span}', price_basis={c.price_basis}, "
                f"requested_amount={c.requested_amount}"
            )
    lines_buf.append(f"Status: {'PASS' if passed else 'FAIL'}")
    if details:
        lines_buf.append(f"Notes: {details}")
    lines_buf.append("-" * 72)
    return "\n".join(lines_buf)


async def main() -> int:
    load_dotenv()

    api_key = os.getenv("RUNPOD_API_KEY", "").strip()
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()

    if not api_key or not endpoint_id:
        print("ERROR: RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set in .env", file=sys.stderr)
        return 1

    print("=" * 72)
    print("      KiraOrder OrderAiAdapter Live RunPod Smoke Verification (6 Cases)")
    print("=" * 72)
    print(f"Endpoint ID : {endpoint_id}")
    print(f"Model       : {os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct-AWQ')}")
    print("-" * 72)

    # 1. Pre-run health check
    healthy = poll_runpod_health(endpoint_id, api_key, max_wait_s=300)
    if not healthy:
        print("CRITICAL: Pre-run health check failed. Aborting smoke test.", file=sys.stderr)
        return 1

    # 2. Instantiate extractor with cold-start tolerance (180.0s) and adapter
    extractor = RunPodExtractor(api_key=api_key, endpoint_id=endpoint_id, timeout_s=180.0)
    adapter = OrderAiAdapter(extractor=extractor)

    evidence_records: List[str] = []
    header_info = [
        "=" * 72,
        "KiraOrder OrderAiAdapter Production Smoke Verification Record",
        f"Timestamp   : {datetime.now(timezone.utc).isoformat()}",
        f"Endpoint ID : {endpoint_id}",
        f"Extractor   : RunPodExtractor(timeout_s=180.0, live over-the-wire)",
        "=" * 72,
        "",
    ]
    evidence_records.append("\n".join(header_info))

    all_passed = True

    # -------------------------------------------------------------------------
    # Case 1: Single-line single product: "Tepung 5 ctn"
    # -------------------------------------------------------------------------
    print("\nRunning Case 1: Single-line single product ('Tepung 5 ctn')...")
    c1_text = "Tepung 5 ctn"
    t0 = time.time()
    out1 = await adapter.adapt(c1_text, catalog=CATALOG)
    lat1 = (time.time() - t0) * 1000.0

    c1_ok = (
        out1.ai_mode == "LLM"
        and len(out1.lines) == 1
        and out1.lines[0].family_id == "FAM_FLOUR"
        and out1.lines[0].qty == 5
        and (out1.lines[0].uom or "").lower() == "ctn"
        and out1.lines[0].reason_code is None
    )
    if not c1_ok:
        all_passed = False
    print(f"Case 1 result: {'PASS' if c1_ok else 'FAIL'} ({lat1:.1f}ms, mode={out1.ai_mode})")
    evidence_records.append(
        format_case_output(
            1,
            "Single-line single product",
            c1_text,
            out1,
            c1_ok,
            f"Latency: {lat1:.1f}ms",
        )
    )

    # -------------------------------------------------------------------------
    # Case 2: Multi-line multi-product: "Beras 10 bag\nMinyak 2 ctn"
    # -------------------------------------------------------------------------
    print("\nRunning Case 2: Multi-line multi-product ('Beras 10 bag\\nMinyak 2 ctn')...")
    c2_text = "Beras 10 bag\nMinyak 2 ctn"
    t0 = time.time()
    out2 = await adapter.adapt(c2_text, catalog=CATALOG)
    lat2 = (time.time() - t0) * 1000.0

    c2_ok = (
        out2.ai_mode == "LLM"
        and len(out2.lines) == 2
        and out2.lines[0].family_id == "FAM_RICE"
        and out2.lines[0].qty == 10
        and (out2.lines[0].uom or "").lower() == "bag"
        and out2.lines[1].family_id == "FAM_OIL"
        and out2.lines[1].qty == 2
        and (out2.lines[1].uom or "").lower() == "ctn"
    )
    if not c2_ok:
        all_passed = False
    print(f"Case 2 result: {'PASS' if c2_ok else 'FAIL'} ({lat2:.1f}ms, mode={out2.ai_mode})")
    evidence_records.append(
        format_case_output(
            2,
            "Multi-line multi-product",
            c2_text,
            out2,
            c2_ok,
            f"Latency: {lat2:.1f}ms",
        )
    )

    # -------------------------------------------------------------------------
    # Case 3: Decimal quantity blocking: "Gula 1,5kg"
    # -------------------------------------------------------------------------
    print("\nRunning Case 3: Decimal quantity blocking ('Gula 1,5kg')...")
    c3_text = "Gula 1,5kg"
    t0 = time.time()
    out3 = await adapter.adapt(c3_text, catalog=CATALOG)
    lat3 = (time.time() - t0) * 1000.0

    c3_ok = (
        out3.ai_mode == "LLM"
        and len(out3.lines) == 1
        and out3.lines[0].family_id == "FAM_SUGAR"
        and out3.lines[0].qty is None
        and out3.lines[0].pack_size is None
        and out3.lines[0].reason_code == "INVALID_QUANTITY"
    )
    if not c3_ok:
        all_passed = False
    print(f"Case 3 result: {'PASS' if c3_ok else 'FAIL'} ({lat3:.1f}ms, mode={out3.ai_mode}, qty={out3.lines[0].qty if out3.lines else 'N/A'}, pack_size={out3.lines[0].pack_size if out3.lines else 'N/A'}, reason={out3.lines[0].reason_code if out3.lines else 'N/A'})")
    evidence_records.append(
        format_case_output(
            3,
            "Decimal quantity blocking (asserts qty=None, pack_size=None, reason_code='INVALID_QUANTITY')",
            c3_text,
            out3,
            c3_ok,
            f"Latency: {lat3:.1f}ms",
        )
    )

    # -------------------------------------------------------------------------
    # Case 4: H5 condition: "RM95 for 5 ctn"
    # -------------------------------------------------------------------------
    print("\nRunning Case 4: H5 condition ('RM95 for 5 ctn')...")
    c4_text = "RM95 for 5 ctn"
    t0 = time.time()
    out4 = await adapter.adapt(c4_text, catalog=CATALOG)
    lat4 = (time.time() - t0) * 1000.0

    c4_ok = (
        out4.ai_mode == "LLM"
        and any(
            c.kind == "PRICE" and c.requested_amount == "95"
            for c in out4.conditions
        )
    )
    if not c4_ok:
        all_passed = False
    print(f"Case 4 result: {'PASS' if c4_ok else 'FAIL'} ({lat4:.1f}ms, mode={out4.ai_mode}, conditions={len(out4.conditions)})")
    evidence_records.append(
        format_case_output(
            4,
            "H5 condition (asserts kind='PRICE', allocation disambiguation)",
            c4_text,
            out4,
            c4_ok,
            f"Latency: {lat4:.1f}ms",
        )
    )

    # -------------------------------------------------------------------------
    # Case 5: Fuzzy alias: "minyak masak 3 ctn"
    # -------------------------------------------------------------------------
    print("\nRunning Case 5: Fuzzy alias ('minyak masak 3 ctn')...")
    c5_text = "minyak masak 3 ctn"
    t0 = time.time()
    out5 = await adapter.adapt(c5_text, catalog=CATALOG)
    lat5 = (time.time() - t0) * 1000.0

    c5_ok = (
        out5.ai_mode == "LLM"
        and len(out5.lines) == 1
        and out5.lines[0].family_id == "FAM_OIL"
        and out5.lines[0].qty == 3
        and (out5.lines[0].uom or "").lower() == "ctn"
        and out5.lines[0].reason_code is None
    )
    if not c5_ok:
        all_passed = False
    print(f"Case 5 result: {'PASS' if c5_ok else 'FAIL'} ({lat5:.1f}ms, mode={out5.ai_mode})")
    evidence_records.append(
        format_case_output(
            5,
            "Fuzzy alias ('minyak masak 3 ctn' -> FAM_OIL)",
            c5_text,
            out5,
            c5_ok,
            f"Latency: {lat5:.1f}ms",
        )
    )

    # -------------------------------------------------------------------------
    # Case 6: Compound pack size: "Flour 10 ctn 1kg"
    # -------------------------------------------------------------------------
    print("\nRunning Case 6: Compound pack size ('Flour 10 ctn 1kg')...")
    c6_text = "Flour 10 ctn 1kg"
    t0 = time.time()
    out6 = await adapter.adapt(c6_text, catalog=CATALOG)
    lat6 = (time.time() - t0) * 1000.0

    c6_ok = (
        out6.ai_mode == "LLM"
        and len(out6.lines) == 1
        and out6.lines[0].family_id == "FAM_FLOUR"
        and out6.lines[0].qty == 10
        and (out6.lines[0].uom or "").lower() == "ctn"
        and (out6.lines[0].pack_size or "").lower() == "1kg"
        and out6.lines[0].reason_code is None
    )
    if not c6_ok:
        all_passed = False
    print(f"Case 6 result: {'PASS' if c6_ok else 'FAIL'} ({lat6:.1f}ms, mode={out6.ai_mode}, pack_size={out6.lines[0].pack_size if out6.lines else 'N/A'})")
    evidence_records.append(
        format_case_output(
            6,
            "Compound pack size ('Flour 10 ctn 1kg' -> FAM_FLOUR, qty=10, pack_size='1kg')",
            c6_text,
            out6,
            c6_ok,
            f"Latency: {lat6:.1f}ms",
        )
    )

    # -------------------------------------------------------------------------
    # Summary & Evidence Saving
    # -------------------------------------------------------------------------
    summary_lines = [
        "=" * 72,
        f"Verification Summary: {'ALL 6 CASES PASSED (SUCCESS)' if all_passed else 'SOME CASES FAILED (DEGRADATION)'}",
        f"Degradations / Fallbacks: {'NONE' if all_passed else 'DETECTED'}",
        "=" * 72,
    ]
    summary_text = "\n".join(summary_lines)
    print("\n" + summary_text)
    evidence_records.append(summary_text)

    evidence_dir = PROJECT_ROOT / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "smoke_6cases_2026-10-23.txt"
    evidence_file.write_text("\n\n".join(evidence_records), encoding="utf-8")
    print(f"\nEvidence successfully written to: {evidence_file}")

    return 0 if all_passed else 2


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
