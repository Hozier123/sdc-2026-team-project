"""Unit tests for KiraOrder AI Adapter (Pre-Resolver Subsystem).

Covers all 7 mandatory verification categories from docs/round3_remediation_orders.md §2:
2.1 H5 16-row truth table parity data-driven from condition-triggers-v3.json & contract_oracles.py
2.2 FieldEvidence raw_text identity on multi-spaces & ligatures (masked_text[fe.start:fe.end] == fe.raw_text)
2.3 Duplicate and overlapping spans handling (DUPLICATE_SPAN, OVERLAPPING_SPAN, SOURCE_EVIDENCE_INVALID)
2.4 ai_mode four states reachability (LLM, FALLBACK, ALIAS_ONLY, MIXED)
2.5 Prohibited fields defense (no leaked domain decision fields)
2.6 H1 double-check and coercion audit (decimal rejection, coercion tracking, catalog=None defense)
2.7 4000 code point limit and missing lexicon fail-fast defense
"""

from dataclasses import fields
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from unittest.mock import AsyncMock, patch

import pytest

from backend.ai.adapter import (
    AdapterLine,
    AdapterOutput,
    ExtractedCondition,
    FieldEvidence,
    OrderAiAdapter,
    extract_conditions_h5,
    locate_span,
)
from backend.ai.extractor import (
    ExtractorResponse,
    MessageTooLongError,
    RunPodExtractor,
)
from backend.ai.fallback import DEFAULT_SEED_CATALOG, load_h1_lexicon
from backend.ai.prompt import LlmExtractionResult, LlmRow


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _find_gate0_root() -> Path:
    proj_root = Path(__file__).resolve().parents[1]
    candidates = [
        proj_root / "gate0",
        proj_root / "Gate 0",
        proj_root / "最终gate" / "Gate 0",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def _load_contract_oracles():
    gate0_dir = _find_gate0_root()
    oracle_path = (
        gate0_dir
        / "tests"
        / "contract"
        / "contract_oracles.py"
    )
    spec = importlib.util.spec_from_file_location("contract_oracles", oracle_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


contract_oracles = _load_contract_oracles()


def load_truth_table():
    gate0_dir = _find_gate0_root()
    lex_path = (
        gate0_dir
        / "contracts"
        / "lexicons"
        / "condition-triggers-v3.json"
    )
    data = json.loads(lex_path.read_text(encoding="utf-8"))
    return data["truth_table"]


# ---------------------------------------------------------------------------
# 2.1 H5 Three-way Alignment Parity (Data-driven 16 rows)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", load_truth_table(), ids=lambda r: f"row_{r['id']}")
def test_h5_parity_with_oracle(row):
    """Verify 100% parity with contract_oracles across all 16 truth table rows."""
    oracle = contract_oracles.evaluate_condition(row["input"])
    got = extract_conditions_h5(row["input"], total_lines=1)

    # 1. Kinds match
    assert sorted(c.kind for c in got) == sorted(oracle["kinds"])

    # 2. Price basis matches
    got_price_basis = next((c.price_basis for c in got if c.kind == "PRICE"), None)
    assert got_price_basis == oracle["price_basis"]

    # 3. Enum legality & offset back-slicing
    for c in got:
        assert c.kind in {"STOCK", "PRICE", "TIME", "OTHER"}
        assert row["input"][c.span_start : c.span_end] == c.span
        if c.requested_amount is not None:
            assert isinstance(c.requested_amount, str)


def test_h5_time_or_other_mapped_to_other():
    """Verify TIME_OR_OTHER triggers produce kind='OTHER' per Gate 0 OpenAPI schema."""
    res1 = extract_conditions_h5("kalau sempat, hantar 5 ctn")
    assert [c.kind for c in res1] == ["OTHER"]
    assert res1[0].span == "kalau sempat"

    res2 = extract_conditions_h5("hantar sebelum jam 3")
    assert [c.kind for c in res2] == ["OTHER"]
    assert res2[0].span == "hantar sebelum"


# ---------------------------------------------------------------------------
# 2.2 FieldEvidence Back-slice Invariant
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "text",
    [
        "Tepung  5 ctn",  # Double whitespace collapse
        "Straße 5 ctn",  # ß -> ss length expansion in NFKC+casefold
        "ﬁle 5 ctn",  # Ligature ﬁ -> fi expansion
        "Minyak 12 x 1L, 5 ctn",  # pack_size evidence
        "Tepung 5kg x 2",  # pack_size with x spec
        "Air 500 g x 12, 3 pack",  # complex pack_size and unit
        "Tepung 5 cartons",  # non-canonical alias in raw_text
    ],
)
async def test_field_evidence_slice_invariant(text):
    """FieldEvidence invariant: fe.raw_text == masked_text[fe.start:fe.end] for all fields."""
    adapter = OrderAiAdapter()
    out = await adapter.adapt(text, catalog=DEFAULT_SEED_CATALOG)
    assert len(out.lines) >= 1

    for line in out.lines:
        assert text[line.span_start : line.span_end] == line.span
        for fe in line.field_evidence:
            assert fe.field in {"qty", "uom", "pack_size"}
            # The crucial identity invariant
            assert text[fe.start : fe.end] == fe.raw_text
            assert fe.raw_text != "" and not fe.raw_text.isspace()

            # Ensure raw_text is verbatim slice, not canonical alias
            if text == "Tepung 5 cartons" and fe.field == "uom":
                assert fe.raw_text == "cartons"
                assert line.uom == "ctn"  # canonical in line.uom, verbatim in raw_text


@pytest.mark.anyio
async def test_field_evidence_llm_normalized_span_with_multiple_internal_spaces():
    """Verify coordinate projection when LLM outputs normalized single space but raw text has 3 spaces."""
    mock_extractor = AsyncMock(spec=RunPodExtractor)
    mock_extractor.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="Tepung 5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn")]),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    adapter = OrderAiAdapter(extractor=mock_extractor)
    masked_text = "  Tepung   5 ctn  "
    out = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    line = out.lines[0]
    assert line.span == "Tepung   5 ctn"
    assert masked_text[line.span_start : line.span_end] == line.span

    ev_by_field = {fe.field: fe for fe in line.field_evidence}
    assert "qty" in ev_by_field
    assert ev_by_field["qty"].raw_text == "5"
    assert masked_text[ev_by_field["qty"].start : ev_by_field["qty"].end] == "5"

    assert "uom" in ev_by_field
    assert ev_by_field["uom"].raw_text == "ctn"
    assert masked_text[ev_by_field["uom"].start : ev_by_field["uom"].end] == "ctn"


@pytest.mark.anyio
async def test_family_not_evidenced_defense_dev_40():
    """DEV-40: Hallucinated family with no textual evidence must degrade to UNKNOWN and FAMILY_NOT_EVIDENCED."""
    mock_extractor = AsyncMock(spec=RunPodExtractor)
    mock_extractor.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="5 ctn", fam="FAM_OIL", qty=5, uom="ctn")]),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    adapter = OrderAiAdapter(extractor=mock_extractor)
    out = await adapter.adapt("5 ctn", catalog=DEFAULT_SEED_CATALOG)

    line = out.lines[0]
    assert line.family_id == "UNKNOWN"
    assert line.issue_code == "LOW_CONFIDENCE_MATCH"
    assert line.reason_code == "FAMILY_NOT_EVIDENCED"


def test_unrelated_amount_not_stolen_by_discount_condition():
    """Unrelated amount earlier in message must NOT be stolen by discount price condition."""
    text = "Last order was RM95. Boleh diskaun?"
    conds = extract_conditions_h5(text)
    assert len(conds) == 1
    c = conds[0]
    assert c.kind == "PRICE"
    assert "diskaun" in c.span.lower()
    # Crucial: requested_amount must be None because RM95 was in historical context, not the condition
    assert c.requested_amount is None


# ---------------------------------------------------------------------------
# 2.3 Duplicate and Overlapping Spans Handling
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_duplicate_span_deduplication():
    """Identical span with identical fields/evidence is deduplicated (only 1 line)."""
    mock_extractor = AsyncMock(spec=RunPodExtractor)
    mock_extractor.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(
            rows=[
                LlmRow(span="5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn"),
                LlmRow(span="5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn"),
            ]
        ),
        ai_mode="LLM",
        latency_ms=10.0,
    )

    adapter = OrderAiAdapter(extractor=mock_extractor)
    text = "Tepung 5 ctn"
    out = await adapter.adapt(text, catalog=DEFAULT_SEED_CATALOG)

    # Identical fields -> duplicate span is deduplicated
    assert len(out.lines) == 1
    assert out.lines[0].qty == 5
    assert out.lines[0].family_id == "FAM_FLOUR"


@pytest.mark.anyio
async def test_duplicate_span_with_different_evidence_preserved():
    """Identical span but differing field evidence is preserved as two separate lines."""
    mock_extractor = AsyncMock(spec=RunPodExtractor)
    mock_extractor.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(
            rows=[
                LlmRow(span="5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn"),
                LlmRow(span="5 ctn", fam="FAM_SUGAR", qty=5, uom="ctn"),
            ]
        ),
        ai_mode="LLM",
        latency_ms=10.0,
    )

    adapter = OrderAiAdapter(extractor=mock_extractor)
    text = "Tepung 5 ctn Gula"
    out = await adapter.adapt(text, catalog=DEFAULT_SEED_CATALOG)

    # Different families -> preserved as two lines
    assert len(out.lines) == 2
    assert out.lines[0].family_id == "FAM_FLOUR"
    assert out.lines[1].family_id == "FAM_SUGAR"


@pytest.mark.anyio
async def test_overlapping_spans_isolated_not_merged():
    """Overlapping but differing spans must produce LOW_CONFIDENCE_MATCH with OVERLAPPING_SPAN."""
    mock_extractor = AsyncMock(spec=RunPodExtractor)
    mock_extractor.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(
            rows=[
                LlmRow(span="Tepung 5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn"),
                LlmRow(span="5 ctn Minyak", fam="FAM_OIL", qty=5, uom="ctn"),
            ]
        ),
        ai_mode="LLM",
        latency_ms=10.0,
    )

    adapter = OrderAiAdapter(extractor=mock_extractor)
    text = "Tepung 5 ctn Minyak"
    out = await adapter.adapt(text, catalog=DEFAULT_SEED_CATALOG)

    assert len(out.lines) == 2
    # First line extracted normally
    assert out.lines[0].issue_code is None
    # Second line overlaps with first line
    assert out.lines[1].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out.lines[1].reason_code == "OVERLAPPING_SPAN"


@pytest.mark.anyio
async def test_source_evidence_invalid_fault_isolation():
    """If a span cannot be located, only that line degrades without crashing the order."""
    mock_extractor = AsyncMock(spec=RunPodExtractor)
    mock_extractor.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(
            rows=[
                LlmRow(span="Tepung 5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn"),
                LlmRow(span="Imaginary Nonexistent Product 100", fam="FAM_OIL", qty=10, uom="ctn"),
            ]
        ),
        ai_mode="LLM",
        latency_ms=10.0,
    )

    adapter = OrderAiAdapter(extractor=mock_extractor)
    text = "Tepung 5 ctn"
    out = await adapter.adapt(text, catalog=DEFAULT_SEED_CATALOG)

    assert len(out.lines) == 2
    assert out.lines[0].family_id == "FAM_FLOUR"
    assert out.lines[0].qty == 5
    assert out.lines[0].match_source == "LLM_EXTRACTED"

    assert out.lines[1].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out.lines[1].reason_code == "SOURCE_EVIDENCE_INVALID"
    assert out.lines[1].match_source == "RAPIDFUZZ_FALLBACK"


# ---------------------------------------------------------------------------
# 2.4 ai_mode Four States Reachability
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ai_mode_four_states():
    """Verify all 4 AiMode states (LLM, FALLBACK, ALIAS_ONLY, MIXED) are reachable."""
    # 1. LLM mode (all rows LLM_EXTRACTED)
    mock_llm = AsyncMock(spec=RunPodExtractor)
    mock_llm.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="Tepung 5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn")]),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    a1 = OrderAiAdapter(extractor=mock_llm)
    out1 = await a1.adapt("Tepung 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert out1.ai_mode == "LLM"

    # 2. FALLBACK mode (pure fallback)
    mock_fb = AsyncMock(spec=RunPodExtractor)
    mock_fb.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="Tepung 5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn")]),
        ai_mode="FALLBACK",
        latency_ms=10.0,
    )
    a2 = OrderAiAdapter(extractor=mock_fb)
    out2 = await a2.adapt("Tepung 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert out2.ai_mode == "FALLBACK"

    # 3. ALIAS_ONLY mode
    mock_alias = AsyncMock(spec=RunPodExtractor)
    mock_alias.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[]),
        ai_mode="ALIAS_ONLY",
        latency_ms=10.0,
    )
    a3 = OrderAiAdapter(extractor=mock_alias)
    out3 = await a3.adapt("Tepung", catalog=DEFAULT_SEED_CATALOG)
    assert out3.ai_mode == "ALIAS_ONLY"

    # 4. MIXED mode (one LLM row, one degraded fallback row)
    mock_mixed = AsyncMock(spec=RunPodExtractor)
    mock_mixed.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(
            rows=[
                LlmRow(span="Tepung 5 ctn", fam="FAM_FLOUR", qty=5, uom="ctn"),
                LlmRow(span="Ghost Item 99", fam="FAM_OIL", qty=1, uom="ctn"),
            ]
        ),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    a4 = OrderAiAdapter(extractor=mock_mixed)
    out4 = await a4.adapt("Tepung 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert out4.ai_mode == "MIXED"
    sources = {line.match_source for line in out4.lines}
    assert sources == {"LLM_EXTRACTED", "RAPIDFUZZ_FALLBACK"}


# ---------------------------------------------------------------------------
# 2.5 Prohibited Fields Redline Defense
# ---------------------------------------------------------------------------


def test_prohibited_fields_defense():
    """Ensure dataclasses do not produce or leak domain-level prohibited fields."""
    prohibited = {
        "sku_id",
        "unit_price",
        "available_qty",
        "sufficient",
        "target_line_ids",
        "blocking",
        "resolved",
        "draft_id",
        "condition_id",
    }
    for cls in (AdapterOutput, AdapterLine, ExtractedCondition, FieldEvidence):
        cls_field_names = {f.name for f in fields(cls)}
        leaks = cls_field_names & prohibited
        assert not leaks, f"{cls.__name__} leaks prohibited domain fields: {leaks}"


# ---------------------------------------------------------------------------
# 2.6 H1 Double Check & Coercion Audit
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_h1_decimal_quantity_defensive_interception():
    """Decimal quantities ('1,5kg', '2.5 ctn') must be strictly rejected with INVALID_QUANTITY."""
    adapter = OrderAiAdapter()
    out1 = await adapter.adapt("Beras 1,5kg", catalog=DEFAULT_SEED_CATALOG)
    assert len(out1.lines) == 1
    assert out1.lines[0].qty is None
    assert out1.lines[0].pack_size is None
    assert not any(fe.field == "pack_size" for fe in out1.lines[0].field_evidence)
    assert out1.lines[0].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out1.lines[0].reason_code == "INVALID_QUANTITY"

    out2 = await adapter.adapt("Minyak 2.5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert len(out2.lines) == 1
    assert out2.lines[0].qty is None
    assert out2.lines[0].pack_size is None
    assert not any(fe.field == "pack_size" for fe in out2.lines[0].field_evidence)
    assert out2.lines[0].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out2.lines[0].reason_code == "INVALID_QUANTITY"

    # Dot decimal: Beras 1.5kg
    out3 = await adapter.adapt("Beras 1.5kg", catalog=DEFAULT_SEED_CATALOG)
    assert len(out3.lines) == 1
    assert out3.lines[0].qty is None
    assert out3.lines[0].pack_size is None
    assert not any(fe.field == "pack_size" for fe in out3.lines[0].field_evidence)
    assert out3.lines[0].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out3.lines[0].reason_code == "INVALID_QUANTITY"

    # Model returns pack_size on decimal quantity: must be forced to None without pack_size FieldEvidence
    mock_ext = AsyncMock(spec=RunPodExtractor)
    mock_ext.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="1,5kg", fam="FAM_SUGAR", qty=None, uom="kg", pack_size="5kg")]),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    adapter_mock = OrderAiAdapter(extractor=mock_ext)
    out_dec = await adapter_mock.adapt("Gula 1,5kg", catalog=DEFAULT_SEED_CATALOG)
    assert out_dec.lines[0].qty is None
    assert out_dec.lines[0].pack_size is None
    assert not any(fe.field == "pack_size" for fe in out_dec.lines[0].field_evidence)
    assert out_dec.lines[0].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out_dec.lines[0].reason_code == "INVALID_QUANTITY"


@pytest.mark.anyio
async def test_five_acceptance_criteria_adapter():
    """Verify the 5 required acceptance criteria at adapter level."""
    adapter = OrderAiAdapter()

    # 1. 'Gula 1,5kg' -> pack=None, qty=None, INVALID_QUANTITY
    out1 = await adapter.adapt("Gula 1,5kg", catalog=DEFAULT_SEED_CATALOG)
    assert len(out1.lines) == 1
    assert out1.lines[0].pack_size is None
    assert out1.lines[0].qty is None
    assert out1.lines[0].reason_code == "INVALID_QUANTITY"

    # 2. 'Beras 1.5kg' -> pack=None, qty=None, INVALID_QUANTITY
    out2 = await adapter.adapt("Beras 1.5kg", catalog=DEFAULT_SEED_CATALOG)
    assert len(out2.lines) == 1
    assert out2.lines[0].pack_size is None
    assert out2.lines[0].qty is None
    assert out2.lines[0].reason_code == "INVALID_QUANTITY"

    # 3. 'Minyak 12 x 1.5L, 5 ctn' -> pack='12 x 1.5L', qty=5
    out3 = await adapter.adapt("Minyak 12 x 1.5L, 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert len(out3.lines) == 1
    assert out3.lines[0].pack_size == "12 x 1.5L"
    assert out3.lines[0].qty == 5
    assert out3.lines[0].uom == "ctn"
    assert out3.lines[0].family_id == "FAM_OIL"

    # 4. 'Minyak 12 x 1L, 5 ctn' -> pack='12 x 1L', qty=5
    out4 = await adapter.adapt("Minyak 12 x 1L, 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert len(out4.lines) == 1
    assert out4.lines[0].pack_size == "12 x 1L"
    assert out4.lines[0].qty == 5
    assert out4.lines[0].uom == "ctn"
    assert out4.lines[0].family_id == "FAM_OIL"

    # 5. 'Flour 10 ctn 1kg' -> pack='1kg', qty=10
    out5 = await adapter.adapt("Flour 10 ctn 1kg", catalog=DEFAULT_SEED_CATALOG)
    assert len(out5.lines) == 1
    assert out5.lines[0].pack_size == "1kg"
    assert out5.lines[0].qty == 10
    assert out5.lines[0].uom == "ctn"
    assert out5.lines[0].family_id == "FAM_FLOUR"


@pytest.mark.anyio
async def test_h1_model_qty_disagreement_and_coercion():
    """Disagreement between model qty and deterministic candidate sets qty=None and FIELD_NOT_EVIDENCED."""
    # 1. Disagreement: text has 5 ctn, model gives 6 -> rejected
    mock_ext = AsyncMock(spec=RunPodExtractor)
    mock_ext.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="5 ctn", fam="FAM_FLOUR", qty=6, uom="ctn")]),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    adapter = OrderAiAdapter(extractor=mock_ext)
    out = await adapter.adapt("Tepung 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert out.lines[0].qty is None
    assert out.lines[0].issue_code == "LOW_CONFIDENCE_MATCH"
    assert out.lines[0].reason_code == "FIELD_NOT_EVIDENCED"

    # 2. Coercion: model gives string '5', matches deterministic 5 -> accepted with model_coerced=True
    mock_ext_str = AsyncMock(spec=RunPodExtractor)
    mock_ext_str.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=[LlmRow(span="5 ctn", fam="FAM_FLOUR", qty="5", uom="ctn")]),
        ai_mode="LLM",
        latency_ms=10.0,
    )
    adapter_str = OrderAiAdapter(extractor=mock_ext_str)
    out_str = await adapter_str.adapt("Tepung 5 ctn", catalog=DEFAULT_SEED_CATALOG)
    assert out_str.lines[0].qty == 5
    assert out_str.lines[0].model_coerced is True


@pytest.mark.anyio
async def test_catalog_none_raises_value_error():
    """Explicit catalog injection is mandatory; None raises ValueError immediately."""
    adapter = OrderAiAdapter()
    with pytest.raises(ValueError, match="Tenant catalog must be explicitly provided"):
        await adapter.adapt("Tepung 5 ctn", catalog=None)  # type: ignore


# ---------------------------------------------------------------------------
# 2.7 4000 Code Points & Missing Lexicon Defense
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_text_over_4000_code_points_raises_before_ai():
    """Text exceeding 4000 Unicode code points must raise MessageTooLongError before calling AI."""
    mock_ext = AsyncMock(spec=RunPodExtractor)
    adapter = OrderAiAdapter(extractor=mock_ext)
    long_text = "A" * 4001

    with pytest.raises(MessageTooLongError, match="exceeds 4000 code points"):
        await adapter.adapt(long_text, catalog=DEFAULT_SEED_CATALOG)

    # Ensure AI extractor was NOT called
    mock_ext.extract.assert_not_called()


def test_missing_lexicon_fail_fast():
    """Missing lexicon raises FileNotFoundError immediately (fail fast -> 503)."""
    with patch("backend.ai.fallback._find_lexicon_path", side_effect=FileNotFoundError("Lexicon not found")):
        with pytest.raises(FileNotFoundError):
            load_h1_lexicon()
