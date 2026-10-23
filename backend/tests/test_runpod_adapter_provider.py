"""Unit tests for the in-process RunPod adapter boundary."""

from dataclasses import asdict

import pytest

from app.ai.adapter import AdapterLine, AdapterOutput, ExtractedCondition, FieldEvidence
from app.extraction.runpod_adapter import RunPodAdapterProvider, adapter_output_to_raw

CATALOG = {"FAM_MILO": ["Milo", "milo"]}


class FakeAdapter:
    def __init__(self, output: AdapterOutput) -> None:
        self.output = output
        self.calls: list[tuple[str, dict[str, list[str]]]] = []

    async def adapt(self, masked_text: str, catalog):
        self.calls.append((masked_text, catalog))
        return self.output


def _output() -> AdapterOutput:
    line = AdapterLine(
        line_id="LNE_1",
        span="Milo 5 ctn RM95",
        span_start=0,
        span_end=15,
        family_id="FAM_MILO",
        qty=5,
        uom="ctn",
        pack_size="1kg",
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
    condition = ExtractedCondition(
        kind="PRICE",
        span="RM95",
        span_start=11,
        span_end=15,
        condition_scope="SINGLE_LINE",
        price_basis="UNIT",
        requested_amount="95",
    )
    return AdapterOutput(
        lines=[line],
        conditions=[condition],
        ai_mode="LLM",
        ignored_spans=[
            "call me",
        ],
    )


def test_adapter_output_maps_to_raw_extraction_without_domain_fields():
    raw = adapter_output_to_raw(_output(), "Milo 5 ctn RM95 call me")

    assert raw.ai_mode == "LLM"
    assert raw.conditions == (
        {
            "kind": "PRICE",
            "span": "RM95",
            "start": 11,
            "end": 15,
            "condition_scope": "SINGLE_LINE",
            "price_basis": "UNIT",
            "requested_amount": "95",
        },
    )
    assert raw.ignored_spans == (
        {
            "text": "call me",
            "start": 16,
            "end": 23,
            "normalizer_version": "field-evidence-v2",
        },
    )
    assert len(raw.rows) == 1
    row = raw.rows[0]
    assert row.span == "Milo 5 ctn RM95"
    assert row.fam == "FAM_MILO"
    assert row.qty == 5
    assert row.uom == "ctn"
    assert row.pack_size == "1kg"
    assert row.source == "LLM_EXTRACTED"
    assert row.field_evidence[0]["field"] == "requested_qty"
    assert row.conds[0]["kind"] == "PRICE"

    forbidden = {"sku_id", "unit_price", "tier_price", "available_qty", "stock"}
    assert forbidden.isdisjoint(asdict(row))
    assert forbidden.isdisjoint(asdict(raw))


def test_provider_passes_catalog_and_preserves_fallback_mode():
    output = _output()
    output = AdapterOutput(
        lines=output.lines,
        conditions=output.conditions,
        ai_mode="FALLBACK",
        ignored_spans=[],
    )
    fake = FakeAdapter(output)
    provider = RunPodAdapterProvider(adapter=fake)

    raw = provider.extract(
        "Milo 5 ctn RM95",
        language_hint="en",
        request_id="req-1",
        catalog=CATALOG,
    )

    assert raw.ai_mode == "FALLBACK"
    assert fake.calls == [("Milo 5 ctn RM95", CATALOG)]


def test_provider_requires_explicit_catalog():
    provider = RunPodAdapterProvider(adapter=FakeAdapter(_output()))

    with pytest.raises(ValueError, match="tenant catalog"):
        provider.extract("Milo 5 ctn", None, "req-1")


@pytest.mark.anyio
async def test_provider_async_requires_catalog_too():
    provider = RunPodAdapterProvider(adapter=FakeAdapter(_output()))

    with pytest.raises(ValueError, match="tenant catalog"):
        await provider.extract_async("Milo 5 ctn", None)
