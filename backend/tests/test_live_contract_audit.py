"""Validate actual API responses, not just fixtures, against signed Gate 0."""

import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient
from test_drafts_approve_do import CLERK, OWNER, WAREHOUSE, _headers, _line, _put
from test_drafts_approve_do import seeded_db as seeded_db

from app.config import REPO_ROOT
from app.main import create_app

CONTRACT = yaml.safe_load((REPO_ROOT / "gate0/contracts/openapi.yaml").read_text("utf-8"))


def validate(response, name):
    assert response.status_code < 300, response.text
    schema = {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]}
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        response.json()
    )
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("Cache-Control") == "no-store"


@pytest.mark.integration
def test_real_responses_match_signed_schema(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        validate(client.get("/api/v1/me", headers=_headers(CLERK)), "MeResponse")
        validate(client.get("/api/v1/customers", headers=_headers(CLERK)), "CustomerListResponse")
        parsed = client.post(
            "/api/v1/orders/parse-draft",
            headers=_headers(CLERK),
            json={"customer_id": "CUS_T1", "message_text": "Milo 1 ctn"},
        )
        validate(parsed, "OrderDraft")
        validate(client.get("/api/v1/orders/drafts", headers=_headers(CLERK)), "DraftListResponse")
        validate(_put(client), "OrderDraft")
        do = client.post(
            "/api/v1/orders/DRF_T1/approve", headers=_headers(CLERK), json={"expected_version": 2}
        )
        validate(do, "DeliveryOrder")
        number = do.json()["do_number"]
        validate(
            client.get(f"/api/v1/delivery-orders/{number}", headers=_headers(CLERK)),
            "DeliveryOrder",
        )
        validate(
            client.get(f"/api/v1/orders/{number}/audit-detail", headers=_headers(OWNER)),
            "AuditDetail",
        )
        validate(
            client.get(f"/api/v1/warehouse/delivery-orders/{number}", headers=_headers(WAREHOUSE)),
            "WarehouseDeliveryOrder",
        )
        validate(client.get("/api/v1/activity", headers=_headers(CLERK)), "ActivityListResponse")
        validate(client.get("/api/v1/ai/status", headers=_headers(CLERK)), "AiStatus")
        validate(client.post("/api/v1/ai/wake", headers=_headers(CLERK)), "AiWakeResult")


@pytest.mark.integration
def test_owner_approval_responses_match_signed_schema(seeded_db):
    with TestClient(create_app(seeded_db)) as client:
        validate(_put(client, lines=[_line(3)]), "OrderDraft")
        approval = client.post(
            "/api/v1/orders/DRF_T1/approve", headers=_headers(CLERK), json={"expected_version": 2}
        )
        validate(approval, "ApprovalRequest")
        approval_id = approval.json()["approval_id"]
        validate(client.get("/api/v1/approvals", headers=_headers(OWNER)), "ApprovalListResponse")
        validate(
            client.get(f"/api/v1/approvals/{approval_id}", headers=_headers(OWNER)),
            "ApprovalDetail",
        )
        validate(
            client.post(
                f"/api/v1/approvals/{approval_id}/decide",
                headers=_headers(OWNER),
                json={"decision": "REJECT", "note": "audit case"},
            ),
            "ApprovalDecisionResult",
        )
        validate(client.get("/api/v1/orders/drafts/DRF_T1", headers=_headers(CLERK)), "OrderDraft")
