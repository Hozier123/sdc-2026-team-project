"""Unit tests for KiraOrder AI Warm-up and Health Check APIRouter (backend/ai/warmup.py).

Verifies compliance with Gate 0 v4 contract and Review Revision v2:
- 1. State machine four states (READY, WARMING, OFFLINE, DEGRADED) and available_modes mapping
- 2. Strict Rate Limiting: 10 requests allowed, 11th triggers HTTP 429 with Retry-After header
- 3. Strict RBAC & Role Forgery Defense:
  - GET /ai/status returns 401 on missing/invalid token, 200 with valid token or request.state.role
  - POST /ai/wake rejects X-User-Role forgery and token substring matching
  - 401 on missing/invalid credentials, 403 on unauthorized roles (e.g. WAREHOUSE), 200 for CLERK/OWNER
- 4. Active wake transitions:
  - OFFLINE -> WARMING -> READY when extractor probe succeeds
  - OFFLINE -> WARMING -> DEGRADED when extractor probe fails but fallback is available
  - 503 AI_AND_FALLBACK_UNAVAILABLE when both fallback and extractor are unavailable
- 5. Exact schema conformance (additionalProperties=false, exact field sets) and X-Request-ID on every response
- 6. Dead routes removal: /ai/ai/status and /ai/ai/wake return 404
- 7. Zero PII in status/wake messages
"""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, Request
import httpx
import pytest

from backend.ai.warmup import (
    AiStatus,
    AiWakeResult,
    ai_state_manager,
    router,
    wake_rate_limiter,
)

app = FastAPI()
app.include_router(router)

AUTH_CLERK = {"Authorization": "Bearer clerk_token_xyz"}
AUTH_OWNER = {"Authorization": "Bearer owner_token_xyz"}
AUTH_WAREHOUSE = {"Authorization": "Bearer warehouse_token_xyz"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_warmup_state():
    """Reset rate limiter and AI state before each test."""
    wake_rate_limiter.reset()
    ai_state_manager.reset()
    yield
    wake_rate_limiter.reset()
    ai_state_manager.reset()


# ---------------------------------------------------------------------------
# 1. State Machine Four States & Mode Mapping
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state,expected_modes",
    [
        ("READY", ["LLM", "FALLBACK", "ALIAS_ONLY"]),
        ("WARMING", ["FALLBACK", "ALIAS_ONLY"]),
        ("OFFLINE", ["FALLBACK", "ALIAS_ONLY"]),
        ("DEGRADED", ["FALLBACK", "ALIAS_ONLY"]),
    ],
)
async def test_ai_status_four_states_and_mode_mapping(state, expected_modes):
    """GET /ai/status accurately reflects all 4 states and maps available_modes per contract."""
    ai_state_manager.set_state(state)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/ai/status", headers={"X-Request-ID": "test-req-001", **AUTH_CLERK})

    assert res.status_code == 200
    assert res.headers.get("x-request-id") == "test-req-001"

    data = res.json()
    # Contract schema exact match
    expected_fields = {"state", "available_modes", "fallback_available", "last_checked_at", "message"}
    assert set(data.keys()) == expected_fields

    assert data["state"] == state
    assert data["available_modes"] == expected_modes
    assert isinstance(data["fallback_available"], bool)
    assert "T" in data["last_checked_at"]  # ISO datetime format

    # Validate against Pydantic model (strict extra=forbid)
    AiStatus.model_validate(data)


# ---------------------------------------------------------------------------
# 2. Strict Rate Limiting (10 req/min, 11th triggers 429)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ai_wake_rate_limit_11th_request_429():
    """POST /ai/wake allows 10 requests/min; the 11th returns 429 with Retry-After header."""
    headers = {"X-Request-ID": "wake-req-001", **AUTH_CLERK}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # First 10 requests succeed
        for i in range(10):
            res = await client.post("/ai/wake", headers=headers)
            assert res.status_code == 200, f"Request {i+1} failed unexpectedly with {res.status_code}"
            assert res.json()["accepted"] is True

        # 11th request triggers rate limit
        res11 = await client.post("/ai/wake", headers=headers)

    assert res11.status_code == 429
    assert res11.headers.get("x-request-id") == "wake-req-001"
    assert "retry-after" in res11.headers
    retry_after = int(res11.headers["retry-after"])
    assert retry_after > 0

    err_data = res11.json()
    assert err_data["error_code"] == "RATE_LIMITED"
    assert err_data["details"]["scope"] == "AI_WAKE"
    assert err_data["details"]["retry_after_seconds"] == retry_after


# ---------------------------------------------------------------------------
# 3. GET /ai/status Authentication Checks (401 vs 200)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ai_status_authentication_checks():
    """GET /ai/status validates Authorization header: 401 on missing/invalid, 200 on valid."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Missing Authorization header -> 401
        res_no_auth = await client.get("/ai/status")
        assert res_no_auth.status_code == 401
        err_no_auth = res_no_auth.json()
        assert err_no_auth["error_code"] == "INVALID_TOKEN"
        assert err_no_auth["message"] == "Missing, expired or invalid bearer token."

        # 2. Invalid bearer token -> 401
        res_bad_tok = await client.get("/ai/status", headers={"Authorization": "Bearer bogus_token_123"})
        assert res_bad_tok.status_code == 401
        assert res_bad_tok.json()["error_code"] == "INVALID_TOKEN"

        # 3. Valid bearer tokens -> 200
        for token_auth in (AUTH_CLERK, AUTH_OWNER, AUTH_WAREHOUSE, {"Authorization": "Bearer CLERK_TOKEN_XYZ"}):
            res_ok = await client.get("/ai/status", headers=token_auth)
            assert res_ok.status_code == 200
            assert "state" in res_ok.json()


# ---------------------------------------------------------------------------
# 4. Strict RBAC & Role Forgery Defense (POST /ai/wake)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ai_wake_role_forgery_defense():
    """Forbid trusting X-User-Role header or searching CLERK/OWNER substring inside arbitrary token."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Attack 1: Forging role via X-User-Role without Authorization -> 401
        res_role_header_only = await client.post("/ai/wake", headers={"X-User-Role": "OWNER"})
        assert res_role_header_only.status_code == 401
        assert res_role_header_only.json()["error_code"] == "INVALID_TOKEN"

        # Attack 2: Forging role via X-User-Role with invalid bearer token -> 401
        res_role_header_bad_token = await client.post(
            "/ai/wake",
            headers={"X-User-Role": "OWNER", "Authorization": "Bearer untrusted_token"},
        )
        assert res_role_header_bad_token.status_code == 401
        assert res_role_header_bad_token.json()["error_code"] == "INVALID_TOKEN"

        # Attack 3: Embedding 'CLERK' or 'OWNER' substring in untrusted token -> 401
        res_substring_clerk = await client.post(
            "/ai/wake",
            headers={"Authorization": "Bearer hacker_CLERK_impostor_token"},
        )
        assert res_substring_clerk.status_code == 401
        assert res_substring_clerk.json()["error_code"] == "INVALID_TOKEN"

        res_substring_owner = await client.post(
            "/ai/wake",
            headers={"Authorization": "Bearer hacker_OWNER_impostor_token"},
        )
        assert res_substring_owner.status_code == 401
        assert res_substring_owner.json()["error_code"] == "INVALID_TOKEN"

        # Legitimate 1: WAREHOUSE role is forbidden for wake -> 403
        res_warehouse = await client.post("/ai/wake", headers=AUTH_WAREHOUSE)
        assert res_warehouse.status_code == 403
        assert res_warehouse.json()["error_code"] == "FORBIDDEN_ACTION"

        # Legitimate 2: CLERK and OWNER succeed -> 200
        res_clerk = await client.post("/ai/wake", headers=AUTH_CLERK)
        assert res_clerk.status_code == 200
        assert res_clerk.json()["accepted"] is True

        res_owner = await client.post("/ai/wake", headers=AUTH_OWNER)
        assert res_owner.status_code == 200
        assert res_owner.json()["accepted"] is True


@pytest.mark.anyio
async def test_ai_middleware_injected_state_role():
    """Verify that trusted roles injected into request.state.role take precedence."""
    test_app = FastAPI()

    # Upstream middleware simulation
    @test_app.middleware("http")
    async def mock_auth_middleware(request: Request, call_next):
        token = request.headers.get("X-Test-Injected-Role")
        if token:
            request.state.role = token
        return await call_next(request)

    test_app.include_router(router)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as client:
        # Injected CLERK -> 200
        res_clerk = await client.post("/ai/wake", headers={"X-Test-Injected-Role": "CLERK"})
        assert res_clerk.status_code == 200

        # Injected WAREHOUSE -> 403
        res_wh = await client.post("/ai/wake", headers={"X-Test-Injected-Role": "WAREHOUSE"})
        assert res_wh.status_code == 403

        # Injected CLERK on status -> 200
        res_st = await client.get("/ai/status", headers={"X-Test-Injected-Role": "CLERK"})
        assert res_st.status_code == 200


# ---------------------------------------------------------------------------
# 5. POST /ai/wake Active Live Probe Transitions
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ai_wake_active_probe_transitions():
    """POST /ai/wake transitions OFFLINE -> WARMING -> READY (on probe success) or DEGRADED (on failure)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Case A: OFFLINE + extractor probe succeeds -> READY
        ai_state_manager.set_state("OFFLINE")
        with patch("backend.ai.warmup.probe_fallback_available", return_value=True), \
             patch("backend.ai.warmup.probe_extractor_available", new_callable=AsyncMock, return_value=True):
            res_wake_ready = await client.post("/ai/wake", headers=AUTH_CLERK)
            assert res_wake_ready.status_code == 200
            data_ready = res_wake_ready.json()
            assert data_ready["state"] == "READY"
            assert data_ready["accepted"] is True
            assert ai_state_manager.get_state() == "READY"

        # Case B: OFFLINE + extractor probe fails -> DEGRADED
        ai_state_manager.set_state("OFFLINE")
        with patch("backend.ai.warmup.probe_fallback_available", return_value=True), \
             patch("backend.ai.warmup.probe_extractor_available", new_callable=AsyncMock, return_value=False):
            res_wake_deg = await client.post("/ai/wake", headers=AUTH_CLERK)
            assert res_wake_deg.status_code == 200
            data_deg = res_wake_deg.json()
            assert data_deg["state"] == "DEGRADED"
            assert data_deg["accepted"] is True
            assert ai_state_manager.get_state() == "DEGRADED"

        # Case C: DEGRADED + extractor probe succeeds -> re-probe recovers to READY
        ai_state_manager.set_state("DEGRADED")
        with patch("backend.ai.warmup.probe_fallback_available", return_value=True), \
             patch("backend.ai.warmup.probe_extractor_available", new_callable=AsyncMock, return_value=True):
            res_wake_recov = await client.post("/ai/wake", headers=AUTH_CLERK)
            assert res_wake_recov.status_code == 200
            data_recov = res_wake_recov.json()
            assert data_recov["state"] == "READY"
            assert data_recov["accepted"] is True
            assert ai_state_manager.get_state() == "READY"


# ---------------------------------------------------------------------------
# 6. Real Fallback Probe & 503 Defense
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fallback_available_real_probe_and_503():
    """Probe reflects real lexicon availability; missing fallback + offline AI returns 503."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Normal state: fallback is available
        res_ok = await client.get("/ai/status", headers=AUTH_CLERK)
        assert res_ok.json()["fallback_available"] is True

        # Simulate missing lexicon / fallback disk error
        with patch("backend.ai.warmup.probe_fallback_available", return_value=False):
            res_bad = await client.get("/ai/status", headers=AUTH_CLERK)
            assert res_bad.json()["fallback_available"] is False

            # If AI is also OFFLINE and extractor probe also fails, waking returns 503 AI_AND_FALLBACK_UNAVAILABLE
            ai_state_manager.set_state("OFFLINE")
            with patch("backend.ai.warmup.probe_extractor_available", new_callable=AsyncMock, return_value=False):
                res_wake_503 = await client.post("/ai/wake", headers=AUTH_CLERK)
                assert res_wake_503.status_code == 503
                assert res_wake_503.json()["error_code"] == "AI_AND_FALLBACK_UNAVAILABLE"


# ---------------------------------------------------------------------------
# 7. Dead Routes Removal (/ai/ai/status and /ai/ai/wake)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dead_routes_removed_404():
    """Verify duplicate /ai/ai/status and /ai/ai/wake routes were deleted and return 404."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res_dead_status = await client.get("/ai/ai/status", headers=AUTH_CLERK)
        assert res_dead_status.status_code == 404

        res_dead_wake = await client.post("/ai/ai/wake", headers=AUTH_CLERK)
        assert res_dead_wake.status_code == 404


# ---------------------------------------------------------------------------
# 8. Exact Schema Conformance & Zero PII
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_exact_schema_and_zero_pii():
    """Ensure response field sets exactly equal openapi contract and contains no PII."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        status_res = await client.get("/ai/status", headers=AUTH_CLERK)
        wake_res = await client.post("/ai/wake", headers=AUTH_CLERK)

    status_data = status_res.json()
    wake_data = wake_res.json()

    # Exact field set assertion (openapi.yaml lines 2117-2160)
    assert set(status_data.keys()) == {"state", "available_modes", "fallback_available", "last_checked_at", "message"}
    assert set(wake_data.keys()) == {"state", "accepted", "fallback_available", "last_checked_at", "message"}

    # Strict Pydantic model validation (extra='forbid')
    AiStatus.model_validate(status_data)
    AiWakeResult.model_validate(wake_data)

    # Zero PII check
    for msg in (status_data["message"], wake_data["message"]):
        assert "@" not in msg
        assert "01" not in msg  # No phone number
        assert "RM" not in msg  # No transaction amount

