"""Atomically replace editable draft lines and create a new immutable version."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.errors import (
    AlreadyApprovedError,
    DraftRejectedError,
    EmptyOrderError,
    ForbiddenActionError,
    InvalidLineOperationError,
    InvalidQuantityError,
    MissingTierPriceError,
    OverrideRequiredError,
    PendingOwnerApprovalError,
    RequestValidationFailedError,
    ResourceNotFoundError,
    StaleVersionError,
)
from app.schemas import (
    Issue,
    OrderDraftResponse,
    OrderTotals,
    SaveLinesRequest,
    WorkingLine,
)

router = APIRouter(prefix="/api/v1", tags=["Drafts"])
MONEY = Decimal("0.01")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> str:
    return format(value.quantize(MONEY, rounding=ROUND_HALF_UP), ".2f")


def _decimal(value: str | None, field: str = "amount") -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise RequestValidationFailedError(
            details={"fields": [{"path": field, "reason": "must be a decimal string"}]}
        ) from None
    if not parsed.is_finite():
        raise RequestValidationFailedError(
            details={"fields": [{"path": field, "reason": "must be finite"}]}
        )
    return parsed


def _stable_id(prefix: str, *parts: str | None) -> str:
    material = "|".join(part or "" for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest().upper()
    return f"{prefix}_{digest[:24]}"


def _order(conn, tenant: str, draft_id: str, *, lock: bool = False) -> dict[str, Any]:
    suffix = " FOR UPDATE" if lock else ""
    row = conn.execute(
        "SELECT status, version, customer_id, message_id, ai_mode, working_lines, issues, "
        "clarification, escalation_preview, created_at, updated_at, "
        "termination_reason, terminated_by_user_id, termination_note "
        "FROM orders WHERE tenant_id=%s AND draft_id=%s" + suffix,
        (tenant, draft_id),
    ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return {
        "draft_id": draft_id,
        "status": row[0],
        "version": row[1],
        "customer_id": row[2],
        "message_id": row[3],
        "ai_mode": row[4],
        "working_lines": row[5] or [],
        "issues": row[6] or [],
        "clarification": row[7],
        "escalation_preview": row[8] or [],
        "created_at": row[9],
        "updated_at": row[10],
        "termination_reason": row[11],
        "terminated_by_user_id": row[12],
        "termination_note": row[13],
    }


def _customer(conn, tenant: str, customer_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT customer_id, name, tier, credit_flag, phone_e164 "
        "FROM customers WHERE tenant_id=%s AND customer_id=%s AND active=true",
        (tenant, customer_id),
    ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return {
        "customer_id": row[0],
        "name": row[1],
        "tier": row[2],
        "credit_flag": row[3],
        "phone_e164": row[4],
    }


def _tenant(conn, tenant: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT amount_threshold_rm, below_tier_price_override_requires_owner, "
        "credit_flag_requires_owner FROM tenants WHERE tenant_id=%s",
        (tenant,),
    ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return {
        "threshold": Decimal(row[0]),
        "price_requires_owner": row[1],
        "credit_requires_owner": row[2],
    }


def _product(conn, tenant: str, sku_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT p.product_id, p.family_id, p.name, p.pack_size, p.grade, p.base_unit "
        "FROM products p JOIN product_families f "
        "ON f.tenant_id=p.tenant_id AND f.family_id=p.family_id "
        "WHERE p.tenant_id=%s AND p.product_id=%s AND p.active=true AND f.active=true",
        (tenant, sku_id),
    ).fetchone()
    if row is None:
        raise RequestValidationFailedError(
            details={"fields": [{"path": "lines.sku_id", "reason": "unknown or inactive SKU"}]}
        )
    return {
        "sku_id": row[0],
        "family_id": row[1],
        "name": row[2],
        "pack_size": row[3],
        "grade": row[4],
        "base_unit": row[5],
    }


def _tier_price(conn, tenant: str, tier: str, sku_id: str) -> Decimal | None:
    row = conn.execute(
        "SELECT unit_price_rm FROM customer_tier_prices "
        "WHERE tenant_id=%s AND product_id=%s AND tier=%s",
        (tenant, sku_id, tier),
    ).fetchone()
    return Decimal(row[0]) if row is not None else None


def _available(conn, tenant: str, sku_id: str) -> int:
    row = conn.execute(
        "SELECT available_qty FROM inventory WHERE tenant_id=%s AND product_id=%s",
        (tenant, sku_id),
    ).fetchone()
    return int(row[0]) if row is not None else 0


def _masked_message(conn, tenant: str, message_id: str | None) -> str:
    if not message_id:
        return ""
    row = conn.execute(
        "SELECT masked_text FROM inbound_messages WHERE tenant_id=%s AND message_id=%s",
        (tenant, message_id),
    ).fetchone()
    return row[0] if row is not None else ""


def _old_lines(order: dict[str, Any]) -> list[WorkingLine]:
    lines = []
    for raw in order["working_lines"]:
        lines.append(WorkingLine.model_validate(raw))
    return lines


def _coverage(old: list[WorkingLine], body: SaveLinesRequest) -> dict[str, Any]:
    old_ids = {line.line_id for line in old}
    submitted_ids: list[str] = []
    new_refs: list[str] = []
    for line in body.lines:
        if line.line_id is not None:
            submitted_ids.append(line.line_id)
        else:
            assert line.client_line_ref is not None
            new_refs.append(line.client_line_ref)

    deleted = body.deleted_line_ids
    duplicate_line_ids = sorted({line for line in submitted_ids if submitted_ids.count(line) > 1})
    overlap = sorted(set(submitted_ids) & set(deleted))
    unknown_deleted = sorted(set(deleted) - old_ids)
    unknown_submitted = sorted(set(submitted_ids) - old_ids)
    covered = set(submitted_ids) | set(deleted)
    missing = sorted(old_ids - covered)

    if duplicate_line_ids or overlap or unknown_deleted or unknown_submitted or missing:
        raise InvalidLineOperationError(
            details={
                "missing_line_ids": missing,
                "duplicate_line_ids": sorted(set(duplicate_line_ids + overlap)),
                "unknown_deleted_line_ids": unknown_deleted,
            }
        )
    if len(new_refs) != len(set(new_refs)):
        raise RequestValidationFailedError(
            details={"fields": [{"path": "lines.client_line_ref", "reason": "must be unique"}]}
        )
    if not body.lines:
        raise EmptyOrderError()
    return {
        "old_ids": old_ids,
        "submitted_ids": set(submitted_ids),
        "deleted_ids": set(deleted),
        "new_refs": new_refs,
    }


def _line(
    *,
    conn,
    tenant: str,
    customer: dict[str, Any],
    item,
    old: WorkingLine | None,
) -> tuple[WorkingLine, list[Issue]]:
    if item.line_id is None and item.confirmed_qty is None:
        raise InvalidQuantityError(
            details={"fields": [{"path": "lines.confirmed_qty", "reason": "new line needs qty"}]}
        )

    qty = (
        item.confirmed_qty
        if item.confirmed_qty is not None
        else (old.requested_qty if old is not None else None)
    )
    if qty is None or qty < 1:
        raise InvalidQuantityError()

    requested_qty = old.requested_qty if old is not None else qty
    family_id = item.family_id or (old.family_id if old is not None else "UNKNOWN")
    description = old.description if old is not None else None
    uom = item.uom or (old.uom if old is not None else None)
    pack_size = item.pack_size or (old.pack_size if old is not None else None)
    grade = item.grade or (old.grade if old is not None else None)
    tier_price: Decimal | None = None
    effective_price: Decimal | None = None
    subtotal: Decimal | None = None
    available: int | None = None
    candidates: list[dict[str, Any]] = []
    issues: list[Issue] = []

    if item.sku_id:
        product = _product(conn, tenant, item.sku_id)
        family_id = product["family_id"]
        description = product["name"]
        uom = uom or product["base_unit"]
        pack_size = pack_size or product["pack_size"]
        grade = grade or product["grade"]
        tier_price = _tier_price(conn, tenant, customer["tier"], item.sku_id)
        if tier_price is None:
            raise MissingTierPriceError(
                details={
                    "customer_id": customer["customer_id"],
                    "sku_id": item.sku_id,
                    "tier": customer["tier"],
                }
            )
        override = _decimal(item.unit_price_override, "lines.unit_price_override")
        if override is not None:
            if override <= 0:
                raise RequestValidationFailedError(
                    details={
                        "fields": [
                            {
                                "path": "lines.unit_price_override",
                                "reason": "must be positive",
                            }
                        ]
                    }
                )
            if not item.override_reason:
                raise OverrideRequiredError()
            effective_price = override
        else:
            effective_price = tier_price
        subtotal = effective_price * qty
        available = _available(conn, tenant, item.sku_id)
    else:
        issues.append(
            Issue(
                issue_id=_stable_id(
                    "ISS", item.line_id or item.client_line_ref, "LOW_CONFIDENCE_MATCH", None
                ),
                code="LOW_CONFIDENCE_MATCH",
                line_id=item.line_id,
                reason_code="NO_CANDIDATE",
                ask="CLERK",
                data_used={"sku_id": item.sku_id},
                blocking=True,
                resolved=False,
            )
        )

    if uom is None:
        issues.append(
            Issue(
                issue_id=_stable_id(
                    "ISS", item.line_id or item.client_line_ref, "MISSING_UOM", None
                ),
                code="MISSING_UOM",
                line_id=item.line_id,
                reason_code="FIELD_NOT_EVIDENCED",
                ask="CLERK",
                data_used={},
                blocking=True,
                resolved=False,
            )
        )
    if available is not None and available < qty:
        issues.append(
            Issue(
                issue_id=_stable_id(
                    "ISS", item.line_id or item.client_line_ref, "INSUFFICIENT_STOCK", None
                ),
                code="INSUFFICIENT_STOCK",
                line_id=item.line_id,
                reason_code="INVALID_QUANTITY",
                ask="CLERK",
                data_used={"available_qty": available, "effective_qty": qty},
                blocking=True,
                resolved=False,
            )
        )

    line = WorkingLine(
        line_id=item.line_id or f"LNE_{uuid4().hex.upper()}",
        client_line_ref=item.client_line_ref,
        sku_id=item.sku_id,
        family_id=family_id,
        description=description,
        requested_qty=requested_qty,
        confirmed_qty=item.confirmed_qty,
        effective_qty=qty,
        uom=uom,
        pack_size=pack_size,
        grade=grade,
        tier_unit_price=_money(tier_price) if tier_price is not None else None,
        unit_price_override=item.unit_price_override,
        override_reason=item.override_reason,
        effective_unit_price=_money(effective_price) if effective_price is not None else None,
        subtotal_rm=_money(subtotal) if subtotal is not None else None,
        match_source=item.match_source,
        source_span=old.source_span if old is not None else None,
        span_start=old.span_start if old is not None else None,
        span_end=old.span_end if old is not None else None,
        field_evidence=old.field_evidence if old is not None else [],
        candidate_skus=candidates,
        available_qty=available,
    )
    for issue in issues:
        if issue.line_id is None:
            issue.line_id = line.line_id
    return line, issues


def _escalation(
    *,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    lines: list[WorkingLine],
    total: Decimal | None,
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    if tenant["price_requires_owner"]:
        for line in lines:
            if (
                line.tier_unit_price is not None
                and line.effective_unit_price is not None
                and Decimal(line.effective_unit_price) < Decimal(line.tier_unit_price)
            ):
                reasons.append(
                    {
                        "code": "PRICE_OVERRIDE_BELOW_TIER",
                        "line_id": line.line_id,
                        "detail": {
                            "tier_unit_price": line.tier_unit_price,
                            "effective_unit_price": line.effective_unit_price,
                        },
                    }
                )
    if total is not None and total >= tenant["threshold"]:
        reasons.append(
            {
                "code": "AMOUNT_OVER_THRESHOLD",
                "line_id": None,
                "detail": {
                    "order_total": _money(total),
                    "threshold": _money(tenant["threshold"]),
                },
            }
        )
    if tenant["credit_requires_owner"] and customer["credit_flag"] == "OVERDUE_NOTICE":
        reasons.append(
            {
                "code": "CUSTOMER_CREDIT_FLAG",
                "line_id": None,
                "detail": {"credit_flag": customer["credit_flag"]},
            }
        )
    return reasons


def _actions(
    *, role: str, status: str, escalation: list[dict[str, Any]]
) -> tuple[list[str], dict[str, list[str]]]:
    if status in {"DO_GENERATED", "REJECTED"}:
        return ["VIEW_ACTIVITY"], {}
    if status == "PENDING_OWNER_APPROVAL":
        if role == "OWNER":
            return ["OWNER_APPROVE", "OWNER_REJECT", "VIEW_ACTIVITY"], {}
        return ["VIEW_ACTIVITY"], {"EDIT_DRAFT": ["PENDING_OWNER_APPROVAL"]}
    if status == "DISAMBIGUATION_REQUIRED":
        return ["EDIT_DRAFT", "RESOLVE_ISSUE", "VIEW_ACTIVITY"], {
            "APPROVE_AND_GENERATE_DO": ["BLOCKING_ISSUES"]
        }
    if escalation:
        return ["SUBMIT_FOR_OWNER", "VIEW_ACTIVITY"], {}
    return ["APPROVE_AND_GENERATE_DO", "VIEW_ACTIVITY"], {}


def _audit(
    conn,
    *,
    tenant: str,
    draft_id: str,
    version: int,
    action: str,
    event: str,
    user: CurrentUser,
    payload: dict[str, Any],
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    audit_id = f"AUD_{uuid4().hex.upper()}"
    conn.execute(
        "INSERT INTO audit_logs "
        "(audit_id, tenant_id, draft_id, draft_version, actor_user_id, "
        " actor_role, action, payload) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (audit_id, tenant, draft_id, version, user.user_id, user.role, action, Jsonb(payload)),
    )
    conn.execute(
        "INSERT INTO activity_log "
        "(tenant_id, draft_id, event_type, payload, actor_user_id, actor_role) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (tenant, draft_id, event, Jsonb(payload), user.user_id, user.role),
    )
    if before is not None and after is not None:
        tracked_fields = (
            "sku_id",
            "family_id",
            "description",
            "requested_qty",
            "confirmed_qty",
            "effective_qty",
            "uom",
            "pack_size",
            "grade",
            "tier_unit_price",
            "unit_price_override",
            "override_reason",
            "effective_unit_price",
            "subtotal_rm",
            "match_source",
            "available_qty",
        )
        for line_id in sorted(set(before) | set(after)):
            old_line = before.get(line_id)
            new_line = after.get(line_id)
            if old_line == new_line:
                continue
            if old_line is None or new_line is None:
                changes = [("line", old_line, new_line)]
            else:
                changes = [
                    (field, old_line.get(field), new_line.get(field))
                    for field in tracked_fields
                    if old_line.get(field) != new_line.get(field)
                ]
            for field_path, old_value, new_value in changes:
                conn.execute(
                    "INSERT INTO field_diffs "
                    "(audit_id, draft_version, line_id, field_path, before_value, "
                    " after_value, source, reason_code) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        audit_id,
                        version,
                        line_id,
                        field_path,
                        Jsonb(old_value) if old_value is not None else None,
                        Jsonb(new_value) if new_value is not None else None,
                        "PUT_LINES",
                        "USER_EDIT",
                    ),
                )


@router.put(
    "/orders/drafts/{draft_id}/lines",
    response_model=OrderDraftResponse,
    responses={
        400: {"description": "Invalid line operation or empty order"},
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "Role not allowed"},
        404: {"description": "Draft not found in tenant"},
        409: {"description": "Stale version or draft not editable"},
        422: {"description": "Validation failed"},
    },
)
def save_lines(
    draft_id: str,
    body: SaveLinesRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OrderDraftResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()

    with connect(settings) as conn:
        conn.execute("BEGIN")
        try:
            order = _order(conn, user.tenant_id, draft_id, lock=True)
            if order["status"] == "PENDING_OWNER_APPROVAL":
                raise PendingOwnerApprovalError()
            if order["status"] == "DO_GENERATED":
                raise AlreadyApprovedError()
            if order["status"] == "REJECTED":
                raise DraftRejectedError()
            if order["status"] not in {"DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"}:
                raise DraftRejectedError()
            if body.expected_version != order["version"]:
                raise StaleVersionError(
                    details={
                        "expected_version": body.expected_version,
                        "current_version": order["version"],
                    }
                )

            old = _old_lines(order)
            _coverage(old, body)
            customer = _customer(conn, user.tenant_id, order["customer_id"])
            tenant = _tenant(conn, user.tenant_id)
            old_by_id = {line.line_id: line for line in old}

            lines: list[WorkingLine] = []
            issues: list[Issue] = []
            for item in body.lines:
                old_line = old_by_id.get(item.line_id) if item.line_id else None
                line, line_issues = _line(
                    conn=conn,
                    tenant=user.tenant_id,
                    customer=customer,
                    item=item,
                    old=old_line,
                )
                lines.append(line)
                issues.extend(line_issues)

            total: Decimal | None = None
            if all(line.subtotal_rm is not None for line in lines):
                total = sum(Decimal(line.subtotal_rm) for line in lines)

            blocking = sorted({issue.code for issue in issues if issue.blocking})
            status = "READY_FOR_APPROVAL" if not blocking and lines else "DISAMBIGUATION_REQUIRED"
            escalation = _escalation(
                tenant=tenant,
                customer=customer,
                lines=lines,
                total=total,
            )
            allowed, blocked = _actions(
                role=user.role,
                status=status,
                escalation=escalation,
            )
            now = _now()
            draft = OrderDraftResponse(
                draft_id=draft_id,
                version=order["version"] + 1,
                status=status,
                customer_id=customer["customer_id"],
                customer={
                    "customer_id": customer["customer_id"],
                    "name": customer["name"],
                    "tier": customer["tier"],
                    "credit_flag": customer["credit_flag"],
                    "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
                    "phone_e164": customer["phone_e164"],
                },
                masked_message=_masked_message(conn, user.tenant_id, order["message_id"]),
                ai_mode=order["ai_mode"],
                lines=lines,
                issues=issues,
                conditions=[],
                blocking_issues=blocking,
                escalation_preview=escalation,
                totals=OrderTotals(
                    order_total=_money(total) if total is not None else None,
                    currency="MYR",
                    is_complete=total is not None,
                ),
                allowed_actions=allowed,
                blocked_actions=blocked,
                clarification_draft=None,
                clarification_lang=None,
                ignored_spans=[],
                created_at=order["created_at"],
                updated_at=now,
            )

            conn.execute(
                "UPDATE orders SET status=%s, version=%s, working_lines=%s, issues=%s, "
                "clarification=%s, escalation_preview=%s, updated_at=now() "
                "WHERE tenant_id=%s AND draft_id=%s",
                (
                    draft.status,
                    draft.version,
                    Jsonb([line.model_dump(mode="json") for line in lines]),
                    Jsonb([issue.model_dump(mode="json") for issue in issues]),
                    Jsonb(draft.clarification_draft) if draft.clarification_draft else None,
                    Jsonb(escalation),
                    user.tenant_id,
                    draft_id,
                ),
            )
            conn.execute(
                "INSERT INTO draft_versions (tenant_id, draft_id, version, snapshot, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    user.tenant_id,
                    draft_id,
                    draft.version,
                    Jsonb(draft.model_dump(mode="json")),
                    user.user_id,
                ),
            )
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=draft_id,
                version=draft.version,
                action="SAVE_LINES",
                event="DRAFT_VERSION_CREATED",
                user=user,
                payload={"version": draft.version, "line_count": len(lines)},
                before={line.line_id: line.model_dump(mode="json") for line in old},
                after={line.line_id: line.model_dump(mode="json") for line in lines},
            )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return draft
