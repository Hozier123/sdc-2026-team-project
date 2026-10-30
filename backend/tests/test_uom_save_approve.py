"""D02 UOM blocking on the save and approve paths (integration).

The parse path is covered without a database in test_d02_uom_blocking.py.
These tests close the loop: a clerk may select a SKU, but a mixed-base-unit
family still needs an explicit unit before the draft can become READY, and the
approve endpoint has independent gates for status, blocking issues and line.uom.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_token
from app.db import connect
from app.extraction.base import RawExtraction, RawRow
from app.main import create_app
from app.migrations import migrate

pytestmark = pytest.mark.integration

T1_CLERK = "tok_t1_clerk"
T2_CLERK = "tok_t2_clerk"


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
            "('USR_T2_CLERK', 'T2', 'T2 Clerk', %s, 'CLERK')",
            (hash_token(T1_CLERK), hash_token(T2_CLERK)),
        )
        conn.execute(
            "INSERT INTO customers (customer_id, tenant_id, name, tier, credit_flag) VALUES "
            "('CUS_T1', 'T1', 'Customer One', 'A', 'NONE'), "
            "('CUS_T2', 'T2', 'Customer Two', 'A', 'NONE')"
        )
        conn.execute(
            "INSERT INTO product_families (family_id, tenant_id, family_name) VALUES "
            "('FAM_BAWANG', 'T1', 'Bawang besar India'), "
            "('FAM_MINYAK', 'T1', 'Minyak masak'), "
            "('FAM_T2_MINYAK', 'T2', 'Minyak masak')"
        )
        conn.execute(
            "INSERT INTO family_aliases "
            "(alias_id, tenant_id, family_id, language, phrase, phrase_norm) VALUES "
            "('ALS_FAM_T1_BAWANG', 'T1', 'FAM_BAWANG', NULL, 'Bawang', 'bawang'), "
            "('ALS_FAM_T1_MINYAK', 'T1', 'FAM_MINYAK', NULL, 'Minyak', 'minyak'), "
            "('ALS_FAM_T2_MINYAK', 'T2', 'FAM_T2_MINYAK', NULL, 'Minyak', 'minyak')"
        )
        conn.execute(
            "INSERT INTO products "
            "(product_id, tenant_id, family_id, sku_code, name, pack_size, grade, base_unit) "
            "VALUES "
            "('SKU_BAWANG_KG', 'T1', 'FAM_BAWANG', 'SKU_BAWANG_KG', "
            "'Bawang bulk', '散装', NULL, 'kg'), "
            "('SKU_BAWANG_10KG', 'T1', 'FAM_BAWANG', 'SKU_BAWANG_10KG', "
            "'Bawang 10kg', '10kg', NULL, 'bag'), "
            "('SKU_MINYAK_5KG', 'T1', 'FAM_MINYAK', 'SKU_MINYAK_5KG', "
            "'Minyak 5kg', '5kg', NULL, 'btl'), "
            "('SKU_MINYAK_17KG', 'T1', 'FAM_MINYAK', 'SKU_MINYAK_17KG', "
            "'Minyak 17kg', '17kg', NULL, 'pail'), "
            "('SKU_T2_MINYAK_5KG', 'T2', 'FAM_T2_MINYAK', 'SKU_T2_MINYAK_5KG', "
            "'Minyak 5kg', '5kg', NULL, 'btl')"
        )
        conn.execute(
            "INSERT INTO customer_tier_prices "
            "(tenant_id, product_id, tier, unit_price_rm) VALUES "
            "('T1', 'SKU_BAWANG_KG', 'A', 3.50), "
            "('T1', 'SKU_BAWANG_10KG', 'A', 32.00), "
            "('T1', 'SKU_MINYAK_5KG', 'A', 29.00), "
            "('T1', 'SKU_MINYAK_17KG', 'A', 94.00), "
            "('T2', 'SKU_T2_MINYAK_5KG', 'A', 29.00)"
        )
        conn.execute(
            "INSERT INTO inventory (tenant_id, product_id, available_qty) VALUES "
            "('T1', 'SKU_BAWANG_KG', 40), "
            "('T1', 'SKU_BAWANG_10KG', 15), "
            "('T1', 'SKU_MINYAK_5KG', 25), "
            "('T1', 'SKU_MINYAK_17KG', 15), "
            "('T2', 'SKU_T2_MINYAK_5KG', 25)"
        )
        conn.execute(
            "INSERT INTO uom_aliases "
            "(alias_id, tenant_id, canonical_unit, language, alias, alias_norm) VALUES "
            "('ALS_UOM_T1_BOTOL', 'T1', 'btl', NULL, 'botol', 'botol'), "
            "('ALS_UOM_T1_PAIL', 'T1', 'pail', NULL, 'pail', 'pail'), "
            "('ALS_UOM_T1_KG', 'T1', 'kg', NULL, 'kg', 'kg'), "
            "('ALS_UOM_T1_BAG', 'T1', 'bag', NULL, 'bag', 'bag'), "
            "('ALS_UOM_T2_BOTOL', 'T2', 'btl', NULL, 'botol', 'botol')"
        )
    return db_settings


def _provider(row: RawRow):
    class Provider:
        def extract(self, masked_text, language_hint, request_id):
            return RawExtraction(rows=(row,))

    return Provider()


def _parse_row(settings, row: RawRow, text: str, *, customer="CUS_T1", token=T1_CLERK):
    app = create_app(settings)
    app.state.extraction_provider = _provider(row)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"customer_id": customer, "message_text": text},
        )
    assert response.status_code == 200, response.text
    return response.json()


def _put(client, draft_id, version, line, *, token=T1_CLERK):
    return client.put(
        f"/api/v1/orders/drafts/{draft_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"expected_version": version, "lines": [line]},
    )


def _approve(client, draft_id, version, *, token=T1_CLERK, confirmed_items=None):
    body = {"expected_version": version}
    if confirmed_items is not None:
        body["confirmed_items"] = confirmed_items
    return client.post(
        f"/api/v1/orders/{draft_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )


def test_save_without_uom_keeps_missing_uom_blocking_and_approve_rejects(seeded_db):
    draft = _parse_row(
        seeded_db,
        RawRow(
            span="Bawang Bsr India 10kg",
            qty=10,
            uom=None,
            fam="FAM_BAWANG",
            pack_size="10kg",
        ),
        "Bawang Bsr India 10kg",
    )
    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    assert draft["lines"][0]["uom"] is None
    assert "APPROVE_AND_GENERATE_DO" in draft["blocked_actions"]
    line_id = draft["lines"][0]["line_id"]

    with TestClient(create_app(seeded_db)) as client:
        # Selecting the bulk SKU is allowed, but omitting the unit must not
        # silently derive "kg" from the SKU and clear the blocker.
        saved = _put(
            client,
            draft["draft_id"],
            1,
            {
                "line_id": line_id,
                "sku_id": "SKU_BAWANG_KG",
                "confirmed_qty": 10,
                "match_source": "MANUAL_SELECTED",
            },
        )
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["version"] == 2
        assert body["status"] == "DISAMBIGUATION_REQUIRED"
        assert body["lines"][0]["sku_id"] == "SKU_BAWANG_KG"
        assert body["lines"][0]["uom"] is None
        assert "MISSING_UOM" in body["blocking_issues"]
        assert "MISSING_UOM" in body["blocked_actions"]["APPROVE_AND_GENERATE_DO"]

        blocked = _approve(client, draft["draft_id"], 2)
        assert blocked.status_code == 400, blocked.text
        assert blocked.json()["error_code"] == "DISAMBIGUATION_UNRESOLVED"

        # The clerk now confirms the unit explicitly; the same SKU resolves.
        saved = _put(
            client,
            draft["draft_id"],
            2,
            {
                "line_id": line_id,
                "sku_id": "SKU_BAWANG_KG",
                "confirmed_qty": 10,
                "uom": "kg",
                "match_source": "MANUAL_SELECTED",
            },
        )
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["version"] == 3
        assert body["status"] == "READY_FOR_APPROVAL"
        assert body["lines"][0]["uom"] == "kg"
        assert body["blocked_actions"] == {}
        assert "APPROVE_AND_GENERATE_DO" in body["allowed_actions"]

        approved = _approve(client, draft["draft_id"], 3)
        assert approved.status_code == 200, approved.text
        assert approved.json()["final_total_rm"] == "35.00"


def test_approve_confirmed_items_cannot_bypass_missing_uom(seeded_db):
    draft = _parse_row(
        seeded_db,
        RawRow(
            span="Bawang Bsr India 10kg",
            qty=10,
            uom=None,
            fam="FAM_BAWANG",
            pack_size="10kg",
        ),
        "Bawang Bsr India 10kg",
    )

    with TestClient(create_app(seeded_db)) as client:
        blocked = _approve(
            client,
            draft["draft_id"],
            1,
            confirmed_items=[
                {
                    "line_id": draft["lines"][0]["line_id"],
                    "sku_id": "SKU_BAWANG_10KG",
                    "confirmed_qty": 10,
                    "match_source": "MANUAL_SELECTED",
                }
            ],
        )
        assert blocked.status_code == 400, blocked.text
        assert blocked.json()["error_code"] == "DISAMBIGUATION_UNRESOLVED"

    with connect(seeded_db) as conn:
        assert conn.execute("SELECT version FROM orders").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM delivery_orders").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM draft_versions").fetchone()[0] == 1


def test_tenant_alias_botol_and_pail_do_not_leak_across_tenants(seeded_db):
    t1_pail = _parse_row(
        seeded_db,
        RawRow(
            span="1 pail Minyak 17kg",
            qty=1,
            uom="pail",
            fam="FAM_MINYAK",
            pack_size="17kg",
        ),
        "1 pail Minyak 17kg",
    )
    assert t1_pail["status"] == "READY_FOR_APPROVAL"
    assert t1_pail["lines"][0]["sku_id"] == "SKU_MINYAK_17KG"
    assert t1_pail["lines"][0]["uom"] == "pail"

    t1_botol = _parse_row(
        seeded_db,
        RawRow(
            span="4 botol minyak 5kg",
            qty=4,
            uom="botol",
            fam="FAM_MINYAK",
            pack_size="5kg",
        ),
        "4 botol minyak 5kg",
    )
    assert t1_botol["status"] == "READY_FOR_APPROVAL"
    assert t1_botol["lines"][0]["sku_id"] == "SKU_MINYAK_5KG"
    assert t1_botol["lines"][0]["uom"] == "btl"

    # T2 has btl/botol but no pail alias and no pail SKU.
    t2_pail = _parse_row(
        seeded_db,
        RawRow(
            span="1 pail Minyak 17kg",
            qty=1,
            uom="pail",
            fam="FAM_T2_MINYAK",
            pack_size="17kg",
        ),
        "1 pail Minyak 17kg",
        customer="CUS_T2",
        token=T2_CLERK,
    )
    assert t2_pail["status"] == "DISAMBIGUATION_REQUIRED"
    assert t2_pail["lines"][0]["uom"] is None
    assert t2_pail["lines"][0]["sku_id"] is None
    assert "APPROVE_AND_GENERATE_DO" in t2_pail["blocked_actions"]

    t2_botol = _parse_row(
        seeded_db,
        RawRow(
            span="4 botol minyak 5kg",
            qty=4,
            uom="botol",
            fam="FAM_T2_MINYAK",
            pack_size="5kg",
        ),
        "4 botol minyak 5kg",
        customer="CUS_T2",
        token=T2_CLERK,
    )
    assert t2_botol["status"] == "READY_FOR_APPROVAL"
    assert t2_botol["lines"][0]["sku_id"] == "SKU_T2_MINYAK_5KG"
    assert t2_botol["lines"][0]["uom"] == "btl"
