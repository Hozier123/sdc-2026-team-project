"""Pydantic models shared by the identity, draft, approval, and DO APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DraftStatus = Literal[
    "DISAMBIGUATION_REQUIRED",
    "READY_FOR_APPROVAL",
    "PENDING_OWNER_APPROVAL",
    "DO_GENERATED",
    "REJECTED",
]
AiMode = Literal["LLM", "FALLBACK", "ALIAS_ONLY", "MIXED"]
AllowedAction = Literal[
    "EDIT_DRAFT",
    "RESOLVE_ISSUE",
    "COPY_CLARIFICATION",
    "APPROVE_AND_GENERATE_DO",
    "SUBMIT_FOR_OWNER",
    "OWNER_APPROVE",
    "OWNER_REJECT",
    "CANCEL_DRAFT",
    "VIEW_ACTIVITY",
    "WAKE_AI",
]
IssueCode = Literal[
    "MULTIPLE_PACK_SIZES",
    "MULTIPLE_GRADES",
    "MISSING_UOM",
    "LOW_CONFIDENCE_MATCH",
    "INSUFFICIENT_STOCK",
    "CUSTOMER_CONDITION",
    "SAME_DAY_ORDER",
    "UNUSUAL_QTY",
]
IssueReasonCode = Literal[
    "INVALID_QUANTITY",
    "FIELD_NOT_EVIDENCED",
    "FAMILY_NOT_EVIDENCED",
    "DUPLICATE_SPAN",
    "OVERLAPPING_SPAN",
    "SOURCE_EVIDENCE_INVALID",
    "UNKNOWN_PRODUCT",
    "NO_CANDIDATE",
    "LOW_SCORE",
    "SMALL_SCORE_GAP",
    "AMBIGUOUS_QUANTITY",
]
ConditionKind = Literal["STOCK", "PRICE", "TIME", "OTHER"]
ConditionScope = Literal["SINGLE_LINE", "MULTI_LINE", "ORDER_LEVEL", "UNKNOWN"]
ResolutionChoice = Literal[
    "CONFIRMED_WITH_CUSTOMER",
    "ACCEPT_REQUESTED_PRICE",
    "NOT_A_CONDITION",
    "SEPARATE_ADD_ON",
    "DUPLICATE",
    "CHANGE_EXISTING",
]
MatchSource = Literal[
    "SUGGESTED_DEFAULT",
    "LLM_EXTRACTED",
    "RAPIDFUZZ_FALLBACK",
    "MANUAL_SELECTED",
]
AliasScope = Literal["CUSTOMER", "TENANT"]
ApprovalStatus = Literal["PENDING", "APPROVED", "REJECTED"]
TerminationReason = Literal["OWNER_REJECTED", "CLERK_DISCARDED", "SYSTEM_TERMINATED"]

DecimalString = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)\.[0-9]{2}$")]


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

    order_total: DecimalString | None
    currency: Literal["MYR"] = "MYR"
    is_complete: bool


class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    raw_text: str
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    normalizer_version: str


class SkuCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: str
    family_id: str
    display_name: str
    pack_size: str | None = None
    grade: str | None = None
    base_unit: str
    tier_unit_price: DecimalString
    available_qty: int = Field(ge=0)


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    code: IssueCode
    condition_id: str | None = None
    line_id: str | None = None
    span: str | None = None
    source_span: str | None = None
    span_start: int | None = Field(default=None, ge=0)
    span_end: int | None = Field(default=None, ge=1)
    condition_kind: ConditionKind | None = None
    condition_scope: ConditionScope | None = None
    candidate_line_ids: list[str] = Field(default_factory=list)
    target_line_ids: list[str] = Field(default_factory=list)
    requested_unit_price: DecimalString | None = None
    price_basis: Literal["UNIT", "TOTAL", "UNKNOWN"] | None = None
    reason_code: IssueReasonCode | None = None
    ask: Literal["CUSTOMER", "OWNER", "CLERK", "SYSTEM"] = "CLERK"
    data_used: dict[str, Any] = Field(default_factory=dict)
    blocking: bool
    resolved: bool
    resolution: ResolutionChoice | None = None
    resolution_note: str | None = Field(default=None, max_length=500)
    auto_resolved_by: Literal["STOCK_CHECK"] | None = None


class ClarificationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = Field(min_length=2, max_length=35)
    message: str = Field(min_length=1, max_length=2000)
    unresolved_issue_ids: list[str] = Field(min_length=1)


class WorkingLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str
    client_line_ref: str | None = None
    sku_id: str | None = None
    family_id: str
    description: str | None = None
    requested_qty: int = Field(ge=1)
    confirmed_qty: int | None = Field(default=None, ge=1)
    effective_qty: int = Field(ge=1)
    uom: str | None = None
    pack_size: str | None = None
    grade: str | None = None
    tier_unit_price: DecimalString | None = None
    unit_price_override: DecimalString | None = None
    override_reason: str | None = Field(default=None, max_length=500)
    effective_unit_price: DecimalString | None = None
    subtotal_rm: DecimalString | None = None
    match_source: MatchSource
    source_span: str | None = None
    span_start: int | None = Field(default=None, ge=0)
    span_end: int | None = Field(default=None, ge=1)
    field_evidence: list[FieldEvidence] = Field(default_factory=list)
    candidate_skus: list[SkuCandidate] = Field(default_factory=list)
    saved_alias: dict[str, Any] | None = None
    available_qty: int | None = Field(default=None, ge=0)


class OrderDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    version: int = Field(ge=1)
    status: DraftStatus
    customer_id: str
    customer: CustomerSummary
    masked_message: str
    ai_mode: AiMode
    lines: list[WorkingLine] = Field(default_factory=list)
    issues: list[Issue]
    conditions: list[Issue] = Field(default_factory=list)
    blocking_issues: list[IssueCode] = Field(default_factory=list)
    escalation_preview: list[dict[str, Any]] = Field(default_factory=list)
    totals: OrderTotals
    allowed_actions: list[AllowedAction] = Field(default_factory=list)
    blocked_actions: dict[str, list[str]] = Field(default_factory=dict)
    clarification_draft: ClarificationDraft | None = None
    clarification_lang: str | None = None
    ignored_spans: list[dict[str, Any]] = Field(default_factory=list)
    disambiguations: list[Issue] = Field(default_factory=list)
    termination_reason: TerminationReason | None = None
    terminated_by_user_id: str | None = None
    termination_note: str | None = Field(default=None, max_length=500)
    created_at: datetime
    updated_at: datetime
    do_number: str | None = None


class WorkingLineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str | None = None
    client_line_ref: str | None = None
    sku_id: str | None = None
    family_id: str | None = Field(default=None, min_length=1)
    confirmed_qty: int | None = Field(default=None, ge=1)
    uom: str | None = None
    pack_size: str | None = None
    grade: str | None = None
    unit_price_override: DecimalString | None = None
    override_reason: str | None = Field(default=None, max_length=500)
    match_source: MatchSource
    save_to_alias_cache: bool = False
    alias_scope: AliasScope = "CUSTOMER"

    @model_validator(mode="after")
    def exactly_one_identity(self) -> "WorkingLineInput":
        if (self.line_id is None) == (self.client_line_ref is None):
            raise ValueError("exactly one of line_id or client_line_ref is required")
        return self


class IssueResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    choice: ResolutionChoice
    target_line_ids: list[str]
    confirmed_unit_price: DecimalString | None = None
    price_basis: Literal["UNIT", "TOTAL", "UNKNOWN"] | None = None
    note: str | None = Field(default=None, max_length=500)


class SaveLinesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    lines: list[WorkingLineInput]
    deleted_line_ids: list[str] = Field(default_factory=list)
    resolutions: list[IssueResolution] = Field(default_factory=list)


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    confirmed_items: list[WorkingLineInput] | None = None


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    draft_id: str
    draft_version: int = Field(ge=1)
    status: ApprovalStatus
    customer: CustomerSummary
    total_rm: DecimalString
    line_count: int = Field(ge=1)
    reasons: list[dict[str, Any]]
    requested_by: str
    requested_at: datetime
    allowed_actions: list[AllowedAction] = Field(default_factory=list)
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None


class ApprovalSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    customer_name: str
    masked_customer_text: str
    lines: list[WorkingLine]
    total_rm: DecimalString
    reasons: list[dict[str, Any]]


class FieldDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_version: int = Field(ge=1)
    line_id: str | None = None
    field_path: str
    before_value: Any = None
    after_value: Any = None
    source: str
    reason_code: str


class StockCheckLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str
    sku_id: str
    requested_qty: int = Field(ge=1)
    available_qty: int = Field(ge=0)
    sufficient: bool
    effective_qty: int = Field(ge=1)


class StockCheckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["NOT_RUN", "PASSED", "FAILED"]
    checked_at: datetime | None = None
    lines: list[StockCheckLine] = Field(default_factory=list)


class ApprovalDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    draft_id: str
    draft_version: int = Field(ge=1)
    status: ApprovalStatus
    customer: CustomerSummary
    total_rm: DecimalString
    line_count: int = Field(ge=1)
    reasons: list[dict[str, Any]]
    requested_by: str
    requested_at: datetime
    allowed_actions: list[AllowedAction] = Field(default_factory=list)
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None
    snapshot: ApprovalSnapshot
    field_diffs: list[FieldDiff] = Field(default_factory=list)
    stock_check: StockCheckSummary


class ApprovalListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ApprovalRequestResponse] = Field(default_factory=list)
    next_cursor: str | None = None


class DecideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["APPROVE", "REJECT"]
    note: str | None = Field(default=None, max_length=500)


class ApprovalDecisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    draft_id: str
    status: Literal["REJECTED"]
    termination_reason: Literal["OWNER_REJECTED"]
    decided_by: str
    decided_at: datetime
    decision_note: str = Field(min_length=1)


class ReplyDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    message: str
    do_number: str
    warnings: list[str] = Field(default_factory=list)


class DeliveryOrderLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str
    sku_id: str
    display_name: str
    quantity: int = Field(ge=1)
    unit: str
    tier_unit_price: DecimalString
    applied_unit_price: DecimalString
    subtotal_rm: DecimalString
    override_reason: str | None = Field(default=None, max_length=500)
    picking_note: str | None = Field(default=None, max_length=500)


class DeliveryOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    do_number: str
    draft_id: str
    draft_version: int = Field(ge=1)
    customer_id: str
    customer_name: str
    lines: list[DeliveryOrderLine] = Field(min_length=1)
    final_total_rm: DecimalString
    prepared_by: str
    approved_by: str
    escalation_reasons: list[dict[str, Any]] = Field(default_factory=list)
    approval_mode: Literal["DIRECT", "OWNER_APPROVED", "OWNER_SELF_APPROVED"]
    reply_draft: ReplyDraft
    related_do_number: str | None = None
    approved_at: datetime
