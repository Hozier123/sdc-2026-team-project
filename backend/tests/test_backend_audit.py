"""Adversarial regressions for the 2026-10-23 backend audit."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_drafts_approve_do import CLERK, OWNER, WAREHOUSE, _headers, _line, _put
from test_drafts_approve_do import seeded_db as seeded_db
from test_export_trial_record import DO

from app.ai_status import AiOrchestrator
from app.config import REPO_ROOT
from app.db import connect
from app.extraction.ai import classify_condition, to_raw_extraction
from app.extraction.evidence import quantity_evidence
from app.main import create_app
from app.schemas import SaveLinesRequest
from app.seed import SeedError, validate_data_only_sql
from tools.export_trial_record import ExportError, build_export, money, write_outputs
from tools.reset_demo import ResetError, init_template, with_dbname


def test_h5_production_matches_all_frozen_truth_rows():
    lexicon = json.loads(
        (REPO_ROOT / "gate0/contracts/lexicons/condition-triggers-v3.json").read_text("utf-8")
    )
    for case in lexicon["truth_table"]:
        actual = classify_condition(case["input"], case["input"])
        assert sorted({c["kind"] for c in actual}) == sorted(case["kinds"]), case
        for condition in actual:
            if condition["kind"] == "PRICE":
                assert condition["price_basis"] == case["price_basis"], case


@pytest.mark.parametrize("qty", [True, "2", 2.0])
def test_quantities_do_not_coerce_non_integer_json(qty):
    with pytest.raises(ValidationError):
        SaveLinesRequest(expected_version=1, lines=[_line(qty)])


def test_seed_insert_cannot_hide_delete_cte():
    with pytest.raises(SeedError):
        validate_data_only_sql(
            "WITH wiped AS (DELETE FROM inventory RETURNING *) "
            "INSERT INTO tenants (tenant_id,name,amount_threshold_rm) VALUES ('T1','x',1)"
        )


def test_template_hash_checked_before_any_database_mutation(tmp_path):
    seed = tmp_path / "seed.sql"
    seed.write_text("INSERT INTO tenants VALUES ('not-the-approved-file');", encoding="utf-8")
    args = SimpleNamespace(
        seed_sql=str(seed),
        seed_version="test",
        seed_sha256="0" * 64,
        template="kiraorder_audit_seed",
        target="kiraorder_trial_audit",
        tenant="T1",
    )
    admin = Mock()
    with pytest.raises(ResetError, match="checksum"):
        init_template(args, admin)
    admin.execute.assert_not_called()


class ConditionalProvider:
    def extract(self, text, language, request_id):
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


def _conditional(client):
    response = client.post(
        "/api/v1/orders/parse-draft",
        headers=_headers(CLERK),
        json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn kalau RM4 untuk 1 ctn"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
def test_condition_survives_parse_get_save_and_price_acceptance(seeded_db):
    app = create_app(seeded_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        draft = _conditional(client)
        draft_id = draft["draft_id"]
        condition = draft["conditions"][0]
        assert condition in draft["issues"]
        fetched = client.get(f"/api/v1/orders/drafts/{draft_id}", headers=_headers(CLERK)).json()
        assert fetched["conditions"] == draft["conditions"]
        item = _line(1)
        item.pop("client_line_ref")
        item["line_id"] = draft["lines"][0]["line_id"]
        saved = _put(client, draft_id=draft_id, lines=[item])
        assert saved.status_code == 200, saved.text
        assert saved.json()["status"] == "DISAMBIGUATION_REQUIRED"
        response = client.put(
            f"/api/v1/orders/drafts/{draft_id}/lines",
            headers=_headers(CLERK),
            json={
                "expected_version": 2,
                "lines": [item],
                "resolutions": [
                    {
                        "issue_id": condition["issue_id"],
                        "choice": "ACCEPT_REQUESTED_PRICE",
                        "target_line_ids": [item["line_id"]],
                        "confirmed_unit_price": "4.00",
                        "price_basis": "UNIT",
                        "note": "Customer confirmed unit price",
                    }
                ],
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["lines"][0]["unit_price_override"] == "4.00"
        assert result["totals"]["order_total"] == "4.00"
        assert result["conditions"][0]["resolved"] is True
        assert result["conditions"][0]["target_line_ids"] == [item["line_id"]]
        assert any(r["code"] == "PRICE_OVERRIDE_BELOW_TIER" for r in result["escalation_preview"])


@pytest.mark.integration
def test_parse_persists_ai_initial_snapshot(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        result = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        ).json()
    with connect(seeded_db) as conn:
        snapshot = conn.execute(
            "SELECT ai_initial_snapshot FROM orders WHERE tenant_id='T1' AND draft_id=%s",
            (result["draft_id"],),
        ).fetchone()[0]
    assert snapshot and snapshot["version"] == 1


@pytest.mark.integration
def test_warehouse_cannot_read_activity_payloads(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert client.get("/api/v1/activity", headers=_headers(WAREHOUSE)).status_code == 403


@pytest.mark.integration
def test_configured_url_does_not_claim_proven_ai_readiness(seeded_db):
    seeded_db.ai_service_url = "https://not-contacted.invalid/extract"
    seeded_db.ai_health_url = "https://not-contacted.invalid/health"
    seeded_db.ai_wake_url = "https://not-contacted.invalid/wake"
    client_transport = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    )
    app = create_app(seeded_db)
    app.state.ai_orchestrator = AiOrchestrator(seeded_db, client=client_transport)
    try:
        with TestClient(app) as client:
            status = client.get("/api/v1/ai/status", headers=_headers(CLERK)).json()
            wake = client.post("/api/v1/ai/wake", headers=_headers(CLERK)).json()
            app.state.ai_orchestrator._warmup.result(timeout=3)
            after = client.get("/api/v1/ai/status", headers=_headers(CLERK)).json()
    finally:
        app.state.ai_orchestrator.close()
        client_transport.close()
    assert status["state"] != "READY"
    assert status["fallback_available"] is True
    assert wake["state"] == "WARMING" and wake["accepted"] is True
    assert wake["fallback_available"] is True
    assert after["state"] == "DEGRADED"


@pytest.mark.integration
def test_get_rejected_draft_retains_termination_identity(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        approval = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        ).json()
        rejected = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decide",
            headers=_headers(OWNER),
            json={"decision": "REJECT", "note": "Please clarify quantities"},
        )
        assert rejected.status_code == 200
        draft = client.get("/api/v1/orders/drafts/DRF_T1", headers=_headers(CLERK)).json()
    assert draft["termination_reason"] == "OWNER_REJECTED"
    assert draft["terminated_by_user_id"] == "USR_T1_OWNER"
    assert draft["termination_note"] == "Please clarify quantities"


@pytest.mark.integration
def test_approval_rechecks_active_sku(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client).status_code == 200
        with connect(seeded_db) as conn:
            conn.execute("UPDATE products SET active=false WHERE product_id='SKU_MILO_1KG'")
        response = client.post(
            "/api/v1/orders/DRF_T1/approve",
            headers=_headers(CLERK),
            json={"expected_version": 2},
        )
    assert response.status_code == 422
    with connect(seeded_db) as conn:
        assert conn.execute("SELECT count(*) FROM delivery_orders").fetchone()[0] == 0
        assert conn.execute("SELECT available_qty FROM inventory").fetchone()[0] == 10


_H1 = json.loads((REPO_ROOT / "gate0/contracts/lexicons/field-evidence-v2.json").read_text("utf-8"))


@pytest.mark.parametrize(
    "case", [c for c in _H1["required_cases"] if "qty" in c], ids=lambda c: c["id"]
)
def test_h1_quantity_truth_and_original_offsets(case):
    qty, reason, start, end = quantity_evidence(case["span"])
    assert qty == case["qty"]
    if qty is None:
        assert reason == case["reason_code"]
    else:
        assert 0 <= start < end <= len(case["span"])
        assert case["span"][start:end].strip()


@pytest.mark.parametrize(
    "text,qty",
    [
        ("３　ｃｔｎ", 3),
        ("-5 ctn", None),
        ("+5 ctn", None),
        ("2026/10/23", None),
        ("1000000 ctn", None),
    ],
)
def test_quantity_adversarial_boundaries(text, qty):
    assert quantity_evidence(text)[0] == qty


@pytest.mark.parametrize(
    "text,kinds,basis",
    [
        ("RM95 per ctn", ["PRICE"], "UNIT"),
        ("ＲＭ９５？", ["PRICE"], "UNKNOWN"),
        ("kalau sempat", ["OTHER"], None),
        ("not asking for discount", [], None),
        ("can lesser", [], None),
        ("stock code RM95", [], None),
        ("price is RM95, can less?", ["PRICE"], "UNKNOWN"),
        ("RM95 per ctn or RM90 per bag?", ["PRICE"], "UNKNOWN"),
    ],
)
def test_h5_boundaries(text, kinds, basis):
    actual = classify_condition(text, text)
    assert sorted({c["kind"] for c in actual}) == kinds
    if "PRICE" in kinds:
        assert next(c for c in actual if c["kind"] == "PRICE")["price_basis"] == basis


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO inventory (tenant_id) SELECT pg_sleep(1)",
        "INSERT INTO inventory (tenant_id) VALUES (pg_sleep(1))",
        "INSERT INTO inventory (tenant_id) VALUES ('T1') ON CONFLICT DO UPDATE SET available_qty=0",
        "INSERT INTO audit_logs (tenant_id) VALUES ('T1')",
    ],
)
def test_seed_rejects_non_literal_or_runtime_mutations(sql):
    with pytest.raises(SeedError):
        validate_data_only_sql(sql)


def test_seed_rejects_cross_tenant_rows():
    with pytest.raises(SeedError, match="different tenant"):
        validate_data_only_sql("INSERT INTO inventory (tenant_id) VALUES ('T2')", "T1")


def test_reset_preserves_transport_security_options():
    value = with_dbname("postgresql://test@localhost/x?sslmode=verify-full&connect_timeout=5", "y")
    assert "sslmode=verify-full" in value and "connect_timeout=5" in value


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_export_rejects_non_finite_or_negative_amount(value):
    with pytest.raises(ExportError):
        money(value)


def test_export_rejects_empty_order_and_escapes_csv_formula(tmp_path):
    with pytest.raises(ExportError):
        build_export("TEST", "T1", {**DO, "lines": []})
    order = {**DO, "lines": [{**DO["lines"][0], "display_name": "=1+1"}]}
    export = build_export("TEST", "T1", order)
    csv_path, json_path = write_outputs(tmp_path, "TEST", [export], True)
    assert "'=1+1" in csv_path.read_text("utf-8-sig")
    assert "=1+1" in json_path.read_text("utf-8")


@pytest.mark.integration
@pytest.mark.parametrize(
    "field,value",
    [
        ("uom", "bag"),
        ("pack_size", "fabricated"),
        ("grade", "fabricated"),
        ("unit_price_override", "99999999999.99"),
    ],
)
def test_save_rejects_inconsistent_sku_fields(seeded_db, field, value):
    with TestClient(create_app(seeded_db)) as client:
        response = _put(client, lines=[_line(**{field: value})])
        assert response.status_code == 422
    with connect(seeded_db) as conn:
        assert conn.execute("SELECT version FROM orders WHERE draft_id='DRF_T1'").fetchone()[0] == 1


@pytest.mark.integration
def test_price_change_after_save_and_stock_before_escalation_are_rechecked(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customer_tier_prices SET unit_price_rm=6")
        response = client.post(
            "/api/v1/orders/DRF_T1/approve", headers=_headers(CLERK), json={"expected_version": 2}
        )
        assert response.status_code == 422
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customer_tier_prices SET unit_price_rm=5")
            conn.execute("UPDATE inventory SET available_qty=2")
        response = client.post(
            "/api/v1/orders/DRF_T1/approve", headers=_headers(CLERK), json={"expected_version": 2}
        )
        assert response.status_code == 400
    with connect(seeded_db) as conn:
        assert conn.execute("SELECT count(*) FROM approval_requests").fetchone()[0] == 0


@pytest.mark.integration
def test_customer_rename_before_approval_is_frozen_and_audit_contains_all_versions(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        saved = _put(client).json()
        item = _line()
        item.pop("client_line_ref")
        item["line_id"] = saved["lines"][0]["line_id"]
        assert _put(client, version=2, lines=[item]).status_code == 200
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customers SET name='Approval-time name'")
        do = client.post(
            "/api/v1/orders/DRF_T1/approve", headers=_headers(CLERK), json={"expected_version": 3}
        ).json()
        assert do["customer_name"] == "Approval-time name"
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customers SET name='Later name',active=false")
        fetched = client.get(
            f"/api/v1/delivery-orders/{do['do_number']}", headers=_headers(CLERK)
        ).json()
        assert fetched["customer_name"] == do["customer_name"]
        audit = client.get(
            f"/api/v1/orders/{do['do_number']}/audit-detail", headers=_headers(CLERK)
        ).json()
        assert any(diff["draft_version"] == 2 for diff in audit["field_diffs"])
        activity = client.get(
            "/api/v1/activity", params={"entity_id": do["do_number"]}, headers=_headers(CLERK)
        ).json()
        assert activity["items"]


@pytest.mark.integration
def test_model_quantity_mismatch_and_omitted_price_do_not_bypass_backend(seeded_db):
    class Provider:
        def extract(self, text, language, request_id):
            return to_raw_extraction(
                {
                    "rows": [
                        {
                            "span": "Milo 5 ctn",
                            "qty": 6,
                            "fam": "FAM_MILO",
                            "uom": "ctn",
                            "conds": [],
                        }
                    ],
                    "ignored_spans": [],
                },
                text,
            )

    app = create_app(seeded_db)
    app.state.extraction_provider = Provider()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn kalau RM4 boleh"},
        )
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["lines"] == []
    assert any(i["reason_code"] == "FIELD_NOT_EVIDENCED" for i in draft["issues"])
    assert draft["conditions"][0]["blocking"] is True


@pytest.mark.integration
def test_price_resolution_persists_reopens_and_cannot_be_closed_generically(seeded_db):
    app = create_app(seeded_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        draft = _conditional(client)
        item = _line()
        item.pop("client_line_ref")
        item["line_id"] = draft["lines"][0]["line_id"]
        url = f"/api/v1/orders/drafts/{draft['draft_id']}/lines"
        resolution = {
            "issue_id": draft["conditions"][0]["issue_id"],
            "choice": "CONFIRMED_WITH_CUSTOMER",
            "target_line_ids": [item["line_id"]],
        }
        assert (
            client.put(
                url,
                headers=_headers(CLERK),
                json={"expected_version": 1, "lines": [item], "resolutions": [resolution]},
            ).status_code
            == 422
        )
        resolution.update(
            choice="ACCEPT_REQUESTED_PRICE",
            confirmed_unit_price="4.00",
            price_basis="UNIT",
            note="confirmed",
        )
        result = client.put(
            url,
            headers=_headers(CLERK),
            json={"expected_version": 1, "lines": [item], "resolutions": [resolution]},
        )
        assert result.status_code == 200, result.text
        item.update(unit_price_override="4.00", override_reason="confirmed")
        saved = client.put(
            url, headers=_headers(CLERK), json={"expected_version": 2, "lines": [item]}
        ).json()
        assert saved["conditions"][0]["resolved"]
        item.update(unit_price_override="3.00", override_reason="changed again")
        changed = client.put(
            url, headers=_headers(CLERK), json={"expected_version": 3, "lines": [item]}
        ).json()
        assert not changed["conditions"][0]["resolved"]
        assert changed["status"] == "DISAMBIGUATION_REQUIRED"


@pytest.mark.integration
def test_dismissal_writes_append_only_activity(seeded_db):
    app = create_app(seeded_db)
    app.state.extraction_provider = ConditionalProvider()
    with TestClient(app) as client:
        draft = _conditional(client)
        item = _line()
        item.pop("client_line_ref")
        item["line_id"] = draft["lines"][0]["line_id"]
        response = client.put(
            f"/api/v1/orders/drafts/{draft['draft_id']}/lines",
            headers=_headers(CLERK),
            json={
                "expected_version": 1,
                "lines": [item],
                "resolutions": [
                    {
                        "issue_id": draft["conditions"][0]["issue_id"],
                        "choice": "NOT_A_CONDITION",
                        "target_line_ids": [],
                        "note": "Historical quote",
                    }
                ],
            },
        )
        assert response.status_code == 200, response.text
    with connect(seeded_db) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM activity_log WHERE event_type='CONDITION_DISMISSED'"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.integration
def test_duplicate_sku_aggregate_shortage_blocks_at_save(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        response = _put(client, lines=[_line(6), _line(6, client_line_ref="new-2")])
    assert response.status_code == 200
    assert response.json()["status"] == "DISAMBIGUATION_REQUIRED"
    assert "INSUFFICIENT_STOCK" in response.json()["blocking_issues"]


@pytest.mark.integration
def test_inactive_customer_can_still_have_pending_request_rejected(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        assert _put(client, lines=[_line(3)]).status_code == 200
        approval = client.post(
            "/api/v1/orders/DRF_T1/approve", headers=_headers(CLERK), json={"expected_version": 2}
        ).json()
        with connect(seeded_db) as conn:
            conn.execute("UPDATE customers SET active=false")
        response = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decide",
            headers=_headers(OWNER),
            json={"decision": "REJECT", "note": "closed"},
        )
        assert response.status_code == 200, response.text


def test_export_prefers_approved_pack_and_grade_snapshot():
    order = {
        **DO,
        "working_lines": [
            {"line_id": DO["lines"][0]["line_id"], "pack_size": "approved pack", "grade": None}
        ],
    }
    export = build_export(
        "TEST",
        "T1",
        order,
        products={DO["lines"][0]["sku_id"]: {"pack_size": "new pack", "grade": "A"}},
    )
    assert export.rows[0]["pack_size"] == "approved pack"
    assert export.rows[0]["grade"] == ""


@pytest.mark.integration
def test_stock_condition_is_recomputed_without_customer_clarification(seeded_db):
    class Provider:
        def extract(self, text, language, request_id):
            return to_raw_extraction(
                {
                    "rows": [
                        {
                            "span": "Milo 1 ctn",
                            "qty": 1,
                            "fam": "FAM_MILO",
                            "uom": "ctn",
                            "conds": ["if available"],
                        }
                    ],
                    "ignored_spans": [],
                },
                text,
            )

    app = create_app(seeded_db)
    app.state.extraction_provider = Provider()
    with TestClient(app) as client:
        draft = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn if available"},
        ).json()
        item = _line()
        item.pop("client_line_ref")
        item["line_id"] = draft["lines"][0]["line_id"]
        saved = _put(client, draft_id=draft["draft_id"], lines=[item]).json()
        assert saved["conditions"][0]["blocking"] is False
        assert saved["conditions"][0]["auto_resolved_by"] == "STOCK_CHECK"
        assert saved["clarification_draft"] is None


@pytest.mark.integration
def test_hallucinated_family_and_duplicate_model_items_are_not_accepted(seeded_db):
    class Provider:
        def extract(self, text, language, request_id):
            row = {
                "span": "Milo 1 ctn",
                "qty": 1,
                "fam": "FAM_NOT_IN_TENANT",
                "uom": "ctn",
                "pack_size": "made up",
                "conds": [],
            }
            return to_raw_extraction({"rows": [row, row], "ignored_spans": []}, text)

    app = create_app(seeded_db)
    app.state.extraction_provider = Provider()
    with TestClient(app) as client:
        draft = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        ).json()
    assert len(draft["lines"]) == 1
    assert draft["lines"][0]["family_id"] == "UNKNOWN"
    assert draft["lines"][0]["pack_size"] is None
    assert {i["reason_code"] for i in draft["issues"]} >= {"FAMILY_NOT_EVIDENCED", "DUPLICATE_SPAN"}
