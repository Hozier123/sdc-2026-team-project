"""Approve a saved draft, create an owner approval request, or decide one."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import uuid4

import psycopg
from fastapi import APIRouter, Depends, Query, Response
from psycopg.types.json import Jsonb

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.drafts import (
    _audit,
    _canonical_uom,
    _customer,
    _escalation,
    _money,
    _old_lines,
    _order,
    _product,
    _tenant,
    _tier_price,
)
from app.errors import (
    AlreadyApprovedError,
    DraftRejectedError,
    ForbiddenActionError,
    InsufficientStockError,
    PendingOwnerApprovalError,
    RejectionReasonRequiredError,
    RequestValidationFailedError,
    ResourceNotFoundError,
    StaleVersionError,
    StockChangedError,
)
from app.schemas import (
    ApprovalDecisionResult,
    ApprovalDetail,
    ApprovalListResponse,
    ApprovalRequestResponse,
    ApprovalSnapshot,
    ApprovalStatus,
    ApproveRequest,
    DecideRequest,
    DeliveryOrder,
    DeliveryOrderLine,
    FieldDiff,
    ReplyDraft,
    StockCheckLine,
    StockCheckSummary,
    WorkingLine,
)

router = APIRouter(prefix="/api/v1", tags=["Approvals"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _approval(conn, tenant: str, approval_id: str, *, lock: bool = False) -> dict[str, Any]:
    suffix = " FOR UPDATE" if lock else ""
    row = conn.execute(
        "SELECT approval_id, draft_id, draft_version, status, reasons, snapshot, "
        "requested_by, requested_at, decided_by, decided_at, decision_note "
        "FROM approval_requests WHERE tenant_id=%s AND approval_id=%s" + suffix,
        (tenant, approval_id),
    ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return {
        "approval_id": row[0],
        "draft_id": row[1],
        "draft_version": row[2],
        "status": row[3],
        "reasons": row[4] or [],
        "snapshot": row[5],
        "requested_by": row[6],
        "requested_at": row[7],
        "decided_by": row[8],
        "decided_at": row[9],
        "decision_note": row[10],
    }


def _customer_summary(customer: dict[str, Any]) -> dict[str, Any]:
    return {
        "customer_id": customer["customer_id"],
        "name": customer["name"],
        "tier": customer["tier"],
        "credit_flag": customer["credit_flag"],
        "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
        "phone_e164": customer["phone_e164"],
    }


def _snapshot(
    customer: dict[str, Any],
    masked_message: str,
    lines: list[WorkingLine],
    total: Decimal,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "customer_id": customer["customer_id"],
        "customer_name": customer["name"],
        "masked_customer_text": masked_message,
        "lines": [line.model_dump(mode="json") for line in lines],
        "total_rm": _money(total),
        "reasons": reasons,
    }


def _approval_response(
    approval: dict[str, Any], customer: dict[str, Any]
) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        approval_id=approval["approval_id"],
        draft_id=approval["draft_id"],
        draft_version=approval["draft_version"],
        status=approval["status"],
        customer={
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "tier": customer["tier"],
            "credit_flag": customer["credit_flag"],
            "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
            "phone_e164": customer["phone_e164"],
        },
        total_rm=approval["snapshot"]["total_rm"],
        line_count=len(approval["snapshot"]["lines"]),
        reasons=approval["reasons"],
        requested_by=approval["requested_by"],
        requested_at=approval["requested_at"],
        allowed_actions=[],
        decided_by=approval["decided_by"],
        decided_at=approval["decided_at"],
        decision_note=approval["decision_note"],
    )


def _do_number() -> str:
    return f"DO_{_now():%Y%m%d}_{uuid4().hex[:8].upper()}"


def _reply(do_number: str) -> ReplyDraft:
    return ReplyDraft(
        language="en",
        message=f"Order {do_number} has been approved.",
        do_number=do_number,
        warnings=[],
    )


def _stock_lines(lines: list[WorkingLine]) -> dict[str, int]:
    quantities: dict[str, int] = {}
    for line in lines:
        if not line.sku_id:
            raise RequestValidationFailedError(
                details={
                    "fields": [
                        {
                            "path": f"lines[{line.line_id}].sku_id",
                            "reason": "required before approval",
                        }
                    ]
                }
            )
        quantities[line.sku_id] = quantities.get(line.sku_id, 0) + line.effective_qty
    return quantities


def _lock_and_verify_stock(
    conn, tenant: str, lines: list[WorkingLine], *, error_cls=StockChangedError
) -> None:
    quantities = _stock_lines(lines)
    rows = conn.execute(
        "SELECT product_id, available_qty FROM inventory "
        "WHERE tenant_id=%s AND product_id = ANY(%s) ORDER BY product_id FOR UPDATE",
        (tenant, list(quantities)),
    ).fetchall()
    available = {row[0]: int(row[1]) for row in rows}
    failed = []
    for sku_id, qty in quantities.items():
        if available.get(sku_id, 0) < qty:
            failed.append(
                {
                    "line_id": next(line.line_id for line in lines if line.sku_id == sku_id),
                    "sku_id": sku_id,
                    "requested_qty": qty,
                    "effective_qty": qty,
                    "available_qty": available.get(sku_id, 0),
                }
            )
    if failed:
        raise error_cls(details={"lines": failed})
    for line in lines:
        line.available_qty = available[line.sku_id]


def _deduct_stock(conn, tenant: str, lines: list[WorkingLine]) -> None:
    quantities = _stock_lines(lines)
    for sku_id, qty in sorted(quantities.items()):
        cursor = conn.execute(
            "UPDATE inventory SET available_qty = available_qty - %s, updated_at=now() "
            "WHERE tenant_id=%s AND product_id=%s AND available_qty >= %s",
            (qty, tenant, sku_id, qty),
        )
        if cursor.rowcount != 1:
            raise StockChangedError(details={"lines": [{"sku_id": sku_id, "required_qty": qty}]})


def _prepared_by(conn, tenant: str, draft_id: str, fallback: str) -> str:
    row = conn.execute(
        "SELECT created_by FROM draft_versions WHERE tenant_id=%s AND draft_id=%s AND version=1",
        (tenant, draft_id),
    ).fetchone()
    return row[0] if row is not None else fallback


def _create_do(
    conn,
    *,
    tenant: str,
    order: dict[str, Any],
    customer: dict[str, Any],
    lines: list[WorkingLine],
    reasons: list[dict[str, Any]],
    user: CurrentUser,
    mode: str,
) -> DeliveryOrder:
    total = sum(Decimal(line.subtotal_rm) for line in lines if line.subtotal_rm)
    do_number = _do_number()
    prepared_by = _prepared_by(conn, tenant, order["draft_id"], user.user_id)
    do_lines = [
        DeliveryOrderLine(
            line_id=line.line_id,
            sku_id=line.sku_id or "",
            display_name=line.description or line.sku_id or "",
            quantity=line.effective_qty,
            unit=line.uom or "UNIT",
            tier_unit_price=line.tier_unit_price or "0.00",
            applied_unit_price=line.effective_unit_price or "0.00",
            subtotal_rm=line.subtotal_rm or "0.00",
            override_reason=line.override_reason,
        )
        for line in lines
    ]
    approved_at = _now()
    conn.execute(
        "INSERT INTO delivery_orders "
        "(do_number, tenant_id, draft_id, draft_version, customer_id, lines, "
        " final_total_rm, prepared_by, approved_by, escalation_reasons, "
        " approval_mode, reply_draft, approved_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            do_number,
            tenant,
            order["draft_id"],
            order["version"],
            customer["customer_id"],
            Jsonb([line.model_dump(mode="json") for line in do_lines]),
            total,
            prepared_by,
            user.user_id,
            Jsonb(reasons),
            mode,
            Jsonb(_reply(do_number).model_dump(mode="json")),
            approved_at,
        ),
    )
    conn.execute(
        "UPDATE orders SET status='DO_GENERATED', updated_at=now() "
        "WHERE tenant_id=%s AND draft_id=%s",
        (tenant, order["draft_id"]),
    )
    return DeliveryOrder(
        do_number=do_number,
        draft_id=order["draft_id"],
        draft_version=order["version"],
        customer_id=customer["customer_id"],
        customer_name=customer["name"],
        lines=do_lines,
        final_total_rm=_money(total),
        prepared_by=prepared_by,
        approved_by=user.user_id,
        escalation_reasons=reasons,
        approval_mode=mode,
        reply_draft=_reply(do_number),
        approved_at=approved_at,
    )


def _create_approval(
    conn,
    *,
    tenant: str,
    order: dict[str, Any],
    customer: dict[str, Any],
    lines: list[WorkingLine],
    reasons: list[dict[str, Any]],
    masked_message: str,
    user: CurrentUser,
) -> ApprovalRequestResponse:
    total = sum(Decimal(line.subtotal_rm) for line in lines if line.subtotal_rm)
    approval_id = f"APR_{uuid4().hex.upper()}"
    snapshot = _snapshot(customer, masked_message, lines, total, reasons)
    try:
        conn.execute(
            "INSERT INTO approval_requests "
            "(approval_id, tenant_id, draft_id, draft_version, status, reasons, "
            " snapshot, requested_by) "
            "VALUES (%s, %s, %s, %s, 'PENDING', %s, %s, %s)",
            (
                approval_id,
                tenant,
                order["draft_id"],
                order["version"],
                Jsonb(reasons),
                Jsonb(snapshot),
                user.user_id,
            ),
        )
    except psycopg.errors.UniqueViolation:
        raise PendingOwnerApprovalError() from None
    conn.execute(
        "UPDATE orders SET status='PENDING_OWNER_APPROVAL', updated_at=now() "
        "WHERE tenant_id=%s AND draft_id=%s",
        (tenant, order["draft_id"]),
    )
    approval = _approval(conn, tenant, approval_id)
    return _approval_response(approval, customer)


def _validate_for_approval(
    conn, order: dict[str, Any], tenant: str, *, allow_pending: bool = False
) -> tuple[dict[str, Any], dict[str, Any], list[WorkingLine], Decimal, list[dict[str, Any]]]:
    if order["status"] == "DO_GENERATED":
        raise AlreadyApprovedError()
    if order["status"] == "PENDING_OWNER_APPROVAL" and not allow_pending:
        raise PendingOwnerApprovalError()
    if order["status"] == "REJECTED":
        raise DraftRejectedError()
    if order["status"] != "READY_FOR_APPROVAL" and not (
        allow_pending and order["status"] == "PENDING_OWNER_APPROVAL"
    ):
        raise RequestValidationFailedError(
            details={"fields": [{"path": "status", "reason": "draft is not ready"}]}
        )
    lines = _old_lines(order)
    if not lines:
        raise RequestValidationFailedError(
            details={"fields": [{"path": "lines", "reason": "at least one line is required"}]}
        )
    if any(line.subtotal_rm is None for line in lines):
        raise RequestValidationFailedError(
            details={"fields": [{"path": "lines", "reason": "all lines need a price"}]}
        )
    if order["issues"]:
        blocking = [
            issue
            for issue in order["issues"]
            if issue.get("blocking") and not issue.get("resolved")
        ]
        if blocking:
            raise RequestValidationFailedError(
                details={"issues": [issue.get("code") for issue in blocking]}
            )
    customer = _customer(conn, tenant, order["customer_id"])
    tenant_rules = _tenant(conn, tenant)
    by_id = {line.line_id: line for line in lines}
    for issue in order["issues"]:
        if issue.get("condition_kind") != "PRICE":
            continue
        dismissed = (
            issue.get("resolution") == "NOT_A_CONDITION"
            and (issue.get("resolution_note") or "").strip()
        )
        if dismissed:
            continue
        confirmed_price = issue.get("data_used", {}).get("confirmed_unit_price")
        targets = issue.get("target_line_ids", [])
        if (
            issue.get("resolution") != "ACCEPT_REQUESTED_PRICE"
            or issue.get("price_basis") != "UNIT"
            or not targets
            or not confirmed_price
            or not (issue.get("resolution_note") or "").strip()
            or any(
                target not in by_id or by_id[target].unit_price_override != confirmed_price
                for target in targets
            )
        ):
            raise RequestValidationFailedError(
                "price condition must be reconfirmed for saved targets"
            )
    for line in lines:
        if not line.sku_id or not line.uom:
            raise RequestValidationFailedError("selected SKU and UOM required")
        product = _product(conn, tenant, line.sku_id)
        _canonical_uom(conn, tenant, line.uom, product["base_unit"])
        price = _tier_price(conn, tenant, customer["tier"], line.sku_id)
        if (
            product["family_id"] != line.family_id
            or price is None
            or _money(price) != line.tier_unit_price
        ):
            raise RequestValidationFailedError("product or tier price changed; save draft again")
        effective = line.unit_price_override or line.tier_unit_price
        if (
            line.effective_qty != (line.confirmed_qty or line.requested_qty)
            or line.effective_unit_price != effective
            or line.subtotal_rm != _money(Decimal(effective) * line.effective_qty)
            or (line.unit_price_override is not None and not (line.override_reason or "").strip())
        ):
            raise RequestValidationFailedError("saved price or quantity is inconsistent")
    total = sum(Decimal(line.subtotal_rm) for line in lines)
    reasons = _escalation(
        tenant=tenant_rules,
        customer=customer,
        lines=lines,
        total=total,
    )
    return customer, tenant_rules, lines, total, reasons


@router.post(
    "/orders/{draft_id}/approve",
    response_model=DeliveryOrder | ApprovalRequestResponse,
    responses={
        200: {"description": "DO generated"},
        202: {"description": "Owner approval requested"},
        400: {"description": "Insufficient stock or invalid lines"},
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "Role not allowed"},
        404: {"description": "Draft not found in tenant"},
        409: {"description": "Stale version or draft not editable"},
        422: {"description": "Validation failed"},
    },
)
def approve(
    draft_id: str,
    body: ApproveRequest,
    response: Response,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeliveryOrder | ApprovalRequestResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    if body.confirmed_items is not None:
        raise RequestValidationFailedError(
            details={
                "fields": [
                    {
                        "path": "confirmed_items",
                        "reason": "deprecated; save lines first with PUT /lines",
                    }
                ]
            }
        )

    with connect(settings) as conn:
        conn.execute("BEGIN")
        try:
            order = _order(conn, user.tenant_id, draft_id, lock=True)
            if body.expected_version != order["version"]:
                raise StaleVersionError(
                    details={
                        "expected_version": body.expected_version,
                        "current_version": order["version"],
                    }
                )
            customer, _tenant_rules, lines, _total, reasons = _validate_for_approval(
                conn, order, user.tenant_id
            )
            masked = conn.execute(
                "SELECT masked_text FROM inbound_messages WHERE tenant_id=%s AND message_id=%s",
                (user.tenant_id, order["message_id"]),
            ).fetchone()
            masked_message = masked[0] if masked else ""
            _lock_and_verify_stock(conn, user.tenant_id, lines, error_cls=InsufficientStockError)

            if reasons and user.role == "CLERK":
                approval = _create_approval(
                    conn,
                    tenant=user.tenant_id,
                    order=order,
                    customer=customer,
                    lines=lines,
                    reasons=reasons,
                    masked_message=masked_message,
                    user=user,
                )
                _audit(
                    conn,
                    tenant=user.tenant_id,
                    draft_id=draft_id,
                    version=order["version"],
                    action="SUBMIT_APPROVAL",
                    event="OWNER_APPROVAL_REQUESTED",
                    user=user,
                    payload={"approval_id": approval.approval_id, "reasons": reasons},
                )
                conn.execute("COMMIT")
                response.status_code = 202
                return approval

            _lock_and_verify_stock(conn, user.tenant_id, lines, error_cls=InsufficientStockError)
            mode = "OWNER_SELF_APPROVED" if reasons and user.role == "OWNER" else "DIRECT"
            do = _create_do(
                conn,
                tenant=user.tenant_id,
                order=order,
                customer=customer,
                lines=lines,
                reasons=reasons,
                user=user,
                mode=mode,
            )
            _deduct_stock(conn, user.tenant_id, lines)
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=draft_id,
                version=order["version"],
                action="APPROVE",
                event="DO_CREATED",
                user=user,
                payload={
                    "do_number": do.do_number,
                    "mode": mode,
                    "customer_name": do.customer_name,
                },
            )
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=draft_id,
                version=order["version"],
                action="INVENTORY_DEDUCT",
                event="INVENTORY_DEDUCTED",
                user=user,
                payload={"do_number": do.do_number},
            )
            conn.execute("COMMIT")
            return do
        except BaseException:
            with suppress(psycopg.Error):
                conn.execute("ROLLBACK")
            raise


@router.post(
    "/approvals/{approval_id}/decide",
    response_model=DeliveryOrder | ApprovalDecisionResult,
    responses={
        200: {"description": "DO generated or approval rejected"},
        400: {"description": "Invalid state"},
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "OWNER only"},
        404: {"description": "Approval not found in tenant"},
        409: {"description": "Stock changed or stale approval"},
        422: {"description": "Rejection note required"},
    },
)
def decide(
    approval_id: str,
    body: DecideRequest,
    response: Response,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeliveryOrder | ApprovalDecisionResult:
    if user.role != "OWNER":
        raise ForbiddenActionError()
    if body.decision == "REJECT" and not (body.note or "").strip():
        raise RejectionReasonRequiredError()

    with connect(settings) as conn:
        conn.execute("BEGIN")
        try:
            approval = _approval(conn, user.tenant_id, approval_id)
            order = _order(conn, user.tenant_id, approval["draft_id"], lock=True)
            approval = _approval(conn, user.tenant_id, approval_id, lock=True)
            if approval["status"] != "PENDING":
                raise PendingOwnerApprovalError()
            if approval["draft_version"] != order["version"]:
                raise StaleVersionError(
                    details={
                        "expected_version": approval["draft_version"],
                        "current_version": order["version"],
                    }
                )
            if order["status"] != "PENDING_OWNER_APPROVAL":
                raise PendingOwnerApprovalError()
            if body.decision == "REJECT":
                conn.execute(
                    "UPDATE approval_requests SET status='REJECTED', decided_by=%s, "
                    "decided_at=now(), decision_note=%s WHERE approval_id=%s",
                    (user.user_id, body.note, approval_id),
                )
                conn.execute(
                    "UPDATE orders SET status='REJECTED', termination_reason='OWNER_REJECTED', "
                    "terminated_by_user_id=%s, termination_note=%s, updated_at=now() "
                    "WHERE tenant_id=%s AND draft_id=%s",
                    (user.user_id, body.note, user.tenant_id, order["draft_id"]),
                )
                _audit(
                    conn,
                    tenant=user.tenant_id,
                    draft_id=order["draft_id"],
                    version=order["version"],
                    action="DECIDE_REJECT",
                    event="OWNER_REJECTED",
                    user=user,
                    payload={"approval_id": approval_id, "note": body.note},
                )
                conn.execute("COMMIT")
                return ApprovalDecisionResult(
                    approval_id=approval_id,
                    draft_id=order["draft_id"],
                    status="REJECTED",
                    termination_reason="OWNER_REJECTED",
                    decided_by=user.user_id,
                    decided_at=_now(),
                    decision_note=body.note or "",
                )

            customer, _tenant_rules, lines, _total, reasons = _validate_for_approval(
                conn, order, user.tenant_id, allow_pending=True
            )
            if order["working_lines"] != approval["snapshot"]["lines"]:
                # Stock availability is a live observation, not editable order content.
                def comparable(row):
                    return {k: v for k, v in row.items() if k != "available_qty"}

                if [comparable(row) for row in order["working_lines"]] != [
                    comparable(row) for row in approval["snapshot"]["lines"]
                ]:
                    raise RequestValidationFailedError("pending approval snapshot changed")
            _lock_and_verify_stock(conn, user.tenant_id, lines)
            do = _create_do(
                conn,
                tenant=user.tenant_id,
                order=order,
                customer=customer,
                lines=lines,
                reasons=reasons,
                user=user,
                mode="OWNER_APPROVED",
            )
            _deduct_stock(conn, user.tenant_id, lines)
            conn.execute(
                "UPDATE approval_requests SET status='APPROVED', decided_by=%s, "
                "decided_at=now(), decision_note=%s WHERE approval_id=%s",
                (user.user_id, body.note, approval_id),
            )
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=order["draft_id"],
                version=order["version"],
                action="DECIDE_APPROVE",
                event="OWNER_APPROVED",
                user=user,
                payload={
                    "approval_id": approval_id,
                    "do_number": do.do_number,
                    "customer_name": do.customer_name,
                    "note": body.note,
                },
            )
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=order["draft_id"],
                version=order["version"],
                action="INVENTORY_DEDUCT",
                event="INVENTORY_DEDUCTED",
                user=user,
                payload={"do_number": do.do_number},
            )
            conn.execute("COMMIT")
            return do
        except BaseException:
            with suppress(psycopg.Error):
                conn.execute("ROLLBACK")
            raise


def _approval_customer(row) -> dict:
    return {
        "customer_id": row[0],
        "name": row[1],
        "tier": row[2],
        "credit_flag": row[3],
        "has_credit_notice": row[3] == "OVERDUE_NOTICE",
        "phone_e164": row[4],
    }


@router.get("/approvals", response_model=ApprovalListResponse)
def list_approvals(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    status: ApprovalStatus | None = None,
    mine: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> ApprovalListResponse:
    if user.role == "WAREHOUSE":
        raise ForbiddenActionError()
    sql = (
        "SELECT a.approval_id, a.draft_id, a.draft_version, a.status, a.reasons, "
        "a.snapshot, a.requested_by, a.requested_at, a.decided_by, a.decided_at, "
        "a.decision_note, c.customer_id, c.name, c.tier, c.credit_flag, c.phone_e164 "
        "FROM approval_requests a "
        "JOIN customers c ON c.tenant_id=a.tenant_id AND c.customer_id="
        "(a.snapshot->>'customer_id') "
        "WHERE a.tenant_id=%s"
    )
    params: list[Any] = [user.tenant_id]
    if status is not None:
        sql += " AND a.status=%s"
        params.append(status)
    if user.role == "CLERK":
        sql += " AND a.requested_by=%s"
        params.append(user.user_id)
    elif mine:
        sql += " AND a.requested_by=%s"
        params.append(user.user_id)
    if cursor:
        sql += (
            " AND (a.requested_at, a.approval_id) < "
            "(SELECT requested_at, approval_id FROM approval_requests "
            " WHERE tenant_id=%s AND approval_id=%s)"
        )
        params.extend([user.tenant_id, cursor])
    sql += " ORDER BY a.requested_at DESC, a.approval_id DESC LIMIT %s"
    params.append(limit)
    with connect(settings) as conn:
        rows = conn.execute(sql, params).fetchall()
    items = []
    for row in rows:
        snapshot = row[5] or {}
        customer = _approval_customer(row[11:])
        if snapshot.get("customer_name"):
            customer["name"] = snapshot["customer_name"]
        items.append(
            ApprovalRequestResponse(
                approval_id=row[0],
                draft_id=row[1],
                draft_version=row[2],
                status=row[3],
                customer=customer,
                total_rm=snapshot.get("total_rm", "0.00"),
                line_count=len(snapshot.get("lines", [])),
                reasons=row[4] or [],
                requested_by=row[6],
                requested_at=row[7],
                allowed_actions=(
                    ["OWNER_APPROVE", "OWNER_REJECT"]
                    if user.role == "OWNER" and row[3] == "PENDING"
                    else []
                ),
                decided_by=row[8],
                decided_at=row[9],
                decision_note=row[10],
            )
        )
    next_cursor = rows[-1][0] if len(rows) == limit else None
    return ApprovalListResponse(items=items, next_cursor=next_cursor)


@router.get("/approvals/{approval_id}", response_model=ApprovalDetail)
def get_approval(
    approval_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApprovalDetail:
    if user.role == "WAREHOUSE":
        raise ForbiddenActionError()
    with connect(settings) as conn:
        approval = _approval(conn, user.tenant_id, approval_id)
        if user.role == "CLERK" and approval["requested_by"] != user.user_id:
            raise ResourceNotFoundError()
        customer = _customer(
            conn, user.tenant_id, approval["snapshot"]["customer_id"], active_only=False
        )
        diff_rows = conn.execute(
            "SELECT fd.draft_version, fd.line_id, fd.field_path, fd.before_value, "
            "fd.after_value, fd.source, fd.reason_code "
            "FROM field_diffs fd JOIN audit_logs al ON al.audit_id=fd.audit_id "
            "WHERE al.tenant_id=%s AND al.draft_id=%s AND al.draft_version=%s "
            "ORDER BY fd.field_diff_id",
            (user.tenant_id, approval["draft_id"], approval["draft_version"]),
        ).fetchall()
        stock_lines: list[StockCheckLine] = []
        for line in approval["snapshot"]["lines"]:
            sku_id = line.get("sku_id")
            if not sku_id:
                continue
            available = int(line.get("available_qty") or 0)
            effective = int(line["effective_qty"])
            stock_lines.append(
                StockCheckLine(
                    line_id=line["line_id"],
                    sku_id=sku_id,
                    requested_qty=int(line["requested_qty"]),
                    available_qty=available,
                    sufficient=available >= effective,
                    effective_qty=effective,
                )
            )
    snapshot = ApprovalSnapshot.model_validate(approval["snapshot"])
    state = (
        "NOT_RUN"
        if not stock_lines
        else ("PASSED" if all(x.sufficient for x in stock_lines) else "FAILED")
    )
    return ApprovalDetail(
        approval_id=approval["approval_id"],
        draft_id=approval["draft_id"],
        draft_version=approval["draft_version"],
        status=approval["status"],
        customer={
            "customer_id": customer["customer_id"],
            "name": approval["snapshot"].get("customer_name") or customer["name"],
            "tier": customer["tier"],
            "credit_flag": customer["credit_flag"],
            "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
            "phone_e164": customer["phone_e164"],
        },
        total_rm=approval["snapshot"]["total_rm"],
        line_count=len(approval["snapshot"]["lines"]),
        reasons=approval["reasons"],
        requested_by=approval["requested_by"],
        requested_at=approval["requested_at"],
        allowed_actions=(
            ["OWNER_APPROVE", "OWNER_REJECT"]
            if user.role == "OWNER" and approval["status"] == "PENDING"
            else []
        ),
        decided_by=approval["decided_by"],
        decided_at=approval["decided_at"],
        decision_note=approval["decision_note"],
        snapshot=snapshot,
        field_diffs=[
            FieldDiff(
                draft_version=row[0],
                line_id=row[1],
                field_path=row[2],
                before_value=row[3],
                after_value=row[4],
                source=row[5],
                reason_code=row[6],
            )
            for row in diff_rows
        ],
        stock_check=StockCheckSummary(
            state=state,
            checked_at=approval["requested_at"] if stock_lines else None,
            lines=stock_lines,
        ),
    )
