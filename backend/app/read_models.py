"""Read-only contract endpoints for drafts, customers, activity, audit, warehouse, AI."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.drafts import (
    _actions,
    _customer,
    _latest_snapshot,
    _masked_message,
    _money,
    _old_lines,
    _order,
)
from app.errors import ForbiddenActionError, ResourceNotFoundError
from app.schemas import (
    ActivityItem,
    ActivityListResponse,
    AiStatus,
    AiWakeResult,
    AuditDetail,
    AuditEvent,
    ClarificationDraft,
    CustomerListResponse,
    CustomerSummary,
    DeliveryOrder,
    DraftListResponse,
    DraftStatus,
    DraftSummary,
    FieldDiff,
    Issue,
    MatchSource,
    OrderDraftResponse,
    OrderTotals,
    WarehouseDeliveryOrder,
    WarehouseDeliveryOrderItem,
)

router = APIRouter(prefix="/api/v1", tags=["Read models"])

PREVIEW_LIMIT = 160


def _preview(text: str | None) -> str:
    value = text or ""
    return value if len(value) <= PREVIEW_LIMIT else value[:PREVIEW_LIMIT].rstrip() + "…"


def _blocking(issues: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {issue["code"] for issue in issues if issue.get("blocking") and not issue.get("resolved")}
    )


def _sources(lines: list[dict[str, Any]]) -> list[MatchSource]:
    allowed = {"SUGGESTED_DEFAULT", "LLM_EXTRACTED", "RAPIDFUZZ_FALLBACK", "MANUAL_SELECTED"}
    return sorted({line["match_source"] for line in lines if line.get("match_source") in allowed})


def _actions_for(
    role: str,
    status: str,
    escalation: list[dict[str, Any]],
    clarification: dict[str, Any] | None,
) -> list[str]:
    allowed, _ = _actions(role=role, status=status, escalation=escalation)
    if clarification:
        allowed.append("COPY_CLARIFICATION")
    return allowed


@router.get("/orders/drafts", response_model=DraftListResponse)
def list_drafts(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    status: DraftStatus | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> DraftListResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    sql = (
        "SELECT o.draft_id, o.version, o.status, o.customer_id, c.name, "
        "m.masked_text, o.issues, o.clarification, o.escalation_preview, "
        "o.updated_at, o.working_lines, d.do_number "
        "FROM orders o "
        "JOIN customers c ON c.tenant_id=o.tenant_id AND c.customer_id=o.customer_id "
        "LEFT JOIN inbound_messages m "
        "  ON m.tenant_id=o.tenant_id AND m.message_id=o.message_id "
        "LEFT JOIN delivery_orders d "
        "  ON d.tenant_id=o.tenant_id AND d.draft_id=o.draft_id "
        "WHERE o.tenant_id=%s"
    )
    params: list[Any] = [user.tenant_id]
    if status is not None:
        sql += " AND o.status=%s"
        params.append(status)
    if cursor:
        sql += (
            " AND (o.updated_at, o.draft_id) < "
            "(SELECT updated_at, draft_id FROM orders WHERE tenant_id=%s AND draft_id=%s)"
        )
        params.extend([user.tenant_id, cursor])
    sql += " ORDER BY o.updated_at DESC, o.draft_id DESC LIMIT %s"
    params.append(limit)
    with connect(settings) as conn:
        rows = conn.execute(sql, params).fetchall()
    items = []
    for row in rows:
        issues = row[6] or []
        escalation = row[8] or []
        clarification = row[7] if isinstance(row[7], dict) else None
        items.append(
            DraftSummary(
                draft_id=row[0],
                version=row[1],
                status=row[2],
                customer_id=row[3],
                customer_name=row[4],
                message_preview=_preview(row[5]),
                blocking_issues=_blocking(issues),
                open_blocking_issue_count=len(
                    [
                        issue
                        for issue in issues
                        if issue.get("blocking") and not issue.get("resolved")
                    ]
                ),
                owner_escalation_count=len(escalation),
                extraction_sources=_sources(row[10] or []),
                allowed_actions=_actions_for(user.role, row[2], escalation, clarification),
                updated_at=row[9],
                do_number=row[11],
            )
        )
    return DraftListResponse(
        items=items,
        next_cursor=items[-1].draft_id if len(items) == limit else None,
    )


@router.get("/orders/drafts/{draft_id}", response_model=OrderDraftResponse)
def get_draft(
    draft_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OrderDraftResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    with connect(settings) as conn:
        order = _order(conn, user.tenant_id, draft_id)
        customer = _customer(conn, user.tenant_id, order["customer_id"], active_only=False)
        lines = _old_lines(order)
        stored_issues = [Issue.model_validate(issue) for issue in (order["issues"] or [])]
        issues = stored_issues
        conditions = [issue for issue in stored_issues if issue.code == "CUSTOMER_CONDITION"]
        blocking = sorted(
            {
                issue.code
                for issue in [*issues, *conditions]
                if issue.blocking and not issue.resolved
            }
        )
        clarification_data = order.get("clarification")
        clarification = (
            ClarificationDraft.model_validate(clarification_data)
            if isinstance(clarification_data, dict)
            else None
        )
        allowed = _actions_for(
            user.role,
            order["status"],
            order["escalation_preview"],
            clarification_data if isinstance(clarification_data, dict) else None,
        )
        _, blocked = _actions(
            role=user.role,
            status=order["status"],
            escalation=order["escalation_preview"],
        )
        snapshot = _latest_snapshot(conn, user.tenant_id, draft_id)
        do_row = conn.execute(
            "SELECT do_number FROM delivery_orders WHERE tenant_id=%s AND draft_id=%s",
            (user.tenant_id, draft_id),
        ).fetchone()
        masked_message = _masked_message(conn, user.tenant_id, order["message_id"])
    total: Decimal | None = None
    if lines and all(line.subtotal_rm is not None for line in lines):
        total = sum(Decimal(line.subtotal_rm) for line in lines)
    return OrderDraftResponse(
        draft_id=order["draft_id"],
        version=order["version"],
        status=order["status"],
        customer_id=customer["customer_id"],
        customer={
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "tier": customer["tier"],
            "credit_flag": customer["credit_flag"],
            "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
            "phone_e164": customer["phone_e164"],
        },
        masked_message=masked_message,
        ai_mode=order["ai_mode"],
        lines=lines,
        issues=issues,
        conditions=conditions,
        blocking_issues=blocking,
        escalation_preview=order["escalation_preview"],
        totals=OrderTotals(
            order_total=_money(total) if total is not None else None,
            currency="MYR",
            is_complete=total is not None,
        ),
        allowed_actions=allowed,
        blocked_actions=blocked,
        clarification_draft=clarification,
        clarification_lang=clarification.language if clarification else None,
        ignored_spans=snapshot.get("ignored_spans", []),
        created_at=order["created_at"],
        updated_at=order["updated_at"],
        do_number=do_row[0] if do_row else None,
        termination_reason=order["termination_reason"],
        terminated_by_user_id=order["terminated_by_user_id"],
        termination_note=order["termination_note"],
    )


@router.get("/customers", response_model=CustomerListResponse)
def list_customers(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> CustomerListResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    sql = (
        "SELECT customer_id, name, tier, credit_flag, phone_e164 "
        "FROM customers WHERE tenant_id=%s AND active=true"
    )
    params: list[Any] = [user.tenant_id]
    if cursor:
        sql += " AND customer_id > %s"
        params.append(cursor)
    sql += " ORDER BY customer_id LIMIT %s"
    params.append(limit)
    with connect(settings) as conn:
        rows = conn.execute(sql, params).fetchall()
    items = [
        CustomerSummary(
            customer_id=row[0],
            name=row[1],
            tier=row[2],
            credit_flag=row[3],
            has_credit_notice=row[3] == "OVERDUE_NOTICE",
            phone_e164=row[4],
        )
        for row in rows
    ]
    return CustomerListResponse(
        items=items,
        next_cursor=items[-1].customer_id if len(items) == limit else None,
    )


@router.get("/activity", response_model=ActivityListResponse)
def list_activity(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    entity_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> ActivityListResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    sql = (
        "SELECT activity_id, draft_id, do_number, event_type, payload, actor_user_id, "
        "actor_role, created_at FROM activity_log WHERE tenant_id=%s"
    )
    params: list[Any] = [user.tenant_id]
    if entity_id:
        sql += " AND (draft_id=%s OR do_number=%s)"
        params.extend([entity_id, entity_id])
    if cursor:
        try:
            activity_id = int(cursor)
        except ValueError as exc:
            raise ResourceNotFoundError("invalid activity cursor") from exc
        sql += " AND activity_id < %s"
        params.append(activity_id)
    sql += " ORDER BY activity_id DESC LIMIT %s"
    params.append(limit)
    with connect(settings) as conn:
        rows = conn.execute(sql, params).fetchall()
    items = [
        ActivityItem(
            activity_id=row[0],
            entity_id=row[1] or row[2],
            event_type=row[3],
            payload=row[4] or {},
            actor_user_id=row[5],
            actor_role=row[6],
            created_at=row[7],
        )
        for row in rows
    ]
    return ActivityListResponse(
        items=items,
        next_cursor=str(items[-1].activity_id) if len(items) == limit else None,
    )


def _delivery_order(conn, tenant: str, do_number: str) -> tuple[DeliveryOrder, dict[str, Any]]:
    row = conn.execute(
        "SELECT d.do_number, d.draft_id, d.draft_version, d.customer_id, "
        "COALESCE((SELECT a.payload->>'customer_name' FROM audit_logs a "
        "WHERE a.tenant_id=d.tenant_id AND a.do_number=d.do_number "
        "AND a.action IN ('APPROVE','DECIDE_APPROVE') "
        "AND a.payload ? 'customer_name' LIMIT 1), "
        "dv.snapshot->'customer'->>'name', c.name), d.lines, d.final_total_rm, "
        "d.prepared_by, d.approved_by, d.escalation_reasons, d.approval_mode, "
        "d.reply_draft, d.related_do_number, d.approved_at, "
        "o.ai_initial_snapshot "
        "FROM delivery_orders d "
        "LEFT JOIN draft_versions dv "
        "  ON dv.tenant_id=d.tenant_id AND dv.draft_id=d.draft_id "
        " AND dv.version=d.draft_version "
        "JOIN customers c ON c.tenant_id=d.tenant_id AND c.customer_id=d.customer_id "
        "JOIN orders o ON o.tenant_id=d.tenant_id AND o.draft_id=d.draft_id "
        "WHERE d.tenant_id=%s AND d.do_number=%s",
        (tenant, do_number),
    ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return (
        DeliveryOrder(
            do_number=row[0],
            draft_id=row[1],
            draft_version=row[2],
            customer_id=row[3],
            customer_name=row[4],
            lines=row[5],
            final_total_rm=format(row[6], ".2f"),
            prepared_by=row[7],
            approved_by=row[8],
            escalation_reasons=row[9] or [],
            approval_mode=row[10],
            reply_draft=row[11],
            related_do_number=row[12],
            approved_at=row[13],
        ),
        {"ai_initial_snapshot": row[14]},
    )


@router.get("/orders/{do_number}/audit-detail", response_model=AuditDetail)
def get_audit_detail(
    do_number: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuditDetail:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    with connect(settings) as conn:
        final, extra = _delivery_order(conn, user.tenant_id, do_number)
        diff_rows = conn.execute(
            "SELECT fd.draft_version, fd.line_id, fd.field_path, fd.before_value, "
            "fd.after_value, fd.source, fd.reason_code "
            "FROM field_diffs fd JOIN audit_logs al ON al.audit_id=fd.audit_id "
            "WHERE al.tenant_id=%s AND al.draft_id=%s AND al.draft_version<=%s "
            "ORDER BY fd.field_diff_id",
            (user.tenant_id, final.draft_id, final.draft_version),
        ).fetchall()
        event_rows = conn.execute(
            "SELECT action, actor_user_id, actor_role, created_at, payload "
            "FROM audit_logs WHERE tenant_id=%s AND draft_id=%s AND draft_version<=%s "
            "ORDER BY created_at, audit_id",
            (user.tenant_id, final.draft_id, final.draft_version),
        ).fetchall()
    return AuditDetail(
        do_number=final.do_number,
        draft_id=final.draft_id,
        draft_version=final.draft_version,
        ai_initial_snapshot=extra["ai_initial_snapshot"] or {},
        final_snapshot=final,
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
        events=[
            AuditEvent(
                event_type=row[0],
                actor_user_id=row[1],
                actor_role=row[2],
                created_at=row[3],
                payload=row[4] or {},
            )
            for row in event_rows
        ],
    )


@router.get("/warehouse/delivery-orders/{do_number}", response_model=WarehouseDeliveryOrder)
def get_warehouse_delivery_order(
    do_number: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WarehouseDeliveryOrder:
    if user.role != "WAREHOUSE":
        raise ForbiddenActionError()
    with connect(settings) as conn:
        final, _ = _delivery_order(conn, user.tenant_id, do_number)
    return WarehouseDeliveryOrder(
        do_number=final.do_number,
        customer_name=final.customer_name,
        items=[
            WarehouseDeliveryOrderItem(
                sku_id=line.sku_id,
                display_name=line.display_name,
                quantity=line.quantity,
                unit=line.unit,
                picking_note=line.picking_note,
            )
            for line in final.lines
        ],
        approved_at=final.approved_at,
    )


@router.get("/ai/status", response_model=AiStatus)
def get_ai_status(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AiStatus:
    return request.app.state.ai_orchestrator.status()


@router.post("/ai/wake", response_model=AiWakeResult)
def wake_ai(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AiWakeResult:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    return request.app.state.ai_orchestrator.wake(user.user_id)
