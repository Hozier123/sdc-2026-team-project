import test from "node:test";
import assert from "node:assert/strict";
import { issueCopy, issueGuidance } from "../src/lib/issueCopy";
import type { Issue } from "../src/lib/types";

const issue = (reason_code: string | null, code = "LOW_CONFIDENCE_MATCH") => ({
  code, reason_code, condition_kind: null,
}) as Issue;

test("R10 generic no-candidate response never invents a unit-conflict diagnosis", () => {
  const copy = issueCopy(issue("NO_CANDIDATE"));
  assert.equal(copy?.title, "No matching product option");
  assert.match(copy!.body, /does not identify a specific cause/);
  assert.doesNotMatch(copy!.body, /unit (?:conflict|is incompatible)/i);
  assert.equal(issueCopy(issue("FAMILY_NOT_EVIDENCED"))?.title, "Product not recognized");
});

test("R10 quantity reasons expose confirmation and explicit manual recovery without a default", () => {
  for (const reason of ["INVALID_QUANTITY", "AMBIGUOUS_QUANTITY"]) {
    const guidance = issueGuidance(issue(reason), true);
    assert.match(guidance, /quantity/i);
    assert.match(guidance, /Add a confirmed product/);
    assert.doesNotMatch(guidance, /default|quantity (?:of )?1/i);
  }
  assert.match(issueGuidance(issue("FIELD_NOT_EVIDENCED"), true), /extracted field/i);
  assert.doesNotMatch(issueGuidance(issue("FIELD_NOT_EVIDENCED"), true), /quantity is missing/i);
});

test("R10 unknown or absent reasons retain generic guidance and do not override other blockers", () => {
  for (const reason of [null, "FUTURE_REASON", "__proto__", "constructor"]) {
    assert.equal(issueCopy(issue(reason))?.title, "Confirm the product");
  }
  assert.equal(issueCopy(issue("INVALID_QUANTITY", "MULTIPLE_PACK_SIZES"))?.title, "Which pack size?");
  assert.match(issueGuidance(issue("NO_CANDIDATE", "INSUFFICIENT_STOCK"), true), /No role can approve/);
});
