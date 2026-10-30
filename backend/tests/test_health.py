import socket

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_liveness_without_database():
    with TestClient(create_app(Settings(_env_file=None, database_url=None))) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert client.get("/readyz").status_code == 503


def test_unavailable_db_only_breaks_readiness(caplog):
    # Reserve a port without listening: no external service or credential needed.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        url = f"postgresql://probe:never_log_this@127.0.0.1:{port}/missing"
        with TestClient(create_app(Settings(_env_file=None, database_url=url))) as client:
            response = client.get("/readyz")
            assert response.status_code == 503
            assert response.json() == {"status": "not_ready"}
            assert client.get("/healthz").status_code == 200
            assert "never_log_this" not in response.text + caplog.text


def test_probe_and_identity_responses_are_documented():
    with TestClient(create_app(Settings(_env_file=None, database_url=None))) as client:
        spec = client.get("/openapi.json").json()
        assert set(spec["paths"]) == {
            "/healthz",
            "/readyz",
            "/api/v1/me",
            "/api/v1/orders/parse-draft",
            "/api/v1/orders/drafts",
            "/api/v1/orders/drafts/{draft_id}",
            "/api/v1/orders/drafts/{draft_id}/lines",
            "/api/v1/orders/drafts/{draft_id}/discard",
            "/api/v1/orders/drafts/{draft_id}/clarification-copied",
            "/api/v1/orders/{draft_id}/approve",
            "/api/v1/orders/{do_number}/audit-detail",
            "/api/v1/approvals",
            "/api/v1/approvals/{approval_id}",
            "/api/v1/approvals/{approval_id}/decide",
            "/api/v1/delivery-orders/{do_number}",
            "/api/v1/customers",
            "/api/v1/catalog/products",
            "/api/v1/activity",
            "/api/v1/warehouse/delivery-orders/{do_number}",
            "/api/v1/ai/status",
            "/api/v1/ai/wake",
        }
        assert "503" in spec["paths"]["/readyz"]["get"]["responses"]
        assert "200" in spec["paths"]["/api/v1/me"]["get"]["responses"]
