import test from "node:test";
import assert from "node:assert/strict";
import {
  assertQuantities,
  pickingItems,
  rebaseInputs,
  validRoute,
  overviewQueue,
} from "../src/lib/review";
import { DemoService } from "../src/lib/demo";
import { toInput } from "../src/lib/types";
import { HttpService } from "../src/lib/api";
import type { DraftSummary } from "../src/lib/types";

test("overview gives the oldest blocked order the same priority in queue and recommendation", () => {
  const draft = (id: string, status: DraftSummary["status"], day: string) => ({
    draft_id: id, status, created_at: `2026-10-${day}T01:00:00Z`,
  } as DraftSummary);
  const input = [
    draft("ready-oldest", "READY_FOR_APPROVAL", "01"),
    draft("blocked-new", "DISAMBIGUATION_REQUIRED", "20"),
    draft("completed", "DO_GENERATED", "02"),
    draft("blocked-oldest", "DISAMBIGUATION_REQUIRED", "03"),
    draft("rejected", "REJECTED", "01"),
    draft("owner", "PENDING_OWNER_APPROVAL", "02"),
  ];
  const before = input.map(d => d.draft_id);
  const queue = overviewQueue(input);
  assert.deepEqual(queue.map(d => d.draft_id), ["blocked-oldest", "blocked-new", "ready-oldest", "owner"]);
  assert.deepEqual(input.map(d => d.draft_id), before, "must not mutate the source list used elsewhere");
});

test("picking consolidates repeated SKU quantities without mixing units or handling notes", () => {
  const input = [
    { sku_id: "FLOUR", display_name: "Flour", quantity: 1, unit: "ctn" },
    { sku_id: "FLOUR", display_name: "Flour", quantity: 2, unit: "ctn" },
    { sku_id: "FLOUR", display_name: "Flour", quantity: 1, unit: "pkt" },
    {
      sku_id: "FLOUR",
      display_name: "Flour",
      quantity: 4,
      unit: "ctn",
      picking_note: "Separate delivery",
    },
  ];
  const items = pickingItems(input);
  assert.deepEqual(
    items.map((i) => i.quantity),
    [3, 1, 4],
  );
  assert.equal(new Set(items.map((i) => i.picking_id)).size, 3);
  assert.equal(input[0].quantity, 1, "must not change the approved document");
});

test("quantity validation rejects values JSON would silently coerce, retaining nullable override semantics", async () => {
  const d = await new DemoService().parse("CUS_001", "Tepung 4 ctn", "en");
  const line = toInput(d.lines[0]);
  for (const quantity of [NaN, Infinity, 0, -1, 1.5, 100001])
    assert.throws(() =>
      assertQuantities([{ ...line, confirmed_qty: quantity }]),
    );
  for (const quantity of [null, 1, 100000])
    assert.doesNotThrow(() =>
      assertQuantities([{ ...line, confirmed_qty: quantity }]),
    );
});

test("HTTP saving rejects invalid quantities before JSON serialization or any request", async () => {
  const d = await new DemoService().parse("CUS_001", "Tepung 4 ctn", "en");
  const fetchBefore = globalThis.fetch;
  let requests = 0;
  globalThis.fetch = async () => {
    requests++;
    throw new Error("must not send invalid input");
  };
  try {
    const service = new HttpService(
      "http://127.0.0.1:8999/api/v1",
      "synthetic-test",
    );
    for (const qty of [NaN, Infinity, 0, -1, 1.5, 100001]) {
      await assert.rejects(
        service.save(d.draft_id, {
          expected_version: d.version,
          lines: d.lines.map((line) => ({
            ...toInput(line),
            confirmed_qty: qty,
          })),
          deleted_line_ids: [],
          resolutions: [],
        }),
        /whole quantity/,
      );
    }
    assert.equal(requests, 0);
  } finally {
    globalThis.fetch = fetchBefore;
  }
});

test("detail routes require exactly one nonempty ID and known list filters", () => {
  for (const route of [
    "order",
    "approval/",
    "delivery/ ",
    "order/id/extra",
    "inbox/garbage",
    "other",
  ])
    assert.equal(validRoute(route), false, route);
  for (const route of [
    "order/DRF_1",
    "approval/APR_1",
    "delivery/DO-T1-1",
    "workspace",
    "inbox/needs",
    "inbox",
  ])
    assert.equal(validRoute(route), true, route);
});

test("conflict recovery retains only local changes and respects newer server fields and lines", async () => {
  const base = await new DemoService().parse("CUS_001", "Tepung 4 ctn", "en");
  const latest = structuredClone(base);
  latest.version++;
  latest.lines[0].tier_unit_price = "99.00";
  latest.lines[0].override_reason = "New server note";
  latest.lines.push({
    ...structuredClone(latest.lines[0]),
    line_id: "NEW_SERVER_LINE",
  });
  const edits = base.lines.map(toInput);
  edits[0].confirmed_qty = 7;
  const recovered = rebaseInputs(base, latest, edits);
  assert.equal(recovered[0].confirmed_qty, 7);
  assert.equal(recovered[0].override_reason, "New server note");
  assert.equal(recovered[1].line_id, "NEW_SERVER_LINE");
  assert.equal(latest.lines[0].confirmed_qty, null);
});

test("conflict recovery never silently drops an edited product removed on the server", async () => {
  const base = await new DemoService().parse("CUS_001", "Tepung 4 ctn", "en");
  const edits = base.lines.map(toInput);
  edits[0].confirmed_qty = 7;
  assert.throws(
    () => rebaseInputs(base, { ...base, lines: [] }, edits),
    /removed/,
  );
});

test("conflict recovery cannot reapply edits to an order that became locked", async () => {
  const base = await new DemoService().parse("CUS_001", "Tepung 4 ctn", "en");
  assert.throws(
    () =>
      rebaseInputs(
        base,
        { ...base, allowed_actions: [] },
        base.lines.map(toInput),
      ),
    /locked/,
  );
});
