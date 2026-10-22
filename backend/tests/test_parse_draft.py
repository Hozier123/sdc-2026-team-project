import json

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token
from app.db import connect
from app.extraction.base import RawExtraction, RawRow
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration

TOKEN = "tok_t1_clerk"
OWNER_TOKEN = "tok_t1_owner"
WAREHOUSE_TOKEN = "tok_t1_warehouse"
RAW = "Tepung 5 ctn, call 012-3456789, email ali@example.com"


@pytest.fixture
def seeded_db(db_settings):
    migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, amount_threshold_rm) VALUES "
            "('T1', 'Tenant One', 1500), ('T2', 'Tenant Two', 1500)"
        )
        conn.execute(
            "INSERT INTO users (user_id, tenant_id, display_name, demo_token_hash, role) "
            "VALUES ('USR_T1_CLERK', 'T1', 'T1 Clerk', %s, 'CLERK'), "
            "('USR_T1_OWNER', 'T1', 'T1 Owner', %s, 'OWNER'), "
            "('USR_T1_WAREHOUSE', 'T1', 'T1 Warehouse', %s, 'WAREHOUSE')",
            (hash_token(TOKEN), hash_token(OWNER_TOKEN), hash_token(WAREHOUSE_TOKEN)),
        )
        conn.execute(
            "INSERT INTO customers (customer_id, tenant_id, name, tier, credit_flag) VALUES "
            "('CUS_T1', 'T1', 'Customer One', 'A', 'NONE'), "
            "('CUS_T2', 'T2', 'Customer Two', 'A', 'NONE')"
        )
    return db_settings


def _client(settings):
    return TestClient(create_app(settings))


def _headers():
    return {"Authorization": f"Bearer {TOKEN}", "X-Request-ID": "parse-test-1"}


def test_parse_requires_auth(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            json={"customer_id": "CUS_T1", "message_text": RAW},
        )
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_TOKEN"


def test_parse_maps_ai_service_failure_to_503(seeded_db):
    from app.extraction.ai import AiServiceError

    class FailingProvider:
        def extract(self, masked_text, language_hint, request_id):
            raise AiServiceError("upstream down")

    app = create_app(seeded_db)
    app.state.extraction_provider = FailingProvider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": "CUS_T1", "message_text": RAW},
        )
    assert response.status_code == 503
    assert response.json()["error_code"] == "AI_AND_FALLBACK_UNAVAILABLE"
    assert "upstream down" not in response.text


def test_parse_rejects_warehouse_role(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {WAREHOUSE_TOKEN}"},
            json={"customer_id": "CUS_T1", "message_text": RAW},
        )
    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN_ACTION"


def test_parse_allows_owner_role(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
            json={"customer_id": "CUS_T1", "message_text": RAW},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "DISAMBIGUATION_REQUIRED"


def test_parse_adapts_provider_rows(seeded_db):
    class RowProvider:
        def extract(self, masked_text, language_hint, request_id):
            return RawExtraction(rows=(RawRow(span="5 ctn", qty=5),))

    app = create_app(seeded_db)
    app.state.extraction_provider = RowProvider()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"customer_id": "CUS_T1", "message_text": RAW},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ai_mode"] == "LLM"
    assert body["status"] == "DISAMBIGUATION_REQUIRED"
    assert len(body["lines"]) == 1
    assert body["lines"][0]["source_span"] == "5 ctn"
    assert any(issue["reason_code"] == "FAMILY_NOT_EVIDENCED" for issue in body["issues"])
    assert body["clarification_draft"] is not None
    assert body["clarification_lang"] == "en"
    assert "COPY_CLARIFICATION" in body["allowed_actions"]
    with connect(seeded_db) as conn:
        assert (
            conn.execute(
                "SELECT clarification FROM orders WHERE draft_id=%s",
                (body["draft_id"],),
            ).fetchone()[0]
            is not None
        )


def test_parse_rejects_overlong_message(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": "CUS_T1", "message_text": "x" * 4001},
        )
    assert response.status_code == 422
    assert response.json()["error_code"] == "MESSAGE_TOO_LONG"


def test_parse_rejects_cross_tenant_customer(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": "CUS_T2", "message_text": RAW},
        )
    assert response.status_code == 404
    assert response.json()["error_code"] == "RESOURCE_NOT_FOUND"


def test_parse_creates_masked_unresolved_draft(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={"customer_id": "CUS_T1", "message_text": RAW, "language_hint": "ms"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DISAMBIGUATION_REQUIRED"
    assert body["version"] == 1
    assert body["customer_id"] == "CUS_T1"
    assert body["masked_message"].startswith("Tepung 5 ctn")
    assert "[REDACTED_PHONE]" in body["masked_message"]
    assert "[REDACTED_EMAIL]" in body["masked_message"]
    assert "012-3456789" not in response.text
    assert "ali@example.com" not in response.text
    assert body["lines"] == []
    assert body["blocking_issues"] == ["LOW_CONFIDENCE_MATCH"]
    assert response.headers["X-Request-ID"] == "parse-test-1"
    assert response.headers["Cache-Control"] == "no-store"

    with connect(seeded_db) as conn:
        inbound = conn.execute(
            "SELECT masked_text, language FROM inbound_messages WHERE tenant_id = 'T1'"
        ).fetchone()
        assert inbound[0] == body["masked_message"]
        assert inbound[1] == "ms"
        assert conn.execute("SELECT count(*) FROM orders").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM draft_versions").fetchone() == (1,)
        snapshot = conn.execute("SELECT snapshot FROM draft_versions").fetchone()[0]
        assert snapshot["masked_message"] == body["masked_message"]
        assert "012-3456789" not in json.dumps(snapshot)


def test_parse_rejects_unknown_fields(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={
                "customer_id": "CUS_T1",
                "message_text": RAW,
                "tenant_id": "T2",
            },
        )
    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"


def test_parse_rejects_pii_in_language_hint(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(),
            json={
                "customer_id": "CUS_T1",
                "message_text": RAW,
                "language_hint": "0123456789",
            },
        )
    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"
