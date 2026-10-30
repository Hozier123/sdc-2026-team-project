import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { HttpService } from "../src/lib/api";
import { DemoService } from "../src/lib/demo";
import { catalogNotice, type CatalogProductsResponse } from "../src/lib/catalog";
import { CatalogResult } from "../src/components/CatalogPage";
import { ApiError, type Service } from "../src/lib/types";
import { validRoute } from "../src/lib/review";

const product = { sku_id: "SKU_TEST", display_name: "Test product", pack_size: null, grade: null, base_unit: "bag" };

test("public Service catalog method preserves nullable specifications and all response metadata", async () => {
  const before = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = async (url, options) => {
    calls.push(String(url));
    assert.equal(options?.method, "GET");
    assert.equal(new Headers(options?.headers).get("Authorization"), "Bearer synthetic-catalog-session");
    assert.equal(options?.body, undefined);
    return new Response(JSON.stringify({ items: [product], limit: 100, truncated: true }));
  };
  try {
    const service: Service = new HttpService("https://example.test/api/v1", "synthetic-catalog-session");
    const result = await service.catalogProducts();
    assert.deepEqual(result, { items: [product], limit: 100, truncated: true });
    assert.deepEqual(calls, ["https://example.test/api/v1/catalog/products"]);
    assert.match(catalogNotice(result), /incomplete/);
  } finally { globalThis.fetch = before; }
});

for (const [status, code] of [[401, "INVALID_TOKEN"], [403, "FORBIDDEN_ACTION"]] as const) {
  test(`catalog ${status} propagates the server error and request ID`, async () => {
    const before = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify({ error_code: code, message: "Synthetic denied", details: {} }), {
      status, headers: { "X-Request-ID": `catalog-${status}` },
    });
    try {
      await assert.rejects(new HttpService("https://example.test/api/v1", "synthetic").catalogProducts(),
        (error: unknown) => error instanceof ApiError && error.error_code === code && error.requestId === `catalog-${status}`);
    } finally { globalThis.fetch = before; }
  });
}

test("directory renders null specifications, explicit truncation and no price/stock fields", () => {
  const result: CatalogProductsResponse = { items: [product], limit: 100, truncated: true };
  const markup = renderToStaticMarkup(createElement(CatalogResult, { result, mode: "live" }));
  assert.match(markup, /role="alert"/);
  assert.match(markup, /directory is incomplete/);
  assert.match(markup, /Limit 100/);
  assert.match(markup, /Live directory/);
  assert.match(markup, /—/);
  assert.doesNotMatch(markup, /undefined|RM|tier_unit_price|available_qty|family_id/);
});

test("empty directory is complete and local demo is clearly labelled", async () => {
  const markup = renderToStaticMarkup(createElement(CatalogResult, { result: { items: [], limit: 100, truncated: false }, mode: "demo" }));
  assert.match(markup, /No active products/);
  assert.match(markup, /0 products. Complete directory/);
  assert.match(markup, /Local demo sample/);
  const service: Service = new DemoService("CLERK");
  const result = await service.catalogProducts();
  assert.ok(result.items.length > 0);
  for (const item of result.items) assert.deepEqual(Object.keys(item).sort(), Object.keys(product).sort());
  await assert.rejects(new DemoService("WAREHOUSE").catalogProducts(), ApiError);
});

test("catalog has an explicit route without allowing arbitrary nested paths", () => {
  assert.equal(validRoute("catalog"), true);
  assert.equal(validRoute("catalog/edit"), false);
});
