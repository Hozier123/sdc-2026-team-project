import pytest
from fastapi.testclient import TestClient

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
            "VALUES ('SKU_MILO_1KG', 'T1', 'FAM_MILO', 'SKU_MILO_1KG', 'Milo 1kg', 'bag')"
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


def test_approve_rejects_confirmed_items_explicitly(seeded_db):
    with _client(seeded_db) as client:
        response = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={
                "expected_version": 1,
                "confirmed_items": [_line(1)],
            },
        )
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert body["details"]["fields"][0]["path"] == "confirmed_items"


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

    with connect(seeded_db) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (7,)


def test_owner_can_self_approve_escalation(seeded_db):
    with _client(seeded_db) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
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
