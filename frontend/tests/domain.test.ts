import test from "node:test";
import assert from "node:assert/strict";
import { DemoService, maskPII, cents, decimal } from "../src/lib/demo";
import {
  ApiError,
  toInput,
  type Draft,
  type SaveRequest,
} from "../src/lib/types";
const request = (d: Draft): SaveRequest => ({
  expected_version: d.version,
  lines: d.lines.map(toInput),
  deleted_line_ids: [],
  resolutions: [],
});
const fail = (code: string) => (e: unknown) =>
  e instanceof ApiError && e.error_code === code;
const memory = () => {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => {
      map.set(k, v);
    },
    map,
  };
};
test("PII is masked before persistence and evidence uses Unicode code points", async () => {
  const storage = memory(),
    s = new DemoService("CLERK", "T1", storage);
  const d = await s.parse(
    "CUS_001",
    "Tepung 2 ctn\nCall +60 12-345 6789\nme@example.test\n991231-10-1234",
    "en",
  );
  const saved = [...storage.map.values()].join("");
  for (const value of ["+60 12-345 6789", "me@example.test", "991231-10-1234"])
    assert.ok(!saved.includes(value));
  assert.match(d.masked_message, /REDACTED_PHONE/);
  assert.match(maskPII("011-12345678"), /REDACTED_PHONE/);
});
test("currency calculation uses exact integer cents", () => {
  assert.equal(decimal(cents("13.50") * 10n), "135.00");
  assert.equal(decimal(cents("0.10") + cents("0.20")), "0.30");
  assert.throws(() => cents("1e4"), fail("REQUEST_VALIDATION_FAILED"));
});
test("a routine order completes once and can be restored from storage", async () => {
  const storage = memory(),
    s = new DemoService("CLERK", "T1", storage);
  const d = await s.parse("CUS_001", "Tepung 2 ctn", "en");
  assert.equal(d.status, "READY_FOR_APPROVAL");
  const result = await s.approve(d.draft_id, d.version);
  assert.ok("do_number" in result);
  assert.equal(result.final_total_rm, "196.00");
  await assert.rejects(
    s.approve(d.draft_id, d.version),
    fail("ALREADY_APPROVED"),
  );
  const recovered = new DemoService("CLERK", "T1", storage);
  assert.equal((await recovered.draft(d.draft_id)).do_number, result.do_number);
  assert.equal(
    (await recovered.delivery(result.do_number)).final_total_rm,
    "196.00",
  );
});
test("ambiguity blocks approval until explicit SKU selection; customer memory is scoped", async () => {
  const s = new DemoService();
  const d = await s.parse("CUS_001", "Milo 5 pkt", "ms");
  assert.equal(d.status, "DISAMBIGUATION_REQUIRED");
  await assert.rejects(
    s.approve(d.draft_id, d.version),
    fail("DISAMBIGUATION_UNRESOLVED"),
  );
  const req = request(d);
  const c = d.lines[0].candidate_skus[0];
  Object.assign(req.lines[0], {
    sku_id: c.sku_id,
    uom: c.base_unit,
    match_source: "MANUAL_SELECTED",
    save_to_alias_cache: true,
    alias_scope: "CUSTOMER",
  });
  const saved = await s.save(d.draft_id, req);
  assert.equal(saved.status, "READY_FOR_APPROVAL");
  assert.ok(saved.lines[0].saved_alias);
  const repeat = await s.parse("CUS_001", "Milo 5 pkt", "ms");
  assert.equal(repeat.ai_mode, "ALIAS_ONLY");
  const other = await s.parse("CUS_003", "Milo 5 pkt", "ms");
  assert.equal(other.lines[0].sku_id, null);
});
test("stock issue closes after reduction and reopens on increase", async () => {
  const s = new DemoService();
  let d = await s.parse("CUS_001", "Ayam A1 5 ctn, kalau ada", "ms");
  assert.ok(d.issues.some((i) => i.code === "INSUFFICIENT_STOCK"));
  assert.equal(d.conditions[0].blocking, false);
  let req = request(d);
  req.lines[0].confirmed_qty = 3;
  d = await s.save(d.draft_id, req);
  assert.equal(d.status, "READY_FOR_APPROVAL");
  assert.equal(d.lines[0].effective_qty, 3);
  assert.equal(d.lines[0].requested_qty, 5);
  assert.equal(d.conditions[0].resolved, true);
  req = request(d);
  req.lines[0].confirmed_qty = 4;
  d = await s.save(d.draft_id, req);
  assert.equal(d.status, "DISAMBIGUATION_REQUIRED");
  assert.equal(d.conditions[0].resolved, false);
});
test("stock check aggregates repeated SKU lines", async () => {
  const s = new DemoService();
  const d = await s.parse("CUS_001", "Ayam A1 2 ctn\nAyam A1 2 ctn", "en");
  assert.equal(d.status, "DISAMBIGUATION_REQUIRED");
  await assert.rejects(
    s.approve(d.draft_id, d.version),
    fail("DISAMBIGUATION_UNRESOLVED"),
  );
});
test("saved demo drafts show current stock and checks after another approval", async () => {
  const store = memory();
  const clerk = new DemoService("CLERK", "T1", store);
  const ready = await clerk.parse("CUS_001", "Tepung 4 ctn", "en");
  assert.equal(ready.status, "READY_FOR_APPROVAL");
  assert.equal(ready.lines[0].available_qty, 22);

  const other = await clerk.parse("CUS_001", "Tepung 20 ctn", "en");
  await new DemoService("OWNER", "T1", store).approve(other.draft_id, other.version);

  const summary = (await clerk.drafts()).find((d) => d.draft_id === ready.draft_id);
  assert.equal(summary?.status, "DISAMBIGUATION_REQUIRED");
  assert.equal(summary?.open_blocking_issue_count, 1);
  assert.ok(!summary?.allowed_actions.includes("APPROVE_AND_GENERATE_DO"));

  const current = await clerk.draft(ready.draft_id);
  assert.equal(current.version, ready.version);
  assert.equal(current.lines[0].available_qty, 2);
  assert.ok(current.blocking_issues.includes("INSUFFICIENT_STOCK"));
  assert.ok(!current.allowed_actions.includes("APPROVE_AND_GENERATE_DO"));
  await assert.rejects(clerk.approve(ready.draft_id, ready.version), fail("STOCK_CHANGED"));

  const saved = JSON.parse(store.map.get("kiraorder.demo.v1.T1")!) as { drafts: Draft[] };
  const savedDraft = saved.drafts.find((d) => d.draft_id === ready.draft_id);
  assert.equal(savedDraft?.version, ready.version);
  assert.equal(savedDraft?.status, "READY_FOR_APPROVAL");
});
test("price evidence never automatically changes tier price; target and override must agree", async () => {
  const s = new DemoService();
  let d = await s.parse("CUS_001", "Tepung 5 ctn, kalau RM95 boleh?", "ms");
  assert.equal(d.lines[0].effective_unit_price, "98.00");
  const issue = d.conditions[0];
  let req = request(d);
  req.resolutions = [
    {
      issue_id: issue.issue_id,
      choice: "ACCEPT_REQUESTED_PRICE",
      target_line_ids: [],
      confirmed_unit_price: "95.00",
      price_basis: "UNIT",
      note: "Customer confirmed price",
    },
  ];
  await assert.rejects(s.save(d.draft_id, req), fail("TARGET_LINE_REQUIRED"));
  req.resolutions[0].target_line_ids = [d.lines[0].line_id];
  req.lines[0].unit_price_override = "94.00";
  req.lines[0].override_reason = "Customer confirmed unit price";
  await assert.rejects(
    s.save(d.draft_id, req),
    fail("REQUEST_VALIDATION_FAILED"),
  );
  req.lines[0].unit_price_override = "95.00";
  d = await s.save(d.draft_id, req);
  assert.equal(d.totals.order_total, "475.00");
  assert.ok(d.allowed_actions.includes("SUBMIT_FOR_OWNER"));
  const a = await s.approve(d.draft_id, d.version);
  assert.ok("approval_id" in a);
  assert.deepEqual(a.allowed_actions, []);
  await assert.rejects(
    s.decide(a.approval_id, "APPROVE", ""),
    fail("FORBIDDEN"),
  );
});
test("save is atomic on invalid condition; alias writes are not leaked", async () => {
  const s = new DemoService();
  const d = await s.parse(
    "CUS_001",
    "Milo 5 pkt\nTepung 2 ctn, kalau RM90 boleh?",
    "en",
  );
  const req = request(d),
    c = d.lines[0].candidate_skus[0];
  Object.assign(req.lines[0], {
    sku_id: c.sku_id,
    uom: c.base_unit,
    match_source: "MANUAL_SELECTED",
    save_to_alias_cache: true,
  });
  req.resolutions = [
    {
      issue_id: d.conditions[0].issue_id,
      choice: "CONFIRMED_WITH_CUSTOMER",
      target_line_ids: [],
      note: "",
    },
  ];
  await assert.rejects(s.save(d.draft_id, req), fail("NOTE_REQUIRED"));
  assert.equal((await s.draft(d.draft_id)).version, 1);
  const repeat = await s.parse("CUS_001", "Milo 5 pkt", "en");
  assert.equal(repeat.ai_mode, "FALLBACK");
});
test("owner approvals bind a version; rejection needs a reason and becomes terminal", async () => {
  const store = memory(),
    clerk = new DemoService("CLERK", "T1", store);
  const d = await clerk.parse("CUS_002", "Tepung 2 ctn", "en");
  const a = await clerk.approve(d.draft_id, d.version);
  assert.ok("approval_id" in a);
  const owner = new DemoService("OWNER", "T1", store);
  await assert.rejects(
    owner.decide(a.approval_id, "REJECT", "  "),
    fail("NOTE_REQUIRED"),
  );
  await owner.decide(
    a.approval_id,
    "REJECT",
    "Customer credit terms need attention.",
  );
  const closed = await owner.draft(d.draft_id);
  assert.equal(closed.status, "REJECTED");
  assert.equal(closed.termination_reason, "OWNER_REJECTED");
  await assert.rejects(
    owner.save(d.draft_id, request(closed)),
    fail("ORDER_LOCKED"),
  );
});
test("owner cannot bypass a stock change between submission and approval", async () => {
  const store = memory(),
    clerk = new DemoService("CLERK", "T1", store);
  const d = await clerk.parse("CUS_002", "Ayam A1 3 ctn", "en");
  const a = await clerk.approve(d.draft_id, 1);
  assert.ok("approval_id" in a);
  const other = await clerk.parse("CUS_001", "Ayam A1 2 ctn", "en");
  await clerk.approve(other.draft_id, 1);
  const owner = new DemoService("OWNER", "T1", store);
  await assert.rejects(
    owner.decide(a.approval_id, "APPROVE", ""),
    fail("STOCK_CHANGED"),
  );
  assert.equal((await owner.approval(a.approval_id)).status, "PENDING");
});
test("owner stock check uses combined quantity for repeated SKU lines", async () => {
  const store = memory();
  const clerk = new DemoService("CLERK", "T1", store);
  const order = await clerk.parse("CUS_002", "Tepung 2 ctn\nTepung 2 ctn", "en");
  const request = await clerk.approve(order.draft_id, order.version);
  assert.ok("approval_id" in request);

  const other = await clerk.parse("CUS_001", "Tepung 20 ctn", "en");
  const owner = new DemoService("OWNER", "T1", store);
  await owner.approve(other.draft_id, other.version);
  const pending = await owner.approval(request.approval_id);
  assert.equal(pending.stock_check?.lines.length, 2);
  assert.ok(pending.stock_check?.lines.every((line) => line.available_qty === 2 && !line.sufficient));
});
test("decided approval keeps the stock seen before its delivery order was generated", async () => {
  const store = memory();
  const clerk = new DemoService("CLERK", "T1", store);
  const order = await clerk.parse("CUS_002", "Tepung 20 ctn", "en");
  const request = await clerk.approve(order.draft_id, order.version);
  assert.ok("approval_id" in request);

  const owner = new DemoService("OWNER", "T1", store);
  const delivery = await owner.decide(request.approval_id, "APPROVE", "");
  assert.ok("do_number" in delivery);
  const decided = await owner.approval(request.approval_id);
  assert.equal(decided.status, "APPROVED");
  assert.equal(decided.stock_check?.lines[0].available_qty, 22);
  assert.equal(decided.stock_check?.lines[0].sufficient, true);
});
test("warehouse receives a cropped object, cannot read raw deliveries or drafts", async () => {
  const store = memory();
  new DemoService("CLERK", "T1", store);
  const warehouse = new DemoService("WAREHOUSE", "T1", store);
  const w = await warehouse.warehouse("DO-T1-0001");
  assert.deepEqual(Object.keys(w).sort(), [
    "approved_at",
    "customer_name",
    "do_number",
    "items",
  ]);
  assert.ok(
    !JSON.stringify(w).match(/price|total_rm|phone|masked_message|credit_flag/),
  );
  await assert.rejects(warehouse.drafts(), fail("FORBIDDEN"));
  await assert.rejects(warehouse.delivery("DO-T1-0001"), fail("FORBIDDEN"));
});
test("tenant data does not cross workspaces", async () => {
  const store = memory(),
    t1 = new DemoService("CLERK", "T1", store),
    t2 = new DemoService("CLERK", "T2", store);
  const d = await t1.parse("CUS_001", "Tepung 1 ctn", "en");
  await assert.rejects(t2.draft(d.draft_id), fail("NOT_FOUND"));
  await assert.rejects(
    t2.parse("CUS_001", "Tepung 1 ctn", "en"),
    fail("NOT_FOUND"),
  );
});
test("stale versions, empty orders and read-only amount writes are rejected", async () => {
  const s = new DemoService(),
    d = await s.parse("CUS_001", "Tepung 1 ctn", "en");
  const req = request(d);
  req.lines[0].confirmed_qty = 2;
  const saved = await s.save(d.draft_id, req);
  await assert.rejects(s.save(d.draft_id, req), fail("STALE_VERSION"));
  await assert.rejects(s.approve(d.draft_id, 1), fail("STALE_VERSION"));
  const invalid = request(saved);
  invalid.lines = [];
  invalid.deleted_line_ids = saved.lines.map((l) => l.line_id);
  await assert.rejects(s.save(d.draft_id, invalid), fail("EMPTY_ORDER"));
  const readonly = request(saved);
  Object.assign(readonly.lines[0], { subtotal_rm: "0.01" });
  await assert.rejects(
    s.save(d.draft_id, readonly),
    fail("REQUEST_VALIDATION_FAILED"),
  );
});
test("missing unit remains a blocking check instead of silently inferring a unit", async () => {
  const s = new DemoService();
  const d = await s.parse("CUS_001", "Tepung 5", "en");
  assert.equal(d.lines[0].uom, null);
  assert.ok(d.blocking_issues.includes("MISSING_UOM"));
});
test("multiple service instances see the latest version and cannot overwrite each other", async () => {
  const store = memory(),
    a = new DemoService("CLERK", "T1", store),
    b = new DemoService("CLERK", "T1", store);
  const d = await a.parse("CUS_001", "Tepung 1 ctn", "en");
  const fromB = await b.draft(d.draft_id);
  const req = request(d);
  req.lines[0].confirmed_qty = 2;
  await a.save(d.draft_id, req);
  await assert.rejects(
    b.save(d.draft_id, request(fromB)),
    fail("STALE_VERSION"),
  );
  assert.equal((await b.draft(d.draft_id)).lines[0].effective_qty, 2);
});
test("evidence spans stay aligned after a surrogate pair", async () => {
  const s = new DemoService();
  const d = await s.parse("CUS_001", "😀 hello\nMilo 5 pkt", "en");
  const l = d.lines[1];
  assert.equal(
    Array.from(d.masked_message).slice(l.span_start, l.span_end).join(""),
    "Milo 5 pkt",
  );
  assert.equal(l.span_start, 8);
});
