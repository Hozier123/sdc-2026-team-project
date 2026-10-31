import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CatalogChoices } from "../src/components/ManualCatalogPicker";
import { HttpService } from "../src/lib/api";
import type { CatalogProduct } from "../src/lib/catalog";
import { clearPriceResolutions, createManualLine, selectCatalogProduct } from "../src/lib/manualRecovery";
import type { Issue, LineInput, Resolution } from "../src/lib/types";

const product: CatalogProduct = {
  sku_id: "SKU_TEST_2KG", display_name: "Test flour 2kg", pack_size: "2kg", grade: null, base_unit: "bag",
};

test("F03 catalog selection clears stale product decisions and requires quantity confirmation", () => {
  const old: LineInput = {
    line_id: "LNE_1", sku_id: null, family_id: "OLD", confirmed_qty: null,
    uom: "ctn", pack_size: "1kg", grade: "A", match_source: "RAPIDFUZZ_FALLBACK",
    unit_price_override: "2.00", override_reason: "Old product price",
    save_to_alias_cache: true, alias_scope: "TENANT",
  };
  const selected = selectCatalogProduct(old, product);
  assert.equal(selected.line_id, old.line_id);
  assert.equal(selected.sku_id, product.sku_id);
  assert.equal(selected.family_id, undefined);
  assert.equal(selected.uom, product.base_unit);
  assert.equal(selected.match_source, "MANUAL_SELECTED");
  assert.ok(Number.isNaN(selected.confirmed_qty));
  assert.equal(selected.unit_price_override, null);
  assert.equal(selected.override_reason, null);
  assert.equal(selected.save_to_alias_cache, false);
  assert.ok(Number.isNaN(selectCatalogProduct({ ...old, confirmed_qty: 3 }, product).confirmed_qty));
  const resolutions = [
    { issue_id: "price", choice: "ACCEPT_REQUESTED_PRICE", target_line_ids: ["LNE_1"] },
    { issue_id: "time", choice: "CONFIRMED_WITH_CUSTOMER", target_line_ids: [] },
  ] as Resolution[];
  const conditions = [
    { issue_id: "price", condition_kind: "PRICE" },
    { issue_id: "time", condition_kind: "TIME" },
  ] as Issue[];
  assert.deepEqual(clearPriceResolutions(resolutions, conditions), [resolutions[1]]);
});

test("F03 zero-line input uses a client reference and no fabricated price or stock", () => {
  const line = createManualLine(product, "manual-test-1");
  assert.equal(line.client_line_ref, "manual-test-1");
  assert.equal(line.sku_id, product.sku_id);
  assert.equal(line.uom, product.base_unit);
  assert.equal(line.match_source, "MANUAL_SELECTED");
  assert.ok(Number.isNaN(line.confirmed_qty));
  assert.equal("line_id" in line, false);
  assert.equal("tier_unit_price" in line, false);
  assert.equal("available_qty" in line, false);
});

test("F03 picker blocks an incomplete directory and never shows price or stock", () => {
  const complete = renderToStaticMarkup(createElement(CatalogChoices, {
    result: { items: [product], limit: 100, truncated: false }, query: "flour", onSelect: () => {},
  }));
  assert.match(complete, /Test flour 2kg/);
  assert.match(complete, /Choose Test flour 2kg/);
  assert.doesNotMatch(complete, /disabled=""|RM|stock/i);
  const incomplete = renderToStaticMarkup(createElement(CatalogChoices, {
    result: { items: [product], limit: 1, truncated: true }, query: "", onSelect: () => {},
  }));
  assert.match(incomplete, /directory is incomplete/);
  assert.match(incomplete, /disabled=""/);
});

test("F03 live save sends the new manual line without a guessed server ID", async () => {
  const original = globalThis.fetch;
  let submitted: Record<string, unknown> | undefined;
  globalThis.fetch = async (_input, init) => {
    submitted = JSON.parse(String(init?.body));
    return new Response(JSON.stringify({
      draft_id: "DRF_TEST", version: 2, status: "DISAMBIGUATION_REQUIRED", do_number: null,
      customer_id: "CUS_TEST", customer: { customer_id: "CUS_TEST", name: "Synthetic customer", tier: "A", credit_flag: "NONE", has_credit_notice: false },
      masked_message: "Synthetic order", ai_mode: "FALLBACK", lines: [], issues: [], conditions: [], blocking_issues: [],
      escalation_preview: [], totals: { order_total: null, is_complete: false }, allowed_actions: ["EDIT_DRAFT"], blocked_actions: {},
      clarification_draft: null, clarification_lang: null, ignored_spans: [], termination_reason: null, termination_note: null,
      created_at: "2026-10-31T00:00:00Z", updated_at: "2026-10-31T00:00:00Z",
    }), { status: 200 });
  };
  try {
    const line = { ...createManualLine(product, "manual-test-2"), confirmed_qty: 2 };
    await new HttpService("https://example.test/api/v1", "synthetic-session").save("DRF_TEST", {
      expected_version: 1, lines: [line], deleted_line_ids: [], resolutions: [],
    });
    const sent = (submitted?.lines as Record<string, unknown>[])[0];
    assert.equal(sent.client_line_ref, "manual-test-2");
    assert.equal(sent.sku_id, product.sku_id);
    assert.equal(sent.confirmed_qty, 2);
    assert.equal(sent.match_source, "MANUAL_SELECTED");
    assert.equal("line_id" in sent, false);
    assert.equal("tier_unit_price" in sent, false);
    assert.equal("available_qty" in sent, false);
  } finally {
    globalThis.fetch = original;
  }
});
