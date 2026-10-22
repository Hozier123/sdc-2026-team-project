// Local development harness. Fixed synthetic snapshots; no business engine or AI.
import http from "node:http";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const contract = JSON.parse(
  await fs.readFile(
    new URL("../contracts/gate0.openapi.json", import.meta.url),
    "utf8",
  ),
);
const ajv = new Ajv2020({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(contract, "gate0");
const validateBody = Object.fromEntries(
  [
    "ParseDraftRequest",
    "SaveLinesRequest",
    "ApproveRequest",
    "DecideRequest",
  ].map((name) => [
    name,
    ajv.compile({ $ref: `gate0#/components/schemas/${name}` }),
  ]),
);

const fixture = async (name) =>
  JSON.parse(
    await fs.readFile(
      new URL(`../tests/fixtures/${name}.json`, import.meta.url),
      "utf8",
    ),
  );
const names = [
  "parse_draft",
  "save_lines_ready",
  "save_lines_insufficient_stock_200",
  "approve_200",
  "approve_202",
  "approval_detail",
  "decide_rejected",
  "warehouse_delivery_order",
  "customers_list",
  "already_approved_409",
  "approve_stock_changed_409",
  "error_catalog",
];
const fixtures = Object.fromEntries(
  await Promise.all(names.map(async (name) => [name, await fixture(name)])),
);
const clone = (value) => structuredClone(value);
const tokens = {
  "fixture-clerk": "CLERK",
  "fixture-owner": "OWNER",
  "fixture-warehouse": "WAREHOUSE",
};
const permissions = [
  "EDIT_DRAFT",
  "RESOLVE_ISSUE",
  "COPY_CLARIFICATION",
  "APPROVE_AND_GENERATE_DO",
  "SUBMIT_FOR_OWNER",
  "VIEW_ACTIVITY",
  "WAKE_AI",
];

export function createFixtureApi() {
  let state;
  const reset = ({
    scenario = "price",
    saveResult = "ready",
    error = null,
    wakeDelayMs = 0,
  } = {}) => {
    if (!["price", "ready", "stock", "candidate", "pending"].includes(scenario))
      throw new Error("Unknown fixture scenario.");
    state = {
      scenario,
      saveResult,
      error,
      wakeDelayMs: Math.min(10000, Math.max(0, Number(wakeDelayMs) || 0)),
      wakeRequests: 0,
      draft: clone(
        fixtures[
          scenario === "stock"
            ? "save_lines_insufficient_stock_200"
            : scenario === "ready" || scenario === "pending"
              ? "save_lines_ready"
              : "parse_draft"
        ].body,
      ),
      approval: clone(fixtures.approval_detail.body),
      delivery: null,
    };
    state.approval.draft_id = state.draft.draft_id;
    state.approval.draft_version = state.draft.version;
    if (scenario === "candidate") {
      const line = state.draft.lines[0];
      line.sku_id = null;
      line.available_qty = null;
      line.tier_unit_price = null;
      line.effective_unit_price = null;
      line.subtotal_rm = null;
      const issue = {
        ...state.draft.issues[0],
        issue_id: "ISS_CANDIDATE",
        code: "MULTIPLE_PACK_SIZES",
        condition_id: null,
        line_id: line.line_id,
        span: line.source_span,
        condition_kind: null,
        condition_scope: null,
        blocking: true,
        resolved: false,
        ask: "CUSTOMER",
      };
      state.draft.issues = [issue];
      state.draft.conditions = [];
      state.draft.blocking_issues = ["MULTIPLE_PACK_SIZES"];
      state.draft.totals = {
        order_total: null,
        currency: "MYR",
        is_complete: false,
      };
      state.draft.clarification_draft = {
        language: "en",
        message: "Which pack size of flour do you need?",
        unresolved_issue_ids: [issue.issue_id],
      };
    }
    if (scenario === "pending") lock("PENDING_OWNER_APPROVAL");
  };
  const lock = (status) => {
    state.draft.status = status;
    state.draft.allowed_actions = ["VIEW_ACTIVITY"];
    state.draft.blocked_actions = {};
  };
  reset();
  const server = http.createServer(async (req, res) => {
    const origin = req.headers.origin;
    // The mock is intentionally inaccessible from remote web origins.
    if (
      origin &&
      !/^http:\/\/(?:127\.0\.0\.1|localhost)(?::\d+)?$/.test(origin)
    ) {
      res.writeHead(403);
      res.end();
      return;
    }
    const headers = {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "X-Request-ID": "fixture-local-only",
      "X-KiraOrder-Fixture": "true",
      "Access-Control-Allow-Origin": origin ?? "http://127.0.0.1:5173",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
      "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
      "Access-Control-Expose-Headers": "X-Request-ID, X-KiraOrder-Fixture",
      Vary: "Origin",
    };
    const send = (status, body) => {
      res.writeHead(status, headers);
      res.end(JSON.stringify(body));
    };
    const fail = (code) => {
      const f = fixtures.error_catalog[code];
      send(f.status, f.body);
    };
    if (req.method === "OPTIONS") {
      res.writeHead(204, headers);
      res.end();
      return;
    }
    const path = new URL(req.url, "http://localhost").pathname.replace(
      /^\/api\/v1/,
      "",
    );
    const role =
      tokens[(req.headers.authorization ?? "").replace(/^Bearer /, "")];
    if (!role) {
      fail("INVALID_TOKEN");
      return;
    }
    try {
      // Read but never log or persist submitted text or tokens.
      let input = "";
      for await (const chunk of req) {
        input += chunk;
        if (input.length > 100000) throw new Error("Request too large.");
      }
      const body = input ? JSON.parse(input) : {};
      const model =
        req.method === "PUT" && /\/lines$/.test(path)
          ? "SaveLinesRequest"
          : req.method === "POST" && path === "/orders/parse-draft"
            ? "ParseDraftRequest"
            : req.method === "POST" && /\/approve$/.test(path)
              ? "ApproveRequest"
              : req.method === "POST" && /\/decide$/.test(path)
                ? "DecideRequest"
                : null;
      if (model && !validateBody[model](body)) {
        send(422, {
          error_code: "REQUEST_VALIDATION_FAILED",
          message: "The request does not match the frozen Gate 0 schema.",
          details: {
            fields: validateBody[model].errors.map((error) => ({
              path: error.instancePath,
              reason: error.keyword,
            })),
          },
        });
        return;
      }
      if (path === "/__fixture/reset" && req.method === "POST") {
        reset(body);
        send(200, { fixture_mock: true, scenario: state.scenario });
        return;
      }
      if (path === "/__fixture/state") {
        send(200, {
          scenario: state.scenario,
          wakeRequests: state.wakeRequests,
          status: state.draft.status,
        });
        return;
      }
      if (path === "/me") {
        send(200, {
          user_id: `FIXTURE_${role}`,
          display_name: `Fixture ${role.toLowerCase()}`,
          tenant: { id: "T1", name: "Fixture workspace" },
          role,
          permissions:
            role === "WAREHOUSE"
              ? []
              : role === "OWNER"
                ? [...permissions, "OWNER_APPROVE", "OWNER_REJECT"]
                : permissions,
          permission_summary:
            "Synthetic fixture session. No real backend, AI or customer data.",
        });
        return;
      }
      if (path === "/ai/status") {
        send(200, {
          state: "OFFLINE",
          available_modes: ["FALLBACK"],
          fallback_available: true,
          last_checked_at: "2026-10-22T00:00:00Z",
          message: "Fixture mock: no AI service is called.",
        });
        return;
      }
      if (path === "/ai/wake" && req.method === "POST") {
        if (role === "WAREHOUSE") {
          fail("FORBIDDEN_ACTION");
          return;
        }
        state.wakeRequests++;
        if (state.wakeDelayMs)
          await new Promise((done) => setTimeout(done, state.wakeDelayMs));
        send(200, {
          state: "OFFLINE",
          accepted: false,
          fallback_available: true,
          last_checked_at: "2026-10-22T00:00:00Z",
          message: "Fixture wake recorded. No model was started.",
        });
        return;
      }
      if (role === "WAREHOUSE") {
        if (
          path.startsWith("/warehouse/delivery-orders/") &&
          req.method === "GET"
        )
          send(200, fixtures.warehouse_delivery_order.body);
        else fail("FORBIDDEN_ACTION");
        return;
      }
      if (path === "/customers") {
        send(200, fixtures.customers_list.body);
        return;
      }
      if (path === "/activity") {
        send(200, { items: [], next_cursor: null });
        return;
      }
      if (path === "/orders/drafts") {
        const d = state.draft;
        send(200, {
          items: [
            {
              draft_id: d.draft_id,
              version: d.version,
              status: d.status,
              customer_id: d.customer_id,
              customer_name: d.customer.name,
              message_preview: d.masked_message,
              blocking_issues: d.blocking_issues,
              open_blocking_issue_count: d.blocking_issues.length,
              owner_escalation_count: d.escalation_preview.length,
              extraction_sources: ["RAPIDFUZZ_FALLBACK"],
              allowed_actions: d.allowed_actions,
              updated_at: d.updated_at,
              do_number: d.do_number,
            },
          ],
          next_cursor: null,
        });
        return;
      }
      if (path === "/orders/parse-draft" && req.method === "POST") {
        send(200, state.draft);
        return;
      }
      if (
        /^\/orders\/drafts\/[^/]+\/lines$/.test(path) &&
        req.method === "PUT"
      ) {
        if (state.draft.status === "PENDING_OWNER_APPROVAL") {
          fail("PENDING_OWNER_APPROVAL");
          return;
        }
        const error = state.error && fixtures.error_catalog[state.error];
        if (error) {
          send(error.status, error.body);
          return;
        }
        state.draft = clone(
          fixtures[
            state.saveResult === "stock"
              ? "save_lines_insufficient_stock_200"
              : "save_lines_ready"
          ].body,
        );
        send(200, state.draft);
        return;
      }
      if (/^\/orders\/drafts\/[^/]+$/.test(path)) {
        send(200, state.draft);
        return;
      }
      if (path === "/approvals") {
        const a = {
          ...state.approval,
          allowed_actions:
            role === "OWNER" && state.approval.status === "PENDING"
              ? ["OWNER_APPROVE", "OWNER_REJECT"]
              : [],
        };
        send(200, { items: [a], next_cursor: null });
        return;
      }
      if (/^\/approvals\/[^/]+\/decide$/.test(path) && req.method === "POST") {
        if (role !== "OWNER") {
          fail("FORBIDDEN_ACTION");
          return;
        }
        if (body.decision === "REJECT") {
          if (!body.note?.trim()) {
            fail("REJECTION_REASON_REQUIRED");
            return;
          }
          state.approval = {
            ...state.approval,
            status: "REJECTED",
            decision_note: body.note.trim(),
            decided_by: "FIXTURE_OWNER",
            decided_at: "2026-10-22T00:00:00Z",
            allowed_actions: [],
          };
          lock("REJECTED");
          send(200, {
            ...fixtures.decide_rejected.body,
            approval_id: state.approval.approval_id,
            draft_id: state.draft.draft_id,
            decision_note: body.note.trim(),
          });
          return;
        }
        if (state.error === "STOCK_CHANGED") {
          send(409, fixtures.approve_stock_changed_409.body);
          return;
        }
        state.approval.status = "APPROVED";
        state.approval.allowed_actions = [];
        state.delivery = clone(fixtures.approve_200.body);
        state.draft.do_number = state.delivery.do_number;
        lock("DO_GENERATED");
        send(200, state.delivery);
        return;
      }
      if (/^\/approvals\/[^/]+$/.test(path)) {
        send(200, {
          ...state.approval,
          allowed_actions:
            role === "OWNER" && state.approval.status === "PENDING"
              ? ["OWNER_APPROVE", "OWNER_REJECT"]
              : [],
        });
        return;
      }
      if (/^\/orders\/[^/]+\/approve$/.test(path) && req.method === "POST") {
        if (state.error && fixtures.error_catalog[state.error]) {
          const f =
            state.error === "STOCK_CHANGED"
              ? fixtures.approve_stock_changed_409
              : fixtures.error_catalog[state.error];
          send(f.status, f.body);
          return;
        }
        if (state.draft.blocking_issues.length) {
          fail("DISAMBIGUATION_UNRESOLVED");
          return;
        }
        if (role === "CLERK" && state.scenario === "price") {
          state.approval.draft_id = state.draft.draft_id;
          state.approval.draft_version = state.draft.version;
          lock("PENDING_OWNER_APPROVAL");
          send(202, {
            ...fixtures.approve_202.body,
            draft_id: state.draft.draft_id,
          });
          return;
        }
        state.delivery = clone(fixtures.approve_200.body);
        state.draft.do_number = state.delivery.do_number;
        lock("DO_GENERATED");
        send(200, state.delivery);
        return;
      }
      if (/^\/delivery-orders\/[^/]+$/.test(path)) {
        send(200, state.delivery ?? fixtures.approve_200.body);
        return;
      }
      if (/^\/orders\/[^/]+\/audit-detail$/.test(path)) {
        send(200, (await fixture("audit_detail")).body);
        return;
      }
      fail("RESOURCE_NOT_FOUND");
    } catch {
      send(400, {
        error_code: "FIXTURE_BAD_REQUEST",
        message: "Invalid local fixture control request.",
        details: {},
      });
    }
  });
  return server;
}

if (
  process.argv[1] &&
  fileURLToPath(import.meta.url) === resolve(process.argv[1])
) {
  const port = Number(process.env.KIRA_FIXTURE_PORT ?? 4191);
  createFixtureApi().listen(port, "127.0.0.1", () =>
    console.log(
      `Fixture mock only: http://127.0.0.1:${port}/api/v1\nSynthetic tokens: fixture-clerk / fixture-owner / fixture-warehouse\nNo real backend, AI, messaging or inventory service is called.`,
    ),
  );
}
