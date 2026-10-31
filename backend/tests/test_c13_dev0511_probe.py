"""Isolated DB probe for the C13 DEV-05/11 missing-unit regression risk."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from test_resolver_memory import TOKEN
from test_resolver_memory import t1_db as t1_db

from app.ai.adapter import OrderAiAdapter
from app.ai.extractor import ExtractorResponse
from app.ai.prompt import LlmExtractionResult, LlmRow
from app.db import connect
from app.extraction.runpod_adapter import RunPodAdapterProvider
from app.main import create_app

CASES = (
    ("DEV-05", "Bawang Bsr India 50kg", "Bawang Bsr India 50kg"),
    (
        "DEV-11-shape",
        "2 ctn Ayam A1, 50kg Bawang Bsr India, 5 bag Milo 粉, kalau ada",
        "50kg Bawang Bsr India",
    ),
)


class FixedModel:
    """Reproduce the model row shape reported in the private pre-check."""

    def __init__(self, span: str) -> None:
        self.span = span

    async def extract(self, masked_text, catalog):
        return ExtractorResponse(
            result=LlmExtractionResult(
                rows=[
                    LlmRow(
                        span=self.span,
                        fam="FAM_BAWANG",
                        qty=50,
                        uom=None,
                        pack_size="50kg",
                    )
                ],
                ignored_spans=[],
            ),
            ai_mode="LLM",
            latency_ms=1,
        )


@pytest.mark.parametrize(("case", "message", "span"), CASES)
def test_adapter_reproduces_missing_uom_without_issue(case, message, span):
    output = asyncio.run(
        OrderAiAdapter(extractor=FixedModel(span)).adapt(message, {"FAM_BAWANG": ["Bawang"]})
    )
    line = output.lines[0]
    assert line.qty == 50, case
    assert line.uom is None, case
    assert line.pack_size == "50kg", case
    assert line.issue_code is None, case
    qty = next(ev for ev in line.field_evidence if ev.field == "qty")
    pack = next(ev for ev in line.field_evidence if ev.field == "pack_size")
    assert qty.start < pack.end and pack.start < qty.end, case


@pytest.mark.integration
@pytest.mark.parametrize(("case", "message", "span"), CASES)
def test_parse_draft_persists_block_for_missing_uom(case, message, span, t1_db):
    app = create_app(t1_db)
    app.state.extraction_provider = RunPodAdapterProvider(
        adapter=OrderAiAdapter(extractor=FixedModel(span))
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders/parse-draft",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"customer_id": "CUS_ALI", "message_text": message},
        )
    assert response.status_code == 200, (case, response.text)
    body = response.json()
    assert body["ai_mode"] == "LLM", case
    assert body["status"] == "DISAMBIGUATION_REQUIRED", case
    assert body["lines"] == [], case
    assert "APPROVE_AND_GENERATE_DO" not in body["allowed_actions"], case
    assert any(
        issue["code"] == "LOW_CONFIDENCE_MATCH"
        and issue["reason_code"] == "FIELD_NOT_EVIDENCED"
        and issue["data_used"].get("guard") == "QTY_FROM_PACK_SIZE"
        for issue in body["issues"]
    ), case

    with connect(t1_db) as conn:
        saved = conn.execute(
            "SELECT status, working_lines FROM orders WHERE tenant_id='T1' AND draft_id=%s",
            (body["draft_id"],),
        ).fetchone()
        do_count = conn.execute(
            "SELECT count(*) FROM delivery_orders WHERE tenant_id='T1' AND draft_id=%s",
            (body["draft_id"],),
        ).fetchone()[0]
    assert saved == ("DISAMBIGUATION_REQUIRED", []), case
    assert do_count == 0, case
