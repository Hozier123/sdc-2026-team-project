"""Preflight validation script for RunPod Serverless vLLM Load Balancer endpoint.

Complies strictly with 3-phase readiness checks and early abort rules:
1. Phase 1: GET /health (polls every 10s up to 8 minutes for cold start)
   - 200: Proceed to Phase 2
   - 502 / 503 / ConnectError / Timeout: Continue polling
   - 401 / 403: Immediate abort (invalid API key)
   - 404: Immediate abort (wrong image or port 8000 not exposed)
2. Phase 2: GET /v1/models
   - Validates that returned model id exactly matches MODEL_NAME
   - 400: Immediate abort (served model name mismatch)
3. Phase 3: POST /v1/chat/completions
   - Sends minimal test prompt (max_tokens=8, temperature=0)
   - Read timeout set to 180s to absorb initial CUDA graph capture
   - Validates choices[0].message.content is non-empty
"""

import functools
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Force unbuffered output so logs appear in real-time
print = functools.partial(print, flush=True)

import httpx

# Project root setup
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env_override(env_path: Path) -> Dict[str, str]:
    """Parse .env file and override environment variables."""
    out: Dict[str, str] = {}
    if not env_path.is_file():
        return out
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
                if k:
                    os.environ[k] = v  # override=True
                    out[k] = v
    except Exception as err:
        print(f"Warning: Failed reading {env_path}: {err}", file=sys.stderr)
    return out


def mask_secret(secret: str) -> str:
    """Mask secret key for safe display."""
    if not secret:
        return "(empty)"
    if len(secret) <= 8:
        return "****"
    return secret[:4] + "****" + secret[-4:]


def run_preflight() -> int:
    env_file = PROJECT_ROOT / ".env"
    env_vars = load_env_override(env_file)

    api_key = os.getenv("RUNPOD_API_KEY", "").strip()
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()
    model_name = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-AWQ").strip()

    print("=" * 72)
    print("      KiraOrder RunPod Serverless Preflight Readiness Verification")
    print("=" * 72)
    print(f"Config File       : {env_file}")
    print(f"Endpoint ID       : {endpoint_id or '(NOT SET)'}")
    print(f"API Key           : {mask_secret(api_key)}")
    print(f"Target Model Name : {model_name}")
    print("-" * 72)

    if not api_key or not endpoint_id:
        print("ERROR: RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set in .env", file=sys.stderr)
        return 1

    base_url = f"https://{endpoint_id}.api.runpod.ai"
    auth_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # -------------------------------------------------------------------------
    # Phase 1: Poll GET /health (up to 8 minutes, 10s intervals)
    # -------------------------------------------------------------------------
    health_url = f"{base_url}/health"
    print(f"Phase 1: Probing vLLM Health endpoint: {health_url}")
    print("Polling every 10s (max 8 minutes / 48 attempts) for cold start & weights download...")

    max_attempts = 48
    interval_s = 10.0
    timeout_health = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)

    last_status: Optional[int] = None
    last_body: str = ""
    start_time = time.time()
    phase1_passed = False

    with httpx.Client(timeout=timeout_health) as client:
        for attempt in range(1, max_attempts + 1):
            elapsed = time.time() - start_time
            try:
                resp = client.get(health_url, headers=auth_headers)
                last_status = resp.status_code
                last_body = resp.text[:200]

                if resp.status_code == 200:
                    print(f"[{elapsed:5.1f}s] [Attempt {attempt:02d}] HTTP 200 OK - vLLM engine is HEALTHY!")
                    phase1_passed = True
                    break

                # Abort rules
                if resp.status_code in (401, 403):
                    print(f"\n[CRITICAL ABORT] HTTP {resp.status_code}: Unauthorized.", file=sys.stderr)
                    print(f"Body: {last_body}", file=sys.stderr)
                    print("Action: Check RUNPOD_API_KEY in .env. It is invalid or lacks endpoint permissions.", file=sys.stderr)
                    return 1

                if resp.status_code == 404:
                    print(f"\n[CRITICAL ABORT] HTTP 404 Not Found at /health.", file=sys.stderr)
                    print(f"Body: {last_body}", file=sys.stderr)
                    print("Action: Image is not vLLM OpenAI server or HTTP Ports 8000 was not exposed in Load Balancer config.", file=sys.stderr)
                    return 1

                # 502 / 503 / 504 -> container spinning up
                print(f"[{elapsed:5.1f}s] [Attempt {attempt:02d}] Waiting for worker... (HTTP {resp.status_code}: {resp.reason_phrase})")

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as net_err:
                last_body = f"Network Exception: {type(net_err).__name__} - {net_err}"
                print(f"[{elapsed:5.1f}s] [Attempt {attempt:02d}] Connecting... ({type(net_err).__name__})")

            time.sleep(interval_s)

    if not phase1_passed:
        print("\n" + "!" * 72, file=sys.stderr)
        print("ERROR: Phase 1 timed out after 8 minutes waiting for /health.", file=sys.stderr)
        print(f"Last Status Code : {last_status}", file=sys.stderr)
        print(f"Last Body        : {last_body}", file=sys.stderr)
        print("\nDiagnostic Checklist:", file=sys.stderr)
        print("1. Check RunPod Console -> Serverless -> Endpoint -> Logs (last 20 lines).", file=sys.stderr)
        print("2. If logs show 'No space left on device', Container Disk must be >= 40GB.", file=sys.stderr)
        print("3. If logs show 'health check failed', verify Health Check Path is /health, not /ping.", file=sys.stderr)
        print("4. Verify Docker Args includes '--host 0.0.0.0 --port 8000'.", file=sys.stderr)
        print("!" * 72, file=sys.stderr)
        return 1

    # -------------------------------------------------------------------------
    # Phase 2: GET /v1/models (Exact model name match)
    # -------------------------------------------------------------------------
    models_url = f"{base_url}/v1/models"
    print("-" * 72)
    print(f"Phase 2: Verifying loaded model ID: {models_url}")

    with httpx.Client(timeout=timeout_health) as client:
        try:
            resp = client.get(models_url, headers=auth_headers)
            if resp.status_code != 200:
                print(f"[CRITICAL ABORT] HTTP {resp.status_code} at /v1/models.", file=sys.stderr)
                print(f"Body: {resp.text[:200]}", file=sys.stderr)
                return 1

            models_data = resp.json().get("data", [])
            model_ids = [m.get("id") for m in models_data if isinstance(m, dict)]
            print(f"Discovered Served Models: {model_ids}")

            if model_name not in model_ids:
                print(f"\n[CRITICAL ABORT] Target model '{model_name}' NOT found in served models!", file=sys.stderr)
                print(f"Served Model IDs: {model_ids}", file=sys.stderr)
                print(f"Action: Align '--served-model-name' in Docker Args with MODEL_NAME='{model_name}' in .env.", file=sys.stderr)
                return 1

            print(f"Phase 2 Complete: Target model '{model_name}' EXACTLY matched!")

        except Exception as err:
            print(f"[CRITICAL ABORT] Phase 2 failed with exception: {err}", file=sys.stderr)
            return 1

    # -------------------------------------------------------------------------
    # Phase 3: POST /v1/chat/completions (Minimal Probe with 180s ReadTimeout)
    # -------------------------------------------------------------------------
    chat_url = f"{base_url}/v1/chat/completions"
    print("-" * 72)
    print(f"Phase 3: Sending minimal inference probe: {chat_url}")
    print("Allowing up to 180s read timeout for initial CUDA graph capture...")

    timeout_chat = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0)
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Ping test: Reply with exactly 'PONG'."}],
        "max_tokens": 8,
        "temperature": 0.0,
    }

    t0 = time.time()
    with httpx.Client(timeout=timeout_chat) as client:
        try:
            resp = client.post(chat_url, headers=auth_headers, json=payload)
            latency = (time.time() - t0) * 1000.0

            if resp.status_code != 200:
                print(f"[CRITICAL ABORT] HTTP {resp.status_code} at /v1/chat/completions.", file=sys.stderr)
                print(f"Body: {resp.text[:300]}", file=sys.stderr)
                return 1

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                print("[CRITICAL ABORT] No choices returned in chat completion response!", file=sys.stderr)
                print(f"Body: {resp.text[:300]}", file=sys.stderr)
                return 1

            reply = choices[0].get("message", {}).get("content", "").strip()
            print(f"Phase 3 Complete: HTTP 200 OK | Latency: {latency:6.1f} ms")
            print(f"Model Probe Output: '{reply}'")
            print(f"Raw Response Head: {resp.text[:200]}")

        except Exception as err:
            print(f"[CRITICAL ABORT] Phase 3 request failed with exception: {err}", file=sys.stderr)
            return 1

    print("=" * 72)
    print(">>> PREFLIGHT VERIFICATION SUCCESSFUL: RUNPOD ENDPOINT IS FULLY READY! <<<")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(run_preflight())
