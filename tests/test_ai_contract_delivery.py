"""Contract delivery verification test suite for KiraOrder AI Subsystem.

Validates that:
1. request.schema.json and response.schema.json are strictly valid Draft-07 JSON Schemas.
2. All 6 sample JSONs in ai_contract/samples/ strictly validate against both schemas.
3. Every span in span_coordinates matches masked_text[start:end] with exact code point offsets.
4. No forbidden domain decision fields (sku_id, price, stock, approval, do_number) leak into responses.
5. End-to-end sanity tests pass through OrderAiAdapter for all 6 sample cases.
6. Schema and boundary defenses correctly reject malformed requests, injected fields, and oversized inputs.
"""

import asyncio
from dataclasses import fields
import json
from pathlib import Path
import re
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import jsonschema
from jsonschema import Draft7Validator
import pytest

from backend.ai.adapter import AdapterOutput, OrderAiAdapter
from backend.ai.extractor import (
    MAX_MESSAGE_CODE_POINTS,
    ExtractorResponse,
    MessageTooLongError,
    RunPodExtractor,
)
from backend.ai.fallback import DEFAULT_SEED_CATALOG
from backend.ai.prompt import LlmExtractionResult, LlmRow

# ---------------------------------------------------------------------------
# Path and Fixture Setup
# ---------------------------------------------------------------------------

AI_CONTRACT_DIR = Path(__file__).resolve().parents[1] / "ai_contract"
SAMPLES_DIR = AI_CONTRACT_DIR / "samples"
REQUEST_SCHEMA_PATH = AI_CONTRACT_DIR / "request.schema.json"
RESPONSE_SCHEMA_PATH = AI_CONTRACT_DIR / "response.schema.json"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def request_schema() -> Dict[str, Any]:
    assert REQUEST_SCHEMA_PATH.is_file(), f"request.schema.json not found at {REQUEST_SCHEMA_PATH}"
    schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="session")
def response_schema() -> Dict[str, Any]:
    assert RESPONSE_SCHEMA_PATH.is_file(), f"response.schema.json not found at {RESPONSE_SCHEMA_PATH}"
    schema = json.loads(RESPONSE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return schema


def get_all_samples() -> List[Path]:
    sample_files = sorted(SAMPLES_DIR.glob("*.json"))
    expected_names = {
        "normal.json",
        "multi_line.json",
        "multi_candidate.json",
        "ambiguous.json",
        "condition.json",
        "empty.json",
    }
    found_names = {f.name for f in sample_files}
    assert expected_names.issubset(found_names), f"Missing required samples: {expected_names - found_names}"
    return sample_files


# ---------------------------------------------------------------------------
# 1. JSON Schema Draft-07 Validation & Contract Conformity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sample_path", get_all_samples(), ids=lambda p: p.stem)
def test_sample_conforms_to_request_and_response_schemas(
    sample_path: Path,
    request_schema: Dict[str, Any],
    response_schema: Dict[str, Any],
):
    """Verify each sample file conforms strictly to request and response Draft-07 schemas."""
    data = json.loads(sample_path.read_text(encoding="utf-8"))

    # Must contain required top-level sample metadata
    for key in ("description", "input", "expected_response", "span_coordinates", "rationale"):
        assert key in data, f"Sample {sample_path.name} missing key '{key}'"

    # Validate input against request.schema.json
    jsonschema.validate(instance=data["input"], schema=request_schema)

    # Validate expected_response against response.schema.json
    jsonschema.validate(instance=data["expected_response"], schema=response_schema)


@pytest.mark.parametrize("sample_path", get_all_samples(), ids=lambda p: p.stem)
def test_sample_span_coordinates_exact_match(sample_path: Path):
    """Verify that every span coordinate in the sample exactly matches masked_text[start:end]."""
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    masked_text = data["input"]["masked_text"]
    coords = data["span_coordinates"]

    assert len(coords) >= 1, f"Sample {sample_path.name} must have at least one coordinate entry"

    for entry in coords:
        start = entry["start"]
        end = entry["end"]
        verbatim = entry["verbatim_span"]

        assert 0 <= start <= end <= len(masked_text), (
            f"Coordinate [{start}:{end}] out of range for masked_text of length {len(masked_text)} "
            f"in {sample_path.name}"
        )
        sliced_text = masked_text[start:end]
        assert sliced_text == verbatim, (
            f"Span mismatch in {sample_path.name} at [{start}:{end}]: "
            f"expected '{verbatim}', got '{sliced_text}'"
        )

        # Verify target path resolves cleanly against expected_response
        target = entry["target"]
        expected_resp = data["expected_response"]
        if target.startswith("rows["):
            m = re.match(r"rows\[(\d+)\]\.(span|fam|qty|uom|pack_size|conds(?:\[(\d+)\])?)", target)
            assert m, f"Invalid target path '{target}' in {sample_path.name}"
            row_idx = int(m.group(1))
            field = m.group(2)
            assert row_idx < len(expected_resp["rows"]), f"Row index {row_idx} out of range in {sample_path.name}"
            row = expected_resp["rows"][row_idx]
            if field == "span":
                assert row["span"] == verbatim, f"{target} mismatch in {sample_path.name}"
            elif field == "uom":
                assert row["uom"] == verbatim, f"{target} mismatch in {sample_path.name}"
            elif field == "pack_size":
                assert row["pack_size"] == verbatim, f"{target} mismatch in {sample_path.name}"
            elif field == "qty":
                assert str(row["qty"]) == verbatim or (row["qty"] is None and verbatim == ""), (
                    f"{target} mismatch in {sample_path.name}"
                )
            elif field == "fam":
                assert row["fam"] is not None and len(row["fam"]) > 0, f"{target} family missing in {sample_path.name}"
            elif field.startswith("conds["):
                cond_idx = int(m.group(3))
                assert row["conds"][cond_idx] == verbatim, f"{target} mismatch in {sample_path.name}"
        elif target.startswith("ignored_spans["):
            m = re.match(r"ignored_spans\[(\d+)\]", target)
            assert m, f"Invalid target path '{target}' in {sample_path.name}"
            ign_idx = int(m.group(1))
            assert ign_idx < len(expected_resp["ignored_spans"]), f"Ignored index {ign_idx} out of range in {sample_path.name}"
            assert expected_resp["ignored_spans"][ign_idx] == verbatim, f"{target} mismatch in {sample_path.name}"
        else:
            pytest.fail(f"Unrecognized target root prefix in '{target}' from {sample_path.name}")


@pytest.mark.parametrize("sample_path", get_all_samples(), ids=lambda p: p.stem)
def test_prohibited_domain_decision_fields_not_leaked(sample_path: Path):
    """Verify that forbidden domain decision fields are never returned in expected_response."""
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    expected_resp = data["expected_response"]

    prohibited_fields = {
        "sku_id",
        "price",
        "unit_price",
        "stock",
        "approval",
        "do_number",
        "tenant_id",
        "customer_id",
        "inventory_level",
    }

    # Top-level check
    for key in expected_resp.keys():
        assert key in {"rows", "ignored_spans"}, f"Unauthorized top-level key '{key}' in response"

    # Row-level check
    allowed_row_keys = {"span", "qty", "uom", "fam", "pack_size", "conds"}
    for idx, row in enumerate(expected_resp.get("rows", [])):
        row_keys = set(row.keys())
        assert row_keys == allowed_row_keys, (
            f"Row {idx} in {sample_path.name} keys mismatch: expected {allowed_row_keys}, got {row_keys}"
        )
        for prohibited in prohibited_fields:
            assert prohibited not in row, f"Forbidden field '{prohibited}' leaked in row {idx} of {sample_path.name}"

        # Quantity type safety check
        qty = row["qty"]
        if qty is not None:
            assert isinstance(qty, int) and not isinstance(qty, bool), (
                f"Row {idx} qty must be positive integer or null, got {type(qty)}"
            )
            assert 1 <= qty <= 999999, f"Row {idx} qty {qty} outside valid range 1..999999"


# ---------------------------------------------------------------------------
# 2. Schema Boundary Rejection Tests
# ---------------------------------------------------------------------------


def test_request_schema_rejects_text_over_4000_code_points(request_schema: Dict[str, Any]):
    """Verify request schema rejects input exceeding 4000 code points."""
    oversized = {"masked_text": "A" * 4001}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=oversized, schema=request_schema)


def test_request_schema_rejects_additional_properties(request_schema: Dict[str, Any]):
    """Verify request schema rejects extra domain fields like customer_id."""
    invalid_req = {
        "masked_text": "Tepung 5 ctn",
        "customer_id": "cust-12345",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_req, schema=request_schema)


@pytest.mark.parametrize(
    "forbidden_field",
    ["sku_id", "price", "unit_price", "stock", "approval", "do_number", "inventory_level"],
)
def test_response_schema_rejects_forbidden_fields_in_rows_and_root(
    response_schema: Dict[str, Any],
    forbidden_field: str,
):
    """Verify response schema rejects all forbidden domain fields in rows and at the root level."""
    # 1. Injected inside a row
    bad_row_resp = {
        "rows": [
            {
                "span": "5 ctn",
                "qty": 5,
                "uom": "ctn",
                "fam": "FAM_FLOUR",
                "pack_size": None,
                "conds": [],
                forbidden_field: "injected_val",
            }
        ],
        "ignored_spans": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_row_resp, schema=response_schema)

    # 2. Injected at response root
    bad_root_resp = {
        "rows": [],
        "ignored_spans": [],
        forbidden_field: "root_injected",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_root_resp, schema=response_schema)


def test_schemas_reject_empty_strings_where_prohibited(
    request_schema: Dict[str, Any],
    response_schema: Dict[str, Any],
):
    """Verify request and response schemas reject empty strings for fields that require null or content."""
    # Empty language_hint and request_id must fail (should be null instead of "")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"masked_text": "text", "language_hint": ""}, schema=request_schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"masked_text": "text", "request_id": ""}, schema=request_schema)

    # Empty uom, pack_size, conds item, or ignored_spans item must fail
    base_row = {
        "span": "5 ctn",
        "qty": 5,
        "uom": "ctn",
        "fam": "FAM_FLOUR",
        "pack_size": None,
        "conds": [],
    }
    for key in ("uom", "pack_size"):
        bad_row = dict(base_row, **{key: ""})
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance={"rows": [bad_row], "ignored_spans": []}, schema=response_schema)

    # Empty string in conds array
    bad_cond_row = dict(base_row, conds=[""])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"rows": [bad_cond_row], "ignored_spans": []}, schema=response_schema)

    # Empty string in ignored_spans array
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"rows": [], "ignored_spans": [""]}, schema=response_schema)


def test_response_schema_rejects_zero_or_negative_quantity(response_schema: Dict[str, Any]):
    """Verify response schema rejects qty=0, negative quantity, or boolean."""
    for bad_qty in (0, -1, True, False, 1.5):
        resp = {
            "rows": [
                {
                    "span": "5 ctn",
                    "qty": bad_qty,
                    "uom": "ctn",
                    "fam": "FAM_FLOUR",
                    "pack_size": None,
                    "conds": [],
                }
            ],
            "ignored_spans": [],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=resp, schema=response_schema)


# ---------------------------------------------------------------------------
# 3. End-to-End Sanity with OrderAiAdapter
# ---------------------------------------------------------------------------


def _build_mock_extractor_from_sample(sample_name: str) -> RunPodExtractor:
    sample_file = SAMPLES_DIR / sample_name
    data = json.loads(sample_file.read_text(encoding="utf-8"))
    raw_rows = data["expected_response"]["rows"]
    llm_rows = [
        LlmRow(
            span=r["span"],
            fam=r["fam"],
            qty=r["qty"],
            uom=r["uom"],
            pack_size=r["pack_size"],
            conds=r["conds"],
        )
        for r in raw_rows
    ]
    ignored = data["expected_response"]["ignored_spans"]

    mock_ext = AsyncMock(spec=RunPodExtractor)
    mock_ext.extract.return_value = ExtractorResponse(
        result=LlmExtractionResult(rows=llm_rows, ignored_spans=ignored),
        ai_mode="LLM",
        latency_ms=12.5,
    )
    return mock_ext


@pytest.mark.anyio
async def test_e2e_normal_sample_through_adapter():
    """Verify normal.json runs through OrderAiAdapter with accurate field evidence."""
    mock_ext = _build_mock_extractor_from_sample("normal.json")
    adapter = OrderAiAdapter(extractor=mock_ext)

    sample = json.loads((SAMPLES_DIR / "normal.json").read_text(encoding="utf-8"))
    masked_text = sample["input"]["masked_text"]

    output: AdapterOutput = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    assert len(output.lines) == 1
    line = output.lines[0]
    assert line.family_id == "FAM_FLOUR"
    assert line.qty == 5
    assert line.uom == "ctn"
    assert line.pack_size == "1kg"
    assert line.span == "Tepung Gandum 5 ctn 1kg"
    assert masked_text[line.span_start : line.span_end] == line.span

    # Check field evidence offsets
    ev_map = {fe.field: fe for fe in line.field_evidence}
    assert "qty" in ev_map and ev_map["qty"].raw_text == "5"
    assert masked_text[ev_map["qty"].start : ev_map["qty"].end] == "5"
    assert "uom" in ev_map and ev_map["uom"].raw_text == "ctn"
    assert masked_text[ev_map["uom"].start : ev_map["uom"].end] == "ctn"
    assert "pack_size" in ev_map and ev_map["pack_size"].raw_text == "1kg"
    assert masked_text[ev_map["pack_size"].start : ev_map["pack_size"].end] == "1kg"


@pytest.mark.anyio
async def test_e2e_multi_line_sample_through_adapter():
    """Verify multi_line.json extracts all 3 distinct product families cleanly."""
    mock_ext = _build_mock_extractor_from_sample("multi_line.json")
    adapter = OrderAiAdapter(extractor=mock_ext)

    sample = json.loads((SAMPLES_DIR / "multi_line.json").read_text(encoding="utf-8"))
    masked_text = sample["input"]["masked_text"]

    output: AdapterOutput = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    assert len(output.lines) == 3
    assert output.lines[0].family_id == "FAM_RICE"
    assert output.lines[0].qty == 10
    assert output.lines[0].uom == "bag"

    assert output.lines[1].family_id == "FAM_OIL"
    assert output.lines[1].qty == 4
    assert output.lines[1].uom == "ctn"
    assert output.lines[1].pack_size == "1L"

    assert output.lines[2].family_id == "FAM_SUGAR"
    assert output.lines[2].qty == 20
    assert output.lines[2].uom == "pack"


@pytest.mark.anyio
async def test_e2e_multi_candidate_sample_through_adapter():
    """Verify multi_candidate.json extracts distinct packaging sizes for the same family."""
    mock_ext = _build_mock_extractor_from_sample("multi_candidate.json")
    adapter = OrderAiAdapter(extractor=mock_ext)

    sample = json.loads((SAMPLES_DIR / "multi_candidate.json").read_text(encoding="utf-8"))
    masked_text = sample["input"]["masked_text"]

    output: AdapterOutput = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    assert len(output.lines) == 2
    assert output.lines[0].family_id == "FAM_OIL"
    assert output.lines[0].pack_size == "1L"
    assert output.lines[0].qty == 5

    assert output.lines[1].family_id == "FAM_OIL"
    assert output.lines[1].pack_size == "250ml"
    assert output.lines[1].qty == 10


@pytest.mark.anyio
async def test_e2e_ambiguous_sample_through_adapter():
    """Verify ambiguous.json decimal quantities are defensively downgraded to INVALID_QUANTITY."""
    mock_ext = _build_mock_extractor_from_sample("ambiguous.json")
    adapter = OrderAiAdapter(extractor=mock_ext)

    sample = json.loads((SAMPLES_DIR / "ambiguous.json").read_text(encoding="utf-8"))
    masked_text = sample["input"]["masked_text"]

    output: AdapterOutput = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    assert len(output.lines) == 2
    for line in output.lines:
        assert line.qty is None
        assert line.issue_code == "LOW_CONFIDENCE_MATCH"
        assert line.reason_code == "INVALID_QUANTITY"


@pytest.mark.anyio
async def test_e2e_condition_sample_through_adapter():
    """Verify condition.json correctly triggers H5 condition with price_basis=UNIT and amount=95."""
    mock_ext = _build_mock_extractor_from_sample("condition.json")
    adapter = OrderAiAdapter(extractor=mock_ext)

    sample = json.loads((SAMPLES_DIR / "condition.json").read_text(encoding="utf-8"))
    masked_text = sample["input"]["masked_text"]

    output: AdapterOutput = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    assert len(output.lines) == 1
    assert output.lines[0].family_id == "FAM_FLOUR"
    assert output.lines[0].qty == 5

    assert len(output.conditions) == 1
    cond = output.conditions[0]
    assert cond.kind == "PRICE"
    assert cond.price_basis == "UNIT"
    assert cond.requested_amount == "95"
    assert masked_text[cond.span_start : cond.span_end] == cond.span


@pytest.mark.anyio
async def test_e2e_empty_sample_through_adapter():
    """Verify empty.json yields 0 lines, 0 conditions, and populates ignored_spans."""
    mock_ext = _build_mock_extractor_from_sample("empty.json")
    adapter = OrderAiAdapter(extractor=mock_ext)

    sample = json.loads((SAMPLES_DIR / "empty.json").read_text(encoding="utf-8"))
    masked_text = sample["input"]["masked_text"]

    output: AdapterOutput = await adapter.adapt(masked_text, catalog=DEFAULT_SEED_CATALOG)

    assert len(output.lines) == 0
    assert len(output.conditions) == 0
    assert set(output.ignored_spans) == {"hantar esok", "terima kasih"}


# ---------------------------------------------------------------------------
# 4. End-to-End Sanity with RunPodExtractor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sample_path", get_all_samples(), ids=lambda p: p.stem)
@pytest.mark.anyio
async def test_runpod_extractor_offline_fallback_on_all_samples(
    sample_path: Path,
    response_schema: Dict[str, Any],
):
    """Verify RunPodExtractor executes on all samples in offline fallback mode and output validates against response.schema.json."""
    extractor = RunPodExtractor(api_key="", endpoint_id="")
    sample_data = json.loads(sample_path.read_text(encoding="utf-8"))
    masked_text = sample_data["input"]["masked_text"]

    resp: ExtractorResponse = await extractor.extract(masked_text, catalog=DEFAULT_SEED_CATALOG)
    assert resp.ai_mode == "FALLBACK"
    assert resp.latency_ms >= 0.0

    # Ensure the fallback extraction result strictly conforms to response.schema.json
    raw_dict = {
        "rows": [r.model_dump() for r in resp.result.rows],
        "ignored_spans": resp.result.ignored_spans,
    }
    jsonschema.validate(instance=raw_dict, schema=response_schema)


@pytest.mark.anyio
async def test_runpod_extractor_rejects_oversized_text():
    """Verify RunPodExtractor physical hard limit intercepts >4000 code points with MessageTooLongError."""
    extractor = RunPodExtractor()
    oversized = "A" * 4001
    with pytest.raises(MessageTooLongError):
        await extractor.extract(oversized)


@pytest.mark.anyio
async def test_runpod_extractor_probe_version_unconfigured():
    """Verify probe_version returns empty dict safely when endpoint_id is not configured."""
    extractor = RunPodExtractor(endpoint_id="")
    result = await extractor.probe_version()
    assert result == {}

