"""RunPod Serverless vLLM Benchmark & Latency Profiler.

Strict Compliance Rules:
- Requires valid RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID.
- Mocking or local fallback benchmark is strictly forbidden to prevent fake evidence.
- Cold start is executed separately with timeout_s=180s to absorb container spin-up.
- 20 iterations benchmark hot state exclusively; aborts immediately on any degradation.
"""

import asyncio
import os
from pathlib import Path
import sys
import time
from typing import List, Optional

# Ensure project root is in sys.path
_root = Path(__file__).resolve().parents[1]
for _p in (_root, _root / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np

from app.ai.extractor import RunPodExtractor

BENCHMARK_SAMPLES = [
    "Tepung 5 ctn, kalau RM95 boleh?",
    "Minyak 2 ctn, Beras 10 bag",
    "1. Tepung 5kg Grade A, 2 ctn; 2. Gula 5 ctn",
    "Air 500g x 12, 3 pack dan Telur 5 tray",
    "Beras Wangi 10 ctn, send tomorrow",
    "Can less? Kalau RM12.50 boleh, ambil 4 pack",
    "10kg bawang merah dan 5 ctn kicap",
    "Tepung lima belas ctn, Minyak dua puluh ctn",
    "Harga lama boleh follow? Milo 10 ctn",
    "Garam 2 ctn, Gula 3 ctn, Telur 10 ctn",
]


def load_dotenv_zero_dependency(env_path: Optional[Path] = None) -> None:
    """Load key-value pairs from .env file into os.environ without external dependencies."""
    if env_path is None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
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
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and not os.environ.get(key):
                    os.environ[key] = val
    except Exception as err:
        print(f"Warning: Failed to load .env from {env_path}: {err}", file=sys.stderr)


async def run_benchmark(iterations: int = 20) -> None:
    load_dotenv_zero_dependency()
    api_key = os.getenv("RUNPOD_API_KEY", "").strip()
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()

    # Rule 4: Mandatory credential check; mock benchmark is strictly forbidden
    if not api_key or not endpoint_id:
        print("=" * 70, file=sys.stderr)
        print("CRITICAL ERROR: RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set.", file=sys.stderr)
        print("Generating benchmark metrics using local fallback is strictly prohibited.", file=sys.stderr)
        print("Please configure .env or environment variables with genuine RunPod endpoint.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("       KiraOrder RunPod Serverless Production Benchmark Suite")
    print("=" * 70)
    print(f"Target Endpoint ID : {endpoint_id}")
    print(f"Total Iterations   : {iterations} (Hot State)")
    print("-" * 70)

    # Step 1: Dedicated Cold Start / Warmup with generous 180s timeout
    print("Phase 1: Warming up endpoint / detecting cold start (timeout: 180s)...")
    warmup_extractor = RunPodExtractor(api_key=api_key, endpoint_id=endpoint_id, timeout_s=180.0)
    t_start = time.perf_counter()
    warmup_resp = await warmup_extractor.extract(BENCHMARK_SAMPLES[0])
    t_end = time.perf_counter()
    cold_start_ms = (t_end - t_start) * 1000.0

    if warmup_resp.ai_mode != "LLM" or not warmup_resp.result.rows:
        print("\n" + "!" * 70, file=sys.stderr)
        print(f"ABORTED: Endpoint failed to warm up on LLM (mode={warmup_resp.ai_mode}).", file=sys.stderr)
        print(f"Error Details: {warmup_resp.raw_error}", file=sys.stderr)
        print("Benchmark terminated. Please verify RunPod endpoint status.", file=sys.stderr)
        print("!" * 70, file=sys.stderr)
        sys.exit(2)

    print(f"Phase 1 Complete: Cold start took {cold_start_ms:6.1f} ms ({cold_start_ms/1000.0:.2f} s)")
    print("-" * 70)
    print("Phase 2: Executing 20 warm-state iterations (timeout: 15s)...")

    # Step 2: 20 warm-state benchmark runs
    hot_extractor = RunPodExtractor(api_key=api_key, endpoint_id=endpoint_id, timeout_s=15.0)
    latencies: List[float] = []

    for i in range(iterations):
        sample = BENCHMARK_SAMPLES[i % len(BENCHMARK_SAMPLES)]
        t0 = time.perf_counter()
        resp = await hot_extractor.extract(sample)
        t1 = time.perf_counter()

        if resp.ai_mode != "LLM" or not resp.result.rows:
            print("\n" + "!" * 70, file=sys.stderr)
            print(f"ABORTED: Warm call {i+1} degraded to fallback (mode={resp.ai_mode}).", file=sys.stderr)
            print(f"Error Details: {resp.raw_error}", file=sys.stderr)
            print("Benchmark terminated to prevent corrupted p95 metrics.", file=sys.stderr)
            print("!" * 70, file=sys.stderr)
            sys.exit(2)

        elapsed_ms = (t1 - t0) * 1000.0
        latencies.append(elapsed_ms)
        status = f"[{resp.ai_mode}]"
        print(f"Warm Call {i+1:02d}/{iterations:02d} | Status: {status:<8} | Latency: {elapsed_ms:6.1f} ms | Text: '{sample[:30]}...'")
        await asyncio.sleep(0.1)

    print("-" * 70)
    p50 = float(np.percentile(latencies, 50))
    p90 = float(np.percentile(latencies, 90))
    p95 = float(np.percentile(latencies, 95))

    p95_seconds = p95 / 1000.0
    recommended_timeout = min(round(p95_seconds + 1.0, 1), 8.0)

    print(f"Cold Start Latency (Phase 1) : {cold_start_ms:6.1f} ms ({cold_start_ms/1000.0:.2f} s)")
    print(f"Warm State p50               : {p50:6.1f} ms")
    print(f"Warm State p90               : {p90:6.1f} ms")
    print(f"Warm State p95               : {p95:6.1f} ms ({p95_seconds:.2f} s)")
    print("=" * 70)
    print(f"RECOMMENDED LLM_TIMEOUT_S    : {recommended_timeout:.1f} s")
    print(f"(Formula: min(round(p95 + 1.0s, 1), 8.0s) per Gate 0 Model Gate)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmark(iterations=20))
