import json

import httpx
import pytest

from app.config import REPO_ROOT
from app.extraction.ai import (
    AiPayloadError,
    AiServiceError,
    HttpAiExtractor,
    classify_condition,
    to_raw_extraction,
)

SAMPLES = REPO_ROOT / "docs" / "ai_contract" / "samples"


def _sample(name: str) -> dict:
    return json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    [
        "normal",
        "multi_line",
        "multi_candidate",
        "ambiguous",
        "condition",
        "empty",
    ],
)
def test_ai_samples_convert_to_backend_extraction(name):
    sample = _sample(name)
    masked_text = sample["input"]["masked_text"]
    raw = to_raw_extraction(sample["expected_response"], masked_text)
    expected = sample["expected_response"]
    assert len(raw.rows) == len(expected["rows"])
    assert len(raw.ignored_spans) == len(expected["ignored_spans"])
    for row, expected_row in zip(raw.rows, expected["rows"], strict=True):
        assert row.span == expected_row["span"]
        assert row.span in masked_text
        assert row.qty == expected_row["qty"]
        assert row.uom == expected_row["uom"]
        assert row.pack_size == expected_row["pack_size"]
    for ignored, expected_ignored in zip(raw.ignored_spans, expected["ignored_spans"], strict=True):
        assert ignored["span"] == expected_ignored
        assert masked_text[ignored["start"] : ignored["end"]] == expected_ignored


def test_ai_samples_map_generic_families_to_canonical_seed():
    sample = _sample("normal")
    raw = to_raw_extraction(sample["expected_response"], sample["input"]["masked_text"])
    assert raw.rows[0].fam == "FAM_TEPUNG"
    assert raw.rows[0].uom == "ctn"
    assert raw.rows[0].qty == 5


def test_ai_condition_is_classified_as_unit_price_condition():
    text = "kalau RM95 untuk 1 ctn boleh?"
    conditions = classify_condition(text, text)
    assert conditions
    assert conditions[0]["kind"] == "PRICE"
    assert conditions[0]["price_basis"] == "UNIT"
    assert conditions[0]["requested_amount"] == "95"
    assert conditions[0]["blocking"] is True


def test_ai_payload_rejects_domain_fields_and_bad_spans():
    payload = {
        "rows": [
            {
                "span": "not in text",
                "qty": 1,
                "uom": None,
                "fam": "FAM_RICE",
                "pack_size": None,
                "conds": [],
                "sku_id": "SKU_X",
            }
        ],
        "ignored_spans": [],
    }
    with pytest.raises(AiPayloadError):
        to_raw_extraction(payload, "Beras 1 bag")
    with pytest.raises(AiPayloadError):
        to_raw_extraction(
            {
                "rows": [
                    {
                        "span": "missing",
                        "qty": 1,
                        "uom": None,
                        "fam": "FAM_RICE",
                        "pack_size": None,
                        "conds": [],
                    }
                ],
                "ignored_spans": [],
            },
            "Beras 1 bag",
        )


def test_http_extractor_posts_contract_and_adapts_response():
    sample = _sample("normal")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=sample["expected_response"])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    extractor = HttpAiExtractor(
        service_url="https://ai.example.test/api/v1/extract",
        api_key="test-key",
        client=client,
    )
    raw = extractor.extract(sample["input"]["masked_text"], "ms", "req-test-1")
    assert raw.rows[0].fam == "FAM_TEPUNG"
    assert seen["url"] == "https://ai.example.test/api/v1/extract"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["masked_text"] == sample["input"]["masked_text"]
    assert seen["body"]["request_id"] == "req-test-1"


def test_http_extractor_surfaces_service_failure():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, text="down"))
    )
    extractor = HttpAiExtractor(service_url="https://ai.example.test/extract", client=client)
    with pytest.raises(AiServiceError):
        extractor.extract("Beras 1 bag", None, "req-test-2")


def test_contract_files_exist():
    for name in (
        "README.md",
        "H1_H5_mapping.md",
        "request.schema.json",
        "response.schema.json",
        "endpoint.env.example",
    ):
        assert (REPO_ROOT / "docs" / "ai_contract" / name).is_file()
    for name in ("normal", "multi_line", "multi_candidate", "ambiguous", "condition", "empty"):
        assert (SAMPLES / f"{name}.json").is_file()


def test_ai_draft_conversion_builds_lines_and_conditions():
    from app.parse import _ai_draft
    from app.schemas import OrderDraftResponse

    sample = _sample("condition")
    masked_text = sample["input"]["masked_text"]
    raw = to_raw_extraction(sample["expected_response"], masked_text)
    draft = _ai_draft(
        customer={
            "customer_id": "CUS_ALI",
            "name": "Restoran Ali",
            "tier": "A",
            "credit_flag": "NONE",
            "phone_e164": "+60120000001",
        },
        masked_text=masked_text,
        raw=raw,
        draft_id="DRF_TEST_AI",
        now="2026-10-22T00:00:00+00:00",
    )
    model = OrderDraftResponse(**draft)
    assert model.ai_mode == "LLM"
    assert len(model.lines) == 1
    assert model.lines[0].family_id == "FAM_TEPUNG"
    assert model.lines[0].source_span == "Tepung Gandum 5 ctn"
    assert model.conditions
    assert model.conditions[0].code == "CUSTOMER_CONDITION"
    assert model.conditions[0].condition_kind == "PRICE"
    assert model.conditions[0].requested_unit_price == "95.00"
    assert model.ignored_spans == []
