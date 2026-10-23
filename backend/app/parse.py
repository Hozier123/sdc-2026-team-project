"""POST /api/v1/orders/parse-draft skeleton.

The transport, PII, tenant isolation, permission, persistence, and provider
boundary are real. The extraction provider is still a deterministic stub; H1/H5
accuracy and order-line resolution come later.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth import CurrentUser
from app.clarification import build_clarification
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.draft_store import persist_parse_draft
from app.drafts import _stable_id
from app.errors import (
    AiAndFallbackUnavailableError,
    ForbiddenActionError,
    MessageTooLongError,
    ResourceNotFoundError,
)
from app.extraction.ai import AiServiceError, classify_condition
from app.extraction.base import ExtractionProvider, RawExtraction, RawRow, validate_raw_extraction
from app.extraction.evidence import exact_phrase, pack_size_evidence, quantity_evidence
from app.extraction.stub import StubExtractor
from app.pii import mask_message
from app.resolver import (
    Catalog,
    candidate_payload,
    load_catalog,
    memory_rows,
    merge_memory,
    resolve_row,
)
from app.schemas import Issue, OrderDraftResponse, SkuCandidate, WorkingLine

router = APIRouter(prefix="/api/v1", tags=["Orders"])


class ParseDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1)
    message_text: str = Field(min_length=1)
    language_hint: str | None = Field(
        default=None,
        max_length=35,
        pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})*$",
    )


def get_extractor(request: Request) -> ExtractionProvider:
    provider = getattr(request.app.state, "extraction_provider", None)
    return provider if provider is not None else StubExtractor()


def _customer(settings: Settings, user: CurrentUser, customer_id: str) -> dict[str, Any]:
    with connect(settings) as conn:
        row = conn.execute(
            "SELECT customer_id, name, tier, credit_flag, phone_e164 "
            "FROM customers WHERE tenant_id = %s AND customer_id = %s AND active = true",
            (user.tenant_id, customer_id),
        ).fetchone()
    if row is None:
        raise ResourceNotFoundError("customer not found")
    return {
        "customer_id": row[0],
        "name": row[1],
        "tier": row[2],
        "credit_flag": row[3],
        "phone_e164": row[4],
    }


def _unresolved_issue() -> dict[str, Any]:
    return {
        "issue_id": f"ISS_{uuid4().hex.upper()}",
        "code": "LOW_CONFIDENCE_MATCH",
        "candidate_line_ids": [],
        "target_line_ids": [],
        "ask": "CLERK",
        "data_used": {"extractor": "STUB"},
        "blocking": True,
        "resolved": False,
    }


def _ai_draft(
    *,
    customer: dict[str, Any],
    masked_text: str,
    raw,
    draft_id: str,
    now: str,
    language_hint: str | None,
    catalog: Catalog | None = None,
    ai_mode: str = "LLM",
) -> dict[str, Any]:
    catalog = catalog or Catalog(products=(), aliases=())
    lines: list[WorkingLine] = []
    issues: list[Issue] = []
    conditions: list[Issue] = []
    blocking: set[str] = set()

    def add_issue(
        *,
        code: str,
        line_id: str | None,
        span: str | None,
        start: int | None,
        end: int | None,
        reason_code: str | None = None,
        data_used: dict[str, Any] | None = None,
    ) -> None:
        issues.append(
            Issue(
                issue_id=f"ISS_{uuid4().hex.upper()}",
                code=code,
                line_id=line_id,
                span=span,
                source_span=span,
                span_start=start,
                span_end=end,
                reason_code=reason_code,
                ask="CLERK",
                data_used=data_used or {"extractor": "AI"},
                blocking=True,
                resolved=False,
            )
        )
        blocking.add(code)

    cursor = 0
    consumed_rows = set()
    condition_records = {}
    for index, row in enumerate(raw.rows):
        start = masked_text.find(row.span, cursor)
        end = start + len(row.span) if start >= 0 else None
        line_id = None
        if row.invalid_reason:
            add_issue(
                code="LOW_CONFIDENCE_MATCH",
                line_id=None,
                span=row.span or None,
                start=start if start >= 0 else None,
                end=end,
                reason_code=row.invalid_reason,
            )
            continue
        qty, qty_reason, qty_start, qty_end = quantity_evidence(row.span)
        if start < 0:
            key = (row.span, row.qty, row.fam, row.uom, row.pack_size)
            qty_reason = "DUPLICATE_SPAN" if key in consumed_rows else "OVERLAPPING_SPAN"
        elif row.qty != qty:
            qty_reason = qty_reason or "FIELD_NOT_EVIDENCED"
        if start >= 0:
            cursor = end
            consumed_rows.add((row.span, row.qty, row.fam, row.uom, row.pack_size))
        if qty_reason or qty is None:
            add_issue(
                code="LOW_CONFIDENCE_MATCH",
                line_id=None,
                span=row.span,
                start=start if start >= 0 else None,
                end=end,
                reason_code=qty_reason or "INVALID_QUANTITY",
            )
        else:
            line_id = f"LNE_{uuid4().hex.upper()}"
            resolution = resolve_row(row, catalog)
            product = resolution.product
            family_id = product.family_id if product else (row.fam or "UNKNOWN")
            tier_price: Decimal | None = None
            effective_price: Decimal | None = None
            subtotal: Decimal | None = None
            available: int | None = None
            candidates: list[SkuCandidate] = []
            saved_alias = row.alias if row.memory else None
            if product is not None:
                tier_price = product.tier_price
                effective_price = tier_price
                subtotal = effective_price * qty if effective_price is not None else None
                available = product.available_qty
            elif resolution.candidates:
                candidates = [
                    SkuCandidate.model_validate(candidate_payload(candidate))
                    for candidate in resolution.candidates
                ]
            line = WorkingLine(
                line_id=line_id,
                client_line_ref=f"ai-{index + 1}",
                sku_id=product.sku_id if product else None,
                family_id=family_id,
                description=product.name if product else row.span,
                requested_qty=qty,
                confirmed_qty=None,
                effective_qty=qty,
                uom=product.base_unit if product else row.uom,
                pack_size=product.pack_size if product else row.pack_size,
                grade=product.grade if product else None,
                tier_unit_price=format(tier_price, ".2f") if tier_price is not None else None,
                unit_price_override=None,
                override_reason=None,
                effective_unit_price=format(effective_price, ".2f")
                if effective_price is not None
                else None,
                subtotal_rm=format(subtotal, ".2f") if subtotal is not None else None,
                match_source=row.source,
                source_span=row.span,
                span_start=start if start >= 0 else None,
                span_end=end,
                field_evidence=[
                    {
                        "field": "requested_qty",
                        "raw_text": row.span[qty_start:qty_end],
                        "start": start + qty_start,
                        "end": start + qty_end,
                        "normalizer_version": "field-evidence-v2",
                    }
                ],
                candidate_skus=candidates,
                saved_alias=saved_alias,
                available_qty=available,
            )
            lines.append(line)
            if family_id == "UNKNOWN":
                add_issue(
                    code="LOW_CONFIDENCE_MATCH",
                    line_id=line_id,
                    span=row.span,
                    start=start if start >= 0 else None,
                    end=end,
                    reason_code="FAMILY_NOT_EVIDENCED",
                )
            if product is None and row.uom is None:
                add_issue(
                    code="MISSING_UOM",
                    line_id=line_id,
                    span=row.span,
                    start=start if start >= 0 else None,
                    end=end,
                    reason_code="FIELD_NOT_EVIDENCED",
                )
            if product is None and candidates:
                add_issue(
                    code=resolution.issue_code or "MULTIPLE_PACK_SIZES",
                    line_id=line_id,
                    span=row.span,
                    start=start if start >= 0 else None,
                    end=end,
                    data_used={
                        "candidate_skus": [
                            candidate.model_dump(mode="json") for candidate in candidates
                        ]
                    },
                )
            elif product is None:
                add_issue(
                    code="LOW_CONFIDENCE_MATCH",
                    line_id=line_id,
                    span=row.span,
                    start=start if start >= 0 else None,
                    end=end,
                    reason_code="NO_CANDIDATE",
                )
            if product is not None and available is not None and available < qty:
                add_issue(
                    code="INSUFFICIENT_STOCK",
                    line_id=line_id,
                    span=row.span,
                    start=start if start >= 0 else None,
                    end=end,
                    data_used={"available_qty": available, "effective_qty": qty},
                )
        # Conditions survive even when their item's quantity is unusable.
        for cond in row.conds:
            kind = cond.get("kind", "OTHER")
            amount = cond.get("requested_amount")
            price = (
                f"{Decimal(amount):.2f}" if cond.get("price_basis") == "UNIT" and amount else None
            )
            condition_id = _stable_id(
                "CND", draft_id, kind, str(cond.get("start")), str(cond.get("end"))
            )
            unique_target = (
                line_id if len(raw.rows) == 1 or cond.get("span", "") in row.span else None
            )
            condition_records.setdefault(
                condition_id,
                Issue(
                    issue_id=_stable_id(
                        "ISS", draft_id, unique_target, "CUSTOMER_CONDITION", condition_id
                    ),
                    code="CUSTOMER_CONDITION",
                    condition_id=condition_id,
                    line_id=unique_target,
                    condition_kind=kind if kind in {"STOCK", "PRICE", "OTHER"} else "OTHER",
                    condition_scope="SINGLE_LINE" if unique_target else "UNKNOWN",
                    candidate_line_ids=[unique_target] if unique_target else [],
                    span=cond.get("span"),
                    source_span=cond.get("span"),
                    span_start=cond.get("start"),
                    span_end=cond.get("end"),
                    requested_unit_price=price,
                    price_basis=cond.get("price_basis"),
                    ask="CLERK",
                    data_used={
                        "trigger_ids": cond.get("trigger_ids", []),
                        "lexicon_version": cond.get("lexicon_version"),
                        "amount_text": amount,
                    },
                    blocking=kind == "PRICE",
                    resolved=False,
                ),
            )
            if kind == "PRICE":
                blocking.add("CUSTOMER_CONDITION")
    conditions = list(condition_records.values())

    total: Decimal | None = None
    if lines and all(line.subtotal_rm is not None for line in lines):
        total = sum(Decimal(line.subtotal_rm) for line in lines)
    status = "READY_FOR_APPROVAL" if lines and not blocking else "DISAMBIGUATION_REQUIRED"
    clarification, clarification_lang = build_clarification(
        issues,
        conditions,
        language_hint,
        lines=lines,
        masked_text=masked_text,
    )
    allowed_actions = ["EDIT_DRAFT", "RESOLVE_ISSUE"]
    if status == "READY_FOR_APPROVAL":
        allowed_actions.append("APPROVE_AND_GENERATE_DO")
    if clarification is not None:
        allowed_actions.append("COPY_CLARIFICATION")
    return {
        "draft_id": draft_id,
        "version": 1,
        "status": status,
        "customer_id": customer["customer_id"],
        "customer": {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "tier": customer["tier"],
            "credit_flag": customer["credit_flag"],
            "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
            "phone_e164": customer["phone_e164"],
        },
        "masked_message": masked_text,
        "ai_mode": ai_mode,
        "lines": [line.model_dump(mode="json") for line in lines],
        "issues": [issue.model_dump(mode="json") for issue in [*issues, *conditions]],
        "conditions": [condition.model_dump(mode="json") for condition in conditions],
        "blocking_issues": sorted(blocking),
        "escalation_preview": [],
        "totals": {
            "order_total": format(total, ".2f") if total is not None else None,
            "currency": "MYR",
            "is_complete": total is not None,
        },
        "allowed_actions": allowed_actions,
        "blocked_actions": ({"APPROVE_AND_GENERATE_DO": sorted(blocking)} if blocking else {}),
        "clarification_draft": clarification.model_dump(mode="json") if clarification else None,
        "clarification_lang": clarification_lang,
        "ignored_spans": [dict(span) for span in raw.ignored_spans],
        "created_at": now,
        "updated_at": now,
    }


def _guard_families_and_units(raw, settings, user, customer_id, masked_text, catalog: Catalog):
    """Only exact, tenant/customer-scoped evidence may support AI fields."""
    with connect(settings) as conn:
        families = conn.execute(
            "SELECT family_id, family_name FROM product_families "
            "WHERE tenant_id=%s AND active=true",
            (user.tenant_id,),
        ).fetchall()
        aliases = conn.execute(
            "SELECT family_id, phrase_norm FROM family_aliases WHERE tenant_id=%s",
            (user.tenant_id,),
        ).fetchall()
        aliases += conn.execute(
            "SELECT COALESCE(a.family_id, p.family_id), a.phrase_norm FROM alias_cache a "
            "LEFT JOIN products p ON p.tenant_id=a.tenant_id AND p.product_id=a.product_id "
            "WHERE a.tenant_id=%s AND a.active=true "
            "AND (a.customer_id=%s OR a.customer_id IS NULL)",
            (user.tenant_id, customer_id),
        ).fetchall()
        units = conn.execute(
            "SELECT canonical_unit, alias_norm FROM uom_aliases WHERE tenant_id=%s",
            (user.tenant_id,),
        ).fetchall()
    from app.extraction.evidence import lexicon

    units += [
        (unit, alias) for unit, values in lexicon()["uom_aliases"].items() for alias in values
    ]
    active = {product.family_id for product in catalog.products}
    guarded = []
    for row in raw.rows:
        if row.invalid_reason:
            guarded.append(row)
            continue
        if row.memory:
            # Memory rows are derived from a confirmed alias + active catalog row.
            guarded.append(row)
            continue
        hits = {
            family_id
            for family_id, phrase in [*families, *aliases]
            if family_id in active and exact_phrase(phrase, row.span)
        }
        family = row.fam if hits == {row.fam} else "UNKNOWN"
        unit = (
            row.uom
            if any(unit == row.uom and exact_phrase(alias, row.span) for unit, alias in units)
            else None
        )
        pack = row.pack_size if row.pack_size and exact_phrase(row.pack_size, row.span) else None
        if pack is None and not row.pack_size:
            evidence = pack_size_evidence(row.span)
            if evidence is not None:
                pack = evidence[0]
        guarded.append(replace(row, fam=family, uom=unit, pack_size=pack))
    # H5 belongs to the backend. An omitted AI conds[] must not remove a price gate.
    for chunk in masked_text.splitlines():
        if not chunk.strip():
            continue
        for condition in classify_condition(chunk, masked_text):
            if any(
                c.get("kind") == condition["kind"] and c.get("span", "") in chunk
                for row in guarded
                for c in row.conds
            ):
                continue
            index = next((i for i, row in enumerate(guarded) if row.span in chunk), None)
            if index is None:
                guarded.append(RawRow(span=chunk, conds=(condition,)))
            else:
                guarded[index] = replace(guarded[index], conds=(*guarded[index].conds, condition))
    return replace(raw, rows=tuple(guarded))


@router.post(
    "/orders/parse-draft",
    response_model=OrderDraftResponse,
    responses={
        401: {"description": "Missing or invalid Bearer token"},
        403: {"description": "WAREHOUSE is not allowed to parse drafts"},
        404: {"description": "Customer not found in this tenant"},
        422: {"description": "Invalid request or message too long"},
    },
)
def parse_draft(
    body: ParseDraftRequest,
    request: Request,
    response: Response,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    extractor: Annotated[ExtractionProvider, Depends(get_extractor)],
) -> OrderDraftResponse:
    if user.role not in {"CLERK", "OWNER"}:
        raise ForbiddenActionError()

    if len(body.message_text) > 4000:
        raise MessageTooLongError()

    masked = mask_message(body.message_text)
    if len(masked.masked_text) > 4000:
        raise MessageTooLongError()

    customer = _customer(settings, user, body.customer_id)
    with connect(settings) as conn:
        catalog = load_catalog(
            conn,
            tenant=user.tenant_id,
            customer_id=body.customer_id,
            tier=customer["tier"],
        )
    memory, memory_covers = memory_rows(masked.masked_text, catalog)
    memory_used = bool(memory_covers)
    try:
        if memory_covers:
            # A confirmed customer alias plus an evidenced quantity bypasses
            # the extraction provider entirely.
            raw = RawExtraction(rows=tuple(memory))
            raw = validate_raw_extraction(raw, masked.masked_text, strict=False)
        else:
            raw = extractor.extract(
                masked.masked_text,
                body.language_hint,
                request.state.request_id,
            )
            raw = validate_raw_extraction(raw, masked.masked_text, strict=False)
            raw, memory_used = merge_memory(raw, memory)
    except (AiServiceError, ValueError, TypeError) as exc:
        raise AiAndFallbackUnavailableError() from exc
    raw = _guard_families_and_units(
        raw, settings, user, body.customer_id, masked.masked_text, catalog
    )
    sources = {row.source for row in raw.rows if not row.invalid_reason}
    if memory_covers:
        ai_mode = "ALIAS_ONLY"
    elif sources and all(source == "RAPIDFUZZ_FALLBACK" for source in sources):
        ai_mode = "FALLBACK"
    elif raw.rows and all(row.invalid_reason for row in raw.rows):
        ai_mode = "FALLBACK"
    elif memory_used or len(sources) > 1 or any(source != "LLM_EXTRACTED" for source in sources):
        ai_mode = "MIXED"
    elif isinstance(extractor, StubExtractor):
        ai_mode = "FALLBACK"
    else:
        ai_mode = "LLM"
    now = datetime.now(timezone.utc).isoformat()
    draft_id = f"DRF_{uuid4().hex.upper()}"
    if raw.rows:
        draft: dict[str, Any] = _ai_draft(
            customer=customer,
            masked_text=masked.masked_text,
            raw=raw,
            draft_id=draft_id,
            now=now,
            language_hint=body.language_hint,
            catalog=catalog,
            ai_mode=ai_mode,
        )
    else:
        issue = Issue(**_unresolved_issue())
        clarification, clarification_lang = build_clarification(
            [issue],
            (),
            body.language_hint,
            masked_text=masked.masked_text,
        )
        allowed_actions = ["EDIT_DRAFT", "RESOLVE_ISSUE"]
        if clarification is not None:
            allowed_actions.append("COPY_CLARIFICATION")
        draft = {
            "draft_id": draft_id,
            "version": 1,
            "status": "DISAMBIGUATION_REQUIRED",
            "customer_id": customer["customer_id"],
            "customer": {
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "tier": customer["tier"],
                "credit_flag": customer["credit_flag"],
                "has_credit_notice": customer["credit_flag"] == "OVERDUE_NOTICE",
                "phone_e164": customer["phone_e164"],
            },
            "masked_message": masked.masked_text,
            "ai_mode": ai_mode,
            "lines": [],
            "issues": [issue.model_dump(mode="json")],
            "conditions": [],
            "blocking_issues": ["LOW_CONFIDENCE_MATCH"],
            "escalation_preview": [],
            "totals": {"order_total": None, "currency": "MYR", "is_complete": False},
            "allowed_actions": allowed_actions,
            "blocked_actions": {"APPROVE_AND_GENERATE_DO": ["LOW_CONFIDENCE_MATCH"]},
            "clarification_draft": (
                clarification.model_dump(mode="json") if clarification else None
            ),
            "clarification_lang": clarification_lang,
            "ignored_spans": [dict(span) for span in raw.ignored_spans],
            "created_at": now,
            "updated_at": now,
        }

    response_draft = OrderDraftResponse(**draft)
    persist_parse_draft(
        settings,
        user=user,
        customer=customer,
        draft=response_draft.model_dump(mode="json"),
        message_id=f"MSG_{uuid4().hex.upper()}",
        masked_text=masked.masked_text,
        language=body.language_hint,
    )
    response.headers["Cache-Control"] = "no-store"
    return response_draft
