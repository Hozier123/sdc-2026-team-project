"""Atomically replace editable draft lines and create a new immutable version."""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb

from app.auth import CurrentUser
from app.checks import apply_checks, normalize_checks
from app.clarification import build_clarification
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
    NoteRequiredError,
    OverrideRequiredError,
    PendingOwnerApprovalError,
    RequestValidationFailedError,
    ResourceNotFoundError,
    StaleVersionError,
    TargetLineRequiredError,
)
from app.pii import mask_message
from app.schemas import (
    ClarificationCopiedRequest,
    ClarificationCopiedResult,
    ClarificationDraft,
    DiscardRequest,
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
    if not value.is_finite() or value < 0 or value > Decimal("9999999999.99"):
        raise RequestValidationFailedError(
            details={"fields": [{"path": "amount", "reason": "outside numeric(12,2) range"}]}
        )
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
    snapshot = _latest_snapshot(conn, tenant, draft_id)
    complete_issues = {
        issue["issue_id"]: issue for issue in [*snapshot.get("conditions", []), *(row[6] or [])]
    }
    return {
        "draft_id": draft_id,
        "status": row[0],
        "version": row[1],
        "customer_id": row[2],
        "message_id": row[3],
        "ai_mode": row[4],
        "working_lines": row[5] or [],
        "issues": list(complete_issues.values()),
        "clarification": row[7],
        "escalation_preview": row[8] or [],
        "created_at": row[9],
        "updated_at": row[10],
        "termination_reason": row[11],
        "terminated_by_user_id": row[12],
        "termination_note": row[13],
    }


def _customer(conn, tenant: str, customer_id: str, *, active_only: bool = True) -> dict[str, Any]:
    row = conn.execute(
        "SELECT customer_id, name, tier, credit_flag, phone_e164 "
        "FROM customers WHERE tenant_id=%s AND customer_id=%s"
        + (" AND active=true" if active_only else "")
        + " FOR SHARE",
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
        "credit_flag_requires_owner, checks_enabled "
        "FROM tenants WHERE tenant_id=%s FOR SHARE",
        (tenant,),
    ).fetchone()
    if row is None:
        raise ResourceNotFoundError()
    return {
        "threshold": Decimal(row[0]),
        "price_requires_owner": row[1],
        "credit_requires_owner": row[2],
        "checks": normalize_checks(row[3]),
    }


def _product(conn, tenant: str, sku_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT p.product_id, p.family_id, p.name, p.pack_size, p.grade, p.base_unit "
        "FROM products p JOIN product_families f "
        "ON f.tenant_id=p.tenant_id AND f.family_id=p.family_id "
        "WHERE p.tenant_id=%s AND p.product_id=%s AND p.active=true AND f.active=true "
        "FOR SHARE OF p, f",
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
        "WHERE tenant_id=%s AND product_id=%s AND tier=%s FOR SHARE",
        (tenant, sku_id, tier),
    ).fetchone()
    return Decimal(row[0]) if row is not None else None


def _family_has_mixed_base_units(conn, tenant: str, family_id: str) -> bool:
    rows = conn.execute(
        "SELECT DISTINCT p.base_unit FROM products p "
        "JOIN product_families f "
        "ON f.tenant_id=p.tenant_id AND f.family_id=p.family_id "
        "WHERE p.tenant_id=%s AND p.family_id=%s AND p.active=true AND f.active=true",
        (tenant, family_id),
    ).fetchall()
    return len(rows) > 1


def _canonical_uom(conn, tenant: str, value: str | None, base_unit: str) -> str:
    if value is None:
        return base_unit
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    row = conn.execute(
        "SELECT canonical_unit FROM uom_aliases WHERE tenant_id=%s AND alias_norm=%s",
        (tenant, normalized),
    ).fetchone()
    canonical = row[0] if row else normalized
    if canonical != base_unit:
        raise RequestValidationFailedError(
            details={
                "fields": [
                    {
                        "path": "lines.uom",
                        "reason": "must match selected SKU base unit; no implicit conversion",
                    }
                ]
            }
        )
    return canonical


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


def _latest_snapshot(conn, tenant: str, draft_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT snapshot FROM draft_versions "
        "WHERE tenant_id=%s AND draft_id=%s ORDER BY version DESC LIMIT 1",
        (tenant, draft_id),
    ).fetchone()
    return row[0] if row is not None and isinstance(row[0], dict) else {}


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
    if len(deleted) != len(set(deleted)):
        raise InvalidLineOperationError(details={"duplicate_line_ids": deleted})
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


def _save_alias(
    conn,
    *,
    user: CurrentUser,
    tenant: str,
    customer: dict[str, Any],
    item,
    old: WorkingLine | None,
) -> dict[str, Any] | None:
    if not item.save_to_alias_cache:
        return None
    if item.alias_scope == "TENANT" and user.role != "OWNER":
        raise ForbiddenActionError("TENANT alias scope requires OWNER")
    if not item.sku_id or old is None or not old.source_span:
        raise RequestValidationFailedError(
            details={
                "fields": [
                    {
                        "path": "lines.save_to_alias_cache",
                        "reason": "requires selected SKU and an existing masked span",
                    }
                ]
            }
        )
    phrase = old.source_span
    phrase_norm = phrase.strip().casefold()
    customer_id = customer["customer_id"] if item.alias_scope == "CUSTOMER" else None
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
        (f"alias|{tenant}|{customer_id or ''}|{phrase_norm}",),
    )
    existing = conn.execute(
        "SELECT alias_id, phrase, target_type, family_id, product_id, active, created_at "
        "FROM alias_cache WHERE tenant_id=%s AND COALESCE(customer_id, '')=%s "
        "AND phrase_norm=%s AND active=true",
        (tenant, customer_id or "", phrase_norm),
    ).fetchone()
    if existing is None:
        alias_id = f"ALI_{uuid4().hex.upper()}"
        conn.execute(
            "INSERT INTO alias_cache "
            "(alias_id, tenant_id, customer_id, phrase, phrase_norm, target_type, "
            " product_id, confirmed_by, active) "
            "VALUES (%s, %s, %s, %s, %s, 'SKU', %s, %s, true)",
            (
                alias_id,
                tenant,
                customer_id,
                phrase,
                phrase_norm,
                item.sku_id,
                user.user_id,
            ),
        )
        row = conn.execute(
            "SELECT alias_id, phrase, target_type, family_id, product_id, active, created_at "
            "FROM alias_cache WHERE alias_id=%s",
            (alias_id,),
        ).fetchone()
    else:
        if existing[2] != "SKU" or existing[4] != item.sku_id:
            raise RequestValidationFailedError("alias already maps to a different target")
        row = existing
    return {
        "alias_id": row[0],
        "phrase": row[1],
        "target_type": row[2],
        "family_id": row[3],
        "product_id": row[4],
        "scope": item.alias_scope,
        "active": row[5],
        "created_at": row[6],
    }


def _line(
    *,
    conn,
    user: CurrentUser,
    tenant: str,
    customer: dict[str, Any],
    item,
    old: WorkingLine | None,
) -> tuple[WorkingLine, list[Issue]]:
    if item.line_id is None and item.confirmed_qty is None:
        raise InvalidQuantityError(
            details={"fields": [{"path": "lines.confirmed_qty", "reason": "new line needs qty"}]}
        )
    if old is None:
        if not (item.client_line_ref or "").strip():
            raise RequestValidationFailedError(
                details={
                    "fields": [{"path": "lines.client_line_ref", "reason": "must not be blank"}]
                }
            )
        if not (item.sku_id or "").strip():
            raise RequestValidationFailedError(
                details={"fields": [{"path": "lines.sku_id", "reason": "new line needs SKU"}]}
            )
    if ((old is None or item.sku_id != old.sku_id) and item.match_source != "MANUAL_SELECTED") or (
        old is not None and item.match_source not in {old.match_source, "MANUAL_SELECTED"}
    ):
        raise RequestValidationFailedError(
            details={
                "fields": [
                    {
                        "path": "lines.match_source",
                        "reason": "manual additions and SKU changes require MANUAL_SELECTED",
                    }
                ]
            }
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
        if uom is None and _family_has_mixed_base_units(conn, tenant, family_id):
            # kg/bag or btl/pail: selecting a SKU is not itself a unit
            # confirmation. Leave uom empty so the MISSING_UOM issue below stays
            # blocking; the clerk must save the unit explicitly. Single-base-unit
            # families keep the documented family-level default.
            pass
        else:
            uom = _canonical_uom(conn, tenant, uom, product["base_unit"])
        for field in ("pack_size", "grade"):
            provided = getattr(item, field)
            if provided is not None and provided != product[field]:
                raise RequestValidationFailedError(f"{field} must match selected SKU")
        pack_size = product["pack_size"]
        grade = product["grade"]
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
            if not (item.override_reason or "").strip():
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
    line.saved_alias = _save_alias(
        conn,
        user=user,
        tenant=tenant,
        customer=customer,
        item=item,
        old=old,
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
    *,
    role: str,
    status: str,
    escalation: list[dict[str, Any]],
    blocking: list[str] | tuple[str, ...] = (),
) -> tuple[list[str], dict[str, list[str]]]:
    if status in {"DO_GENERATED", "REJECTED"}:
        return ["VIEW_ACTIVITY"], {}
    if status == "PENDING_OWNER_APPROVAL":
        if role == "OWNER":
            return ["OWNER_APPROVE", "OWNER_REJECT", "VIEW_ACTIVITY"], {}
        return ["VIEW_ACTIVITY"], {"EDIT_DRAFT": ["PENDING_OWNER_APPROVAL"]}
    if status == "DISAMBIGUATION_REQUIRED":
        # Name the actual blockers so the client does not have to guess, and
        # always keep APPROVE_AND_GENERATE_DO blocked while status is unresolved.
        return ["EDIT_DRAFT", "RESOLVE_ISSUE", "CANCEL_DRAFT", "VIEW_ACTIVITY"], {
            "APPROVE_AND_GENERATE_DO": sorted(set(blocking)) or ["BLOCKING_ISSUES"]
        }
    if escalation:
        if role == "OWNER":
            return [
                "EDIT_DRAFT",
                "APPROVE_AND_GENERATE_DO",
                "CANCEL_DRAFT",
                "VIEW_ACTIVITY",
            ], {}
        return ["EDIT_DRAFT", "SUBMIT_FOR_OWNER", "CANCEL_DRAFT", "VIEW_ACTIVITY"], {}
    return ["EDIT_DRAFT", "APPROVE_AND_GENERATE_DO", "CANCEL_DRAFT", "VIEW_ACTIVITY"], {}


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
        " actor_role, action, payload, do_number) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            audit_id,
            tenant,
            draft_id,
            version,
            user.user_id,
            user.role,
            action,
            Jsonb(payload),
            payload.get("do_number"),
        ),
    )
    conn.execute(
        "INSERT INTO activity_log "
        "(tenant_id, draft_id, event_type, payload, actor_user_id, actor_role, do_number) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            tenant,
            draft_id,
            event,
            Jsonb(payload),
            user.user_id,
            user.role,
            payload.get("do_number"),
        ),
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


def _validate_resolutions(
    body: SaveLinesRequest,
    old_issues: list[dict[str, Any]],
    lines: list[WorkingLine],
    issues: list[Issue],
    conditions: list[Issue] | None = None,
) -> None:
    if not body.resolutions:
        return
    old_ids = {issue["issue_id"] for issue in old_issues}
    line_ids = {line.line_id for line in lines}
    issue_by_id = {issue.issue_id: issue for issue in [*issues, *(conditions or [])]}
    if len({r.issue_id for r in body.resolutions}) != len(body.resolutions):
        raise RequestValidationFailedError("duplicate issue resolutions")
    for resolution in body.resolutions:
        if resolution.issue_id not in old_ids:
            raise RequestValidationFailedError(
                details={
                    "fields": [
                        {
                            "path": "resolutions.issue_id",
                            "reason": "issue is not in the current draft",
                        }
                    ]
                }
            )
        if any(target not in line_ids for target in resolution.target_line_ids):
            raise TargetLineRequiredError(details={"issue_id": resolution.issue_id})
        if len(set(resolution.target_line_ids)) != len(resolution.target_line_ids):
            raise TargetLineRequiredError(details={"issue_id": resolution.issue_id})
        target_issue = issue_by_id.get(resolution.issue_id)
        if target_issue is None:
            raise RequestValidationFailedError("issue is not in the current draft")
        if target_issue.code == "SAME_DAY_ORDER":
            if resolution.target_line_ids:
                raise RequestValidationFailedError("same-day order resolution is order-level")
            if resolution.choice != "SEPARATE_ADD_ON":
                raise RequestValidationFailedError(
                    "duplicate/change-existing same-day decisions use discard"
                )
            existing = target_issue.data_used.get("existing_do_numbers") or []
            related = resolution.related_do_number
            if not related or related not in existing:
                raise RequestValidationFailedError(
                    details={
                        "fields": [
                            {
                                "path": "resolutions.related_do_number",
                                "reason": "must select an existing DO from this issue",
                            }
                        ]
                    }
                )
            target_issue.resolved = True
            target_issue.resolution = "SEPARATE_ADD_ON"
            target_issue.resolution_note = resolution.note
            target_issue.data_used["related_do_number"] = related
            continue
        if target_issue.code != "CUSTOMER_CONDITION":
            raise RequestValidationFailedError("resolve line checks by correcting the line")
        if target_issue.condition_kind == "STOCK":
            raise RequestValidationFailedError("stock conditions are resolved by stock checks")
        if resolution.choice not in {
            "ACCEPT_REQUESTED_PRICE",
            "NOT_A_CONDITION",
            "CONFIRMED_WITH_CUSTOMER",
        }:
            raise RequestValidationFailedError("choice is not valid for a customer condition")
        if (
            target_issue.condition_kind == "PRICE"
            and resolution.choice == "CONFIRMED_WITH_CUSTOMER"
        ):
            raise RequestValidationFailedError("price requires explicit UNIT price acceptance")
        if resolution.choice == "ACCEPT_REQUESTED_PRICE" and target_issue.condition_kind != "PRICE":
            raise RequestValidationFailedError("price acceptance requires a PRICE condition")
        if resolution.choice == "NOT_A_CONDITION" and not (resolution.note or "").strip():
            raise NoteRequiredError()
        if resolution.choice == "ACCEPT_REQUESTED_PRICE":
            if not (resolution.note or "").strip():
                raise NoteRequiredError()
            if not resolution.target_line_ids:
                raise TargetLineRequiredError(details={"issue_id": resolution.issue_id})
            if resolution.confirmed_unit_price is None:
                raise RequestValidationFailedError(
                    details={
                        "fields": [
                            {
                                "path": "resolutions.confirmed_unit_price",
                                "reason": "required when accepting a requested price",
                            }
                        ]
                    }
                )
            if resolution.price_basis != "UNIT":
                raise RequestValidationFailedError(
                    details={
                        "fields": [
                            {
                                "path": "resolutions.price_basis",
                                "reason": "accepted price must use UNIT",
                            }
                        ]
                    }
                )
            if Decimal(resolution.confirmed_unit_price) <= 0:
                raise RequestValidationFailedError("confirmed unit price must be positive")
            if resolution.confirmed_unit_price is not None:
                for line in lines:
                    if (
                        line.line_id in resolution.target_line_ids
                        and line.unit_price_override is not None
                        and line.unit_price_override != resolution.confirmed_unit_price
                    ):
                        raise RequestValidationFailedError(
                            details={
                                "fields": [
                                    {
                                        "path": "resolutions.confirmed_unit_price",
                                        "reason": "must equal target line unit_price_override",
                                    }
                                ]
                            }
                        )
                for line in lines:
                    if line.line_id in resolution.target_line_ids:
                        if not line.sku_id or line.tier_unit_price is None:
                            raise RequestValidationFailedError("price target requires selected SKU")
                        line.unit_price_override = resolution.confirmed_unit_price
                        line.effective_unit_price = resolution.confirmed_unit_price
                        line.override_reason = resolution.note.strip()
                        line.subtotal_rm = _money(
                            Decimal(resolution.confirmed_unit_price) * line.effective_qty
                        )
            target_issue.price_basis = "UNIT"
            target_issue.data_used["confirmed_unit_price"] = resolution.confirmed_unit_price
        if target_issue is not None:
            target_issue.target_line_ids = resolution.target_line_ids
            target_issue.resolution = resolution.choice
            target_issue.resolution_note = resolution.note
            target_issue.resolved = True


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
            draft = _apply_save_lines(conn, user, order, body)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return draft


def _draft_payload(conn, user, order) -> OrderDraftResponse:
    """Project a stored order into the draft response used by P1 actions."""
    customer = _customer(conn, user.tenant_id, order["customer_id"], active_only=False)
    lines = _old_lines(order)
    issues = [Issue.model_validate(issue) for issue in (order["issues"] or [])]
    conditions = [issue for issue in issues if issue.code == "CUSTOMER_CONDITION"]
    blocking = sorted(
        {issue.code for issue in [*issues, *conditions] if issue.blocking and not issue.resolved}
    )
    clarification_data = order.get("clarification")
    clarification = (
        ClarificationDraft.model_validate(clarification_data)
        if isinstance(clarification_data, dict)
        else None
    )
    allowed, blocked = _actions(
        role=user.role,
        status=order["status"],
        escalation=order["escalation_preview"],
        blocking=blocking,
    )
    if clarification is not None:
        allowed.append("COPY_CLARIFICATION")
    snapshot = _latest_snapshot(conn, user.tenant_id, order["draft_id"])
    do_row = conn.execute(
        "SELECT do_number FROM delivery_orders WHERE tenant_id=%s AND draft_id=%s",
        (user.tenant_id, order["draft_id"]),
    ).fetchone()
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
        masked_message=_masked_message(conn, user.tenant_id, order["message_id"]),
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


@router.post(
    "/orders/drafts/{draft_id}/discard",
    response_model=OrderDraftResponse,
    responses={
        400: {"description": "A non-empty note is required"},
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "Role not allowed"},
        404: {"description": "Draft not found in tenant"},
        409: {"description": "Stale version or draft not editable"},
        422: {"description": "Validation failed"},
    },
)
def discard_draft(
    draft_id: str,
    body: DiscardRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OrderDraftResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()
    note = mask_message(body.note.strip()).masked_text
    if not note:
        raise NoteRequiredError()

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
            before_status = order["status"]
            conn.execute(
                "UPDATE orders SET status='REJECTED', termination_reason='CLERK_DISCARDED', "
                "terminated_by_user_id=%s, termination_note=%s, updated_at=now() "
                "WHERE tenant_id=%s AND draft_id=%s",
                (user.user_id, note, user.tenant_id, draft_id),
            )
            order = _order(conn, user.tenant_id, draft_id)
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=draft_id,
                version=order["version"],
                action="CANCEL_DRAFT",
                event="DRAFT_DISCARDED",
                user=user,
                payload={
                    "note": note,
                    "before_status": before_status,
                    "after_status": "REJECTED",
                },
            )
            draft = _draft_payload(conn, user, order)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return draft


@router.post(
    "/orders/drafts/{draft_id}/clarification-copied",
    response_model=ClarificationCopiedResult,
    responses={
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "Role not allowed"},
        404: {"description": "Draft not found in tenant"},
        409: {"description": "Stale version or draft not editable"},
        422: {"description": "Clarification is not available"},
    },
)
def clarification_copied(
    draft_id: str,
    body: ClarificationCopiedRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClarificationCopiedResult:
    """Append a copy event; never mutate the draft or its clarification."""
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
            if body.expected_version != order["version"]:
                raise StaleVersionError(
                    details={
                        "expected_version": body.expected_version,
                        "current_version": order["version"],
                    }
                )
            clarification_data = order.get("clarification")
            if not isinstance(clarification_data, dict):
                raise RequestValidationFailedError("clarification is not available")
            clarification = ClarificationDraft.model_validate(clarification_data)
            issue_ids = list(clarification.unresolved_issue_ids)
            issue_by_id = {
                issue["issue_id"]: Issue.model_validate(issue) for issue in (order["issues"] or [])
            }
            if any(issue_id not in issue_by_id for issue_id in issue_ids):
                raise RequestValidationFailedError("clarification issue binding is stale")
            line_ids: set[str] = set()
            for issue_id in issue_ids:
                issue = issue_by_id[issue_id]
                if issue.line_id:
                    line_ids.add(issue.line_id)
                line_ids.update(issue.target_line_ids)
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=draft_id,
                version=order["version"],
                action="COPY_CLARIFICATION",
                event="CLARIFICATION_COPIED",
                user=user,
                payload={
                    "draft_version": order["version"],
                    "language": clarification.language,
                    "issue_ids": issue_ids,
                    "line_ids": sorted(line_ids),
                    "message_sha256": hashlib.sha256(
                        clarification.message.encode("utf-8")
                    ).hexdigest(),
                },
            )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return ClarificationCopiedResult(recorded=True)


def _carry_same_day_resolution(order, issues: list[Issue]) -> None:
    """Keep an explicit add-on decision across unchanged same-day checks."""
    previous = {}
    for raw in order.get("issues") or []:
        if raw.get("code") != "SAME_DAY_ORDER" or not raw.get("resolved"):
            continue
        if raw.get("resolution") != "SEPARATE_ADD_ON":
            continue
        previous[raw["issue_id"]] = raw
    for issue in issues:
        if issue.code != "SAME_DAY_ORDER" or issue.resolved:
            continue
        old = previous.get(issue.issue_id)
        if old is None:
            continue
        old_existing = old.get("data_used", {}).get("existing_do_numbers")
        new_existing = issue.data_used.get("existing_do_numbers")
        if old_existing != new_existing:
            continue
        issue.resolved = True
        issue.resolution = "SEPARATE_ADD_ON"
        issue.resolution_note = old.get("resolution_note")
        related = old.get("data_used", {}).get("related_do_number")
        if related:
            issue.data_used["related_do_number"] = related


def _apply_save_lines(conn, user, order, body):
    """Apply a lines save on an already locked connection, without committing."""
    draft_id = order["draft_id"]
    old = _old_lines(order)
    _coverage(old, body)
    customer = _customer(conn, user.tenant_id, order["customer_id"])
    tenant = _tenant(conn, user.tenant_id)
    old_by_id = {line.line_id: line for line in old}
    snapshot = _latest_snapshot(conn, user.tenant_id, draft_id)
    ignored_spans = snapshot.get("ignored_spans", [])

    lines: list[WorkingLine] = []
    issues: list[Issue] = []
    for item in body.lines:
        old_line = old_by_id.get(item.line_id) if item.line_id else None
        line, line_issues = _line(
            conn=conn,
            user=user,
            tenant=user.tenant_id,
            customer=customer,
            item=item,
            old=old_line,
        )
        lines.append(line)
        issues.extend(line_issues)

    for line in lines:
        if line.sku_id and line.available_qty is not None:
            combined = sum(other.effective_qty for other in lines if other.sku_id == line.sku_id)
            if combined > line.available_qty and not any(
                issue.code == "INSUFFICIENT_STOCK" and issue.line_id == line.line_id
                for issue in issues
            ):
                issues.append(
                    Issue(
                        issue_id=_stable_id("ISS", draft_id, line.line_id, "INSUFFICIENT_STOCK"),
                        code="INSUFFICIENT_STOCK",
                        line_id=line.line_id,
                        data_used={
                            "available_qty": line.available_qty,
                            "combined_qty": combined,
                        },
                        blocking=True,
                        resolved=False,
                    )
                )

    issues.extend(
        apply_checks(
            conn,
            tenant=user.tenant_id,
            customer=customer,
            lines=lines,
            checks=tenant["checks"],
            draft_id=draft_id,
        )
    )
    _carry_same_day_resolution(order, issues)

    # Older application versions stored conditions only in immutable snapshots.
    # Recover them without altering the signed schema or historical snapshots.
    merged_issues = {
        issue["issue_id"]: issue
        for issue in [*snapshot.get("conditions", []), *(order["issues"] or [])]
    }
    old_issues = [Issue.model_validate(issue) for issue in merged_issues.values()]
    line_ids = {line.line_id for line in lines}
    conditions = (
        [issue for issue in old_issues if issue.code == "CUSTOMER_CONDITION"]
        if tenant["checks"]["customer_condition"]
        else []
    )
    by_id = {line.line_id: line for line in lines}
    for condition in conditions:
        missing_source_line = condition.line_id and condition.line_id not in line_ids
        missing_targets = any(target not in line_ids for target in condition.target_line_ids)
        price_changed = condition.resolved and condition.resolution == "ACCEPT_REQUESTED_PRICE"
        if price_changed:
            price = condition.data_used.get("confirmed_unit_price")
            price_changed = not condition.target_line_ids or any(
                target not in by_id
                or by_id[target].unit_price_override != price
                or target not in old_by_id
                or by_id[target].sku_id != old_by_id[target].sku_id
                for target in condition.target_line_ids
            )
        if missing_source_line:
            condition.line_id = None
            condition.condition_scope = "UNKNOWN"
        condition.candidate_line_ids = [
            candidate for candidate in condition.candidate_line_ids if candidate in line_ids
        ]
        condition.target_line_ids = [
            target for target in condition.target_line_ids if target in line_ids
        ]
        if missing_source_line or missing_targets or price_changed:
            condition.resolved = False
            condition.resolution = None
            condition.resolution_note = None
            condition.auto_resolved_by = None
            condition.data_used.pop("confirmed_unit_price", None)
        if condition.condition_kind == "STOCK":
            condition.blocking = False
            condition.resolved = bool(lines) and all(
                line.sku_id
                and line.available_qty is not None
                and line.available_qty
                >= sum(other.effective_qty for other in lines if other.sku_id == line.sku_id)
                for line in lines
            )
            condition.auto_resolved_by = "STOCK_CHECK" if condition.resolved else None
    _validate_resolutions(body, list(merged_issues.values()), lines, issues, conditions)

    total: Decimal | None = None
    if all(line.subtotal_rm is not None for line in lines):
        total = sum(Decimal(line.subtotal_rm) for line in lines)

    blocking = sorted(
        {issue.code for issue in [*issues, *conditions] if issue.blocking and not issue.resolved}
    )
    status = "READY_FOR_APPROVAL" if not blocking and lines else "DISAMBIGUATION_REQUIRED"
    old_clarification = order.get("clarification") or {}
    masked_message = _masked_message(conn, user.tenant_id, order["message_id"])
    clarification, clarification_lang = build_clarification(
        issues,
        conditions,
        old_clarification.get("language") if isinstance(old_clarification, dict) else None,
        lines=lines,
        masked_text=masked_message,
    )
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
        blocking=blocking,
    )
    if clarification is not None:
        allowed.append("COPY_CLARIFICATION")
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
        masked_message=masked_message,
        ai_mode=order["ai_mode"],
        lines=lines,
        issues=[*issues, *conditions],
        conditions=conditions,
        blocking_issues=blocking,
        escalation_preview=escalation,
        totals=OrderTotals(
            order_total=_money(total) if total is not None else None,
            currency="MYR",
            is_complete=total is not None,
        ),
        allowed_actions=allowed,
        blocked_actions=blocked,
        clarification_draft=clarification,
        clarification_lang=clarification_lang,
        ignored_spans=ignored_spans,
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
            Jsonb([issue.model_dump(mode="json") for issue in draft.issues]),
            (
                Jsonb(draft.clarification_draft.model_dump(mode="json"))
                if draft.clarification_draft
                else None
            ),
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
    for resolution in body.resolutions:
        if resolution.choice == "NOT_A_CONDITION":
            _audit(
                conn,
                tenant=user.tenant_id,
                draft_id=draft_id,
                version=draft.version,
                action="CONDITION_DISMISSED",
                event="CONDITION_DISMISSED",
                user=user,
                payload=resolution.model_dump(mode="json"),
            )
    return draft
