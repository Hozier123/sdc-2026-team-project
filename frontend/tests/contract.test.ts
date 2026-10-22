import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const root = process.cwd();
const schema = JSON.parse(
  fs.readFileSync(path.join(root, "contracts/gate0.openapi.json"), "utf8"),
);
const ajv = new Ajv2020({
  strict: false,
  allErrors: true,
  validateFormats: true,
});
addFormats(ajv);
ajv.addSchema(schema, "gate0");
const check = (model: string, value: unknown) => {
  const validate = ajv.compile({ $ref: `gate0#/components/schemas/${model}` });
  assert.ok(validate(value), `${model}: ${ajv.errorsText(validate.errors)}`);
};
const load = (name: string) =>
  JSON.parse(
    fs.readFileSync(path.join(root, `tests/fixtures/${name}.json`), "utf8"),
  );

test("frozen contract snapshot and imported fixtures keep their recorded hashes", () => {
  const provenance = JSON.parse(
    fs.readFileSync(path.join(root, "contracts/provenance.json"), "utf8"),
  );
  const sha = (file: string) =>
    crypto
      .createHash("sha256")
      .update(fs.readFileSync(path.join(root, file)))
      .digest("hex");
  assert.equal(sha("contracts/gate0.openapi.json"), provenance.snapshot_sha256);
  for (const [file, expected] of Object.entries(provenance.fixtures_sha256))
    assert.equal(sha(`tests/fixtures/${file}`), expected, file);
});

const responses: Record<string, string> = {
  parse_draft: "OrderDraft",
  save_lines_ready: "OrderDraft",
  save_lines_insufficient_stock_200: "OrderDraft",
  approve_200: "DeliveryOrder",
  approve_202: "ApprovalRequest",
  approval_detail: "ApprovalDetail",
  decide_rejected: "ApprovalDecisionResult",
  warehouse_delivery_order: "WarehouseDeliveryOrder",
  customers_list: "CustomerListResponse",
  audit_detail: "AuditDetail",
  already_approved_409: "Error",
  approve_stock_changed_409: "Error",
  save_lines_target_required: "Error",
  save_lines_price_mismatch_422: "Error",
};
for (const [file, model] of Object.entries(responses))
  test(`Gate 0 ${file} satisfies ${model}`, () => {
    const fixture = load(file);
    check(model, fixture.body);
    assert.ok(fixture.headers["X-Request-ID"]);
  });

test("the full error catalogue is valid, including canonical authentication codes", () => {
  for (const [code, fixture] of Object.entries(load("error_catalog")) as [
    string,
    any,
  ][]) {
    check("Error", fixture.body);
    assert.equal(fixture.body.error_code, code);
  }
});

test("warehouse contract rejects leaked prices, contacts, original text and AI differences", () => {
  const validate = ajv.compile({
    $ref: "gate0#/components/schemas/WarehouseDeliveryOrder",
  });
  const fixture = load("warehouse_delivery_order").body;
  for (const field of [
    "final_total_rm",
    "phone_e164",
    "masked_message",
    "field_diffs",
  ])
    assert.equal(
      validate({ ...fixture, [field]: "must not leak" }),
      false,
      field,
    );
  assert.equal(
    validate({
      ...fixture,
      items: [{ ...fixture.items[0], tier_unit_price: "1.00" }],
    }),
    false,
  );
});

test("the contract prevents old states, decimal quantities and caller-written prices", () => {
  const validate = (model: string, value: unknown) =>
    ajv.compile({ $ref: `gate0#/components/schemas/${model}` })(value);
  assert.equal(validate("DraftStatus", "APPROVED"), false);
  const valid = {
    line_id: "LIN_001",
    sku_id: "SKU_FLOUR_5KG_A",
    confirmed_qty: 3,
    match_source: "MANUAL_SELECTED",
  };
  assert.equal(validate("WorkingLineInput", valid), true);
  for (const qty of [0, -1, 1.5])
    assert.equal(
      validate("WorkingLineInput", { ...valid, confirmed_qty: qty }),
      false,
    );
  assert.equal(
    validate("WorkingLineInput", { ...valid, tier_unit_price: "0.01" }),
    false,
  );
});
