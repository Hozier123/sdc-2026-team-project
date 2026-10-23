"""Integration tests: parse-draft can use the in-process adapter provider."""

import pytest
from fastapi.testclient import TestClient
from test_parse_draft import TOKEN  # noqa: F401
from test_parse_draft import seeded_db as seeded_db

from app.ai.adapter import AdapterLine, AdapterOutput, ExtractedCondition, FieldEvidence
from app.db import connect
from app.extraction.runpod_adapter import RunPodAdapterProvider
from app.main import create_app

pytestmark = pytest.mark.integration


def _seed(seeded_db):
    with connect(seeded_db) as conn:
        conn.execute(
            "INSERT INTO product_families (family_id, tenant_id, family_name) "
            "VALUES ('FAM_MILO', 'T1', 'Milo')"
        )
        conn.execute(
            "INSERT INTO products "
            "(product_id, tenant_id, family_id, sku_code, name, base_unit) "
            "VALUES ('SKU_MILO', 'T1', 'FAM_MILO', 'SKU_MILO', 'Milo 1kg', 'ctn')"
        )
        conn.execute(
            "INSERT INTO customer_tier_prices "
            "(tenant_id, product_id, tier, unit_price_rm) "
            "VALUES ('T1', 'SKU_MILO', 'A', 5.00)"
        )
        conn.execute(
            "INSERT INTO inventory (tenant_id, product_id, available_qty) "
            "VALUES ('T1', 'SKU_MILO', 10)"
        )


def _line(span: str = "Milo 5 ctn", qty: int = 5) -> AdapterLine:
    return AdapterLine(
        line_id=f"LNE_MILO_{qty}",
        span=span,
        span_start=0,
        span_end=len(span),
        family_id="FAM_MILO",
        qty=qty,
        uom="ctn",
        pack_size=None,
        field_evidence=[
            FieldEvidence(
                field="requested_qty",
                raw_text=str(qty),
                start=5,
                end=6,
            )
        ],
        match_source="LLM_EXTRACTED",
    )


class CapturingAdapter:
    def __init__(self, output: AdapterOutput) -> None:
        self.output = output
        self.catalog = None

    async def adapt(self, masked_text, catalog):
        self.catalog = catalog
        return self.output


def _post(seeded_db, adapter, message: str, request_id: str):
    fake = CapturingAdapter(adapter)
    app = create_app(seeded_db)
    app.state.extraction_provider = RunPodAdapterProvider(adapter=fake)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {TOKEN}", "X-Request-ID": request_id},
            json={"customer_id": "CUS_T1", "message_text": message},
        )
    return response, fake


def test_parse_draft_uses_runpod_adapter_and_db_catalog(seeded_db):
    _seed(seeded_db)
    response, fake = _post(
        seeded_db,
        AdapterOutput(
            lines=[_line()],
            conditions=[],
            ai_mode="LLM",
            ignored_spans=[],
        ),
        "Milo 5 ctn",
        "parse-runpod-1",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_mode"] == "LLM"
    assert len(body["lines"]) == 1
    assert body["lines"][0]["sku_id"] == "SKU_MILO"
    assert fake.catalog is not None
    assert fake.catalog["FAM_MILO"][0] == "Milo"


def test_parse_draft_preserves_condition_inside_line_once(seeded_db):
    _seed(seeded_db)
    condition = ExtractedCondition(
        kind="PRICE",
        span="RM95",
        span_start=11,
        span_end=15,
        condition_scope="SINGLE_LINE",
        price_basis="UNIT",
        requested_amount="95",
    )
    response, _ = _post(
        seeded_db,
        AdapterOutput(
            lines=[_line("Milo 5 ctn RM95")],
            conditions=[condition],
            ai_mode="MIXED",
            ignored_spans=[],
        ),
        "Milo 5 ctn RM95",
        "parse-runpod-condition-inside",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_mode"] == "MIXED"
    assert len(body["conditions"]) == 1
    saved = body["conditions"][0]
    assert saved["condition_kind"] == "PRICE"
    assert saved["condition_scope"] == "SINGLE_LINE"
    assert saved["line_id"] == body["lines"][0]["line_id"]
    assert saved["requested_unit_price"] == "95.00"
    assert "CUSTOMER_CONDITION" in body["blocking_issues"]


def test_parse_draft_preserves_condition_outside_all_lines(seeded_db):
    _seed(seeded_db)
    condition = ExtractedCondition(
        kind="STOCK",
        span="Kalau ada",
        span_start=23,
        span_end=32,
        condition_scope="MULTI_LINE",
        price_basis=None,
        requested_amount=None,
    )
    response, _ = _post(
        seeded_db,
        AdapterOutput(
            lines=[_line(), _line("Milo 3 ctn", qty=3)],
            conditions=[condition],
            ai_mode="MIXED",
            ignored_spans=[],
        ),
        "Milo 5 ctn Milo 3 ctn. Kalau ada",
        "parse-runpod-condition-outside",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_mode"] == "MIXED"
    assert len(body["lines"]) == 2
    assert len(body["conditions"]) == 1
    saved = body["conditions"][0]
    assert saved["condition_kind"] == "STOCK"
    assert saved["condition_scope"] == "MULTI_LINE"
    assert saved["line_id"] is None
    assert saved["candidate_line_ids"] == []
    assert saved["blocking"] is False
