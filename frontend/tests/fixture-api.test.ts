import test from "node:test";
import assert from "node:assert/strict";
// The harness is JavaScript so it runs directly in Node without the browser build.
import { createFixtureApi } from "../scripts/fixture_api.mjs";
import { HttpService } from "../src/lib/api";
import { ApiError, toInput } from "../src/lib/types";

async function withMock(run: (base: string) => Promise<void>) {
  const server = createFixtureApi();
  await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
  const base = `http://127.0.0.1:${server.address().port}/api/v1`;
  try {
    await run(base);
  } finally {
    await new Promise<void>((done, reject) =>
      server.close((error: Error) => (error ? reject(error) : done())),
    );
  }
}

test("real HTTP fixture flow preserves 202, immutable pending view, diffs, rejection and authentication", async () =>
  withMock(async (base) => {
    const clerk = new HttpService(base, "fixture-clerk");
    const me = await clerk.me();
    assert.equal(me.role, "CLERK");
    assert.equal(clerk.fixture, true);
    const draft = await clerk.parse(
      "CUS_001",
      "Synthetic fixture request",
      "en",
    );
    const saved = await clerk.save(draft.draft_id, {
      expected_version: draft.version,
      lines: draft.lines.map(toInput),
      deleted_line_ids: [],
      resolutions: [],
    });
    assert.equal(saved.status, "READY_FOR_APPROVAL");
    const result = await clerk.approve(saved.draft_id, saved.version);
    assert.ok("approval_id" in result);
    assert.equal(
      (await clerk.draft(draft.draft_id)).allowed_actions.includes(
        "EDIT_DRAFT",
      ),
      false,
    );
    const owner = new HttpService(base, "fixture-owner");
    const approval = await owner.approval("APR_001");
    assert.equal(approval.field_diffs?.[0].before, "98.00");
    assert.equal(approval.field_diffs?.[0].after, "95.00");
    await assert.rejects(
      clerk.decide("APR_001", "REJECT", "Synthetic rejection"),
      (e: unknown) =>
        e instanceof ApiError && e.error_code === "FORBIDDEN_ACTION",
    );
    const rejected = await owner.decide(
      "APR_001",
      "REJECT",
      "Synthetic rejection",
    );
    assert.equal("status" in rejected && rejected.status, "REJECTED");
    await assert.rejects(
      new HttpService(base, "invalid-fixture").me(),
      (e: unknown) =>
        e instanceof ApiError &&
        e.error_code === "INVALID_TOKEN" &&
        !!e.requestId,
    );
  }));

test("fixture stock snapshot keeps saving successful and approval blocked; warehouse never gets commercial fields", async () =>
  withMock(async (base) => {
    await fetch(`${base}/__fixture/reset`, {
      method: "POST",
      headers: {
        Authorization: "Bearer fixture-owner",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ scenario: "stock", saveResult: "stock" }),
    });
    const clerk = new HttpService(base, "fixture-clerk");
    const draft = await clerk.draft("DRF_001");
    const saved = await clerk.save(draft.draft_id, {
      expected_version: draft.version,
      lines: draft.lines.map(toInput),
      deleted_line_ids: [],
      resolutions: [],
    });
    assert.equal(saved.status, "DISAMBIGUATION_REQUIRED");
    assert.equal(saved.lines[0].available_qty, 3);
    assert.ok(saved.blocking_issues.includes("INSUFFICIENT_STOCK"));
    await assert.rejects(
      clerk.approve(draft.draft_id, saved.version),
      /Resolve blocking/,
    );
    const warehouse = new HttpService(base, "fixture-warehouse");
    const picking = await warehouse.warehouse("DO-20261021-0003");
    assert.equal("final_total_rm" in picking, false);
    assert.equal("tier_unit_price" in picking.items[0], false);
    await assert.rejects(
      warehouse.delivery("DO-20261021-0003"),
      (e: unknown) =>
        e instanceof ApiError && e.error_code === "FORBIDDEN_ACTION",
    );
    const forbidden = await fetch(`${base}/me`, {
      headers: {
        Origin: "https://untrusted.example",
        Authorization: "Bearer fixture-clerk",
      },
    });
    assert.equal(forbidden.status, 403);
  }));
