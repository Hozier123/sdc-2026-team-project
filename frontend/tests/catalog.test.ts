import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { HttpService } from "../src/lib/api";
import { DemoService } from "../src/lib/demo";
import { catalogNotice, matchingCatalogProducts, type CatalogProductsResponse } from "../src/lib/catalog";
import { CatalogResult } from "../src/components/CatalogPage";
import { CatalogChoices } from "../src/components/ManualCatalogPicker";
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

test("contextual choices show all egg grades and packs without silently selecting one", () => {
  const eggs = ["A", "B", "C"].flatMap((grade) => ["papan", "ctn"].map((unit) => ({
    sku_id: `SKU_TELUR_${grade}_${unit}`,
    display_name: "Telur 鸡蛋",
    pack_size: unit === "papan" ? "30枚" : "12托×30枚",
    grade,
    base_unit: unit,
  })));
  const chicken = { sku_id: "SKU_AYAM", display_name: "Ayam 鸡肉", pack_size: "10kg", grade: "A", base_unit: "ctn" };
  const directory = [chicken, ...eggs];
  const result = matchingCatalogProducts(directory, "来一个鸡蛋");
  assert.equal(result.phrase, "鸡蛋");
  assert.deepEqual(result.items, eggs);
  const markup = renderToStaticMarkup(createElement(CatalogChoices, {
    result: { items: directory, limit: 100, truncated: false },
    items: result.items, query: "", onSelect: () => {},
  }));
  assert.match(markup, /Choose Telur 鸡蛋, 30枚, grade A, papan/);
  assert.doesNotMatch(markup, /Ayam 鸡肉/);
  assert.deepEqual(matchingCatalogProducts(directory, "来一个鸡").items, []);
  assert.deepEqual(matchingCatalogProducts(directory, "来一个鸡蛋", [chicken.sku_id]).items, [chicken]);
});

test("contextual matching distinguishes shared product words across two tenant catalogues", () => {
  const make = (name: string, sku: string) => ({
    sku_id: sku, display_name: name, pack_size: "1kg", grade: null, base_unit: "bag",
  });
  const food = [
    make("Milo 美禄", "MILO_1"), make("Milo 美禄", "MILO_2"),
    make("Tepung gandum 面粉", "FLOUR_1"), make("Tepung gandum 面粉", "FLOUR_2"),
    make("Tepung jagung 玉米淀粉", "CORN"),
    make("Kacang merah 红豆", "RED_BEAN"), make("Kacang dal 扁豆", "DAL"),
    make("Sos tomato 番茄酱", "TOMATO"), make("Sos cili 辣椒酱", "CHILI"),
  ];
  const supplies = [
    make("Liquid soap", "SOAP_1"), make("Liquid soap", "SOAP_5"),
    make("Dishwashing liquid", "DISH"),
    make("Garbage bag", "BAG_S"), make("Garbage bag", "BAG_M"), make("Garbage bag", "BAG_L"),
    make("Gloves", "GLOVE_S"), make("Gloves", "GLOVE_M"), make("Gloves", "GLOVE_L"),
  ];
  for (const [directory, message, expected] of [
    [food, "美禄要两包", ["MILO_1", "MILO_2"]],
    [food, "Milo 2 bags", ["MILO_1", "MILO_2"]],
    [food, "Tepung gandum 5 bag", ["FLOUR_1", "FLOUR_2"]],
    [food, "请给我 Tepung gandum 面粉 2 bag, terima kasih", ["FLOUR_1", "FLOUR_2"]],
    [food, "Tepung jagung 1 bag", ["CORN"]],
    [food, "Kacang merah 2 bag", ["RED_BEAN"]],
    [food, "Kacang dal 2 bag", ["DAL"]],
    [food, "Sos cili 1 btl", ["CHILI"]],
    [supplies, "Liquid soap 2 btl", ["SOAP_1", "SOAP_5"]],
    [supplies, "请给我 Liquid soap 2 btl untuk kedai", ["SOAP_1", "SOAP_5"]],
    [supplies, "Dishwashing liquid 1 btl", ["DISH"]],
    [supplies, "Garbage bag 2 pack", ["BAG_S", "BAG_M", "BAG_L"]],
    [supplies, "Gloves 1 box", ["GLOVE_S", "GLOVE_M", "GLOVE_L"]],
  ] as const) {
    assert.deepEqual(
      matchingCatalogProducts(directory, message).items.map((item) => item.sku_id),
      expected,
      message,
    );
  }
  assert.deepEqual(matchingCatalogProducts(food, "Tepung 1 bag").items.map((item) => item.sku_id),
    ["FLOUR_1", "FLOUR_2", "CORN"]);
  assert.deepEqual(matchingCatalogProducts(food, "Milotest 2 bag").items, []);
});

test("backend candidate IDs provide variants for aliases absent from directory display names", () => {
  const items = [
    { sku_id: "SOAP_1", display_name: "Liquid soap", pack_size: "1L", grade: null, base_unit: "btl" },
    { sku_id: "SOAP_5", display_name: "Liquid soap", pack_size: "5L", grade: null, base_unit: "btl" },
    { sku_id: "DISH", display_name: "Dishwashing liquid", pack_size: "1L", grade: null, base_unit: "btl" },
  ];
  assert.deepEqual(matchingCatalogProducts(items, "sabun cecair", ["SOAP_1", "SOAP_5"]).items,
    items.slice(0, 2));
  assert.deepEqual(matchingCatalogProducts(items, "清洁液").items, []);
});
