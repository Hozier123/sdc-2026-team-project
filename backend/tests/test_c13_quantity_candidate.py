"""C13: incorrect model quantities must not become approvable drafts."""

import asyncio
from decimal import Decimal

import pytest

from app.ai.adapter import AdapterLine, AdapterOutput, FieldEvidence, OrderAiAdapter
from app.ai.extractor import ExtractorResponse
from app.ai.prompt import LlmExtractionResult, LlmRow, build_system_prompt
from app.extraction.base import RawExtraction, RawRow
from app.extraction.runpod_adapter import adapter_output_to_raw
from app.parse import _ai_draft, _quantity_from_pack_size
from app.resolver import Catalog, CatalogProduct


def _line(span="Milo 1kg", qty=1, evidence=None, *, issue_code=None):
    return AdapterLine(
        line_id="LINE_0",
        span=span,
        span_start=0,
        span_end=len(span),
        family_id="FAM_MILO",
        qty=qty,
        uom=None,
        pack_size="1kg",
        field_evidence=evidence or [],
        match_source="LLM_EXTRACTED",
        issue_code=issue_code,
        reason_code="FIELD_NOT_EVIDENCED" if issue_code else None,
    )


def _draft(raw, message, *, catalog=None):
    return _ai_draft(
        customer={
            "customer_id": "CUS_SYNTHETIC",
            "name": "Synthetic customer",
            "tier": "A",
            "credit_flag": "NONE",
            "phone_e164": None,
        },
        masked_text=message,
        raw=raw,
        draft_id="DRF_SYNTHETIC",
        now="2026-10-31T00:00:00+00:00",
        language_hint="en",
        catalog=catalog,
    )


def test_prompt_describes_complete_span_and_pack_quantity_separation():
    prompt = build_system_prompt(["FAM_MILO"])
    assert 'span="Milo 1kg 2 bag", qty=2, uom="bag", pack_size="1kg"' in prompt
    assert "Never put an ordered quantity" in prompt


def test_exact_old_model_output_is_blocked_end_to_end():
    message = "Milo 1kg 2 bag"
    evidence = [
        FieldEvidence(field="qty", raw_text="1", start=5, end=6),
        FieldEvidence(field="pack_size", raw_text="1kg", start=5, end=8),
    ]
    raw = adapter_output_to_raw(
        AdapterOutput(
            lines=[_line(evidence=evidence, issue_code="LOW_CONFIDENCE_MATCH")],
            conditions=[],
            ai_mode="LLM",
            ignored_spans=["2 bag"],
        ),
        message,
    )
    assert raw.rows[0].invalid_reason == "FIELD_NOT_EVIDENCED"
    draft = _draft(raw, message)
    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    assert draft["lines"] == []
    assert draft["blocking_issues"] == ["LOW_CONFIDENCE_MATCH"]
    assert "APPROVE_AND_GENERATE_DO" not in draft["allowed_actions"]


def test_adjacent_ignored_quantity_blocks_even_without_adapter_warning():
    raw = adapter_output_to_raw(
        AdapterOutput(lines=[_line()], conditions=[], ai_mode="LLM", ignored_spans=["2 bag"]),
        "Milo 1kg 2 bag",
    )
    assert raw.rows[0].invalid_reason == "FIELD_NOT_EVIDENCED"


def test_unrelated_ignored_text_does_not_block_good_line():
    raw = adapter_output_to_raw(
        AdapterOutput(
            lines=[_line(span="Milo 1kg 2 bag", qty=2)],
            conditions=[],
            ai_mode="LLM",
            ignored_spans=["thanks"],
        ),
        "Milo 1kg 2 bag thanks",
    )
    assert raw.rows[0].invalid_reason is None


@pytest.mark.parametrize(
    ("span", "qty", "pack", "expected"),
    [
        ("Milo 1kg", (5, 6), (5, 8), True),
        ("Milo 2 bag", (5, 6), None, False),
        ("1 bag Bawang 10kg", (0, 1), (13, 17), False),
        ("Bawang 10kg", (7, 9), (7, 11), True),
    ],
)
def test_pack_digit_overlap_is_detected(span, qty, pack, expected):
    evidence = ({"field": "qty", "start": qty[0], "end": qty[1]},)
    if pack:
        evidence += ({"field": "pack_size", "start": pack[0], "end": pack[1]},)
    assert _quantity_from_pack_size(RawRow(span=span, field_evidence=evidence)) is expected


def test_pack_digit_overlap_blocks_without_an_adapter_issue():
    raw = RawExtraction(
        rows=(
            RawRow(
                span="Milo 1kg",
                qty=1,
                fam="FAM_MILO",
                pack_size="1kg",
                field_evidence=(
                    {"field": "qty", "start": 5, "end": 6},
                    {"field": "pack_size", "start": 5, "end": 8},
                ),
            ),
        )
    )
    draft = _draft(raw, "Milo 1kg 2 bag")
    assert draft["status"] == "DISAMBIGUATION_REQUIRED"
    assert draft["issues"][0]["data_used"]["guard"] == "QTY_FROM_PACK_SIZE"


class _ModelOutput:
    def __init__(self, result):
        self.result = result

    async def extract(self, masked_text, catalog):
        return ExtractorResponse(result=self.result, ai_mode="LLM", latency_ms=1)


def test_adapter_marks_original_bad_model_response():
    result = LlmExtractionResult(
        rows=[LlmRow(span="Milo 1kg", fam="FAM_MILO", qty=1, uom="kg")],
        ignored_spans=["2 bag"],
    )
    output = asyncio.run(
        OrderAiAdapter(extractor=_ModelOutput(result)).adapt(
            "Milo 1kg 2 bag", {"FAM_MILO": ["Milo"]}
        )
    )
    assert output.lines[0].issue_code == "LOW_CONFIDENCE_MATCH"
    raw = adapter_output_to_raw(output, "Milo 1kg 2 bag")
    assert raw.rows[0].invalid_reason == "FIELD_NOT_EVIDENCED"


def test_adapter_accepts_correct_full_span_model_response():
    result = LlmExtractionResult(
        rows=[
            LlmRow(
                span="Milo 1kg 2 bag",
                fam="FAM_MILO",
                qty=2,
                uom="bag",
                pack_size="1kg",
            )
        ],
        ignored_spans=[],
    )
    output = asyncio.run(
        OrderAiAdapter(extractor=_ModelOutput(result)).adapt(
            "Milo 1kg 2 bag", {"FAM_MILO": ["Milo"]}
        )
    )
    assert output.lines[0].qty == 2
    assert output.lines[0].issue_code is None
    raw = adapter_output_to_raw(output, "Milo 1kg 2 bag")
    assert raw.rows[0].invalid_reason is None
    catalog = Catalog(
        products=(
            CatalogProduct(
                sku_id="SKU_MILO_1KG",
                family_id="FAM_MILO",
                name="Milo 1kg",
                pack_size="1kg",
                grade=None,
                base_unit="bag",
                tier_price=Decimal("18.00"),
                available_qty=10,
            ),
        ),
        aliases=(),
    )
    draft = _draft(raw, "Milo 1kg 2 bag", catalog=catalog)
    assert draft["status"] == "READY_FOR_APPROVAL"
    assert draft["lines"][0]["requested_qty"] == 2
    assert draft["lines"][0]["uom"] == "bag"
    assert draft["lines"][0]["subtotal_rm"] == "36.00"
