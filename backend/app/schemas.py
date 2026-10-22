"""Response models for the parse-draft skeleton.

Only the fields emitted by this skeleton are modeled; later H1/H5 work will
extend these models without changing the frozen Gate 0 wire names.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    name: str
    tier: str
    credit_flag: Literal["NONE", "OVERDUE_NOTICE"]
    has_credit_notice: bool
    phone_e164: str | None = None


class OrderTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_total: str | None
    currency: Literal["MYR"] = "MYR"
    is_complete: bool


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    code: Literal["LOW_CONFIDENCE_MATCH"]
    condition_id: str | None = None
    line_id: str | None = None
    span: str | None = None
    source_span: str | None = None
    span_start: int | None = Field(default=None, ge=0)
    span_end: int | None = Field(default=None, ge=1)
    condition_kind: str | None = None
    condition_scope: str | None = None
    candidate_line_ids: list[str] = Field(default_factory=list)
    target_line_ids: list[str] = Field(default_factory=list)
    requested_unit_price: str | None = None
    price_basis: str | None = None
    reason_code: str | None = None
    ask: Literal["CLERK"]
    data_used: dict[str, Any] = Field(default_factory=dict)
    blocking: bool
    resolved: bool
    resolution: str | None = None
    resolution_note: str | None = Field(default=None, max_length=500)
    auto_resolved_by: Literal["STOCK_CHECK"] | None = None


class WorkingLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str
    family_id: str
    requested_qty: int = Field(ge=1)
    effective_qty: int = Field(ge=1)
    match_source: str
    field_evidence: list[dict[str, Any]] = Field(default_factory=list)
    candidate_skus: list[dict[str, Any]] = Field(default_factory=list)
    available_qty: int | None = Field(default=None, ge=0)


class OrderDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    version: int = Field(ge=1)
    status: Literal["DISAMBIGUATION_REQUIRED"]
    customer_id: str
    customer: CustomerSummary
    masked_message: str
    ai_mode: Literal["FALLBACK"]
    lines: list[WorkingLine] = Field(default_factory=list)
    issues: list[Issue]
    conditions: list[Issue] = Field(default_factory=list)
    blocking_issues: list[Literal["LOW_CONFIDENCE_MATCH"]]
    escalation_preview: list[dict[str, Any]] = Field(default_factory=list)
    totals: OrderTotals
    allowed_actions: list[Literal["EDIT_DRAFT", "RESOLVE_ISSUE"]]
    blocked_actions: dict[str, list[str]]
    clarification_draft: dict[str, Any] | None = None
    clarification_lang: str | None = None
    ignored_spans: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
