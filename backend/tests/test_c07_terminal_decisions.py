"""C07: replaying either decision must report the actual terminal state without writes."""

import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.auth import hash_token
from app.db import connect
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration
TOKENS = {"CLERK": "c07-regression-clerk", "OWNER": "c07-regression-owner"}


@pytest.fixture
def c07_owner_db(db_settings):
    migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants(tenant_id,name,amount_threshold_rm) VALUES('T1','C07',10)"
        )
        for role, token in TOKENS.items():
            conn.execute(
                "INSERT INTO users(user_id,tenant_id,display_name,demo_token_hash,role) "
                "VALUES(%s,'T1',%s,%s,%s)",
                ("USR_" + role, role, hash_token(token), role),
            )
        conn.execute(
            "INSERT INTO customers(customer_id,tenant_id,name,tier) "
            "VALUES('CUS_C07','T1','C07 customer','A')"
        )
        conn.execute(
            "INSERT INTO product_families(family_id,tenant_id,family_name) "
            "VALUES('FAM_MILO','T1','Milo')"
        )
        conn.execute(
            "INSERT INTO products(product_id,tenant_id,family_id,sku_code,name,base_unit) "
            "VALUES('SKU_C07','T1','FAM_MILO','SKU_C07','Milo 1kg','ctn')"
        )
        conn.execute(
            "INSERT INTO customer_tier_prices(tenant_id,product_id,tier,unit_price_rm) "
            "VALUES('T1','SKU_C07','A',5)"
        )
        conn.execute(
            "INSERT INTO inventory(tenant_id,product_id,available_qty) VALUES('T1','SKU_C07',10)"
        )
    return db_settings


def _snapshot(settings):
    tables = (
        "orders",
        "draft_versions",
        "approval_requests",
        "delivery_orders",
        "inventory",
        "audit_logs",
        "inbound_messages",
        "alias_cache",
    )
    with connect(settings) as conn:
        conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return {
            table: [
                row[0]
                for row in conn.execute(
                    sql.SQL("SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text").format(
                        sql.Identifier(table)
                    )
                ).fetchall()
            ]
            for table in tables
        }


@pytest.mark.parametrize("first_decision", ["APPROVE", "REJECT"])
@pytest.mark.parametrize("repeat_decision", ["APPROVE", "REJECT"])
def test_owner_terminal_decision_replay_is_correct_and_read_only(
    c07_owner_db, first_decision, repeat_decision
):
    clerk = {"Authorization": "Bearer " + TOKENS["CLERK"]}
    owner = {"Authorization": "Bearer " + TOKENS["OWNER"]}
    with TestClient(create_app(c07_owner_db)) as client:
        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=clerk,
            json={"customer_id": "CUS_C07", "message_text": "Milo 3 ctn"},
        )
        assert parsed.status_code == 200, parsed.text
        draft = parsed.json()["draft_id"]
        saved = client.put(
            f"/api/v1/orders/drafts/{draft}/lines",
            headers=clerk,
            json={
                "expected_version": 1,
                "lines": [
                    {
                        "client_line_ref": "c07",
                        "sku_id": "SKU_C07",
                        "confirmed_qty": 3,
                        "uom": "ctn",
                        "match_source": "MANUAL_SELECTED",
                    }
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        submitted = client.post(
            f"/api/v1/orders/{draft}/approve",
            headers=clerk,
            json={"expected_version": 2},
        )
        assert submitted.status_code == 202, submitted.text
        path = f"/api/v1/approvals/{submitted.json()['approval_id']}/decide"
        first = client.post(
            path,
            headers=owner,
            json={"decision": first_decision, "note": "C07 first"},
        )
        assert first.status_code == 200, first.text
        before = _snapshot(c07_owner_db)
        request_id = f"c07-terminal-{first_decision}-{repeat_decision}"
        repeated = client.post(
            path,
            headers={**owner, "X-Request-ID": request_id},
            json={"decision": repeat_decision, "note": "C07 repeat"},
        )
    approved = first_decision == "APPROVE"
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["error_code"] == ("ALREADY_APPROVED" if approved else "DRAFT_REJECTED")
    assert "waiting" not in repeated.json()["message"].lower()
    assert repeated.headers["X-Request-ID"] == request_id
    assert _snapshot(c07_owner_db) == before
    assert before["approval_requests"][0]["status"] == ("APPROVED" if approved else "REJECTED")
    assert before["orders"][0]["status"] == ("DO_GENERATED" if approved else "REJECTED")
    assert before["inventory"][0]["available_qty"] == (7 if approved else 10)
    assert len(before["delivery_orders"]) == int(approved)
    assert sum(row["action"] == "INVENTORY_DEDUCT" for row in before["audit_logs"]) == int(approved)
