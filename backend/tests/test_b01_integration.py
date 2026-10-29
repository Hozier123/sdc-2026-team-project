"""B01 real API/auth/database with simulated provider responses; no GPU calls."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_ai_status import KEY, MODEL, Upstream
from test_drafts_approve_do import CLERK, WAREHOUSE, _headers
from test_drafts_approve_do import seeded_db as seeded_db

from app.db import connect
from app.main import create_app

pytestmark = pytest.mark.integration


def configure(settings):
    settings.ai_provider = "runpod_adapter"
    settings.runpod_api_key = SecretStr(KEY)
    settings.runpod_endpoint_id = "b01-endpoint"
    # These belong to another provider and must never receive requests.
    settings.ai_service_url = "https://unused.invalid/extract"
    settings.ai_health_url = "https://unused.invalid/health"
    settings.ai_wake_url = "https://unused.invalid/wake"
    settings.ai_api_key = SecretStr("unused-key")


@pytest.mark.parametrize(
    "failure", [None, "timeout", 401, 403, "wrong_model", "fallback_unavailable"]
)
def test_runpod_parse_status_and_recovery_use_one_config(seeded_db, monkeypatch, caplog, failure):
    configure(seeded_db)
    scenario = {"failure": failure}
    upstream = Upstream()

    async def post(self, url, **kwargs):
        assert url == "https://b01-endpoint.api.runpod.ai/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == f"Bearer {KEY}"
        assert kwargs["json"]["model"] == MODEL
        assert self.timeout.read == 4.1
        request = httpx.Request("POST", url)
        if scenario["failure"] == "timeout":
            raise httpx.ReadTimeout(KEY, request=request)
        if scenario["failure"] in {401, 403, "fallback_unavailable"}:
            if scenario["failure"] == "fallback_unavailable":
                return httpx.Response(401, text=KEY, request=request)
            return httpx.Response(scenario["failure"], text=KEY, request=request)
        text = kwargs["json"]["messages"][-1]["content"]
        qty = int(text.split()[1])
        content = {
            "rows": [{"span": text, "fam": "FAM_MILO", "qty": qty, "uom": "ctn"}],
            "ignored_spans": [],
        }
        return httpx.Response(
            200,
            request=request,
            json={
                "model": "wrong" if scenario["failure"] == "wrong_model" else MODEL,
                "choices": [{"message": {"content": json.dumps(content)}}],
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    if failure == "fallback_unavailable":

        def unavailable(*args, **kwargs):
            if scenario["failure"] == "fallback_unavailable":
                raise RuntimeError(KEY)
            return original_fallback(*args, **kwargs)

        from app.ai import extractor as extractor_module

        original_fallback = extractor_module.extract_fallback_order
        monkeypatch.setattr(extractor_module, "extract_fallback_order", unavailable)
    app = create_app(seeded_db)
    ai = app.state.ai_orchestrator
    ai._client.close()
    with httpx.Client(transport=httpx.MockTransport(upstream)) as transport:
        ai._client = transport
        ai._owns_client = False
        with TestClient(app) as client:
            assert client.get("/api/v1/ai/status", headers=_headers(CLERK)).json()["state"] == (
                "DEGRADED"
            )
            response = client.post(
                "/api/v1/orders/parse-draft",
                headers=_headers(CLERK),
                json={"customer_id": "CUS_T1", "message_text": "Milo 2 ctn"},
            )
            if failure == "fallback_unavailable":
                assert response.status_code == 503
                assert response.json()["error_code"] == "AI_AND_FALLBACK_UNAVAILABLE"
                with connect(seeded_db) as conn:
                    assert conn.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
            else:
                assert response.status_code == 200, response.text
                assert response.json()["ai_mode"] == ("FALLBACK" if failure else "LLM")
            status = client.get("/api/v1/ai/status", headers=_headers(CLERK))
            assert status.json()["state"] == ("DEGRADED" if failure else "READY")
            assert status.headers["X-Request-ID"] == "draft-test"
            assert KEY not in response.text + status.text + caplog.text
            scenario["failure"] = None
            recovered = client.post(
                "/api/v1/orders/parse-draft",
                headers=_headers(CLERK),
                json={"customer_id": "CUS_T1", "message_text": "Milo 3 ctn"},
            )
            assert recovered.status_code == 200
            assert recovered.json()["ai_mode"] == "LLM"
            assert client.get("/api/v1/ai/status", headers=_headers(CLERK)).json()["state"] == (
                "READY"
            )


def test_background_wake_keeps_real_auth_rate_limit_and_response_contract(seeded_db):
    configure(seeded_db)
    upstream = Upstream()
    app = create_app(seeded_db)
    ai = app.state.ai_orchestrator
    ai._client.close()
    with httpx.Client(transport=httpx.MockTransport(upstream)) as transport:
        ai._client = transport
        ai._owns_client = False
        with TestClient(app) as client:
            assert client.get("/api/v1/ai/status").status_code == 401
            assert client.post("/api/v1/ai/wake", headers=_headers(WAREHOUSE)).status_code == 403
            assert upstream.calls == []
            response = client.post("/api/v1/ai/wake", headers=_headers(CLERK))
            assert response.status_code == 200
            assert set(response.json()) == {
                "state",
                "accepted",
                "fallback_available",
                "last_checked_at",
                "message",
            }
            assert response.json()["state"] == "WARMING"
            assert response.json()["accepted"]
            ai._warmup.result(timeout=3)
            assert client.get("/api/v1/ai/status", headers=_headers(CLERK)).json()["state"] == (
                "READY"
            )
            limited = client.post("/api/v1/ai/wake", headers=_headers(CLERK))
            assert limited.status_code == 429
            assert limited.json()["error_code"] == "RATE_LIMITED"
            assert int(limited.headers["Retry-After"]) > 0
            assert KEY not in response.text + limited.text
