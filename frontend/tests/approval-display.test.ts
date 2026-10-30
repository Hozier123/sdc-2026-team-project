import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { approvalReasonPrices, approvalSubmissionLabel } from "../src/lib/approval-display";
import { ApprovalsPage } from "../src/components/fulfillment";
import { Reasons } from "../src/components/ui";
import type { Approval, Me } from "../src/lib/types";

test("approval timestamps distinguish dates across midnight in MYT", () => {
  assert.equal(approvalSubmissionLabel("2026-10-30T15:56:00Z"), "Submitted 30 Oct 2026 at 23:56 MYT");
  assert.equal(approvalSubmissionLabel("2026-10-30T16:08:00Z"), "Submitted 31 Oct 2026 at 00:08 MYT");
  assert.equal(approvalSubmissionLabel(null), "Submission time unavailable");
  assert.equal(approvalSubmissionLabel("invalid"), "Submission time unavailable");
});

test("same-customer approval rows expose dates, draft identities and versions", () => {
  const make = (draft: string, requested_at: string): Approval => ({
    approval_id: `APR_${draft}`, draft_id: draft, draft_version: 2, status: "PENDING",
    customer: { customer_id: "CUS_SYNTHETIC", name: "Kedai Rasa", tier: "B", credit_flag: "NONE", has_credit_notice: false },
    total_rm: "34.00", line_count: 1, reasons: [], requested_by: "USR_T1_CLERK", requested_at, allowed_actions: [],
  });
  const html = renderToStaticMarkup(createElement(ApprovalsPage, {
    approvals: [make("DRF_FIRST1", "2026-10-29T15:56:00Z"), make("DRF_SECOND", "2026-10-30T15:56:00Z")],
    me: { role: "OWNER" } as Me, navigate: () => {},
  }));
  assert.match(html, /Submitted 29 Oct 2026 at 23:56 MYT/);
  assert.match(html, /Submitted 30 Oct 2026 at 23:56 MYT/);
  assert.match(html, /Draft #FIRST1/);
  assert.match(html, /Draft #SECOND/);
  assert.match(html, /Requested by USR_T1_CLERK/);
});

test("live price reasons show the actual tier and requested price", () => {
  const html = renderToStaticMarkup(createElement(Reasons, { reasons: [{
    code: "PRICE_OVERRIDE_BELOW_TIER",
    detail: { tier_unit_price: "19.00", effective_unit_price: "17.00" },
  }] }));
  assert.match(html, /Tier price RM 19\.00 → requested RM 17\.00/);
  assert.doesNotMatch(html, /RM 0\.00/);
  assert.deepEqual(approvalReasonPrices({ tier_price: "98.00", applied_price: "95.00" }), { tier: "98.00", applied: "95.00" });
  assert.deepEqual(approvalReasonPrices({ tier_unit_price: "19.00", effective_unit_price: "17.00", tier_price: "0", applied_price: "0" }), { tier: "19.00", applied: "17.00" });
});

test("unavailable prices remain missing while actual zeros remain zeros", () => {
  const render = (detail: Record<string, unknown>) => renderToStaticMarkup(createElement(Reasons, { reasons: [{ code: "PRICE_OVERRIDE_BELOW_TIER", detail }] }));
  assert.match(render({}), /Tier price — → requested —/);
  assert.match(render({ tier_unit_price: "0.00", effective_unit_price: 0 }), /Tier price RM 0\.00 → requested RM 0\.00/);
  assert.deepEqual(approvalReasonPrices({ tier_unit_price: "invalid", effective_unit_price: Infinity }), { tier: null, applied: null });
});
