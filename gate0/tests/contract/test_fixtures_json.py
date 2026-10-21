import json
from pathlib import Path


FIXTURES = Path(__file__).parents[2] / "contracts" / "fixtures"


def _endpoint_fixtures():
    for path in sorted(FIXTURES.glob("*.json")):
        if path.name != "error_catalog.json":
            yield path, json.loads(path.read_text(encoding="utf-8"))


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _check_mask(mask, root, fixture_name):
    for node in _walk(root):
        for text_key in ("span", "source_span"):
            text = node.get(text_key)
            start = node.get("span_start")
            end = node.get("span_end")
            if isinstance(text, str) and isinstance(start, int) and isinstance(end, int):
                assert mask[start:end] == text, f"{fixture_name}: {text_key} {start}:{end}"
        text = node.get("raw_text")
        start = node.get("start")
        end = node.get("end")
        if isinstance(text, str) and isinstance(start, int) and isinstance(end, int):
            assert mask[start:end] == text, f"{fixture_name}: field_evidence {start}:{end}"


def test_masked_span_offsets_are_slice_exact():
    for path, fixture in _endpoint_fixtures():
        for node in _walk(fixture["body"]):
            for mask_key in ("masked_message", "masked_customer_text"):
                mask = node.get(mask_key)
                if isinstance(mask, str):
                    _check_mask(mask, node, f"{path.name}:{mask_key}")



def test_all_fixtures_are_json():
    paths = sorted(FIXTURES.glob("*.json"))
    assert len(paths) >= 8
    for path in paths:
        json.loads(path.read_text(encoding="utf-8"))


def test_endpoint_fixture_wrapper_and_request_id():
    for path, fixture in _endpoint_fixtures():
        assert fixture["method"] in {"GET", "POST", "PUT"}, path.name
        assert fixture["path"].startswith("/api/v1/"), path.name
        assert isinstance(fixture["status"], int), path.name
        assert fixture["headers"]["X-Request-ID"], path.name
        assert isinstance(fixture["body"], dict), path.name


def test_error_fixtures_are_flat_not_data_wrapped():
    for path, fixture in _endpoint_fixtures():
        if fixture["status"] >= 400:
            assert set(fixture["body"]) == {"error_code", "message", "details"}, path.name


def test_error_catalog_covers_every_public_error():
    catalog = json.loads((FIXTURES / "error_catalog.json").read_text(encoding="utf-8"))
    expected = {
        "DISAMBIGUATION_UNRESOLVED", "INSUFFICIENT_STOCK", "TARGET_LINE_REQUIRED",
        "OVERRIDE_REQUIRED", "NOTE_REQUIRED", "EMPTY_ORDER", "INVALID_LINE_OPERATION",
        "INVALID_TOKEN", "FORBIDDEN_ACTION", "TENANT_MISMATCH", "RESOURCE_NOT_FOUND",
        "STALE_VERSION", "PENDING_OWNER_APPROVAL", "ALREADY_APPROVED", "DRAFT_REJECTED",
        "STOCK_CHANGED", "REQUEST_VALIDATION_FAILED", "MESSAGE_TOO_LONG",
        "REJECTION_REASON_REQUIRED", "INVALID_QUANTITY", "MISSING_TIER_PRICE",
        "RATE_LIMITED", "AI_AND_FALLBACK_UNAVAILABLE",
    }
    assert set(catalog) == expected
    for code, example in catalog.items():
        assert example["body"]["error_code"] == code
        assert set(example["body"]) == {"error_code", "message", "details"}
