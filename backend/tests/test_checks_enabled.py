"""B31 tenant checks_enabled integration tests."""

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token
from app.db import connect
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration

TOKEN = "tok_b31_clerk"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-Request-ID": "b31"}


@pytest.fixture
def b31_db(db_settings):
    migrate(db_settings)
    with connect(db_settings) as conn:
        conn.execute(
            "INSERT INTO tenants "
            "(tenant_id, name, amount_threshold_rm, checks_enabled) "
            "VALUES ('T1', 'Tenant One', 10, %s::jsonb)",
            ('{"customer_condition": true, "same_day_order": true, "unusual_qty": false}',),
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
            "VALUES ('T1', 'SKU_MILO_1KG', 100)"
        )
    return db_settings


def _set_checks(settings, checks: dict):
    import json

    with connect(settings) as conn:
        conn.execute(
            "UPDATE tenants SET checks_enabled=%s::jsonb WHERE tenant_id='T1'",
            (json.dumps(checks),),
        )


def _ready_draft(client, text="Milo 1 ctn") -> str:
    parsed = client.post(
        "/api/v1/orders/parse-draft",
        headers=HEADERS,
        json={"customer_id": "CUS_T1", "message_text": text},
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
                    "client_line_ref": "b31-line",
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


def _approve_ready(client, draft_id: str):
    response = client.post(
        f"/api/v1/orders/{draft_id}/approve",
        headers=HEADERS,
        json={"expected_version": 2},
    )
    assert response.status_code == 200, response.text
    return response.json()


class ConditionalProvider:
    def extract(self, text, language, request_id):
        from app.extraction.ai import to_raw_extraction

        return to_raw_extraction(
            {
                "rows": [
                    {
                        "span": "Milo 1 ctn",
                        "qty": 1,
                        "uom": "ctn",
                        "fam": "FAM_MILO",
                        "conds": ["kalau RM4 untuk 1 ctn"],
                    }
                ],
                "ignored_spans": [],
            },
            text,
        )


class QuantityProvider:
    def extract(self, text, language, request_id):
        from app.extraction.base import RawExtraction, RawRow

        return RawExtraction(rows=(RawRow(span="Milo 10 ctn", qty=10, uom="ctn", fam="FAM_MILO"),))


class OneProvider:
    def extract(self, text, language, request_id):
        from app.extraction.base import RawExtraction, RawRow

        return RawExtraction(rows=(RawRow(span="Milo 1 ctn", qty=1, uom="ctn", fam="FAM_MILO"),))


def test_customer_condition_switch_controls_h5(b31_db):
    _set_checks(b31_db, {"customer_condition": False})
    app = create_app(b31_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=HEADERS,
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn kalau RM4 untuk 1 ctn"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conditions"] == []
    assert not any(issue["code"] == "CUSTOMER_CONDITION" for issue in body["issues"])
    assert body["status"] == "READY_FOR_APPROVAL"


def test_same_day_order_switch_controls_existing_do_check(b31_db):
    _set_checks(b31_db, {"same_day_order": False})
    disabled_app = create_app(b31_db)
    disabled_app.state.extraction_provider = OneProvider()
    with TestClient(disabled_app) as client:
        first = _ready_draft(client)
        _approve_ready(client, first)

        disabled = client.post(
            "/api/v1/orders/parse-draft",
            headers=HEADERS,
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        )
        assert disabled.status_code == 200
        assert not any(issue["code"] == "SAME_DAY_ORDER" for issue in disabled.json()["issues"])

    _set_checks(b31_db, {"same_day_order": True})
    app = create_app(b31_db)
    app.state.extraction_provider = OneProvider()
    with TestClient(app) as client:
        enabled = client.post(
            "/api/v1/orders/parse-draft",
            headers=HEADERS,
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        )
    assert enabled.status_code == 200
    assert any(issue["code"] == "SAME_DAY_ORDER" for issue in enabled.json()["issues"])


def test_unusual_qty_switch_controls_history_check(b31_db):
    _set_checks(b31_db, {"same_day_order": False, "unusual_qty": False})
    with TestClient(create_app(b31_db)) as client:
        for _ in range(3):
            _approve_ready(client, _ready_draft(client))

    app = create_app(b31_db)
    app.state.extraction_provider = QuantityProvider()
    with TestClient(app) as client:
        disabled = client.post(
            "/api/v1/orders/parse-draft",
            headers=HEADERS,
            json={"customer_id": "CUS_T1", "message_text": "Milo 10 ctn"},
        )
    assert disabled.status_code == 200
    assert not any(issue["code"] == "UNUSUAL_QTY" for issue in disabled.json()["issues"])

    _set_checks(b31_db, {"same_day_order": False, "unusual_qty": True})
    app = create_app(b31_db)
    app.state.extraction_provider = QuantityProvider()
    with TestClient(app) as client:
        enabled = client.post(
            "/api/v1/orders/parse-draft",
            headers=HEADERS,
            json={"customer_id": "CUS_T1", "message_text": "Milo 10 ctn"},
        )
    assert enabled.status_code == 200
    assert any(issue["code"] == "UNUSUAL_QTY" for issue in enabled.json()["issues"])


def test_soft_checks_cannot_disable_stock_hard_rule(b31_db):
    _set_checks(
        b31_db,
        {"customer_condition": False, "same_day_order": False, "unusual_qty": False},
    )
    with connect(b31_db) as conn:
        conn.execute("UPDATE inventory SET available_qty=0 WHERE product_id='SKU_MILO_1KG'")
    with TestClient(create_app(b31_db)) as client:
        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=HEADERS,
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        )
        draft_id = parsed.json()["draft_id"]
        saved = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=HEADERS,
            json={
                "expected_version": 1,
                "lines": [
                    {
                        "client_line_ref": "b31-hard-stock",
                        "sku_id": "SKU_MILO_1KG",
                        "confirmed_qty": 1,
                        "uom": "ctn",
                        "match_source": "MANUAL_SELECTED",
                    }
                ],
            },
        )
    assert saved.status_code == 200
    body = saved.json()
    assert "INSUFFICIENT_STOCK" in body["blocking_issues"]
    assert body["status"] == "DISAMBIGUATION_REQUIRED"
