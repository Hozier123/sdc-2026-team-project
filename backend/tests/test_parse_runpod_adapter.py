"""Integration test: parse-draft can use the in-process adapter provider."""

import pytest
from fastapi.testclient import TestClient
from test_parse_draft import TOKEN  # noqa: F401
from test_parse_draft import seeded_db as seeded_db

from app.ai.adapter import AdapterLine, AdapterOutput, FieldEvidence
from app.db import connect
from app.extraction.runpod_adapter import RunPodAdapterProvider
from app.main import create_app

pytestmark = pytest.mark.integration


class CapturingAdapter:
    def __init__(self) -> None:
        self.catalog = None

    async def adapt(self, masked_text, catalog):
        self.catalog = catalog
        return AdapterOutput(
            lines=[
                AdapterLine(
                    line_id="LNE_MILO",
                    span="Milo 5 ctn",
                    span_start=0,
                    span_end=10,
                    family_id="FAM_MILO",
                    qty=5,
                    uom="ctn",
                    pack_size=None,
                    field_evidence=[
                        FieldEvidence(
                            field="requested_qty",
                            raw_text="5",
                            start=5,
                            end=6,
                        )
                    ],
                    match_source="LLM_EXTRACTED",
                )
            ],
            conditions=[],
            ai_mode="LLM",
            ignored_spans=[],
        )


def test_parse_draft_uses_runpod_adapter_and_db_catalog(seeded_db):
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

    fake = CapturingAdapter()
    app = create_app(seeded_db)
    app.state.extraction_provider = RunPodAdapterProvider(adapter=fake)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {TOKEN}", "X-Request-ID": "parse-runpod-1"},
            json={"customer_id": "CUS_T1", "message_text": "Milo 5 ctn"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_mode"] == "LLM"
    assert len(body["lines"]) == 1
    assert body["lines"][0]["sku_id"] == "SKU_MILO"
    assert fake.catalog is not None
    assert fake.catalog["FAM_MILO"][0] == "Milo"
