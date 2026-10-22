"""POST /api/v1/orders/parse-draft skeleton.

The transport, PII, tenant isolation, permission, persistence, and provider
boundary are real. The extraction provider is still a deterministic stub; H1/H5
accuracy and order-line resolution come later.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
from app.schemas import OrderDraftResponse

router = APIRouter(prefix="/api/v1", tags=["Orders"])


class ParseDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1)
    message_text: str = Field(min_length=1)
    language_hint: str | None = None


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
    if raw.rows:
        # Do not silently discard provider rows before the H1/H5 line adapter exists.
        raise RuntimeError("extraction row adapter is not implemented")

    now = datetime.now(timezone.utc).isoformat()
    draft_id = f"DRF_{uuid4().hex.upper()}"
    issue = _unresolved_issue()
    draft: dict[str, Any] = {
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
