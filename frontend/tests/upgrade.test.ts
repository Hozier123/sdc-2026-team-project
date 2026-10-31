import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { HttpService } from "../src/lib/api";
import { ApiError } from "../src/lib/types";
import { ActivityPage } from "../src/components/fulfillment";
import { RECONNECT_KEY, defaultApiBase, reconnectRequired, rememberConnection, validateApiBase } from "../src/lib/connection";
import { snapshotMode } from "../src/lib/extraction";
import { validRoute } from "../src/lib/review";

test("refresh recovery persists only a boolean and explicit demo clears it", () => {
  const values = new Map<string, string>();
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); }, removeItem: (key: string) => { values.delete(key); } };
  assert.equal(reconnectRequired(storage), false);
  rememberConnection(storage, true);
  assert.deepEqual([...values], [[RECONNECT_KEY, "true"]]);
  assert.equal(reconnectRequired(storage), true);
  rememberConnection(storage, false);
  assert.equal(values.size, 0);
  assert.doesNotThrow(() => rememberConnection({ setItem() { throw new Error("Storage disabled"); }, removeItem() {} }, true));
});

test("unconfigured production never silently suggests a loopback API", () => {
  assert.equal(defaultApiBase(undefined, false), "");
  assert.equal(defaultApiBase("  ", false), "");
  assert.equal(defaultApiBase(undefined, true), "http://127.0.0.1:8000/api/v1");
  assert.equal(defaultApiBase(" https://api.example/api/v1 ", false), "https://api.example/api/v1");
  assert.equal(validateApiBase(" http://127.0.0.1:8000/api/v1/ "), "http://127.0.0.1:8000/api/v1");
  for (const base of ["https://api.example/api/v1?token=synthetic", "https://api.example/api/v1#synthetic", "https://user:synthetic@api.example/api/v1", "http://api.example/api/v1"])
    assert.throws(() => validateApiBase(base));
});

test("all four extraction modes come from the order snapshot, unknown stays unknown", () => {
  for (const mode of ["LLM", "FALLBACK", "MIXED", "ALIAS_ONLY"])
    assert.equal(snapshotMode({ ai_mode: mode }), mode);
  for (const snapshot of [null, {}, { state: "READY" }, { ai_mode: "UNKNOWN" }])
    assert.equal(snapshotMode(snapshot), null);
  assert.equal(validRoute("activity/DRF_SYNTHETIC"), true);
  assert.equal(validRoute("activity/"), false);
  assert.equal(validRoute("activity/one/two"), false);
});

test("scoped HTTP activity preserves actor, rejection reason and result", async () => {
  const original = globalThis.fetch;
  let requestUrl = "";
  globalThis.fetch = async (input) => {
    requestUrl = String(input);
    return new Response(JSON.stringify({ items: [{ activity_id: 1, draft_id: "DRF_SYNTHETIC", event_type: "OWNER_REJECTED", actor_user_id: "synthetic-owner", actor_role: "OWNER", created_at: "2026-10-29T08:00:00Z", payload: { note: "Synthetic rejection reason" } }], next_cursor: null }));
  };
  try {
    const activity = await new HttpService("http://localhost:8000/api/v1", "synthetic").activity("DRF_SYNTHETIC");
    assert.equal(requestUrl, "http://localhost:8000/api/v1/activity?entity_id=DRF_SYNTHETIC&limit=50");
    assert.equal(activity[0].actor, "synthetic-owner");
    assert.equal(activity[0].actor_role, "OWNER");
    assert.equal(activity[0].entity_id, "DRF_SYNTHETIC");
    assert.equal(activity[0].do_number, null);
    assert.equal(activity[0].detail, "Synthetic rejection reason");
    const markup = renderToStaticMarkup(createElement(ActivityPage, { activity, drafts: [], navigate() {}, scopeId: "DRF_SYNTHETIC" }));
    assert.ok(markup.includes("Synthetic rejection reason"));
    assert.ok(markup.includes("Closed without a delivery order"));
    assert.ok(markup.includes("synthetic-owner · OWNER"));
    assert.ok(markup.includes("2026-10-29T08:00:00Z"));
  } finally { globalThis.fetch = original; }
});

test("DO activity exposes its generated result and DO lookup", () => {
  const markup = renderToStaticMarkup(createElement(ActivityPage, {
    activity: [{
      activity_id: "2", entity_id: "DRF_SYNTHETIC", action: "DO_CREATED",
      actor: "synthetic-clerk", actor_role: "CLERK", do_number: "DO-SYNTHETIC",
      created_at: "2026-10-29T08:01:00Z", detail: "do created",
    }],
    drafts: [], navigate() {}, scopeId: "DRF_SYNTHETIC",
  }));
  assert.ok(markup.includes("Delivery order generated"));
  assert.ok(markup.includes("DO-SYNTHETIC"));
  assert.ok(markup.includes("synthetic-clerk · CLERK"));
});

test("warehouse adapter rejects commercial and contact fields in the raw server response", async () => {
  const original = globalThis.fetch;
  const order = { do_number: "DO-SYNTHETIC", customer_name: "Synthetic customer", items: [{ sku_id: "SKU_SYNTHETIC", display_name: "Synthetic product", quantity: 2, unit: "ctn" }], approved_at: "2026-10-29T08:00:00Z" };
  try {
    const service = new HttpService("http://localhost:8000/api/v1", "synthetic-warehouse");
    globalThis.fetch = async () => new Response(JSON.stringify(order));
    assert.equal((await service.warehouse(order.do_number)).items[0].quantity, 2);
    for (const body of [{ ...order, final_total_rm: "999.00" }, { ...order, phone_e164: "synthetic-contact" }, { ...order, items: [{ ...order.items[0], tier_unit_price: "999.00" }] }]) {
      globalThis.fetch = async () => new Response(JSON.stringify(body));
      await assert.rejects(service.warehouse(order.do_number), (error: unknown) => error instanceof ApiError && error.error_code === "WAREHOUSE_RESPONSE_NOT_REDACTED" && !error.message.includes("999.00") && !error.message.includes("synthetic-contact"));
    }
  } finally { globalThis.fetch = original; }
});
