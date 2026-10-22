// Normalize optional wire fields for the UI. Never infer permissions, prices or states.
import { ApiError } from "./types";
import type {
  Approval,
  Draft,
  DraftSummary,
  FieldDiff,
  Gate0,
  Issue,
  Line,
  SaveRequest,
} from "./types";

// Wire formatting only: preserve the amount without using floating-point arithmetic.
export function decimalInput(value: string): string {
  const text = value.trim();
  if (!/^\d+(?:\.\d{1,2})?$/.test(text))
    throw new ApiError(
      "REQUEST_VALIDATION_FAILED",
      "Enter a unit price with at most two decimal places.",
    );
  const [whole, fraction = ""] = text.split(".");
  return `${whole.replace(/^0+(?=\d)/, "")}.${fraction.padEnd(2, "0")}`;
}

export function savePayload(request: SaveRequest): SaveRequest {
  return {
    ...request,
    lines: request.lines.map((line) => ({
      ...line,
      unit_price_override:
        line.unit_price_override == null
          ? null
          : decimalInput(line.unit_price_override),
    })),
    resolutions: request.resolutions.map((resolution) => ({
      ...resolution,
      ...(resolution.confirmed_unit_price == null
        ? {}
        : {
            confirmed_unit_price: decimalInput(resolution.confirmed_unit_price),
          }),
    })),
  };
}

export const fieldDiffView = (diff: Gate0["FieldDiff"]): FieldDiff => ({
  line_id: diff.line_id ?? null,
  field_path: diff.field_path,
  before: diff.before_value,
  after: diff.after_value,
  reason_code: diff.reason_code,
});

export const lineView = (line: Gate0["WorkingLine"]): Line => ({
  ...line,
  sku_id: line.sku_id ?? null,
  description: line.description ?? null,
  confirmed_qty: line.confirmed_qty ?? null,
  uom: line.uom ?? null,
  pack_size: line.pack_size ?? null,
  grade: line.grade ?? null,
  tier_unit_price: line.tier_unit_price ?? null,
  unit_price_override: line.unit_price_override ?? null,
  override_reason: line.override_reason ?? null,
  effective_unit_price: line.effective_unit_price ?? null,
  subtotal_rm: line.subtotal_rm ?? null,
  source_span: line.source_span ?? "",
  // Invalid/missing offsets intentionally fall back to source_span in MessageText.
  span_start: line.span_start ?? -1,
  span_end: line.span_end ?? -1,
  saved_alias: line.saved_alias ?? null,
  candidate_skus: line.candidate_skus.map((candidate) => ({
    ...candidate,
    pack_size: candidate.pack_size ?? "",
    grade: candidate.grade ?? undefined,
  })),
});

export const issueView = (issue: Gate0["Issue"]): Issue => ({
  ...issue,
  line_id: issue.line_id ?? null,
  span: issue.span ?? null,
});

export const draftView = (draft: Gate0["OrderDraft"]): Draft => ({
  ...draft,
  do_number: draft.do_number ?? null,
  lines: draft.lines.map(lineView),
  issues: draft.issues.map(issueView),
  conditions: draft.conditions.map(issueView),
  clarification_draft: draft.clarification_draft ?? null,
  clarification_lang: draft.clarification_lang ?? null,
  termination_reason: draft.termination_reason ?? null,
  termination_note: draft.termination_note ?? null,
});

export const summaryView = (draft: Gate0["DraftSummary"]): DraftSummary => ({
  ...draft,
  do_number: draft.do_number ?? null,
  created_at: draft.updated_at,
});

export function approvalView(
  approval: Gate0["ApprovalRequest"] | Gate0["ApprovalDetail"],
): Approval {
  if ("snapshot" in approval)
    return {
      ...approval,
      snapshot: {
        ...approval.snapshot,
        lines: approval.snapshot.lines.map(lineView),
      },
      field_diffs: approval.field_diffs.map(fieldDiffView),
    };
  return approval;
}
