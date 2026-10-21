from pathlib import Path

import yaml
from openapi_spec_validator import validate
OPENAPI = Path(__file__).parents[2] / "contracts" / "openapi.yaml"


EXPECTED_PATHS = {
    "/orders/parse-draft",
    "/orders/drafts",
    "/orders/drafts/{draft_id}",
    "/orders/drafts/{draft_id}/lines",
    "/orders/{draft_id}/approve",
    "/approvals",
    "/approvals/{approval_id}",
    "/approvals/{approval_id}/decide",
    "/orders/{do_number}/audit-detail",
    "/customers",
    "/delivery-orders/{do_number}",
    "/warehouse/delivery-orders/{do_number}",
    "/activity",
    "/me",
    "/ai/status",
    "/ai/wake",
}


def _load():
    return yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))


def test_openapi_parses_and_has_exact_contract_paths():
    doc = _load()
    assert doc["openapi"] == "3.1.0"
    assert set(doc["paths"]) == EXPECTED_PATHS


def test_openapi_31_document_passes_the_official_validator():
    validate(_load())


def test_all_operations_have_request_id_on_every_response():
    doc = _load()
    responses = doc["components"]["responses"]
    for path_item in doc["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            for response in operation["responses"].values():
                component = response["$ref"].rsplit("/", 1)[-1]
                assert "X-Request-ID" in responses[component]["headers"]


def test_local_refs_resolve():
    doc = _load()

    def walk(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/"):
                target = doc
                for token in ref[2:].split("/"):
                    target = target[token.replace("~1", "/").replace("~0", "~")]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(doc)


def test_public_error_enum_matches_catalog():
    import json

    doc = _load()
    catalog_path = OPENAPI.parent / "fixtures" / "error_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert set(doc["components"]["schemas"]["ErrorCode"]["enum"]) == set(catalog)
