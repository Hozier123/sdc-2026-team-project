import json
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"
SPEC = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
SPEC_URI = "urn:kiraorder:openapi"
REGISTRY = Registry().with_resource(
    SPEC_URI,
    Resource.from_contents(SPEC, default_specification=DRAFT202012),
)


CASES = {
    "parse_draft.json": ("ParseDraftRequest", "OrderDraft"),
    "parse_draft_ambiguous.json": ("ParseDraftRequest", "OrderDraft"),
    "save_lines_ready.json": ("SaveLinesRequest", "OrderDraft"),
    "save_lines_target_required.json": ("SaveLinesRequest", "Error"),
    "save_lines_empty_order_400.json": ("SaveLinesRequest", "Error"),
    "approve_200.json": ("ApproveRequest", "DeliveryOrder"),
    "approve_202.json": ("ApproveRequest", "ApprovalRequest"),
    "approve_stock_changed_409.json": ("DecideRequest", "Error"),
    "already_approved_409.json": ("ApproveRequest", "Error"),
    "audit_detail.json": (None, "AuditDetail"),
    "approval_detail.json": (None, "ApprovalDetail"),
    "approval_list_clerk.json": (None, "ApprovalListResponse"),
    "customers_list.json": (None, "CustomerListResponse"),
    "delivery_order.json": (None, "DeliveryOrder"),
    "warehouse_delivery_order.json": (None, "WarehouseDeliveryOrder"),
    "save_lines_insufficient_stock_200.json": ("SaveLinesRequest", "OrderDraft"),
    "save_lines_price_mismatch_422.json": ("SaveLinesRequest", "Error"),
    "owner_self_approved.json": ("ApproveRequest", "DeliveryOrder"),
    "decide_rejected.json": ("DecideRequest", "ApprovalDecisionResult"),
}


def _validate(schema_name, instance):
    schema = {"$ref": f"{SPEC_URI}#/components/schemas/{schema_name}"}
    validator = jsonschema.Draft202012Validator(
        schema,
        registry=REGISTRY,
        format_checker=jsonschema.FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    assert not errors, "\n".join(error.message for error in errors)


def test_fixture_requests_and_bodies_match_openapi_schemas():
    assert set(CASES).issubset({path.name for path in FIXTURES.glob("*.json")})
    for filename, (request_schema, body_schema) in CASES.items():
        fixture = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
        if request_schema is not None:
            _validate(request_schema, fixture["request"])
        _validate(body_schema, fixture["body"])


def test_error_catalog_examples_match_error_schema():
    catalog = json.loads((FIXTURES / "error_catalog.json").read_text(encoding="utf-8"))
    for example in catalog.values():
        _validate("Error", example["body"])
