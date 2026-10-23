import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai_status import AiOrchestrator
from app.auth import hash_token
from app.db import connect
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration

CLERK = "tok_t1_clerk"
OWNER = "tok_t1_owner"
WAREHOUSE = "tok_t1_warehouse"


@pytest.fixture
def seeded_db(db_settings):
    migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants "
            "(tenant_id, name, amount_threshold_rm) VALUES "
            "('T1', 'Tenant One', 10), ('T2', 'Tenant Two', 10)"
        )
        conn.execute(
            "INSERT INTO users "
            "(user_id, tenant_id, display_name, demo_token_hash, role) VALUES "
            "('USR_T1_CLERK', 'T1', 'T1 Clerk', %s, 'CLERK'), "
            "('USR_T1_OWNER', 'T1', 'T1 Owner', %s, 'OWNER'), "
            "('USR_T1_WAREHOUSE', 'T1', 'T1 Warehouse', %s, 'WAREHOUSE')",
            (hash_token(CLERK), hash_token(OWNER), hash_token(WAREHOUSE)),
        )
        conn.execute(
            "INSERT INTO customers (customer_id, tenant_id, name, tier) VALUES "
            "('CUS_T1', 'T1', 'Customer One', 'A')"
        )
        conn.execute(
            "INSERT INTO product_families (family_id, tenant_id, family_name) "
            "VALUES ('FAM_MILO', 'T1', 'Milo')"
        )
        conn.execute(
            "INSERT INTO products "
            "(product_id, tenant_id, family_id, sku_code, name, base_unit) "
            "VALUES ('SKU_MILO_1KG', 'T1', 'FAM_MILO', 'SKU_MILO_1KG', 'Milo 1kg', 'ctn')"
        )
        conn.execute(
            "INSERT INTO customer_tier_prices "
            "(tenant_id, product_id, tier, unit_price_rm) "
            "VALUES ('T1', 'SKU_MILO_1KG', 'A', 5.00)"
        )
        conn.execute(
            "INSERT INTO inventory (tenant_id, product_id, available_qty) "
            "VALUES ('T1', 'SKU_MILO_1KG', 10)"
        )
        conn.execute(
            "INSERT INTO inbound_messages "
            "(tenant_id, message_id, customer_id, source, masked_text) "
            "VALUES ('T1', 'MSG_T1', 'CUS_T1', 'PASTE', 'Milo 5 ctn')"
        )
        conn.execute(
            "INSERT INTO orders "
            "(tenant_id, draft_id, customer_id, message_id, status, version, ai_mode) "
            "VALUES ('T1', 'DRF_T1', 'CUS_T1', 'MSG_T1', 'DISAMBIGUATION_REQUIRED', 1, 'FALLBACK')"
        )
        conn.execute(
            "INSERT INTO draft_versions "
            "(tenant_id, draft_id, version, snapshot, created_by) "
            "VALUES ('T1', 'DRF_T1', 1, '{}', 'USR_T1_CLERK')"
        )
    return db_settings


def _client(settings):
    return TestClient(create_app(settings))


def _headers(token):
    return {"Authorization": f"Bearer {token}", "X-Request-ID": "draft-test"}


def _line(qty=1, **overrides):
    line = {
        "client_line_ref": "new-1",
        "sku_id": "SKU_MILO_1KG",
        "confirmed_qty": qty,
        "uom": "ctn",
        "match_source": "MANUAL_SELECTED",
    }
    line.update(overrides)
    return line


def _put(client, *, version=1, lines=None, headers=None, draft_id="DRF_T1"):
    return client.put(
        f"/api/v1/orders/drafts/{draft_id}/lines",
        headers=headers or _headers(CLERK),
        json={"expected_version": version, "lines": lines or [_line()]},
    )


def test_parse_put_approve_and_get_do_end_to_end(seeded_db):
    with _client(seeded_db) as client:
        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn"},
        )
        assert parsed.status_code == 200, parsed.text
        draft_id = parsed.json()["draft_id"]
        assert parsed.json()["version"] == 1
        assert parsed.json()["status"] == "DISAMBIGUATION_REQUIRED"

        saved = _put(client, draft_id=draft_id, version=1, lines=[_line(1)])
        assert saved.status_code == 200, saved.text
        assert saved.json()["version"] == 2
        assert saved.json()["status"] == "READY_FOR_APPROVAL"

        approved = client.post(
            f"/api/v1/orders/{draft_id}/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        do = approved.json()
        assert do["final_total_rm"] == "5.00"

        fetched = client.get(f"/api/v1/delivery-orders/{do['do_number']}", headers=_headers(CLERK))
        assert fetched.status_code == 200
        assert fetched.json()["draft_id"] == draft_id

    with connect(seeded_db) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (9,)


def test_approve_confirmed_items_saves_new_version_and_approves(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={
                "expected_version": 1,
                "confirmed_items": [_line(1)],
            },
        )
        assert response.status_code == 200, response.text
        do = response.json()
        assert do["lines"][0]["sku_id"] == "SKU_MILO_1KG"
        assert do["lines"][0]["quantity"] == 1
        assert do["draft_version"] == 2
    with connect(seeded_db) as conn:
        order = conn.execute(
            "SELECT status, version FROM orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()
        versions = conn.execute(
            "SELECT count(*) FROM draft_versions WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
        dos = conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
    assert order == ("DO_GENERATED", 2)
    assert versions == 2
    assert dos == 1


def test_approve_confirmed_items_failure_rolls_back_new_version(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 1, "confirmed_items": []},
        )
        assert response.status_code == 400
    with connect(seeded_db) as conn:
        order = conn.execute(
            "SELECT status, version FROM orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()
        versions = conn.execute(
            "SELECT count(*) FROM draft_versions WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
        dos = conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
    assert order == ("DISAMBIGUATION_REQUIRED", 1)
    assert versions == 1
    assert dos == 0


def test_approve_confirmed_items_failure_after_save_rolls_back(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 1, "confirmed_items": [_line(11)]},
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "DISAMBIGUATION_UNRESOLVED"
    with connect(seeded_db) as conn:
        order = conn.execute(
            "SELECT status, version FROM orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()
        versions = conn.execute(
            "SELECT count(*) FROM draft_versions WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
        dos = conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
    assert order == ("DISAMBIGUATION_REQUIRED", 1)
    assert versions == 1
    assert dos == 0


def test_approve_confirmed_items_stale_version_does_not_save(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 99, "confirmed_items": [_line(1)]},
        )
        assert response.status_code == 409
    with connect(seeded_db) as conn:
        order = conn.execute(
            "SELECT status, version FROM orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()
        versions = conn.execute(
            "SELECT count(*) FROM draft_versions WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
        dos = conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()[0]
    assert order == ("DISAMBIGUATION_REQUIRED", 1)
    assert versions == 1
    assert dos == 0


def test_parse_uses_ai_rows_instead_of_runtime_error(seeded_db):
    class FakeAi:
        def extract(self, masked_text, language_hint, request_id):
            from app.extraction.base import RawExtraction, RawRow

            return RawExtraction(
                rows=(
                    RawRow(
                        span="Milo 5 ctn",
                        qty=5,
                        uom="ctn",
                        fam="FAM_MILO",
                    ),
                ),
                ignored_spans=(),
            )

    app = create_app(seeded_db)
    app.state.extraction_provider = FakeAi()
    with TestClient(app) as client:
        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn"},
        )
    assert parsed.status_code == 200, parsed.text
    body = parsed.json()
    assert body["ai_mode"] == "LLM"
    assert body["status"] == "READY_FOR_APPROVAL"
    assert len(body["lines"]) == 1
    line = body["lines"][0]
    assert line["source_span"] == "Milo 5 ctn"
    assert line["sku_id"] == "SKU_MILO_1KG"
    assert line["match_source"] == "LLM_EXTRACTED"
    assert line["candidate_skus"] == []
    assert not any(issue["reason_code"] == "NO_CANDIDATE" for issue in body["issues"])


def test_put_then_direct_approve_and_do(seeded_db):
    with _client(seeded_db) as client:
        saved = _put(client, lines=[_line(1)])
        assert saved.status_code == 200, saved.text
        draft = saved.json()
        assert draft["version"] == 2
        assert draft["status"] == "READY_FOR_APPROVAL"
        assert draft["lines"][0]["subtotal_rm"] == "5.00"

        approved = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        do = approved.json()
        assert do["final_total_rm"] == "5.00"
        assert do["approval_mode"] == "DIRECT"
        assert do["lines"][0]["applied_unit_price"] == "5.00"
        reply = do["reply_draft"]
        assert reply["language"] == "en"
        assert reply["do_number"] == do["do_number"]
        assert "Milo 1kg" in reply["message"]
        assert "1 ctn" in reply["message"]
        assert "Total RM 5.00" in reply["message"]

        again = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert again.status_code == 409
        assert again.json()["error_code"] == "ALREADY_APPROVED"

        get_do = client.get(f"/api/v1/delivery-orders/{do['do_number']}", headers=_headers(CLERK))
        assert get_do.status_code == 200
        assert get_do.json()["do_number"] == do["do_number"]
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customers SET name='Renamed Customer' WHERE customer_id='CUS_T1'")
        snapshotted = client.get(
            f"/api/v1/delivery-orders/{do['do_number']}", headers=_headers(CLERK)
        )
        assert snapshotted.status_code == 200
        assert snapshotted.json()["customer_name"] == "Customer One"

    with connect(seeded_db) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (9,)


def test_put_stale_version_and_warehouse(seeded_db):
    with _client(seeded_db) as client:
        stale = _put(client, version=0)
        assert stale.status_code == 422  # Pydantic rejects expected_version=0

        denied = _put(client, headers=_headers(WAREHOUSE))
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "FORBIDDEN_ACTION"


def test_put_insufficient_stock_is_200_issue(seeded_db):
    with _client(seeded_db) as client:
        saved = _put(client, lines=[_line(11)])
        assert saved.status_code == 200
        draft = saved.json()
        assert draft["status"] == "DISAMBIGUATION_REQUIRED"
        assert "INSUFFICIENT_STOCK" in draft["blocking_issues"]
        assert any(issue["code"] == "INSUFFICIENT_STOCK" for issue in draft["issues"])


def test_clerk_escalation_creates_approval_and_owner_approves(seeded_db):
    with _client(seeded_db) as client:
        saved = _put(client, lines=[_line(3)])  # 15 >= threshold 10
        assert saved.status_code == 200
        pending = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert pending.status_code == 202, pending.text
        approval = pending.json()
        assert approval["status"] == "PENDING"
        assert approval["reasons"][0]["code"] == "AMOUNT_OVER_THRESHOLD"

        decided = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decide",
            headers=_headers(OWNER),
            json={"decision": "APPROVE"},
        )
        assert decided.status_code == 200, decided.text
        do = decided.json()
        assert do["approval_mode"] == "OWNER_APPROVED"
        assert do["prepared_by"] == "USR_T1_CLERK"
        assert do["approved_by"] == "USR_T1_OWNER"

    with connect(seeded_db) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (7,)


def test_owner_can_self_approve_escalation(seeded_db):
    with _client(seeded_db) as client:
        saved = _put(client, lines=[_line(3)], headers=_headers(OWNER))
        assert saved.status_code == 200
        assert "APPROVE_AND_GENERATE_DO" in saved.json()["allowed_actions"]
        approved = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(OWNER),
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["approval_mode"] == "OWNER_SELF_APPROVED"


def test_approvals_list_and_detail(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        pending = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert pending.status_code == 202, pending.text
        approval_id = pending.json()["approval_id"]

        owner_list = client.get("/api/v1/approvals", headers=_headers(OWNER))
        assert owner_list.status_code == 200
        assert any(item["approval_id"] == approval_id for item in owner_list.json()["items"])

        clerk_list = client.get("/api/v1/approvals", headers=_headers(CLERK))
        assert clerk_list.status_code == 200
        assert all(item["requested_by"] == "USR_T1_CLERK" for item in clerk_list.json()["items"])

        warehouse = client.get("/api/v1/approvals", headers=_headers(WAREHOUSE))
        assert warehouse.status_code == 403

        detail = client.get(f"/api/v1/approvals/{approval_id}", headers=_headers(OWNER))
        assert detail.status_code == 200, detail.text
        assert detail.json()["approval_id"] == approval_id
        assert detail.json()["status"] == "PENDING"
        stock = detail.json()["stock_check"]
        assert stock["state"] == "PASSED"
        assert stock["lines"][0]["available_qty"] == 10
        assert stock["lines"][0]["effective_qty"] == 3
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customers SET name='Renamed Customer' WHERE customer_id='CUS_T1'")
        snapshotted = client.get(f"/api/v1/approvals/{approval_id}", headers=_headers(OWNER))
        assert snapshotted.status_code == 200
        assert snapshotted.json()["customer"]["name"] == "Customer One"


def test_owner_rejects_with_note(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        pending = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        approval = pending.json()
        rejected = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decide",
            headers=_headers(OWNER),
            json={"decision": "REJECT", "note": "price is wrong"},
        )
        assert rejected.status_code == 200, rejected.text
        assert rejected.json()["status"] == "REJECTED"
        assert rejected.json()["termination_reason"] == "OWNER_REJECTED"

        no_note = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decide",
            headers=_headers(OWNER),
            json={"decision": "REJECT"},
        )
        assert no_note.status_code == 422
        assert no_note.json()["error_code"] == "REJECTION_REASON_REQUIRED"


def test_contract_read_endpoints_after_do(seeded_db):
    with _client(seeded_db) as client:
        customers = client.get("/api/v1/customers", headers=_headers(CLERK))
        assert customers.status_code == 200, customers.text
        assert customers.json()["items"][0]["customer_id"] == "CUS_T1"

        drafts = client.get("/api/v1/orders/drafts", headers=_headers(CLERK))
        assert drafts.status_code == 200, drafts.text
        assert any(item["draft_id"] == "DRF_T1" for item in drafts.json()["items"])

        detail = client.get("/api/v1/orders/drafts/DRF_T1", headers=_headers(CLERK))
        assert detail.status_code == 200, detail.text
        assert detail.json()["draft_id"] == "DRF_T1"

        saved = _put(client, lines=[_line(1)])
        assert saved.status_code == 200, saved.text
        approved = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        do_number = approved.json()["do_number"]

        audit = client.get(f"/api/v1/orders/{do_number}/audit-detail", headers=_headers(CLERK))
        assert audit.status_code == 200, audit.text
        assert audit.json()["final_snapshot"]["do_number"] == do_number
        assert audit.json()["events"]

        activity = client.get("/api/v1/activity", headers=_headers(CLERK))
        assert activity.status_code == 200, activity.text
        assert activity.json()["items"]

        warehouse = client.get(
            f"/api/v1/warehouse/delivery-orders/{do_number}",
            headers=_headers(WAREHOUSE),
        )
        assert warehouse.status_code == 200, warehouse.text
        body = warehouse.json()
        assert body["items"][0]["sku_id"] == "SKU_MILO_1KG"
        assert "final_total_rm" not in body
        assert "applied_unit_price" not in body

        status = client.get("/api/v1/ai/status", headers=_headers(CLERK))
        assert status.status_code == 200
        assert status.json()["state"] == "OFFLINE"
        wake = client.post("/api/v1/ai/wake", headers=_headers(CLERK))
        assert wake.status_code == 200
        assert wake.json()["accepted"] is False


def test_parse_propagates_mixed_row_sources(seeded_db):
    from app.extraction.base import RawExtraction, RawRow

    class SourceProvider:
        def extract(self, masked_text, language_hint, request_id):
            return RawExtraction(
                rows=(
                    RawRow(
                        span="Milo 5 ctn",
                        qty=5,
                        uom="ctn",
                        fam="FAM_MILO",
                        source="LLM_EXTRACTED",
                    ),
                    RawRow(
                        span="Milo 2 ctn",
                        qty=2,
                        uom="ctn",
                        fam="FAM_MILO",
                        source="RAPIDFUZZ_FALLBACK",
                    ),
                )
            )

    app = create_app(seeded_db)
    app.state.extraction_provider = SourceProvider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn\nMilo 2 ctn"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_mode"] == "MIXED"
    assert {line["match_source"] for line in body["lines"]} == {
        "LLM_EXTRACTED",
        "RAPIDFUZZ_FALLBACK",
    }


def test_parse_isolates_invalid_row_instead_of_503(seeded_db):
    from app.extraction.base import RawExtraction, RawRow

    class BadRowProvider:
        def extract(self, masked_text, language_hint, request_id):
            return RawExtraction(
                rows=(
                    RawRow(
                        span="Milo 5 ctn",
                        qty=5,
                        uom="ctn",
                        fam="FAM_MILO",
                    ),
                    RawRow(
                        span="span-not-present",
                        qty=1,
                        uom="ctn",
                        fam="FAM_MILO",
                    ),
                )
            )

    app = create_app(seeded_db)
    app.state.extraction_provider = BadRowProvider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["lines"]) == 1
    assert body["lines"][0]["sku_id"] == "SKU_MILO_1KG"
    assert any(issue["reason_code"] == "SOURCE_EVIDENCE_INVALID" for issue in body["issues"])


def test_parse_marks_all_fallback_rows(seeded_db):
    from app.extraction.base import RawExtraction, RawRow

    class FallbackProvider:
        def extract(self, masked_text, language_hint, request_id):
            return RawExtraction(
                rows=(
                    RawRow(
                        span="Milo 5 ctn",
                        qty=5,
                        uom="ctn",
                        fam="FAM_MILO",
                        source="RAPIDFUZZ_FALLBACK",
                    ),
                )
            )

    app = create_app(seeded_db)
    app.state.extraction_provider = FallbackProvider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_mode"] == "FALLBACK"
    assert body["lines"][0]["match_source"] == "RAPIDFUZZ_FALLBACK"


def test_parse_all_invalid_rows_becomes_fallback_not_503(seeded_db):
    from app.extraction.base import RawExtraction, RawRow

    class AllBadProvider:
        def extract(self, masked_text, language_hint, request_id):
            return RawExtraction(rows=(RawRow(span="not-present", qty=1),))

    app = create_app(seeded_db)
    app.state.extraction_provider = AllBadProvider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_mode"] == "FALLBACK"
    assert body["lines"] == []
    assert any(issue["reason_code"] == "SOURCE_EVIDENCE_INVALID" for issue in body["issues"])


def test_ai_status_probe_wake_transition_and_rate_limit(seeded_db):
    seeded_db.ai_service_url = "https://ai.test/extract"
    seeded_db.ai_health_url = "https://ai.test/health"
    seeded_db.ai_wake_url = "https://ai.test/wake"
    seeded_db.ai_warmup_grace_s = 0
    seeded_db.ai_wake_rate_limit_s = 60
    calls = []

    def handler(request):
        calls.append((request.method, str(request.url)))
        if request.method == "GET":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(200, json={"status": "warming"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    app = create_app(seeded_db)
    app.state.ai_orchestrator = AiOrchestrator(seeded_db, client=client)
    try:
        with TestClient(app) as api:
            status = api.get("/api/v1/ai/status", headers=_headers(CLERK))
            assert status.status_code == 200
            assert status.json()["state"] == "READY"
            assert status.json()["available_modes"] == ["LLM", "FALLBACK", "ALIAS_ONLY"]
            assert status.json()["fallback_available"] is True

            wake = api.post("/api/v1/ai/wake", headers=_headers(CLERK))
            assert wake.status_code == 200
            assert wake.json()["accepted"] is True
            assert wake.json()["state"] == "WARMING"

            after = api.get("/api/v1/ai/status", headers=_headers(CLERK))
            assert after.json()["state"] == "READY"

            limited = api.post("/api/v1/ai/wake", headers=_headers(CLERK))
            assert limited.status_code == 429
            assert limited.json()["error_code"] == "RATE_LIMITED"
            assert limited.json()["details"]["scope"] == "AI_WAKE"
            assert limited.headers["Retry-After"]
    finally:
        client.close()
    assert ("GET", "https://ai.test/health") in calls
    assert ("POST", "https://ai.test/wake") in calls


def test_ai_wake_failure_returns_degraded_not_ready(seeded_db):
    seeded_db.ai_service_url = "https://ai.test/extract"
    seeded_db.ai_health_url = "https://ai.test/health"
    seeded_db.ai_wake_url = "https://ai.test/wake"

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200)
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    app = create_app(seeded_db)
    app.state.ai_orchestrator = AiOrchestrator(seeded_db, client=client)
    try:
        with TestClient(app) as api:
            wake = api.post("/api/v1/ai/wake", headers=_headers(CLERK))
            assert wake.status_code == 200
            assert wake.json()["accepted"] is False
            assert wake.json()["state"] == "DEGRADED"
            assert wake.json()["fallback_available"] is True
    finally:
        client.close()


def test_ai_status_offline_without_endpoint(seeded_db):
    seeded_db.ai_service_url = None
    with TestClient(create_app(seeded_db)) as api:
        status = api.get("/api/v1/ai/status", headers=_headers(CLERK)).json()
        wake = api.post("/api/v1/ai/wake", headers=_headers(CLERK)).json()
    assert status["state"] == "OFFLINE"
    assert status["available_modes"] == ["FALLBACK", "ALIAS_ONLY"]
    assert status["fallback_available"] is True
    assert wake["state"] == "OFFLINE"
    assert wake["accepted"] is False
    assert wake["fallback_available"] is True


def test_clerk_discards_ready_draft_with_audit(seeded_db):
    with _client(seeded_db) as client:
        saved = _put(client)
        assert saved.status_code == 200
        assert "CANCEL_DRAFT" in saved.json()["allowed_actions"]

        discarded = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(CLERK),
            json={
                "expected_version": 2,
                "note": "Customer cancelled; call +60 12-345 6789",
            },
        )
        assert discarded.status_code == 200, discarded.text
        draft = discarded.json()
        assert draft["status"] == "REJECTED"
        assert draft["termination_reason"] == "CLERK_DISCARDED"
        assert draft["terminated_by_user_id"] == "USR_T1_CLERK"
        assert "[REDACTED_PHONE]" in draft["termination_note"]
        assert draft["allowed_actions"] == ["VIEW_ACTIVITY"]

        fetched = client.get("/api/v1/orders/drafts/DRF_T1", headers=_headers(CLERK))
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "REJECTED"
        assert fetched.json()["termination_reason"] == "CLERK_DISCARDED"

        again = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(CLERK),
            json={"expected_version": 2, "note": "again"},
        )
        assert again.status_code == 409
        assert again.json()["error_code"] == "DRAFT_REJECTED"

        blocked = _put(client)
        assert blocked.status_code == 409
        assert blocked.json()["error_code"] == "DRAFT_REJECTED"

    with connect(seeded_db) as conn:
        row = conn.execute(
            "SELECT status, version, termination_reason, terminated_by_user_id, termination_note "
            "FROM orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()
        audit = conn.execute(
            "SELECT action, payload FROM audit_logs "
            "WHERE tenant_id='T1' AND draft_id='DRF_T1' AND action='CANCEL_DRAFT'"
        ).fetchone()
    assert row[0] == "REJECTED"
    assert row[1] == 2
    assert row[2] == "CLERK_DISCARDED"
    assert row[3] == "USR_T1_CLERK"
    assert "[REDACTED_PHONE]" in row[4]
    assert audit is not None
    assert audit[0] == "CANCEL_DRAFT"
    assert "[REDACTED_PHONE]" in audit[1]["note"]


def test_discard_requires_note_and_current_version(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client).status_code == 200
        missing = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert missing.status_code == 400
        assert missing.json()["error_code"] == "NOTE_REQUIRED"

        stale = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(CLERK),
            json={"expected_version": 1, "note": "duplicate"},
        )
        assert stale.status_code == 409
        assert stale.json()["error_code"] == "STALE_VERSION"

        denied = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(WAREHOUSE),
            json={"expected_version": 2, "note": "duplicate"},
        )
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "FORBIDDEN_ACTION"


def test_discard_is_blocked_while_pending(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        pending = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert pending.status_code == 202, pending.text
        blocked_pending = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(CLERK),
            json={"expected_version": 2, "note": "duplicate"},
        )
        assert blocked_pending.status_code == 409
        assert blocked_pending.json()["error_code"] == "PENDING_OWNER_APPROVAL"


def test_discard_is_blocked_after_approval(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client).status_code == 200
        approved = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert approved.status_code == 200, approved.text
        blocked_approved = client.post(
            "/api/v1/orders/drafts/DRF_T1/discard",
            headers=_headers(CLERK),
            json={"expected_version": 2, "note": "duplicate"},
        )
        assert blocked_approved.status_code == 409
        assert blocked_approved.json()["error_code"] == "ALREADY_APPROVED"


def test_clarification_copy_event_binds_draft_line_and_issue(seeded_db):
    with _client(seeded_db) as client:
        saved = _put(client, lines=[_line(11)])
        assert saved.status_code == 200
        body = saved.json()
        assert body["clarification_draft"] is not None
        issue_ids = body["clarification_draft"]["unresolved_issue_ids"]
        assert issue_ids

        first = client.post(
            "/api/v1/orders/drafts/DRF_T1/clarification-copied",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert first.status_code == 200, first.text
        assert first.json() == {"recorded": True}

        second = client.post(
            "/api/v1/orders/drafts/DRF_T1/clarification-copied",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert second.status_code == 200, second.text

        stale = client.post(
            "/api/v1/orders/drafts/DRF_T1/clarification-copied",
            headers=_headers(CLERK),
            json={"expected_version": 1},
        )
        assert stale.status_code == 409
        assert stale.json()["error_code"] == "STALE_VERSION"

        denied = client.post(
            "/api/v1/orders/drafts/DRF_T1/clarification-copied",
            headers=_headers(WAREHOUSE),
            json={"expected_version": 2},
        )
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "FORBIDDEN_ACTION"

    with connect(seeded_db) as conn:
        rows = conn.execute(
            "SELECT event_type, payload, actor_user_id, draft_id FROM activity_log "
            "WHERE tenant_id='T1' AND draft_id='DRF_T1' "
            "AND event_type='CLARIFICATION_COPIED' ORDER BY activity_id"
        ).fetchall()
        audit = conn.execute(
            "SELECT action, payload FROM audit_logs "
            "WHERE tenant_id='T1' AND draft_id='DRF_T1' "
            "AND action='COPY_CLARIFICATION' ORDER BY created_at"
        ).fetchall()
        order = conn.execute(
            "SELECT status, version FROM orders WHERE tenant_id='T1' AND draft_id='DRF_T1'"
        ).fetchone()
    assert len(rows) == 2
    assert len(audit) == 2
    assert order == ("DISAMBIGUATION_REQUIRED", 2)
    payload = rows[0][1]
    assert rows[0][0] == "CLARIFICATION_COPIED"
    assert rows[0][2] == "USR_T1_CLERK"
    assert rows[0][3] == "DRF_T1"
    assert payload["draft_version"] == 2
    assert payload["issue_ids"] == issue_ids
    assert payload["line_ids"]
    assert payload["language"] in {"ms", "en", "zh"}
    assert len(payload["message_sha256"]) == 64
    assert "message" not in payload


def test_clarification_copy_requires_available_clarification(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client).status_code == 200
        response = client.post(
            "/api/v1/orders/drafts/DRF_T1/clarification-copied",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"


def test_same_day_add_on_requires_explicit_do_and_persists(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client).status_code == 200
        first = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
        assert first.status_code == 200, first.text
        original = first.json()["do_number"]

        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        )
        assert parsed.status_code == 200, parsed.text
        draft_id = parsed.json()["draft_id"]
        saved = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=_headers(CLERK),
            json={"expected_version": 1, "lines": [_line(1)]},
        )
        assert saved.status_code == 200, saved.text
        issue = next(i for i in saved.json()["issues"] if i["code"] == "SAME_DAY_ORDER")
        assert original in issue["data_used"]["existing_do_numbers"]
        working_line = _line(
            1,
            line_id=saved.json()["lines"][0]["line_id"],
            client_line_ref=None,
        )

        missing = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=_headers(CLERK),
            json={
                "expected_version": 2,
                "lines": [working_line],
                "resolutions": [
                    {
                        "issue_id": issue["issue_id"],
                        "choice": "SEPARATE_ADD_ON",
                        "target_line_ids": [],
                    }
                ],
            },
        )
        assert missing.status_code == 422

        resolved = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=_headers(CLERK),
            json={
                "expected_version": 2,
                "lines": [working_line],
                "resolutions": [
                    {
                        "issue_id": issue["issue_id"],
                        "choice": "SEPARATE_ADD_ON",
                        "target_line_ids": [],
                        "related_do_number": original,
                        "note": "Separate add-on",
                    }
                ],
            },
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["status"] == "READY_FOR_APPROVAL"
        resolved_issue = next(i for i in resolved.json()["issues"] if i["code"] == "SAME_DAY_ORDER")
        assert resolved_issue["resolved"] is True
        assert resolved_issue["resolution"] == "SEPARATE_ADD_ON"
        assert resolved_issue["data_used"]["related_do_number"] == original

        carried = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=_headers(CLERK),
            json={"expected_version": 3, "lines": [working_line]},
        )
        assert carried.status_code == 200, carried.text
        carried_issue = next(i for i in carried.json()["issues"] if i["code"] == "SAME_DAY_ORDER")
        assert carried_issue["resolved"] is True
        assert carried_issue["data_used"]["related_do_number"] == original

        approved = client.post(
            f"/api/v1/orders/{draft_id}/approve",
            headers=_headers(CLERK),
            json={"expected_version": 4},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["related_do_number"] == original


def test_same_day_check_ignores_unapproved_draft(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client).status_code == 200
        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        )
        draft_id = parsed.json()["draft_id"]
        saved = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=_headers(CLERK),
            json={"expected_version": 1, "lines": [_line(1)]},
        )
        assert saved.status_code == 200, saved.text
        assert not any(issue["code"] == "SAME_DAY_ORDER" for issue in saved.json()["issues"])
