"""Offline B04 smoke responses, deliberately separate from live API evidence."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import httpx


def mock_client(case: dict) -> httpx.Client:
    route = case["route"]
    owner = route.startswith("owner_")
    has_do = route in {"direct", "owner_approve"}
    expected = case["expected"]["lines"]
    lines = [
        {
            "line_id": f"MOCK_LINE_{i}",
            "sku_id": x["sku_id"],
            "family_id": "MOCK_FAMILY",
            "effective_qty": x["quantity"],
            "requested_qty": x["quantity"],
            "confirmed_qty": None,
            "uom": x["unit"],
            "match_source": "RAPIDFUZZ_FALLBACK",
            "effective_unit_price": x["applied_unit_price"],
            "subtotal_rm": str(Decimal(x["applied_unit_price"]) * x["quantity"]),
        }
        for i, x in enumerate(expected)
    ]
    status = "DISAMBIGUATION_REQUIRED" if route == "stock_blocked" else "READY_FOR_APPROVAL"
    draft = {
        "draft_id": "MOCK_DRAFT",
        "version": 1,
        "status": status,
        "customer_id": case["parse"]["customer_id"],
        "ai_mode": case["allowed_ai_modes"][0],
        "lines": lines,
        "escalation_preview": [{"code": "BELOW_TIER_PRICE"}] if owner else [],
        "blocking_issues": ["INSUFFICIENT_STOCK"] if route == "stock_blocked" else [],
    }
    saved = {**draft, "version": 2}
    delivery_lines = [
        {
            "line_id": line["line_id"],
            "sku_id": x["sku_id"],
            "quantity": x["quantity"],
            "unit": x["unit"],
            "applied_unit_price": x["applied_unit_price"],
            "subtotal_rm": line["subtotal_rm"],
        }
        for line, x in zip(lines, expected, strict=True)
    ]
    delivery = {
        "do_number": "MOCK_DO",
        "draft_id": "MOCK_DRAFT",
        "draft_version": 2,
        "customer_id": case["parse"]["customer_id"],
        "lines": delivery_lines,
        "final_total_rm": str(sum(Decimal(x["subtotal_rm"]) for x in lines)),
        "approval_mode": "OWNER_APPROVED" if owner else "DIRECT",
        "approved_by": "MOCK_OWNER" if owner else "MOCK_CLERK",
    }
    approval = {
        "approval_id": "MOCK_APPROVAL",
        "draft_id": "MOCK_DRAFT",
        "draft_version": 2,
        "status": "PENDING",
        "snapshot": {"lines": lines},
    }
    rejection = {
        "approval_id": "MOCK_APPROVAL",
        "draft_id": "MOCK_DRAFT",
        "termination_reason": "OWNER_REJECTED",
        "status": "REJECTED",
        "decision_note": case.get("decision_note"),
        "decided_by": "MOCK_OWNER",
    }

    def handle(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path.removeprefix("/api/v1"), request.method
        code = 200
        if path == "/me":
            role = request.headers["Authorization"].split("-")[-1]
            body = {"user_id": "MOCK_" + role, "role": role, "tenant": {"id": case["tenant_id"]}}
        elif path == "/orders/parse-draft" and method == "POST":
            body = draft
        elif path == "/orders/drafts/MOCK_DRAFT/lines" and method == "PUT":
            body = saved
        elif path == "/orders/MOCK_DRAFT/approve" and method == "POST":
            code = 400 if route == "stock_blocked" else (202 if owner else 200)
            body = (
                {"error_code": "DISAMBIGUATION_UNRESOLVED"}
                if route == "stock_blocked"
                else approval
                if owner
                else delivery
            )
        elif path == "/approvals/MOCK_APPROVAL/decide" and method == "POST":
            body = rejection if route == "owner_reject" else delivery
        elif path == "/approvals/MOCK_APPROVAL":
            body = approval
        elif path == "/orders/drafts/MOCK_DRAFT":
            body = {
                **saved,
                "status": "DO_GENERATED"
                if has_do
                else ("REJECTED" if route == "owner_reject" else status),
                "do_number": "MOCK_DO" if has_do else None,
                "termination_reason": "OWNER_REJECTED" if route == "owner_reject" else None,
            }
        elif path == "/delivery-orders/MOCK_DO":
            body = delivery
        elif path == "/warehouse/delivery-orders/MOCK_DO":
            body = {
                "do_number": "MOCK_DO",
                "items": [
                    {k: line[k] for k in ("sku_id", "quantity", "unit")} for line in delivery_lines
                ],
            }
        elif path == "/orders/MOCK_DO/audit-detail":
            body = {
                "draft_id": "MOCK_DRAFT",
                "do_number": "MOCK_DO",
                "final_snapshot": delivery,
                "events": [
                    {"event_type": "DECIDE_APPROVE" if owner else "APPROVE"},
                    {"event_type": "INVENTORY_DEDUCT"},
                ],
            }
        elif path == "/activity":
            events = (
                ["OWNER_APPROVED" if owner else "DO_CREATED", "INVENTORY_DEDUCTED"]
                if has_do
                else ["OWNER_REJECTED"]
                if route == "owner_reject"
                else []
            )
            body = {"items": [{"event_type": event} for event in events], "next_cursor": None}
        else:
            code, body = 404, {"error_code": "UNEXPECTED_MOCK_REQUEST"}
        return httpx.Response(
            code, json=deepcopy(body), headers={"X-Request-ID": request.headers["X-Request-ID"]}
        )

    return httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=False)
