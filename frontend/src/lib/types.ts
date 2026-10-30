import type { components } from "./gate0.generated";
import type { CatalogProductsResponse } from "./catalog";
export type Gate0 = components["schemas"];
export type Navigate = (path: string) => void;
export type Notify = (message: string) => void;
export type Role = Gate0["Role"];
export type DraftStatus = Gate0["DraftStatus"];
export type Action = Gate0["AllowedAction"];
export type Source = Gate0["MatchSource"];
export type AiMode = Gate0["AiMode"];
export interface Customer {
  customer_id: string;
  name: string;
  tier: string;
  credit_flag: "NONE" | "OVERDUE_NOTICE";
  has_credit_notice: boolean;
  phone_e164?: string | null;
}
export interface Me {
  user_id: string;
  display_name: string;
  tenant: { id: string; name: string };
  role: Role;
  permissions: Action[];
  permission_summary: string;
}
export interface Candidate {
  sku_id: string;
  family_id: string;
  display_name: string;
  pack_size: string;
  grade?: string;
  base_unit: string;
  tier_unit_price: string;
  available_qty: number;
}
export interface Alias {
  alias_id: string;
  phrase: string;
  target_type: "FAMILY" | "SKU";
  product_id?: string | null;
  family_id?: string | null;
  scope: "CUSTOMER" | "TENANT";
  active: boolean;
  created_at: string;
}
export interface Line {
  line_id: string;
  sku_id: string | null;
  family_id: string;
  description: string | null;
  requested_qty: number;
  confirmed_qty: number | null;
  effective_qty: number;
  uom: string | null;
  pack_size: string | null;
  grade: string | null;
  tier_unit_price: string | null;
  unit_price_override: string | null;
  override_reason: string | null;
  effective_unit_price: string | null;
  subtotal_rm: string | null;
  match_source: Source;
  source_span: string;
  span_start: number;
  span_end: number;
  field_evidence: {
    field: string;
    raw_text: string;
    start: number;
    end: number;
    normalizer_version: string;
  }[];
  candidate_skus: Candidate[];
  available_qty: number | null;
  saved_alias: Alias | null;
}
export interface LineInput {
  line_id: string;
  sku_id: string | null;
  family_id?: string;
  confirmed_qty: number | null;
  uom: string | null;
  pack_size: string | null;
  grade: string | null;
  unit_price_override: string | null;
  override_reason: string | null;
  match_source: Source;
  save_to_alias_cache?: boolean;
  alias_scope?: "CUSTOMER" | "TENANT";
}
export type ResolutionChoice = Gate0["ResolutionChoice"];
export interface Resolution {
  issue_id: string;
  choice: ResolutionChoice;
  target_line_ids: string[];
  confirmed_unit_price?: string;
  price_basis?: "UNIT";
  related_do_number?: string;
  note?: string;
}
export interface Issue {
  issue_id: string;
  code: string;
  line_id: string | null;
  condition_id?: string | null;
  span: string | null;
  span_start?: number | null;
  span_end?: number | null;
  condition_kind?: "STOCK" | "PRICE" | "TIME" | "OTHER" | null;
  condition_scope?: string | null;
  candidate_line_ids: string[];
  target_line_ids: string[];
  requested_unit_price?: string | null;
  price_basis?: string | null;
  reason_code?: string | null;
  ask: "CUSTOMER" | "OWNER" | "CLERK" | "SYSTEM";
  data_used: Record<string, unknown>;
  blocking: boolean;
  resolved: boolean;
  resolution?: ResolutionChoice | null;
  resolution_note?: string | null;
  auto_resolved_by?: string | null;
}
export interface Reason {
  code: string;
  line_id?: string | null;
  detail: Record<string, unknown>;
}
export interface Draft {
  draft_id: string;
  version: number;
  status: DraftStatus;
  do_number: string | null;
  customer_id: string;
  customer: Customer;
  masked_message: string;
  ai_mode: AiMode;
  lines: Line[];
  issues: Issue[];
  conditions: Issue[];
  blocking_issues: string[];
  escalation_preview: Reason[];
  totals: Gate0["OrderTotals"];
  allowed_actions: Action[];
  blocked_actions: Record<string, string[]>;
  clarification_draft: {
    language: string;
    message: string;
    unresolved_issue_ids: string[];
  } | null;
  clarification_lang: string | null;
  ignored_spans: {
    text: string;
    start: number;
    end: number;
    normalizer_version: string;
  }[];
  termination_reason: string | null;
  termination_note: string | null;
  created_at: string;
  updated_at: string;
}
export interface DraftSummary {
  draft_id: string;
  version: number;
  status: DraftStatus;
  do_number: string | null;
  customer_name: string;
  message_preview: string;
  open_blocking_issue_count: number;
  owner_escalation_count: number;
  extraction_sources: Source[];
  allowed_actions: Action[];
  created_at: string;
  updated_at: string;
  order_total?: string | null;
}
export interface SaveRequest {
  expected_version: number;
  lines: LineInput[];
  deleted_line_ids: string[];
  resolutions: Resolution[];
}
export interface DOLine {
  line_id: string;
  sku_id: string;
  display_name: string;
  quantity: number;
  unit: string;
  tier_unit_price: string;
  applied_unit_price: string;
  subtotal_rm: string;
  override_reason?: string | null;
}
export interface DeliveryOrder {
  do_number: string;
  draft_id: string;
  draft_version: number;
  customer_id: string;
  customer_name: string;
  lines: DOLine[];
  final_total_rm: string;
  prepared_by: string;
  approved_by: string;
  escalation_reasons: Reason[];
  approval_mode: "DIRECT" | "OWNER_APPROVED" | "OWNER_SELF_APPROVED";
  reply_draft: { language: string; message: string; do_number: string };
  related_do_number: string | null;
  approved_at: string;
}
export interface WarehouseOrder {
  do_number: string;
  customer_name: string;
  items: {
    sku_id: string;
    display_name: string;
    quantity: number;
    unit: string;
    picking_note?: string;
  }[];
  approved_at: string;
}
export interface FieldDiff {
  line_id: string | null;
  field_path: string;
  before: unknown;
  after: unknown;
  reason_code?: string;
}
export interface Approval {
  approval_id: string;
  draft_id: string;
  draft_version: number;
  status: "PENDING" | "APPROVED" | "REJECTED";
  customer: Customer;
  total_rm: string;
  line_count: number;
  reasons: Reason[];
  requested_by: string;
  requested_at: string;
  allowed_actions: Action[];
  snapshot?: {
    customer_id: string;
    customer_name: string;
    masked_customer_text: string;
    lines: Line[];
    total_rm: string;
    reasons: Reason[];
  };
  field_diffs?: FieldDiff[];
  stock_check?: {
    lines: {
      line_id: string;
      sku_id: string;
      requested_qty: number;
      effective_qty: number;
      available_qty: number;
      sufficient: boolean;
    }[];
  };
  decided_by?: string | null;
  decided_at?: string | null;
  decision_note?: string | null;
}
export interface Activity {
  activity_id: string;
  entity_id: string;
  action: string;
  actor: string;
  created_at: string;
  detail: string;
  actor_role?: string | null;
  do_number?: string | null;
}
export interface Audit {
  delivery_order: DeliveryOrder;
  ai_initial_snapshot: unknown;
  final_snapshot: unknown;
  field_diffs: FieldDiff[];
  timeline: Activity[];
}
export interface AiStatus {
  state: "OFFLINE" | "WARMING" | "READY" | "DEGRADED";
  fallback_available: boolean;
  last_checked_at: string;
  message: string;
}
export interface PageResult<T> {
  items: T[];
  next_cursor: string | null;
}
export class ApiError extends Error {
  constructor(
    public error_code: string,
    message: string,
    public details: Record<string, unknown> = {},
    public requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export interface Service {
  readonly mode: "demo" | "live";
  readonly fixture?: boolean;
  me(): Promise<Me>;
  customers(): Promise<Customer[]>;
  catalogProducts(): Promise<CatalogProductsResponse>;
  drafts(): Promise<DraftSummary[]>;
  draft(id: string): Promise<Draft>;
  parse(customerId: string, text: string, lang: string): Promise<Draft>;
  save(id: string, request: SaveRequest): Promise<Draft>;
  approve(id: string, version: number): Promise<DeliveryOrder | Approval>;
  approvals(): Promise<Approval[]>;
  approval(id: string): Promise<Approval>;
  decide(
    id: string,
    decision: "APPROVE" | "REJECT",
    note: string,
  ): Promise<DeliveryOrder | Approval | Gate0["ApprovalDecisionResult"]>;
  delivery(id: string): Promise<DeliveryOrder>;
  warehouse(id: string): Promise<WarehouseOrder>;
  activity(entity?: string): Promise<Activity[]>;
  audit(id: string): Promise<Audit>;
  aiStatus(): Promise<AiStatus>;
  wake(): Promise<AiStatus>;
  discard?(id: string, version: number, note: string): Promise<Draft>;
  clarificationCopied?(id: string, version: number): Promise<void>;
}
export const STATUS: Record<DraftStatus, { label: string; tone: string }> = {
  DISAMBIGUATION_REQUIRED: { label: "Needs review", tone: "amber" },
  READY_FOR_APPROVAL: { label: "Ready to approve", tone: "mint" },
  PENDING_OWNER_APPROVAL: { label: "Awaiting owner", tone: "blue" },
  DO_GENERATED: { label: "Delivery order ready", tone: "mint" },
  REJECTED: { label: "Closed", tone: "rose" },
};
export const toInput = (l: Line): LineInput => ({
  line_id: l.line_id,
  sku_id: l.sku_id,
  family_id: l.family_id,
  confirmed_qty: l.confirmed_qty,
  uom: l.uom,
  pack_size: l.pack_size,
  grade: l.grade,
  unit_price_override: l.unit_price_override,
  override_reason: l.override_reason,
  match_source: l.match_source,
});
export const money = (value: string | null | undefined) =>
  value == null
    ? "—"
    : `RM ${Number(value).toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
