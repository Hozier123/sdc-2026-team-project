"""B30 approval concurrency and failure-rollback integration tests."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token
from app.db import connect
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration

TOKEN = "tok_b30_clerk"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-Request-ID": "b30"}


@pytest.fixture
def b30_db(db_settings):
    migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, amount_threshold_rm) "
            "VALUES ('T1', 'Tenant One', 10)"
        )
        conn.execute(
            "INSERT INTO users (user_id, tenant_id, display_name, demo_token_hash, role) "
            "VALUES ('USR_T1_CLERK', 'T1', 'Clerk', %s, 'CLERK')",
            (hash_token(TOKEN),),
        )
        conn.execute(
            "INSERT INTO customers (customer_id, tenant_id, name, tier) "
            "VALUES ('CUS_T1', 'T1', 'Customer One', 'A')"
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
            "INSERT INTO customer_tier_prices (tenant_id, product_id, tier, unit_price_rm) "
            "VALUES ('T1', 'SKU_MILO_1KG', 'A', 5.00)"
        )
        conn.execute(
            "INSERT INTO inventory (tenant_id, product_id, available_qty) "
            "VALUES ('T1', 'SKU_MILO_1KG', 10)"
        )
    return db_settings


def _ready_draft(client) -> str:
    parsed = client.post(
        "/api/v1/orders/parse-draft",
        headers=HEADERS,
        json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
    )
    assert parsed.status_code == 200, parsed.text
    draft_id = parsed.json()["draft_id"]
    saved = client.put(
        f"/api/v1/orders/drafts/{draft_id}/lines",
        headers=HEADERS,
        json={
            "expected_version": 1,
            "lines": [
                {
                    "client_line_ref": "b30-line",
                    "sku_id": "SKU_MILO_1KG",
                    "confirmed_qty": 1,
                    "uom": "ctn",
                    "match_source": "MANUAL_SELECTED",
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "READY_FOR_APPROVAL"
    return draft_id


def _approve_concurrently(settings, draft_ids):
    barrier = Barrier(len(draft_ids))

    def run(draft_id):
        barrier.wait(timeout=10)
        with TestClient(create_app(settings)) as client:
            response = client.post(
                f"/api/v1/orders/{draft_id}/approve",
                headers=HEADERS,
                json={"expected_version": 2},
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=len(draft_ids)) as pool:
        return list(pool.map(run, draft_ids))


def test_two_orders_competing_for_last_stock_never_go_negative(b30_db):
    with TestClient(create_app(b30_db)) as client:
        first = _ready_draft(client)
        second = _ready_draft(client)
    with connect(b30_db) as conn:
        conn.execute("UPDATE inventory SET available_qty=1 WHERE product_id='SKU_MILO_1KG'")

    results = _approve_concurrently(b30_db, [first, second])
    statuses = sorted(status for status, _ in results)
    assert statuses == [200, 400], results
    failure = next(body for status, body in results if status == 400)
    assert failure["error_code"] == "INSUFFICIENT_STOCK"

    with connect(b30_db) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE draft_id IN (%s, %s)",
            (first, second),
        ).fetchone() == (1,)
        assert conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE draft_id IN (%s, %s) "
            "AND final_total_rm < 0",
            (first, second),
        ).fetchone() == (0,)


def test_same_draft_concurrent_approval_generates_one_do(b30_db):
    with TestClient(create_app(b30_db)) as client:
        draft_id = _ready_draft(client)

    results = _approve_concurrently(b30_db, [draft_id, draft_id])
    statuses = sorted(status for status, _ in results)
    assert statuses == [200, 409], results
    failure = next(body for status, body in results if status == 409)
    assert failure["error_code"] in {"ALREADY_APPROVED", "STALE_VERSION"}

    with connect(b30_db) as conn:
        assert conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE draft_id=%s", (draft_id,)
        ).fetchone() == (1,)
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (9,)


def test_failure_after_do_insert_rolls_back_whole_approval(b30_db, monkeypatch):
    with TestClient(create_app(b30_db)) as client:
        draft_id = _ready_draft(client)

    def fail_deduct(*args, **kwargs):
        raise RuntimeError("injected failure after DO insert")

    monkeypatch.setattr("app.approvals._deduct_stock", fail_deduct)
    with TestClient(create_app(b30_db), raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/orders/{draft_id}/approve",
            headers=HEADERS,
            json={"expected_version": 2},
        )
    assert response.status_code == 500

    with connect(b30_db) as conn:
        assert conn.execute(
            "SELECT status, version FROM orders WHERE tenant_id='T1' AND draft_id=%s",
            (draft_id,),
        ).fetchone() == ("READY_FOR_APPROVAL", 2)
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (10,)
        assert conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE draft_id=%s", (draft_id,)
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM audit_logs WHERE draft_id=%s AND event_type='DO_CREATED'",
            (draft_id,),
        ).fetchone() == (0,)
