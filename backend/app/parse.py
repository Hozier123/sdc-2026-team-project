"""POST /api/v1/orders/parse-draft skeleton.

The transport, PII, tenant isolation, permission, persistence, and provider
boundary are real. The extraction provider is still a deterministic stub; H1/H5
accuracy and order-line resolution come later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth import CurrentUser
from app.config import Settings
from app.db import connect
from app.deps import get_current_user, get_settings
from app.draft_store import persist_parse_draft
from app.errors import ForbiddenActionError, MessageTooLongError, ResourceNotFoundError
from app.extraction.base import ExtractionProvider, validate_raw_extraction
from app.extraction.stub import StubExtractor
from app.pii import mask_message
from app.schemas import Issue, OrderDraftResponse, WorkingLine

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
) -> dict[str, Any]:
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
                data_used={"extractor": "AI"},
                blocking=True,
                resolved=False,
            )
        )
        blocking.add(code)

    for index, row in enumerate(raw.rows):
        start = masked_text.find(row.span)
        end = start + len(row.span) if start >= 0 else None
        if row.qty is None:
            add_issue(
                code="LOW_CONFIDENCE_MATCH",
                line_id=None,
                span=row.span,
                start=start if start >= 0 else None,
                end=end,
                reason_code="INVALID_QUANTITY",
            )
        else:
            line_id = f"LNE_{uuid4().hex.upper()}"
            family_id = row.fam or "UNKNOWN"
            line = WorkingLine(
                line_id=line_id,
                client_line_ref=f"ai-{index + 1}",
                family_id=family_id,
                description=row.span,
                requested_qty=row.qty,
                confirmed_qty=row.qty,
                effective_qty=row.qty,
                uom=row.uom,
                pack_size=row.pack_size,
                match_source="LLM_EXTRACTED",
                source_span=row.span,
                span_start=start if start >= 0 else None,
                span_end=end,
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
            if row.uom is None:
                add_issue(
                    code="MISSING_UOM",
                    line_id=line_id,
                    span=row.span,
                    start=start if start >= 0 else None,
                    end=end,
                    reason_code="FIELD_NOT_EVIDENCED",
                )
            add_issue(
                code="LOW_CONFIDENCE_MATCH",
                line_id=line_id,
                span=row.span,
                start=start if start >= 0 else None,
                end=end,
                reason_code="NO_CANDIDATE",
            )
            for cond in row.conds:
                kind = cond.get("kind", "OTHER")
                if kind == "TIME":
                    kind = "TIME"
                requested_amount = cond.get("requested_amount")
                requested_unit_price = None
                if cond.get("price_basis") == "UNIT" and requested_amount:
                    requested_unit_price = f"{Decimal(requested_amount):.2f}"
                conditions.append(
                    Issue(
                        issue_id=f"ISS_{uuid4().hex.upper()}",
                        code="CUSTOMER_CONDITION",
                        condition_id=f"CND_{uuid4().hex.upper()}",
                        line_id=line_id,
                        condition_kind=kind
                        if kind in {"STOCK", "PRICE", "TIME", "OTHER"}
                        else "OTHER",
                        condition_scope="SINGLE_LINE",
                        span=cond.get("span"),
                        source_span=cond.get("span"),
                        span_start=cond.get("start"),
                        span_end=cond.get("end"),
                        requested_unit_price=requested_unit_price,
                        price_basis=cond.get("price_basis"),
                        ask="CLERK",
                        data_used={
                            "trigger_ids": cond.get("trigger_ids", []),
                            "lexicon_version": cond.get("lexicon_version"),
                        },
                        blocking=bool(cond.get("blocking")),
                        resolved=False,
                    )
                )
                if cond.get("blocking"):
                    blocking.add("CUSTOMER_CONDITION")

    status = "READY_FOR_APPROVAL" if lines and not blocking else "DISAMBIGUATION_REQUIRED"
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
        "ai_mode": "LLM",
        "lines": [line.model_dump(mode="json") for line in lines],
        "issues": [issue.model_dump(mode="json") for issue in issues],
        "conditions": [condition.model_dump(mode="json") for condition in conditions],
        "blocking_issues": sorted(blocking),
        "escalation_preview": [],
        "totals": {"order_total": None, "currency": "MYR", "is_complete": False},
        "allowed_actions": ["EDIT_DRAFT", "RESOLVE_ISSUE"],
        "blocked_actions": {"APPROVE_AND_GENERATE_DO": sorted(blocking)},
        "clarification_draft": None,
        "clarification_lang": None,
        "ignored_spans": [dict(span) for span in raw.ignored_spans],
        "created_at": now,
        "updated_at": now,
    }


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
    raw = extractor.extract(
        masked.masked_text,
        body.language_hint,
        request.state.request_id,
    )
    validate_raw_extraction(raw, masked.masked_text)
    now = datetime.now(timezone.utc).isoformat()
    draft_id = f"DRF_{uuid4().hex.upper()}"
    if raw.rows:
        draft: dict[str, Any] = _ai_draft(
            customer=customer,
            masked_text=masked.masked_text,
            raw=raw,
            draft_id=draft_id,
            now=now,
        )
    else:
        issue = _unresolved_issue()
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
            "ai_mode": "FALLBACK",
            "lines": [],
            "issues": [issue],
            "conditions": [],
            "blocking_issues": ["LOW_CONFIDENCE_MATCH"],
            "escalation_preview": [],
            "totals": {"order_total": None, "currency": "MYR", "is_complete": False},
            "allowed_actions": ["EDIT_DRAFT", "RESOLVE_ISSUE"],
            "blocked_actions": {"APPROVE_AND_GENERATE_DO": ["LOW_CONFIDENCE_MATCH"]},
            "clarification_draft": None,
            "clarification_lang": None,
            "ignored_spans": [],
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
