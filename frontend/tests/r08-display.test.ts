import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { issueCopy, issueGuidance } from "../src/lib/issueCopy";
import { issueView } from "../src/lib/wire";
import { R08IdentityCandidates } from "../src/components/orders";
import { ErrorNotice } from "../src/components/ui";
import { ApiError } from "../src/lib/types";
import {
  MISSING_TIER_PRICE_FALLBACK_BODY,
  MISSING_TIER_PRICE_SAVE_ERROR,
  r08Diagnostics,
  tierPriceLabel,
} from "../src/lib/r08";
import type { Issue, Gate0 } from "../src/lib/types";

const HE_SAMPLE_R08 = {
  problem_kind: "MISSING_TIER_PRICE",
  explanation:
    "Identity is ambiguous and a compatible SKU has no customer tier price. Confirm the SKU; an authorized operator must configure the missing tier price before saving.",
  identity_candidates: [
    {
      sku_id: "SAMPLE_GULA_1KG",
      family_id: "FAM_GULA",
      display_name: "Interface sample GULA_1KG",
      pack_size: "1kg",
      grade: null,
      base_unit: "bag",
      tier_unit_price: "7.10",
      available_qty: 30,
    },
    {
      sku_id: "SAMPLE_GULA_2KG",
      family_id: "FAM_GULA",
      display_name: "Interface sample GULA_2KG",
      pack_size: "2kg",
      grade: null,
      base_unit: "bag",
      tier_unit_price: null,
      available_qty: 30,
    },
  ],
  identity_candidates_complete: true,
  priced_candidate_list_withheld: true,
  selectable: false,
  recovery: "CONFIRM_SKU_THEN_AUTHORIZED_PRICE_CONFIGURATION",
} as Record<string, unknown>;

const issue = (data_used: Record<string, unknown>, extra: Partial<Issue> = {}) =>
  ({
    issue_id: "I1",
    code: "LOW_CONFIDENCE_MATCH",
    line_id: "L1",
    span: "2 bag sugar",
    candidate_line_ids: [],
    target_line_ids: [],
    reason_code: "NO_CANDIDATE",
    ask: "CLERK",
    blocking: true,
    resolved: false,
    data_used,
    ...extra,
  }) as unknown as Issue;

test("R10/R08 accessor narrows the He v0.1r1 missing-price diagnostic", () => {
  const diag = r08Diagnostics(issue({ r08: HE_SAMPLE_R08 }));
  assert.equal(diag?.problem_kind, "MISSING_TIER_PRICE");
  assert.equal(diag?.selectable, false);
  assert.equal(diag?.priced_candidate_list_withheld, true);
  assert.equal(diag?.identity_candidates.length, 2);
  assert.equal(diag?.identity_candidates[1].tier_unit_price, null);
  assert.equal(
    diag?.explanation,
    HE_SAMPLE_R08.explanation as unknown as string,
  );
});

test("R10/R08 accessor is total: malformed payloads degrade, never throw", () => {
  assert.equal(r08Diagnostics(issue({})), undefined);
  assert.equal(r08Diagnostics(issue({ r08: "nope" })), undefined);
  assert.equal(r08Diagnostics(issue({ r08: ["array"] })), undefined);
  assert.equal(r08Diagnostics(issue({ r08: null })), undefined);
  assert.equal(r08Diagnostics(issue({ r08: { explanation: "only text" } })), undefined);
  // Missing or non-string explanation keeps the diagnostic with "".
  const noExplanation = r08Diagnostics(
    issue({ r08: { problem_kind: "MISSING_TIER_PRICE" } }),
  );
  assert.equal(noExplanation?.problem_kind, "MISSING_TIER_PRICE");
  assert.equal(noExplanation?.explanation, "");
  assert.equal(noExplanation?.identity_candidates.length, 0);
  // Missing selectable must never become selectable.
  assert.equal(noExplanation?.selectable, false);
  const badCandidates = r08Diagnostics(
    issue({ r08: { problem_kind: "MISSING_TIER_PRICE", explanation: "e", identity_candidates: "no" } }),
  );
  assert.equal(badCandidates?.identity_candidates.length, 0);
});

test("R10/R08 missing tier price replaces the misleading NO_CANDIDATE copy", () => {
  const missingPrice = issue({ r08: HE_SAMPLE_R08 });
  const copy = issueCopy(missingPrice);
  assert.equal(copy?.title, "Tier price is not configured");
  assert.equal(copy?.body, HE_SAMPLE_R08.explanation as unknown as string);
  assert.doesNotMatch(copy!.body, /does not identify a specific cause/);
  assert.match(issueGuidance(missingPrice, true), /authorized operator/);
});

test("R10/R08 empty or malformed explanation gets a safe fallback, not NO_CANDIDATE", () => {
  for (const payload of [
    { problem_kind: "MISSING_TIER_PRICE" },
    { problem_kind: "MISSING_TIER_PRICE", explanation: "" },
    { problem_kind: "MISSING_TIER_PRICE", explanation: 42 },
  ]) {
    const copy = issueCopy(issue({ r08: payload }));
    assert.equal(copy?.title, "Tier price is not configured", JSON.stringify(payload));
    assert.equal(copy?.body, MISSING_TIER_PRICE_FALLBACK_BODY, JSON.stringify(payload));
    assert.doesNotMatch(copy!.body, /No product option was returned/);
  }
});

test("R10/R08 copy stays generic without a valid r08 diagnostic", () => {
  assert.equal(issueCopy(issue({}))?.title, "No matching product option");
  assert.equal(
    issueCopy(issue({ r08: { problem_kind: "OTHER_KIND", explanation: "e" } }))?.title,
    "No matching product option",
  );
  const resolved = issue({ r08: HE_SAMPLE_R08 }, { resolved: true });
  assert.equal(issueCopy(resolved)?.title, "No matching product option");
});

test("R10/R08 identity candidate price rendering distinguishes unconfigured tiers", () => {
  assert.equal(tierPriceLabel(null), "Not configured");
  assert.equal(tierPriceLabel(undefined), "Not configured");
  assert.equal(tierPriceLabel("7.10"), "RM 7.10");
});

test("R10/R08 422 MISSING_TIER_PRICE save error copy states all three facts", () => {
  assert.equal(MISSING_TIER_PRICE_SAVE_ERROR.title, "Tier price is not configured");
  assert.match(MISSING_TIER_PRICE_SAVE_ERROR.body, /was not saved/);
  assert.match(MISSING_TIER_PRICE_SAVE_ERROR.body, /version is unchanged/);
  assert.match(MISSING_TIER_PRICE_SAVE_ERROR.body, /edits are kept/);
  assert.match(MISSING_TIER_PRICE_SAVE_ERROR.body, /authorized operator must configure/);
  assert.match(MISSING_TIER_PRICE_SAVE_ERROR.body, /product directory/);
});

test("R10/R08 identity candidates render read-only and never as selectable controls", () => {
  const markup = renderToStaticMarkup(
    createElement(R08IdentityCandidates, { issue: issue({ r08: HE_SAMPLE_R08 }) }),
  );
  assert.ok(markup.includes("Interface sample GULA_1KG"));
  assert.ok(markup.includes("Interface sample GULA_2KG"));
  assert.ok(markup.includes("Not configured"));
  assert.ok(markup.includes("RM 7.10"));
  assert.ok(markup.includes("identity check"));
  assert.equal(markup.includes("<button"), false);
  assert.equal(markup.includes("candidate-grid"), false);
  for (const forbidden of ['role="button"', "tabindex", "onclick", "tabIndex"]) {
    assert.equal(markup.toLowerCase().includes(forbidden.toLowerCase()), false, forbidden);
  }
  assert.equal(
    renderToStaticMarkup(createElement(R08IdentityCandidates, { issue: issue({}) })),
    "",
  );
  assert.equal(
    renderToStaticMarkup(
      createElement(R08IdentityCandidates, {
        issue: issue({ r08: HE_SAMPLE_R08 }, { resolved: true }),
      }),
    ),
    "",
  );
});

test("R10/R08 selectable=true diagnostics still render without controls", () => {
  const selectable = { ...HE_SAMPLE_R08, selectable: true };
  const markup = renderToStaticMarkup(
    createElement(R08IdentityCandidates, { issue: issue({ r08: selectable }) }),
  );
  assert.ok(markup.includes("Interface sample GULA_1KG"));
  assert.equal(markup.includes("<button"), false);
});

test("R10/R08 summary renders zero stock, null grade and keeps full names in title", () => {
  const payload = {
    problem_kind: "MISSING_TIER_PRICE",
    explanation: "e",
    identity_candidates: [
      {
        sku_id: "S0",
        display_name: "Zero stock product with a very long descriptive name",
        pack_size: "1kg",
        grade: null,
        base_unit: "bag",
        tier_unit_price: "3.00",
        available_qty: 0,
      },
    ],
  };
  const markup = renderToStaticMarkup(
    createElement(R08IdentityCandidates, { issue: issue({ r08: payload }) }),
  );
  assert.ok(markup.includes("0 in stock"));
  assert.ok(markup.includes("Grade —"));
  assert.ok(
    markup.includes('title="Zero stock product with a very long descriptive name"'),
  );
});

test("R10/R08 422 save failure shows the dedicated error notice copy", () => {
  const markup = renderToStaticMarkup(
    createElement(ErrorNotice, {
      error: new ApiError("MISSING_TIER_PRICE", "Synthetic 422 payload", {}),
      retry: () => {},
    }),
  );
  assert.ok(markup.includes("Tier price is not configured"));
  assert.ok(markup.includes("version is unchanged"));
  assert.ok(markup.includes("MISSING_TIER_PRICE"));
  assert.equal(markup.includes("Synthetic 422 payload"), false);
});

test("R10 wire normalization passes data_used through with unknown sibling keys", () => {
  const gate0Issue = {
    issue_id: "G1",
    code: "LOW_CONFIDENCE_MATCH",
    reason_code: "NO_CANDIDATE",
    ask: "CLERK",
    blocking: true,
    resolved: false,
    candidate_line_ids: [],
    target_line_ids: [],
    data_used: {
      r08: { problem_kind: "MISSING_TIER_PRICE", explanation: "e", selectable: false },
      requires_uom: true,
    },
  } as unknown as Gate0["Issue"];
  const normalized = issueView(gate0Issue);
  assert.deepEqual(normalized.data_used, {
    r08: { problem_kind: "MISSING_TIER_PRICE", explanation: "e", selectable: false },
    requires_uom: true,
  });
  const diag = r08Diagnostics(normalized);
  assert.equal(diag?.problem_kind, "MISSING_TIER_PRICE");
});
