import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { HttpService } from "../src/lib/api";
import { ApiError } from "../src/lib/types";
const fixture = async (name: string) =>
  JSON.parse(
    await readFile(
      resolve(process.cwd(), "tests/fixtures", name + ".json"),
      "utf8",
    ),
  );
test("HTTP adapter preserves Gate 0 parse data, allowed actions and evidence", async () => {
  const f = await fixture("parse_draft");
  const original = globalThis.fetch;
  let submitted: unknown;
  globalThis.fetch = async (input, init) => {
    assert.equal(input, "http://localhost:8000/api/v1/orders/parse-draft");
    assert.equal(
      new Headers(init?.headers).get("Authorization"),
      "Bearer session-in-memory",
    );
    submitted = JSON.parse(init?.body as string);
    return new Response(JSON.stringify(f.body), {
      status: f.status,
      headers: f.headers,
    });
  };
  try {
    const s = new HttpService(
      "http://localhost:8000/api/v1/",
      "session-in-memory",
    );
    const d = await s.parse(
      f.request.customer_id,
      f.request.message_text,
      "ms",
    );
    assert.deepEqual(submitted, f.request);
    assert.deepEqual(d.allowed_actions, f.body.allowed_actions);
    assert.equal(d.lines[0].available_qty, 20);
    assert.deepEqual(d.issues, f.body.issues);
  } finally {
    globalThis.fetch = original;
  }
});
test("HTTP adapter projects audit events into the UI and preserves stable line diffs", async () => {
  const f = await fixture("audit_detail");
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify(f.body), { status: 200 });
  try {
    const s = new HttpService("http://localhost:8000/api/v1", "session");
    const a = await s.audit(f.body.do_number);
    assert.equal(a.delivery_order.do_number, f.body.final_snapshot.do_number);
    assert.equal(a.field_diffs[0].before, null);
    assert.equal(a.field_diffs[0].after, "SKU_OIL_1L");
    assert.equal(a.field_diffs[0].field_path, "sku_id");
    assert.equal(a.timeline.length, f.body.events.length);
    assert.equal(a.timeline[0].action, f.body.events[0].event_type);
  } finally {
    globalThis.fetch = original;
  }
});
test("HTTP 202 is an owner request; 409 error retains request ID and details", async () => {
  const accepted = await fixture("approve_202"),
    conflict = await fixture("approve_stock_changed_409");
  const original = globalThis.fetch;
  let n = 0;
  globalThis.fetch = async () => {
    const f = n++ === 0 ? accepted : conflict;
    return new Response(JSON.stringify(f.body), {
      status: f.status,
      headers: f.headers,
    });
  };
  try {
    const s = new HttpService("http://localhost:8000/api/v1", "session");
    const a = await s.approve("DRF_001", 2);
    assert.ok("approval_id" in a);
    await assert.rejects(
      s.approve("DRF_001", 2),
      (e: unknown) =>
        e instanceof ApiError &&
        e.error_code === conflict.body.error_code &&
        !!e.requestId,
    );
  } finally {
    globalThis.fetch = original;
  }
});
test("pagination follows cursors and never invents role headers", async () => {
  const original = globalThis.fetch;
  const urls: string[] = [];
  globalThis.fetch = async (input, init) => {
    urls.push(String(input));
    const h = new Headers(init?.headers);
    assert.equal(h.has("X-Mock-Role"), false);
    return new Response(
      JSON.stringify({
        items: [{ customer_id: `CUS_${urls.length}` }],
        next_cursor: urls.length === 1 ? "next page" : null,
      }),
    );
  };
  try {
    const result = await new HttpService(
      "http://localhost:8000/api/v1",
      "session",
    ).customers();
    assert.equal(result.length, 2);
    assert.match(urls[1], /cursor=next%20page/);
  } finally {
    globalThis.fetch = original;
  }
});
test("remote HTTP and embedded URL credentials are rejected", () => {
  assert.throws(() => new HttpService("http://remote.example/api/v1", "token"));
  assert.throws(
    () => new HttpService("https://name:secret@example.test/api/v1", "token"),
  );
});

test("nullable stock and incomplete totals remain unknown; candidates never fill selected stock or permissions", async () => {
  const f = await fixture("parse_draft");
  const original = globalThis.fetch;
  const body = structuredClone(f.body);
  delete body.lines[0].description;
  delete body.lines[0].confirmed_qty;
  delete body.lines[0].source_span;
  body.lines[0].available_qty = null;
  body.lines[0].candidate_skus[0].available_qty = 0;
  body.lines[0].candidate_skus[0].pack_size = null;
  body.totals = { order_total: null, currency: "MYR", is_complete: false };
  body.allowed_actions = [];
  globalThis.fetch = async () => new Response(JSON.stringify(body));
  try {
    const draft = await new HttpService(
      "http://localhost:8000/api/v1",
      "synthetic",
    ).draft("DRF_001");
    assert.equal(draft.lines[0].available_qty, null);
    assert.equal(draft.lines[0].candidate_skus[0].available_qty, 0);
    assert.equal(draft.lines[0].description, null);
    assert.equal(draft.lines[0].confirmed_qty, null);
    assert.equal(draft.totals.order_total, null);
    assert.deepEqual(draft.allowed_actions, []);
  } finally {
    globalThis.fetch = original;
  }
});

test("manual unit prices are serialized as exact two-decimal strings without changing the edit buffer", async () => {
  const f = await fixture("save_lines_ready");
  const original = globalThis.fetch;
  const line = {
    line_id: "LIN_001",
    sku_id: "SKU_FLOUR_5KG_A",
    confirmed_qty: 5,
    uom: "ctn",
    pack_size: "5kg",
    grade: "A",
    unit_price_override: "095.0",
    override_reason: "Synthetic agreed unit price",
    match_source: "MANUAL_SELECTED" as const,
  };
  let sends = 0;
  globalThis.fetch = async (_input, init) => {
    sends++;
    const submitted = JSON.parse(init?.body as string);
    assert.equal(submitted.lines[0].unit_price_override, "95.00");
    assert.equal(submitted.resolutions[0].confirmed_unit_price, "95.00");
    return new Response(JSON.stringify(f.body));
  };
  try {
    const service = new HttpService(
      "http://localhost:8000/api/v1",
      "synthetic",
    );
    await service.save("DRF_001", {
      expected_version: 1,
      lines: [line],
      deleted_line_ids: [],
      resolutions: [
        {
          issue_id: "ISS_PRICE_001",
          choice: "ACCEPT_REQUESTED_PRICE",
          target_line_ids: [line.line_id],
          confirmed_unit_price: "95",
          price_basis: "UNIT",
          note: "Synthetic confirmation",
        },
      ],
    });
    assert.equal(line.unit_price_override, "095.0");
    await assert.rejects(
      service.save("DRF_001", {
        expected_version: 1,
        lines: [{ ...line, unit_price_override: "95.001" }],
        deleted_line_ids: [],
        resolutions: [],
      }),
      /two decimal places/,
    );
    assert.equal(sends, 1);
  } finally {
    globalThis.fetch = original;
  }
});

test("HTTP discard sends P1 version/note and projects the terminal draft", async () => {
  const f = await fixture("save_lines_ready");
  const body = {
    ...f.body,
    status: "REJECTED",
    termination_reason: "CLERK_DISCARDED",
    terminated_by_user_id: "USR_T1_CLERK",
    termination_note: "Customer cancelled",
  };
  const original = globalThis.fetch;
  let url = "";
  let payload: unknown;
  globalThis.fetch = async (input, init) => {
    url = String(input);
    payload = JSON.parse(init?.body as string);
    return new Response(JSON.stringify(body), { status: 200 });
  };
  try {
    const draft = await new HttpService(
      "http://localhost:8000/api/v1",
      "session",
    ).discard("DRF_001", 2, "Customer cancelled");
    assert.equal(url, "http://localhost:8000/api/v1/orders/drafts/DRF_001/discard");
    assert.deepEqual(payload, {
      expected_version: 2,
      note: "Customer cancelled",
    });
    assert.equal(draft.status, "REJECTED");
    assert.equal(draft.termination_reason, "CLERK_DISCARDED");
    assert.equal(draft.termination_note, "Customer cancelled");
  } finally {
    globalThis.fetch = original;
  }
});
