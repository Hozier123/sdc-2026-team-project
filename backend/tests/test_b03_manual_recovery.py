"""B03 API acceptance: recover synthetic orders on disposable PostgreSQL only."""

import pytest
from fastapi.testclient import TestClient
from test_backend_audit import ConditionalProvider, _conditional
from test_drafts_approve_do import CLERK, OWNER, WAREHOUSE, _headers, _line
from test_drafts_approve_do import seeded_db as seeded_db

from app.auth import hash_token
from app.db import connect
from app.extraction.base import RawExtraction, RawRow
from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def recovery_db(seeded_db):
    with connect(seeded_db) as conn:
        conn.execute(
            "INSERT INTO products "
            "(product_id, tenant_id, family_id, sku_code, name, base_unit, pack_size) VALUES "
            "('SKU_MILO_2KG','T1','FAM_MILO','MILO2','Milo 2kg','ctn','2kg')"
        )
        conn.execute(
            "INSERT INTO customer_tier_prices (tenant_id,product_id,tier,unit_price_rm) VALUES "
            "('T1','SKU_MILO_2KG','A',7), ('T1','SKU_MILO_1KG','B',6)"
        )
        conn.execute(
            "INSERT INTO inventory (tenant_id,product_id,available_qty) "
            "VALUES ('T1','SKU_MILO_2KG',8)"
        )
        conn.execute(
            "INSERT INTO users (user_id,tenant_id,display_name,demo_token_hash,role) "
            "VALUES ('USR_T2_CLERK','T2','Other tenant',%s,'CLERK')",
            (hash_token("b03-other-tenant"),),
        )
    return seeded_db


def _save(client, draft, lines, **extra):
    return client.put(
        f"/api/v1/orders/drafts/{draft['draft_id']}/lines",
        headers=_headers(CLERK),
        json={"expected_version": draft["version"], "lines": lines, **extra},
    )


def _existing(line, **changes):
    return {
        "line_id": line["line_id"],
        "sku_id": line["sku_id"],
        "confirmed_qty": line["effective_qty"],
        "uom": line["uom"],
        "match_source": "MANUAL_SELECTED",
        "unit_price_override": line["unit_price_override"],
        "override_reason": line["override_reason"],
        **changes,
    }


def _state(settings):
    """Compare every business row, including evidence, after rejected requests."""
    with connect(settings) as conn:
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ).fetchall()
        from psycopg import sql

        return {
            table: conn.execute(
                sql.SQL("SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text").format(
                    sql.Identifier(table)
                )
            ).fetchall()
            for (table,) in tables
        }


def _approve(client, draft):
    return client.post(
        f"/api/v1/orders/{draft['draft_id']}/approve",
        headers=_headers(CLERK),
        json={"expected_version": draft["version"]},
    )


def _parse(client, text="Unlisted product 2 ctn"):
    result = client.post(
        "/api/v1/orders/parse-draft",
        headers=_headers(CLERK),
        json={"customer_id": "CUS_T1", "message_text": text},
    )
    assert result.status_code == 200, result.text
    return result.json()


class UnmatchedProvider:
    def extract(self, text, language, request_id):
        return RawExtraction(rows=(RawRow(span=text, qty=2, uom="ctn"),))


class EmptyProvider:
    def extract(self, text, language, request_id):
        return RawExtraction()


def test_zero_line_recovery_preserves_evidence_and_only_approval_deducts_stock(recovery_db):
    app = create_app(recovery_db)
    app.state.extraction_provider = EmptyProvider()
    with TestClient(app) as client:
        draft = _parse(client, "Please confirm my order")
        assert draft["lines"] == []
        before = _state(recovery_db)
        directory = client.get("/api/v1/catalog/products", headers=_headers(CLERK))
        assert directory.status_code == 200
        assert "SKU_MILO_1KG" in {p["sku_id"] for p in directory.json()["items"]}
        saved = _save(client, draft, [_line()])
        assert saved.status_code == 200, saved.text
        draft = saved.json()
        line = draft["lines"][0]
        assert line["client_line_ref"] == "new-1"
        assert line["match_source"] == "MANUAL_SELECTED"
        assert line["source_span"] is None and line["field_evidence"] == []
        assert draft["masked_message"] == "Please confirm my order"
        assert draft["totals"]["order_total"] == "5.00"
        after_save = _state(recovery_db)
        for table in ("inventory", "delivery_orders", "approval_requests", "inbound_messages"):
            assert after_save[table] == before[table], table
        assert all(row in after_save["draft_versions"] for row in before["draft_versions"])
        initial = {row[0]["draft_id"]: row[0]["ai_initial_snapshot"] for row in before["orders"]}
        assert all(
            row[0]["ai_initial_snapshot"] == initial[row[0]["draft_id"]]
            for row in after_save["orders"]
        )
        do = _approve(client, draft)
        assert do.status_code == 200, do.text
        assert do.json()["final_total_rm"] == "5.00"
        assert do.json()["lines"][0]["quantity"] == 1
    with connect(recovery_db) as conn:
        assert conn.execute(
            "SELECT available_qty FROM inventory WHERE product_id='SKU_MILO_1KG'"
        ).fetchone() == (9,)


def test_no_candidate_reselection_keeps_original_source_and_line_identity(recovery_db):
    app = create_app(recovery_db)
    app.state.extraction_provider = UnmatchedProvider()
    with TestClient(app) as client:
        draft = _parse(client)
        original = draft["lines"][0]
        assert original["sku_id"] is None and original["candidate_skus"] == []
        saved = _save(client, draft, [_existing(original, sku_id="SKU_MILO_2KG", confirmed_qty=3)])
        assert saved.status_code == 200, saved.text
        result = saved.json()["lines"][0]
        for field in ("line_id", "source_span", "span_start", "span_end", "field_evidence"):
            assert result[field] == original[field], field
        assert result["requested_qty"] == 2 and result["effective_qty"] == 3
        assert result["pack_size"] == "2kg"
        assert result["tier_unit_price"] == "7.00" and result["subtotal_rm"] == "21.00"
        assert saved.json()["version"] == draft["version"] + 1


@pytest.mark.parametrize(
    "patch",
    [
        {"sku_id": None},
        {"sku_id": ""},
        {"match_source": "LLM_EXTRACTED"},
        {"match_source": "RAPIDFUZZ_FALLBACK"},
        {"match_source": "SUGGESTED_DEFAULT"},
        {"client_line_ref": "   "},
        {"confirmed_qty": None},
        {"confirmed_qty": True},
        {"confirmed_qty": 1.5},
        {"confirmed_qty": 0},
        {"confirmed_qty": "2"},
        {"subtotal_rm": "0.01"},
        {"available_qty": 999},
        {"tier_unit_price": "0.01"},
        {"source_span": "invented source"},
    ],
)
def test_invalid_new_manual_line_is_rejected_without_business_writes(recovery_db, patch):
    with TestClient(create_app(recovery_db)) as client:
        before = _state(recovery_db)
        result = _save(client, {"draft_id": "DRF_T1", "version": 1}, [_line(**patch)])
        assert result.status_code == 422, result.text
        assert result.headers["X-Request-ID"] == "draft-test"
        assert _state(recovery_db) == before


def test_selected_sku_change_cannot_be_labelled_as_ai_output(recovery_db):
    with TestClient(create_app(recovery_db)) as client:
        saved = _save(client, {"draft_id": "DRF_T1", "version": 1}, [_line()]).json()
        before = _state(recovery_db)
        result = _save(
            client,
            saved,
            [_existing(saved["lines"][0], sku_id="SKU_MILO_2KG", match_source="LLM_EXTRACTED")],
        )
        assert result.status_code == 422, result.text
        assert _state(recovery_db) == before


def _accept_price(client, draft, item):
    result = _save(
        client,
        draft,
        [item],
        resolutions=[
            {
                "issue_id": draft["conditions"][0]["issue_id"],
                "choice": "ACCEPT_REQUESTED_PRICE",
                "target_line_ids": [item["line_id"]],
                "confirmed_unit_price": "4.00",
                "price_basis": "UNIT",
                "note": "Customer explicitly confirmed this product and unit price",
            }
        ],
    )
    assert result.status_code == 200, result.text
    return result.json()


def test_delete_and_replace_reopens_price_condition_then_rebinds_with_owner_approval(recovery_db):
    app = create_app(recovery_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        draft = _conditional(client)
        draft = _accept_price(client, draft, _existing(draft["lines"][0], sku_id="SKU_MILO_1KG"))
        old_id = draft["lines"][0]["line_id"]
        original_span = draft["conditions"][0]["span"]
        replaced = _save(
            client,
            draft,
            [_line(sku_id="SKU_MILO_2KG", client_line_ref="corrected-row")],
            deleted_line_ids=[old_id],
        )
        assert replaced.status_code == 200, replaced.text
        draft = replaced.json()
        new_line = draft["lines"][0]
        condition = draft["conditions"][0]
        assert condition["span"] == original_span
        assert condition["resolved"] is False and condition["resolution"] is None
        assert condition["resolution_note"] is None
        assert "confirmed_unit_price" not in condition["data_used"]
        assert old_id not in condition["candidate_line_ids"] + condition["target_line_ids"]
        assert new_line["line_id"] != old_id
        assert draft["status"] == "DISAMBIGUATION_REQUIRED"
        before = _state(recovery_db)
        assert _approve(client, draft).status_code == 400
        assert _state(recovery_db) == before
        draft = _accept_price(client, draft, _existing(new_line))
        assert draft["conditions"][0]["target_line_ids"] == [new_line["line_id"]]
        assert any(r["code"] == "PRICE_OVERRIDE_BELOW_TIER" for r in draft["escalation_preview"])
        pending = _approve(client, draft)
        assert pending.status_code == 202, pending.text
        do = client.post(
            f"/api/v1/approvals/{pending.json()['approval_id']}/decide",
            headers=_headers(OWNER),
            json={"decision": "APPROVE"},
        )
        assert do.status_code == 200, do.text
        assert do.json()["final_total_rm"] == "4.00"
        assert do.json()["lines"][0]["sku_id"] == "SKU_MILO_2KG"
    with connect(recovery_db) as conn:
        assert conn.execute(
            "SELECT product_id, available_qty FROM inventory ORDER BY product_id"
        ).fetchall() == [("SKU_MILO_1KG", 10), ("SKU_MILO_2KG", 7)]


def test_reselecting_sku_reopens_previously_accepted_price(recovery_db):
    app = create_app(recovery_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        draft = _conditional(client)
        draft = _accept_price(client, draft, _existing(draft["lines"][0], sku_id="SKU_MILO_1KG"))
        result = _save(client, draft, [_existing(draft["lines"][0], sku_id="SKU_MILO_2KG")])
        assert result.status_code == 200, result.text
        assert result.json()["conditions"][0]["resolved"] is False
        assert result.json()["status"] == "DISAMBIGUATION_REQUIRED"


def test_save_reads_customer_tier_and_approval_rechecks_live_price(recovery_db):
    with connect(recovery_db) as conn:
        conn.execute("UPDATE customers SET tier='B' WHERE customer_id='CUS_T1'")
    with TestClient(create_app(recovery_db)) as client:
        draft = _save(client, {"draft_id": "DRF_T1", "version": 1}, [_line()]).json()
        assert draft["totals"]["order_total"] == "6.00"
        with connect(recovery_db) as conn:
            conn.execute("UPDATE customer_tier_prices SET unit_price_rm=8 WHERE tier='B'")
        before = _state(recovery_db)
        response = _approve(client, draft)
        assert response.status_code == 422, response.text
        assert _state(recovery_db) == before
        refreshed = _save(client, draft, [_existing(draft["lines"][0])])
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["totals"]["order_total"] == "8.00"


@pytest.mark.parametrize(
    "status,error",
    [
        ("PENDING_OWNER_APPROVAL", "PENDING_OWNER_APPROVAL"),
        ("DO_GENERATED", "ALREADY_APPROVED"),
        ("REJECTED", "DRAFT_REJECTED"),
    ],
)
def test_manual_recovery_never_edits_locked_orders(recovery_db, status, error):
    with connect(recovery_db) as conn:
        conn.execute(
            "UPDATE orders SET status=%s, termination_reason=%s WHERE draft_id='DRF_T1'",
            (status, "SYSTEM_TERMINATED" if status == "REJECTED" else None),
        )
    with TestClient(create_app(recovery_db)) as client:
        before = _state(recovery_db)
        result = _save(client, {"draft_id": "DRF_T1", "version": 1}, [_line()])
        assert result.status_code == 409 and result.json()["error_code"] == error
        assert _state(recovery_db) == before


@pytest.mark.parametrize(
    "token,status", [(WAREHOUSE, 403), ("b03-other-tenant", 404), ("invalid-b03-token", 401)]
)
def test_recovery_keeps_role_and_tenant_boundaries(recovery_db, token, status):
    with TestClient(create_app(recovery_db)) as client:
        before = _state(recovery_db)
        result = client.put(
            "/api/v1/orders/drafts/DRF_T1/lines",
            headers=_headers(token),
            json={"expected_version": 1, "lines": [_line()]},
        )
        assert result.status_code == status, result.text
        assert _state(recovery_db) == before


def test_stale_empty_and_duplicate_ref_saves_have_no_business_side_effects(recovery_db):
    with TestClient(create_app(recovery_db)) as client:
        before = _state(recovery_db)
        draft = {"draft_id": "DRF_T1", "version": 1}
        for lines, version, error in [
            ([], 1, "EMPTY_ORDER"),
            ([_line()], 2, "STALE_VERSION"),
            ([_line(), _line()], 1, "REQUEST_VALIDATION_FAILED"),
        ]:
            response = _save(client, {**draft, "version": version}, lines)
            assert response.json()["error_code"] == error, response.text
            assert _state(recovery_db) == before


def test_new_recovery_rows_cannot_bind_conditions_by_client_reference(recovery_db):
    app = create_app(recovery_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        draft = _conditional(client)
        before = _state(recovery_db)
        result = _save(
            client,
            draft,
            [_line()],
            deleted_line_ids=[draft["lines"][0]["line_id"]],
            resolutions=[
                {
                    "issue_id": draft["conditions"][0]["issue_id"],
                    "choice": "ACCEPT_REQUESTED_PRICE",
                    "target_line_ids": ["new-1"],
                    "confirmed_unit_price": "4.00",
                    "price_basis": "UNIT",
                    "note": "Must save to obtain the server line ID first",
                }
            ],
        )
        assert result.status_code == 400, result.text
        assert result.json()["error_code"] == "TARGET_LINE_REQUIRED"
        assert _state(recovery_db) == before


def test_stock_is_rechecked_for_aggregate_manual_rows_and_again_at_approval(recovery_db):
    with TestClient(create_app(recovery_db)) as client:
        saved = _save(
            client,
            {"draft_id": "DRF_T1", "version": 1},
            [_line(6), _line(6, client_line_ref="second-row")],
        )
        assert saved.status_code == 200, saved.text
        draft = saved.json()
        assert "INSUFFICIENT_STOCK" in draft["blocking_issues"]
        before = _state(recovery_db)
        assert _approve(client, draft).status_code == 400
        assert _state(recovery_db) == before
        result = _save(
            client,
            draft,
            [_existing(draft["lines"][0], confirmed_qty=1)],
            deleted_line_ids=[draft["lines"][1]["line_id"]],
        )
        assert result.status_code == 200, result.text
        draft = result.json()
        with connect(recovery_db) as conn:
            conn.execute("UPDATE inventory SET available_qty=0 WHERE product_id='SKU_MILO_1KG'")
        before = _state(recovery_db)
        response = _approve(client, draft)
        assert response.status_code == 400, response.text
        assert response.json()["error_code"] == "INSUFFICIENT_STOCK"
        assert _state(recovery_db) == before
