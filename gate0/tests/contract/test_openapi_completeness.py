from pathlib import Path

import yaml


SPEC = yaml.safe_load((Path(__file__).parents[2] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
SCHEMAS = SPEC["components"]["schemas"]


def _required(schema, names):
    assert set(names).issubset(schema["required"])


def test_frontend_read_models_contain_rendering_contracts():
    _required(SCHEMAS["OrderDraft"], {
        "customer", "masked_message", "conditions", "totals", "allowed_actions", "blocked_actions",
    })
    _required(SCHEMAS["DraftSummary"], {
        "customer_name", "message_preview", "open_blocking_issue_count",
        "owner_escalation_count", "extraction_sources", "allowed_actions",
    })
    _required(SCHEMAS["MeResponse"], {"tenant", "permission_summary"})
    _required(SCHEMAS["ApprovalRequest"], {"customer", "total_rm", "line_count", "allowed_actions"})
    _required(SCHEMAS["ApprovalDetail"], {"customer", "total_rm", "line_count", "stock_check"})


def test_boundary_and_role_redaction_models_are_explicit():
    assert SCHEMAS["ParseDraftRequest"]["required"] == ["customer_id", "message_text"]
    assert "masked_text" not in SCHEMAS["ParseDraftRequest"]["properties"]
    _required(SCHEMAS["DeliveryOrderLine"], {"tier_unit_price", "applied_unit_price"})
    _required(SCHEMAS["DeliveryOrder"], {"customer_id", "customer_name"})
    warehouse = SCHEMAS["WarehouseDeliveryOrder"]
    serialized = str(warehouse).lower()
    warehouse_item = SCHEMAS["WarehouseDeliveryOrderItem"]
    for forbidden in ("price", "phone", "masked_message", "ai_mode"):
        assert forbidden not in warehouse.get("properties", {})
        assert forbidden not in warehouse_item.get("properties", {})
    assert "role-redacted" in serialized


def test_ai_and_action_enums_do_not_drift():
    assert SCHEMAS["AiState"]["enum"] == ["OFFLINE", "WARMING", "READY", "DEGRADED"]
    actions = set(SCHEMAS["AllowedAction"]["enum"])
    assert {"OWNER_APPROVE", "OWNER_REJECT", "SUBMIT_FOR_OWNER", "APPROVE_AND_GENERATE_DO"}.issubset(actions)


def test_approval_read_access_is_explicitly_role_filtered():
    list_get = SPEC["paths"]["/approvals"]["get"]
    detail_get = SPEC["paths"]["/approvals/{approval_id}"]["get"]
    assert any(parameter.get("$ref", "").endswith("/Mine") for parameter in list_get["parameters"])
    assert "requested_by=current_user" in list_get["description"]
    assert "requested_by equals the current user" in detail_get["description"]
    assert "404" in detail_get["description"]


def test_customer_condition_identity_is_a_machine_contract():
    issue = SCHEMAS["Issue"]
    assert issue["properties"]["condition_id"]["pattern"] == "^CND_[0-9A-F]{24}$"
    assert any("condition_id" in branch.get("then", {}).get("required", []) for branch in issue["allOf"])


def test_frontend_candidate_customer_do_alias_and_stock_contracts():
    _required(SCHEMAS["WorkingLine"], {"candidate_skus", "available_qty"})
    assert "saved_alias" in SCHEMAS["WorkingLine"]["properties"]
    _required(SCHEMAS["SkuCandidate"], {
        "sku_id", "family_id", "display_name", "base_unit",
        "tier_unit_price", "available_qty",
    })
    _required(SCHEMAS["AliasRecord"], {"alias_id", "phrase", "target_type", "scope", "active", "created_at"})
    assert "do_number" in SCHEMAS["OrderDraft"]["properties"]
    assert "do_number" in SCHEMAS["DraftSummary"]["properties"]
    stock_item = SCHEMAS["StockCheckSummary"]["properties"]["lines"]["items"]
    assert "effective_qty" in stock_item["required"]
    _required(SCHEMAS["CustomerListResponse"], {"items"})
    for path in (
        "/customers",
        "/delivery-orders/{do_number}",
        "/warehouse/delivery-orders/{do_number}",
    ):
        assert path in SPEC["paths"]
    assert "relative to line_id" in SCHEMAS["FieldDiff"]["properties"]["field_path"]["description"]

