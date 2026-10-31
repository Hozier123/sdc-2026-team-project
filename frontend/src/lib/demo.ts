import {
  ApiError,
  toInput,
  type Action,
  type Activity,
  type AiStatus,
  type Alias,
  type Approval,
  type Audit,
  type Candidate,
  type Customer,
  type DeliveryOrder,
  type Draft,
  type DraftSummary,
  type FieldDiff,
  type Issue,
  type Line,
  type LineInput,
  type Me,
  type Reason,
  type Role,
  type SaveRequest,
  type Service,
  type WarehouseOrder,
} from "./types";
import type { CatalogProductsResponse } from "./catalog";

// The local demo is a separate service, never used to authorize a live API request.
export const DEMO_CUSTOMERS: Customer[] = [
  {
    customer_id: "CUS_001",
    name: "Restoran Ali",
    tier: "A",
    credit_flag: "NONE",
    has_credit_notice: false,
  },
  {
    customer_id: "CUS_002",
    name: "Kedai Mesra",
    tier: "B",
    credit_flag: "OVERDUE_NOTICE",
    has_credit_notice: true,
  },
  {
    customer_id: "CUS_003",
    name: "Maju Mini Market",
    tier: "A",
    credit_flag: "NONE",
    has_credit_notice: false,
  },
  {
    customer_id: "CUS_004",
    name: "Warung Seri Pagi",
    tier: "B",
    credit_flag: "NONE",
    has_credit_notice: false,
  },
];
export const CATALOG: Candidate[] = [
  {
    sku_id: "SKU_FLOUR",
    family_id: "FAM_FLOUR",
    display_name: "Tepung · Wheat flour",
    pack_size: "5kg",
    grade: "A",
    base_unit: "ctn",
    tier_unit_price: "98.00",
    available_qty: 24,
  },
  {
    sku_id: "SKU_OIL",
    family_id: "FAM_OIL",
    display_name: "Minyak · Cooking oil",
    pack_size: "5L × 4",
    base_unit: "ctn",
    tier_unit_price: "86.00",
    available_qty: 18,
  },
  {
    sku_id: "SKU_MILO_1",
    family_id: "FAM_MILO",
    display_name: "Milo · Chocolate malt",
    pack_size: "1kg",
    base_unit: "pkt",
    tier_unit_price: "23.00",
    available_qty: 40,
  },
  {
    sku_id: "SKU_MILO_2",
    family_id: "FAM_MILO",
    display_name: "Milo · Chocolate malt",
    pack_size: "2kg",
    base_unit: "pkt",
    tier_unit_price: "42.00",
    available_qty: 20,
  },
  {
    sku_id: "SKU_CHICKEN",
    family_id: "FAM_CHICKEN",
    display_name: "Ayam A1 · Frozen chicken",
    pack_size: "10kg",
    grade: "A1",
    base_unit: "ctn",
    tier_unit_price: "112.00",
    available_qty: 3,
  },
  {
    sku_id: "SKU_EGG_A",
    family_id: "FAM_EGG",
    display_name: "Telur · Fresh eggs",
    pack_size: "30 eggs",
    grade: "A",
    base_unit: "tray",
    tier_unit_price: "13.50",
    available_qty: 60,
  },
  {
    sku_id: "SKU_EGG_B",
    family_id: "FAM_EGG",
    display_name: "Telur · Fresh eggs",
    pack_size: "30 eggs",
    grade: "B",
    base_unit: "tray",
    tier_unit_price: "11.80",
    available_qty: 50,
  },
];
const HARDWARE: Candidate[] = [
  {
    sku_id: "SKU_SCREW",
    family_id: "FAM_SCREW",
    display_name: "Skru · Wood screws",
    pack_size: "4mm × 100",
    base_unit: "box",
    tier_unit_price: "18.50",
    available_qty: 50,
  },
  {
    sku_id: "SKU_TAPE",
    family_id: "FAM_TAPE",
    display_name: "Tape · Packing tape",
    pack_size: "48mm",
    base_unit: "roll",
    tier_unit_price: "4.50",
    available_qty: 90,
  },
];
const clone = <T>(v: T): T => structuredClone(v);
const now = () => new Date().toISOString();
const id = (prefix: string) =>
  `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 12).toUpperCase()}`;
export function maskPII(text: string) {
  return text
    .replace(/\b\d{6}[- ]?\d{2}[- ]?\d{4}\b/g, "[REDACTED_ID]")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[REDACTED_EMAIL]")
    .replace(/(?:\+?60[\s-]?|0)1\d(?:[\s-]?\d){7,8}\b/g, "[REDACTED_PHONE]");
}
export function cents(value: string): bigint {
  if (!/^\d{1,8}(?:\.\d{1,2})?$/.test(value))
    throw new ApiError(
      "REQUEST_VALIDATION_FAILED",
      "Enter a positive price with up to two decimal places.",
    );
  const [a, b = ""] = value.split(".");
  return BigInt(a) * 100n + BigInt(b.padEnd(2, "0"));
}
export const decimal = (v: bigint) =>
  `${v / 100n}.${(v % 100n).toString().padStart(2, "0")}`;
interface State {
  drafts: Draft[];
  approvals: Approval[];
  deliveries: DeliveryOrder[];
  activity: Activity[];
  stock: Record<string, number>;
  aliases: { customer: string; alias: Alias }[];
  initial: Record<string, Line[]>;
  diffs: Record<string, FieldDiff[]>;
}
export interface Persistence {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}
const PERMISSIONS: Action[] = [
  "EDIT_DRAFT",
  "RESOLVE_ISSUE",
  "COPY_CLARIFICATION",
  "APPROVE_AND_GENERATE_DO",
  "SUBMIT_FOR_OWNER",
  "VIEW_ACTIVITY",
  "WAKE_AI",
  "CANCEL_DRAFT",
];
export class DemoService implements Service {
  readonly mode = "demo" as const;
  private state: State;
  private storage?: Persistence;
  private role: Role;
  readonly tenant: string;
  constructor(role: Role = "CLERK", tenant = "T1", storage?: Persistence) {
    this.role = role;
    this.tenant = tenant;
    this.storage = storage;
    const saved = storage?.getItem(`kiraorder.demo.v1.${tenant}`);
    try {
      this.state = saved ? JSON.parse(saved) : this.blank();
      if (!this.state.initial) throw Error();
    } catch {
      this.state = this.blank();
    }
    if (!saved) {
      this.seed();
      this.persist();
    }
  }
  private blank(): State {
    return {
      drafts: [],
      approvals: [],
      deliveries: [],
      activity: [],
      stock: Object.fromEntries(
        this.catalog().map((s) => [s.sku_id, s.available_qty]),
      ),
      aliases: [],
      initial: {},
      diffs: {},
    };
  }
  private sync() {
    const saved = this.storage?.getItem(`kiraorder.demo.v1.${this.tenant}`);
    if (saved) {
      try {
        this.state = JSON.parse(saved);
      } catch {
        throw new ApiError(
          "LOCAL_DATA_INVALID",
          "Saved demo data is not readable. Export or clear the demo storage before continuing.",
        );
      }
    }
  }
  private persist() {
    try {
      this.storage?.setItem(
        `kiraorder.demo.v1.${this.tenant}`,
        JSON.stringify(this.state),
      );
    } catch {
      throw new ApiError(
        "LOCAL_STORAGE_UNAVAILABLE",
        "The browser could not save this demo. Free some local storage and retry.",
      );
    }
  }
  private catalog() {
    return this.tenant === "T2" ? HARDWARE : CATALOG;
  }
  async catalogProducts(): Promise<CatalogProductsResponse> {
    this.require(["CLERK", "OWNER"]);
    return {
      items: this.catalog().slice(0, 100).map((product) => ({
        sku_id: product.sku_id,
        display_name: product.display_name,
        pack_size: product.pack_size ?? null,
        grade: product.grade ?? null,
        base_unit: product.base_unit,
      })),
      limit: 100,
      truncated: this.catalog().length > 100,
    };
  }
  private customersForTenant() {
    return this.tenant === "T2"
      ? DEMO_CUSTOMERS.map((c, i) => ({
          ...c,
          customer_id: `HW_${i + 1}`,
          name: [
            "Bina Hardware",
            "Mesra Supplies",
            "Maju Workshop",
            "Seri Tools",
          ][i],
        }))
      : DEMO_CUSTOMERS;
  }
  private user() {
    return this.role === "CLERK"
      ? "Siti"
      : this.role === "OWNER"
        ? "Boss Tan"
        : "Ah Kow";
  }
  private require(roles: Role[]) {
    if (!roles.includes(this.role))
      throw new ApiError(
        "FORBIDDEN",
        "Your current role cannot perform this action.",
      );
  }
  private get(id: string) {
    const d = this.state.drafts.find((d) => d.draft_id === id);
    if (!d)
      throw new ApiError(
        "NOT_FOUND",
        "This order is not available in this workspace.",
      );
    return d;
  }
  private event(
    entity: string,
    action: string,
    detail: string,
    actor = this.user(),
  ) {
    this.state.activity.unshift({
      activity_id: id("ACT"),
      entity_id: entity,
      action,
      actor,
      created_at: now(),
      detail: maskPII(detail),
    });
  }
  private projected(d: Draft): Draft {
    const result = clone(d);
    result.allowed_actions = this.actions(d);
    return result;
  }
  private currentDraft(d: Draft): Draft {
    const result = this.projected(d);
    if (
      ["DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"].includes(result.status)
    )
      this.recalc(result);
    return result;
  }
  private actions(d: Draft): Action[] {
    if (this.role === "WAREHOUSE") return [];
    const base: Action[] = ["VIEW_ACTIVITY"];
    if (["DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"].includes(d.status)) {
      base.push("EDIT_DRAFT", "RESOLVE_ISSUE", "CANCEL_DRAFT");
      if (d.clarification_draft) base.push("COPY_CLARIFICATION");
      if (!d.blocking_issues.length)
        base.push(
          this.role === "OWNER" || !d.escalation_preview.length
            ? "APPROVE_AND_GENERATE_DO"
            : "SUBMIT_FOR_OWNER",
        );
    }
    return base;
  }
  private candidate(s: Candidate, c: Customer) {
    return {
      ...s,
      available_qty: this.state.stock[s.sku_id],
      tier_unit_price: decimal(
        cents(s.tier_unit_price) + (c.tier === "B" ? 200n : 0n),
      ),
    };
  }
  private fill(l: Line, s: Candidate, c: Customer) {
    const p = this.candidate(s, c);
    Object.assign(l, {
      sku_id: s.sku_id,
      family_id: s.family_id,
      description: s.display_name,
      pack_size: s.pack_size,
      grade: s.grade ?? null,
      tier_unit_price: p.tier_unit_price,
      available_qty: p.available_qty,
      candidate_skus: [],
    });
  }
  private issue(
    d: Draft,
    code: string,
    line: Line | null,
    kind?: Issue["condition_kind"],
  ): Issue {
    return {
      issue_id: `ISS_${line?.line_id ?? d.draft_id}_${kind ?? code}`,
      code,
      line_id: line?.line_id ?? null,
      span: line?.source_span ?? d.masked_message,
      candidate_line_ids: line ? [line.line_id] : d.lines.map((l) => l.line_id),
      target_line_ids: [],
      condition_kind: kind ?? null,
      ask:
        kind === "STOCK"
          ? "SYSTEM"
          : kind === "PRICE" || kind === "OTHER"
            ? "CLERK"
            : "CUSTOMER",
      data_used: {},
      blocking: kind !== "STOCK",
      resolved: false,
    };
  }
  private recalc(d: Draft) {
    let total = 0n;
    const derived: Issue[] = [];
    const requested: Record<string, number> = {};
    for (const l of d.lines) {
      l.effective_qty = l.confirmed_qty ?? l.requested_qty;
      if (l.sku_id) {
        const sku = this.catalog().find((s) => s.sku_id === l.sku_id);
        if (!sku) throw new ApiError("NOT_FOUND", "Product not found.");
        this.fill(l, sku, d.customer);
        l.effective_unit_price = l.unit_price_override ?? l.tier_unit_price;
        l.subtotal_rm = decimal(
          cents(l.effective_unit_price!) * BigInt(l.effective_qty),
        );
        total += cents(l.subtotal_rm);
        requested[l.sku_id] = (requested[l.sku_id] ?? 0) + l.effective_qty;
      } else {
        l.subtotal_rm = null;
        l.effective_unit_price = null;
        const kind =
          l.family_id === "FAM_MILO"
            ? "MULTIPLE_PACK_SIZES"
            : l.family_id === "FAM_EGG"
              ? "MULTIPLE_GRADES"
              : "LOW_CONFIDENCE_MATCH";
        const issue = this.issue(d, kind, l);
        issue.data_used = { candidates: l.candidate_skus.length };
        derived.push(issue);
      }
      if (!l.uom) derived.push(this.issue(d, "MISSING_UOM", l));
    }
    for (const l of d.lines) {
      if (l.sku_id && requested[l.sku_id] > (this.state.stock[l.sku_id] ?? 0)) {
        const iss = this.issue(d, "INSUFFICIENT_STOCK", l);
        iss.data_used = {
          effective_qty: l.effective_qty,
          available_qty: l.available_qty,
          combined_qty: requested[l.sku_id],
        };
        derived.push(iss);
      }
    }
    const conditions = d.issues.filter((i) => i.code === "CUSTOMER_CONDITION");
    for (const cond of conditions) {
      if (cond.condition_kind === "STOCK") {
        cond.resolved = !derived.some((i) => i.code === "INSUFFICIENT_STOCK");
        cond.blocking = false;
        cond.auto_resolved_by = cond.resolved ? "STOCK_CHECK" : null;
        cond.data_used = { stock_sufficient: cond.resolved };
      } else if (
        cond.resolved &&
        cond.resolution === "ACCEPT_REQUESTED_PRICE"
      ) {
        const targets = cond.target_line_ids.map((t) =>
          d.lines.find((l) => l.line_id === t),
        );
        cond.resolved =
          targets.length > 0 &&
          targets.every(
            (l) =>
              !!l &&
              l.unit_price_override != null &&
              l.tier_unit_price != null &&
              cents(l.unit_price_override) < cents(l.tier_unit_price) &&
              !!l.override_reason?.trim(),
          );
      }
    }
    d.issues = [...derived, ...conditions];
    d.conditions = conditions;
    d.blocking_issues = [
      ...new Set(
        d.issues.filter((i) => i.blocking && !i.resolved).map((i) => i.code),
      ),
    ];
    d.totals = {
      order_total: decimal(total),
      currency: "MYR",
      is_complete: d.lines.every((l) => !!l.sku_id),
    };
    const reasons: Reason[] = d.lines
      .filter(
        (l) =>
          l.unit_price_override != null &&
          l.tier_unit_price != null &&
          cents(l.unit_price_override) < cents(l.tier_unit_price),
      )
      .map((l) => ({
        code: "PRICE_OVERRIDE_BELOW_TIER",
        line_id: l.line_id,
        detail: {
          tier_price: l.tier_unit_price,
          applied_price: l.unit_price_override,
        },
      }));
    if (total >= BigInt(this.tenant === "T2" ? 80000 : 150000))
      reasons.push({
        code: "AMOUNT_OVER_THRESHOLD",
        line_id: null,
        detail: {
          threshold_rm: this.tenant === "T2" ? "800.00" : "1500.00",
          total_rm: decimal(total),
        },
      });
    if (d.customer.credit_flag === "OVERDUE_NOTICE")
      reasons.push({
        code: "CUSTOMER_CREDIT_FLAG",
        line_id: null,
        detail: { customer: d.customer.name },
      });
    d.escalation_preview = reasons;
    if (["DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"].includes(d.status))
      d.status = d.blocking_issues.length
        ? "DISAMBIGUATION_REQUIRED"
        : "READY_FOR_APPROVAL";
    const unresolved = d.issues.filter((i) => i.blocking && !i.resolved);
    const lang = d.clarification_lang ?? "en";
    const questions = unresolved.map((i) => {
      const line = d.lines.find((l) => l.line_id === i.line_id);
      if (i.code === "MULTIPLE_PACK_SIZES")
        return lang === "ms"
          ? "Milo nak 1kg atau 2kg?"
          : lang === "zh"
            ? "请问美禄需要 1kg 还是 2kg？"
            : "Would you like Milo in 1kg or 2kg packs?";
      if (i.code === "MULTIPLE_GRADES")
        return lang === "ms"
          ? "Telur nak gred A atau B?"
          : lang === "zh"
            ? "请问鸡蛋需要 A 级还是 B 级？"
            : "Would you like grade A or B eggs?";
      if (i.code === "INSUFFICIENT_STOCK")
        return lang === "ms"
          ? `${line?.description}: stok tinggal ${line?.available_qty} ${line?.uom}. Boleh kurangkan kuantiti?`
          : lang === "zh"
            ? `${line?.description} 库存剩 ${line?.available_qty} ${line?.uom}，可以减少数量吗？`
            : `We have ${line?.available_qty} ${line?.uom} of ${line?.description}. Would a smaller quantity work?`;
      if (i.condition_kind === "PRICE")
        return lang === "ms"
          ? "Boleh sahkan harga seunit dan barang yang dimaksudkan?"
          : lang === "zh"
            ? "请确认议价对应的商品及每单位价格。"
            : "Please confirm which item the requested unit price applies to.";
      if (i.condition_kind)
        return lang === "ms"
          ? "Boleh sahkan syarat penghantaran?"
          : lang === "zh"
            ? "请确认送货条件。"
            : "Could you confirm the delivery condition?";
      return lang === "ms"
        ? `Boleh sahkan barang dan unit untuk “${i.span}”?`
        : lang === "zh"
          ? `请确认“${i.span}”的商品和单位。`
          : `Could you clarify the product and unit for “${i.span}”?`;
    });
    d.clarification_draft = questions.length
      ? {
          language: lang,
          message: [...new Set(questions)].join("\n"),
          unresolved_issue_ids: unresolved.map((i) => i.issue_id),
        }
      : null;
    d.allowed_actions = this.actions(d);
    d.blocked_actions = d.blocking_issues.length
      ? {
          APPROVE_AND_GENERATE_DO: d.blocking_issues,
          SUBMIT_FOR_OWNER: d.blocking_issues,
        }
      : {};
  }
  private create(customerId: string, text: string, lang: string): Draft {
    const customer = this.customersForTenant().find(
      (c) => c.customer_id === customerId,
    );
    if (!customer)
      throw new ApiError("NOT_FOUND", "Choose a customer in this workspace.");
    const message = maskPII(text.trim());
    if (!message || text.length > 4000)
      throw new ApiError(
        "REQUEST_VALIDATION_FAILED",
        "Use a message between 1 and 4,000 characters.",
      );
    const d: Draft = {
      draft_id: id("DRF"),
      version: 1,
      status: "DISAMBIGUATION_REQUIRED",
      do_number: null,
      customer_id: customerId,
      customer: clone(customer),
      masked_message: message,
      ai_mode: "FALLBACK",
      lines: [],
      issues: [],
      conditions: [],
      blocking_issues: [],
      escalation_preview: [],
      totals: { order_total: "0.00", currency: "MYR", is_complete: false },
      allowed_actions: [],
      blocked_actions: {},
      clarification_draft: null,
      clarification_lang:
        lang === "auto"
          ? /[\u4e00-\u9fff]/.test(message)
            ? "zh"
            : /\b(kalau|nak|ctn|ayam|tepung)\b/i.test(message)
              ? "ms"
              : "en"
          : lang,
      ignored_spans: [],
      termination_reason: null,
      termination_note: null,
      created_at: now(),
      updated_at: now(),
    };
    const families: [string, RegExp][] = [
      ["FAM_FLOUR", /tepung|flour|面粉/i],
      ["FAM_OIL", /minyak|cooking oil|食用油/i],
      ["FAM_MILO", /milo|美禄|美祿/i],
      ["FAM_CHICKEN", /ayam|chicken|鸡肉|雞肉/i],
      ["FAM_EGG", /telur|eggs?|鸡蛋|雞蛋/i],
      ["FAM_SCREW", /skru|screws?|螺丝/i],
      ["FAM_TAPE", /tape|胶带/i],
    ];
    for (const raw of message.split(/[\n;；]+/).filter((s) => s.trim())) {
      const span = raw.trim();
      let found = families.filter(
        ([f, r]) =>
          r.test(span) && this.catalog().some((c) => c.family_id === f),
      );
      const family = found.length === 1 ? found[0][0] : "UNKNOWN";
      let candidates = this.catalog().filter((s) => s.family_id === family);
      const size = span
        .match(/\b(1|2)\s?kg\b/i)?.[0]
        .replace(/\s/g, "")
        .toLowerCase();
      if (size)
        candidates = candidates.filter(
          (s) => s.pack_size.toLowerCase() === size || family !== "FAM_MILO",
        );
      const grade = span.match(/(?:grade|gred|级)\s*([ab])|telur\s+([ab])\b/i);
      if (grade && family === "FAM_EGG")
        candidates = candidates.filter(
          (s) => s.grade === (grade[1] ?? grade[2]).toUpperCase(),
        );
      const qtyMatch =
        span.match(
          /(\d+)\s*(ctn|cartons?|pkt|packets?|packs?|tray|papan|box|roll|包|箱|盘|盒|卷)/i,
        ) ?? span.match(/(?:^|\s)(\d+)(?:\s|$)/);
      let qty = qtyMatch ? Number(qtyMatch[1]) : 1;
      if (!Number.isSafeInteger(qty) || qty < 1 || qty > 100000)
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Quantity must be a whole number from 1 to 100,000.",
        );
      const rawUnit = qtyMatch?.[2]?.toLowerCase();
      const units: Record<string, string> = {
        ctn: "ctn",
        carton: "ctn",
        cartons: "ctn",
        箱: "ctn",
        pkt: "pkt",
        packet: "pkt",
        packets: "pkt",
        pack: "pkt",
        packs: "pkt",
        包: "pkt",
        tray: "tray",
        papan: "tray",
        盘: "tray",
        box: "box",
        盒: "box",
        roll: "roll",
        卷: "roll",
      };
      const start = Array.from(message.slice(0, message.indexOf(span))).length;
      const l: Line = {
        line_id: id("LIN"),
        sku_id: null,
        family_id: family,
        description:
          family === "UNKNOWN"
            ? "Unrecognized item"
            : (candidates[0]?.display_name ?? "Choose product"),
        requested_qty: qty,
        confirmed_qty: null,
        effective_qty: qty,
        uom: rawUnit ? (units[rawUnit] ?? null) : null,
        pack_size: null,
        grade: null,
        tier_unit_price: null,
        unit_price_override: null,
        override_reason: null,
        effective_unit_price: null,
        subtotal_rm: null,
        match_source: "RAPIDFUZZ_FALLBACK",
        source_span: span,
        span_start: start,
        span_end: start + Array.from(span).length,
        field_evidence: [],
        candidate_skus: (candidates.length ? candidates : this.catalog()).map(
          (s) => this.candidate(s, customer),
        ),
        available_qty: null,
        saved_alias: null,
      };
      const remembered = this.state.aliases.find(
        (a) =>
          a.customer === customerId &&
          a.alias.active &&
          a.alias.phrase === span,
      );
      if (remembered) {
        const sku = this.catalog().find(
          (s) => s.sku_id === remembered.alias.product_id,
        );
        if (sku) {
          this.fill(l, sku, customer);
          l.match_source = "SUGGESTED_DEFAULT";
          l.saved_alias = clone(remembered.alias);
        }
      } else if (candidates.length === 1 && qtyMatch) {
        this.fill(l, candidates[0], customer);
      }
      if (!qtyMatch) {
        l.sku_id = null;
        l.description = "Confirm quantity and product";
        l.family_id = "UNKNOWN";
        l.candidate_skus = this.catalog().map((s) =>
          this.candidate(s, customer),
        );
      }
      d.lines.push(l);
    }
    if (!d.lines.length)
      throw new ApiError("EMPTY_ORDER", "Add at least one order line.");
    for (const span of message.split(/[\n;；]+/)) {
      const marked =
        /kalau|kalo|\bklu\b|\bif\b|如果|的话|便宜|kurang|diskaun|discount|harga lama/i.test(
          span,
        );
      if (!marked) continue;
      const kind: Issue["condition_kind"] =
        /RM\s?\d|kurang|murah|便宜|discount|harga lama/i.test(span)
          ? "PRICE"
          : /\bada\b|stok|stock|有货|没有就算了/i.test(span)
            ? "STOCK"
            : "OTHER";
      const cond = this.issue(d, "CUSTOMER_CONDITION", null, kind);
      cond.issue_id = id("ISS");
      cond.condition_id = `CND_${crypto.randomUUID().replaceAll("-", "").slice(0, 24).toUpperCase()}`;
      cond.span = span.trim();
      const target = d.lines.filter((l) => l.source_span === span.trim());
      cond.candidate_line_ids =
        target.length === 1
          ? target.map((l) => l.line_id)
          : d.lines.map((l) => l.line_id);
      cond.condition_scope =
        cond.candidate_line_ids.length === 1 ? "SINGLE_LINE" : "UNKNOWN";
      cond.price_basis = kind === "PRICE" ? "UNKNOWN" : null;
      cond.requested_unit_price = null;
      cond.data_used = {
        amount_text: span.match(/RM\s?\d+(?:\.\d+)?/i)?.[0] ?? null,
      };
      d.issues.push(cond);
    }
    d.ai_mode = d.lines.every((l) => l.match_source === "SUGGESTED_DEFAULT")
      ? "ALIAS_ONLY"
      : "FALLBACK";
    this.recalc(d);
    this.state.drafts.unshift(d);
    this.state.initial[d.draft_id] = clone(d.lines);
    this.state.diffs[d.draft_id] = [];
    this.event(
      d.draft_id,
      "DRAFT_PARSED",
      "Message masked and matched against the demo catalogue.",
    );
    return d;
  }
  private diff(d: Draft) {
    const before = this.state.initial[d.draft_id] ?? [];
    const fields = [
      "sku_id",
      "confirmed_qty",
      "unit_price_override",
      "override_reason",
      "uom",
    ] as const;
    this.state.diffs[d.draft_id] = d.lines.flatMap((l) =>
      fields
        .filter(
          (f) =>
            (before.find((b) => b.line_id === l.line_id)?.[f] ?? null) !==
            (l[f] ?? null),
        )
        .map((f) => ({
          line_id: l.line_id,
          field_path: f,
          before: before.find((b) => b.line_id === l.line_id)?.[f] ?? null,
          after: l[f],
          reason_code: l.override_reason ? "HUMAN_CONFIRMED" : "MANUAL_REVIEW",
        })),
    );
  }
  private finish(d: Draft, mode: DeliveryOrder["approval_mode"]) {
    this.recalc(d);
    if (d.totals.order_total === null)
      throw new ApiError(
        "DISAMBIGUATION_UNRESOLVED",
        "Confirm every product price before approval.",
      );
    if (d.blocking_issues.length)
      throw new ApiError(
        "STOCK_CHANGED",
        "Stock or order details changed. Refresh and review this order.",
        { issues: d.issues },
      );
    const number = `DO-${this.tenant}-${String(this.state.deliveries.length + 1).padStart(4, "0")}`;
    for (const l of d.lines) this.state.stock[l.sku_id!] -= l.effective_qty;
    const delivery: DeliveryOrder = {
      do_number: number,
      draft_id: d.draft_id,
      draft_version: d.version,
      customer_id: d.customer_id,
      customer_name: d.customer.name,
      lines: d.lines.map((l) => ({
        line_id: l.line_id,
        sku_id: l.sku_id!,
        display_name: `${l.description} · ${l.pack_size}${l.grade ? ` · ${l.grade}` : ""}`,
        quantity: l.effective_qty,
        unit: l.uom!,
        tier_unit_price: l.tier_unit_price!,
        applied_unit_price: l.effective_unit_price!,
        subtotal_rm: l.subtotal_rm!,
        override_reason: l.override_reason,
      })),
      final_total_rm: d.totals.order_total,
      prepared_by: "Siti",
      approved_by: this.user(),
      escalation_reasons: clone(d.escalation_preview),
      approval_mode: mode,
      reply_draft: {
        language: "en",
        message: `Your order ${number} is confirmed.\n${d.lines.map((l) => `${l.description}: ${l.effective_qty} ${l.uom}`).join("\n")}\nTotal: RM ${d.totals.order_total}. Thank you!`,
        do_number: number,
      },
      related_do_number: null,
      approved_at: now(),
    };
    d.status = "DO_GENERATED";
    d.do_number = number;
    d.updated_at = now();
    this.state.deliveries.unshift(delivery);
    this.event(
      d.draft_id,
      "DO_GENERATED",
      `${number} approved. Stock reserved and reply drafted.`,
    );
    return delivery;
  }
  private seed() {
    const customers = this.customersForTenant();
    if (this.tenant === "T2") {
      this.create(customers[0].customer_id, "Skru 12 box\nTape 8 roll", "en");
      return;
    }
    const complete = this.create(
      customers[2].customer_id,
      "Tepung 2 ctn\nMinyak 1 ctn",
      "en",
    );
    this.finish(complete, "DIRECT");
    const pending = this.create(customers[1].customer_id, "Tepung 5 ctn", "ms");
    this.submit(pending);
    this.create(
      customers[0].customer_id,
      "Boss, Milo 5 pkt\nTepung 3 ctn\nMinyak 2 ctn",
      "ms",
    );
    this.create(customers[3].customer_id, "Ayam A1 5 ctn, kalau ada", "ms");
    this.create(customers[2].customer_id, "Telur 10 tray", "en");
    this.create(customers[0].customer_id, "Tepung 4 ctn\nMinyak 2 ctn", "ms");
    this.create(
      customers[3].customer_id,
      "Tepung 5 ctn, kalau RM95 boleh?",
      "ms",
    );
    // Distribute synthetic initial timestamps for a readable queue.
    this.state.drafts.forEach((d, i) => {
      d.created_at = new Date(Date.now() - (i + 1) * 7 * 60000).toISOString();
      d.updated_at = d.created_at;
    });
  }
  private submit(d: Draft) {
    if (d.totals.order_total === null)
      throw new ApiError(
        "DISAMBIGUATION_UNRESOLVED",
        "Confirm every product price before submission.",
      );
    const a: Approval = {
      approval_id: id("APR"),
      draft_id: d.draft_id,
      draft_version: d.version,
      status: "PENDING",
      customer: clone(d.customer),
      total_rm: d.totals.order_total,
      line_count: d.lines.length,
      reasons: clone(d.escalation_preview),
      requested_by: "Siti",
      requested_at: now(),
      allowed_actions: [],
      snapshot: {
        customer_id: d.customer_id,
        customer_name: d.customer.name,
        masked_customer_text: d.masked_message,
        lines: clone(d.lines),
        total_rm: d.totals.order_total,
        reasons: clone(d.escalation_preview),
      },
      field_diffs: clone(this.state.diffs[d.draft_id] ?? []),
      stock_check: {
        lines: d.lines.map((l) => ({
          line_id: l.line_id,
          sku_id: l.sku_id!,
          requested_qty: l.requested_qty,
          effective_qty: l.effective_qty,
          available_qty: l.available_qty ?? 0,
          sufficient: (l.available_qty ?? 0) >= l.effective_qty,
        })),
      },
    };
    d.status = "PENDING_OWNER_APPROVAL";
    d.updated_at = now();
    this.state.approvals.unshift(a);
    this.event(
      d.draft_id,
      "OWNER_REQUESTED",
      "Submitted a saved version to the owner.",
    );
    return a;
  }
  private refreshApprovalStock(a: Approval) {
    if (a.stock_check) {
      const requested = new Map<string, number>();
      for (const l of a.stock_check.lines)
        requested.set(
          l.sku_id,
          (requested.get(l.sku_id) ?? 0) + l.effective_qty,
        );
      for (const l of a.stock_check.lines) {
        l.available_qty = this.state.stock[l.sku_id] ?? 0;
        l.sufficient = l.available_qty >= (requested.get(l.sku_id) ?? 0);
      }
    }
  }
  private approvalView(a: Approval) {
    const v = clone(a);
    v.allowed_actions =
      this.role === "OWNER" && a.status === "PENDING"
        ? ["OWNER_APPROVE", "OWNER_REJECT"]
        : [];
    if (v.status === "PENDING") this.refreshApprovalStock(v);
    return v;
  }
  async me(): Promise<Me> {
    return {
      user_id: this.user(),
      display_name: this.user(),
      tenant: {
        id: this.tenant,
        name: this.tenant === "T1" ? "Bintang Wholesale" : "Bina Hardware",
      },
      role: this.role,
      permissions:
        this.role === "WAREHOUSE"
          ? []
          : this.role === "OWNER"
            ? [...PERMISSIONS, "OWNER_APPROVE", "OWNER_REJECT"]
            : PERMISSIONS,
      permission_summary:
        this.role === "WAREHOUSE"
          ? "Read-only picking lists. Prices and customer contact details are excluded."
          : this.role === "OWNER"
            ? "Review, approve and audit all orders in this workspace."
            : "Prepare orders and approve routine orders. Exceptions go to the owner.",
    };
  }
  async customers() {
    this.require(["CLERK", "OWNER"]);
    return clone(this.customersForTenant());
  }
  async drafts(): Promise<DraftSummary[]> {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    return this.state.drafts.map((saved) => {
      const d = this.currentDraft(saved);
      return {
        draft_id: d.draft_id,
        version: d.version,
        status: d.status,
        do_number: d.do_number,
        customer_name: d.customer.name,
        message_preview: d.masked_message,
        open_blocking_issue_count: d.issues.filter(
          (i) => i.blocking && !i.resolved,
        ).length,
        owner_escalation_count: d.escalation_preview.length,
        extraction_sources: [...new Set(d.lines.map((l) => l.match_source))],
        allowed_actions: d.allowed_actions,
        created_at: d.created_at,
        updated_at: d.updated_at,
        order_total: d.totals.order_total,
      };
    });
  }
  async draft(id: string) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    return this.currentDraft(this.get(id));
  }
  async parse(customerId: string, text: string, lang: string) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    const d = this.create(customerId, text, lang);
    this.persist();
    return this.projected(d);
  }
  async save(draftId: string, req: SaveRequest) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    // The local demo has no zero-line recovery contract. Never simulate a live catalog save.
    const lines = req.lines.filter((line): line is LineInput => "line_id" in line);
    if (lines.length !== req.lines.length)
      throw new ApiError("NOT_SUPPORTED", "Manual line recovery requires the live API.");
    const original = this.get(draftId);
    if (original.version !== req.expected_version)
      throw new ApiError(
        "STALE_VERSION",
        "This order has a newer saved version. Refresh before continuing.",
      );
    if (
      !["DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"].includes(
        original.status,
      )
    )
      throw new ApiError(
        "ORDER_LOCKED",
        "This order is locked after submission.",
      );
    if (!lines.length)
      throw new ApiError(
        "EMPTY_ORDER",
        "Keep at least one product in the order.",
      );
    const ids = lines.map((l) => l.line_id),
      deleted = req.deleted_line_ids ?? [];
    if (
      new Set([...ids, ...deleted]).size !== ids.length + deleted.length ||
      original.lines.some(
        (l) => !ids.includes(l.line_id) && !deleted.includes(l.line_id),
      ) ||
      [...ids, ...deleted].some(
        (id) => !original.lines.some((l) => l.line_id === id),
      )
    )
      throw new ApiError(
        "REQUEST_VALIDATION_FAILED",
        "Every original line must be retained once or explicitly deleted.",
      );
    const d = clone(original);
    const aliasWrites: { customer: string; alias: Alias }[] = [];
    d.lines = d.lines.filter((l) => !deleted.includes(l.line_id));
    for (const l of d.lines) {
      const input = lines.find((i) => i.line_id === l.line_id)!;
      const allowed = [
        "line_id",
        "sku_id",
        "family_id",
        "confirmed_qty",
        "uom",
        "pack_size",
        "grade",
        "unit_price_override",
        "override_reason",
        "match_source",
        "save_to_alias_cache",
        "alias_scope",
      ];
      if (Object.keys(input).some((k) => !allowed.includes(k)))
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Read-only amounts and status cannot be submitted.",
        );
      if (
        input.confirmed_qty != null &&
        (!Number.isSafeInteger(input.confirmed_qty) ||
          input.confirmed_qty < 1 ||
          input.confirmed_qty > 100000)
      )
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Quantity must be a whole number from 1 to 100,000.",
        );
      if (
        input.sku_id &&
        !this.catalog().some((s) => s.sku_id === input.sku_id)
      )
        throw new ApiError(
          "NOT_FOUND",
          "Product not available in this tenant.",
        );
      if (
        input.uom &&
        !["ctn", "pkt", "tray", "box", "roll"].includes(input.uom)
      )
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Choose a catalogue unit.",
        );
      if (
        input.sku_id &&
        input.uom !==
          this.catalog().find((s) => s.sku_id === input.sku_id)?.base_unit
      )
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Use the catalogue unit; this demo does not convert units.",
        );
      if (
        input.unit_price_override != null &&
        (cents(input.unit_price_override) <= 0n ||
          !input.override_reason?.trim())
      )
        throw new ApiError(
          "OVERRIDE_REQUIRED",
          "A positive unit price and a reason are required.",
        );
      Object.assign(l, {
        sku_id: input.sku_id,
        confirmed_qty: input.confirmed_qty,
        uom: input.uom,
        pack_size: input.pack_size,
        grade: input.grade,
        unit_price_override: input.unit_price_override,
        override_reason: input.override_reason
          ? maskPII(input.override_reason.trim())
          : null,
        match_source: input.match_source,
      });
      if (!input.sku_id) {
        l.tier_unit_price = null;
        l.available_qty = null;
      }
      if (input.save_to_alias_cache) {
        if (input.alias_scope === "TENANT")
          throw new ApiError(
            "NOT_SUPPORTED",
            "Tenant-wide alias memory is outside this demo.",
          );
        if (!l.sku_id || input.match_source !== "MANUAL_SELECTED")
          throw new ApiError(
            "REQUEST_VALIDATION_FAILED",
            "Manually choose a product before remembering its phrase.",
          );
        const alias: Alias = {
          alias_id: id("ALS"),
          phrase: l.source_span,
          target_type: "SKU",
          product_id: l.sku_id,
          scope: "CUSTOMER",
          active: true,
          created_at: now(),
        };
        l.saved_alias = alias;
        aliasWrites.push({ customer: d.customer_id, alias });
      }
    }
    this.recalc(d);
    for (const r of req.resolutions) {
      const issue = d.issues.find(
        (i) => i.issue_id === r.issue_id && i.code === "CUSTOMER_CONDITION",
      );
      if (!issue)
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "This condition is no longer available.",
        );
      if (issue.condition_kind === "STOCK")
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Stock conditions are checked automatically.",
        );
      if (r.choice === "ACCEPT_REQUESTED_PRICE") {
        if (issue.condition_kind !== "PRICE" || !r.target_line_ids.length)
          throw new ApiError(
            "TARGET_LINE_REQUIRED",
            "Select the product the price applies to.",
          );
        if (r.price_basis !== "UNIT" || !r.confirmed_unit_price)
          throw new ApiError(
            "REQUEST_VALIDATION_FAILED",
            "Confirm a price per catalogue unit.",
          );
        for (const target of r.target_line_ids) {
          const l = d.lines.find((l) => l.line_id === target);
          if (!l)
            throw new ApiError(
              "TARGET_LINE_REQUIRED",
              "Choose an existing product.",
            );
          if (
            !l.unit_price_override ||
            cents(l.unit_price_override) !== cents(r.confirmed_unit_price)
          )
            throw new ApiError(
              "REQUEST_VALIDATION_FAILED",
              "The condition price and product override must agree.",
            );
          if (
            !l.tier_unit_price ||
            cents(l.unit_price_override) >= cents(l.tier_unit_price) ||
            !l.override_reason?.trim()
          )
            throw new ApiError(
              "OVERRIDE_REQUIRED",
              "Accepting a requested discount requires a below-tier price and reason.",
            );
        }
        issue.ask = "OWNER";
        issue.price_basis = "UNIT";
      } else if (
        r.choice === "CONFIRMED_WITH_CUSTOMER" ||
        r.choice === "NOT_A_CONDITION"
      ) {
        if (!r.note?.trim())
          throw new ApiError(
            "NOTE_REQUIRED",
            "Add a note about your confirmation.",
          );
      } else
        throw new ApiError(
          "REQUEST_VALIDATION_FAILED",
          "Choose a supported condition resolution.",
        );
      Object.assign(issue, {
        resolved: true,
        resolution: r.choice,
        resolution_note: r.note ? maskPII(r.note.trim()) : null,
        target_line_ids: r.target_line_ids,
      });
    }
    this.recalc(d);
    d.version++;
    d.updated_at = now();
    this.state.drafts[this.state.drafts.indexOf(original)] = d;
    this.state.aliases.push(...aliasWrites);
    this.diff(d);
    this.event(
      draftId,
      "DRAFT_SAVED",
      `Version ${d.version} saved · ${d.blocking_issues.length} blocking checks remaining.`,
    );
    this.persist();
    return this.projected(d);
  }
  async approve(draftId: string, version: number) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    const d = this.get(draftId);
    if (d.do_number)
      throw new ApiError(
        "ALREADY_APPROVED",
        "This order already has a delivery order.",
        { do_number: d.do_number },
      );
    if (d.status === "PENDING_OWNER_APPROVAL")
      throw new ApiError(
        "PENDING_OWNER_APPROVAL",
        "This version is already with the owner.",
      );
    if (d.status === "REJECTED")
      throw new ApiError(
        "DRAFT_REJECTED",
        "This order is closed. Create a new draft.",
      );
    if (version !== d.version)
      throw new ApiError(
        "STALE_VERSION",
        "Refresh to approve the latest saved version.",
      );
    const stockChanged = d.lines.some(
      (l) => l.sku_id && l.available_qty !== (this.state.stock[l.sku_id] ?? 0),
    );
    this.recalc(d);
    if (stockChanged && d.blocking_issues.includes("INSUFFICIENT_STOCK"))
      throw new ApiError(
        "STOCK_CHANGED",
        "Available stock changed. Review the updated checks and adjust the quantity before approving.",
      );
    if (d.blocking_issues.length)
      throw new ApiError(
        "DISAMBIGUATION_UNRESOLVED",
        "Resolve every blocking check before approving.",
      );
    const result =
      this.role === "CLERK" && d.escalation_preview.length
        ? this.submit(d)
        : this.finish(
            d,
            this.role === "OWNER" && d.escalation_preview.length
              ? "OWNER_SELF_APPROVED"
              : "DIRECT",
          );
    this.persist();
    return "approval_id" in result ? this.approvalView(result) : clone(result);
  }
  async approvals() {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    return this.state.approvals
      .filter((a) => this.role === "OWNER" || a.requested_by === this.user())
      .map((a) => this.approvalView(a));
  }
  async approval(id: string) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    const a = this.state.approvals.find(
      (a) =>
        a.approval_id === id &&
        (this.role === "OWNER" || a.requested_by === this.user()),
    );
    if (!a) throw new ApiError("NOT_FOUND", "Approval not found.");
    return this.approvalView(a);
  }
  async decide(
    approvalId: string,
    decision: "APPROVE" | "REJECT",
    note: string,
  ) {
    this.sync();
    this.require(["OWNER"]);
    const a = this.state.approvals.find((a) => a.approval_id === approvalId);
    if (!a) throw new ApiError("NOT_FOUND", "Approval not found.");
    if (a.status !== "PENDING")
      throw new ApiError(
        "ALREADY_DECIDED",
        "This request has already been decided.",
      );
    const d = this.get(a.draft_id);
    if (d.version !== a.draft_version)
      throw new ApiError(
        "STALE_VERSION",
        "The saved order no longer matches this approval snapshot.",
      );
    this.refreshApprovalStock(a);
    let result: DeliveryOrder | Approval;
    if (decision === "REJECT") {
      if (!note.trim())
        throw new ApiError("NOTE_REQUIRED", "Add a reason before rejecting.");
      a.status = "REJECTED";
      d.status = "REJECTED";
      d.termination_reason = "OWNER_REJECTED";
      d.termination_note = maskPII(note.trim());
      this.event(d.draft_id, "OWNER_REJECTED", d.termination_note);
      result = this.approvalView(a);
    } else {
      result = this.finish(d, "OWNER_APPROVED");
      a.status = "APPROVED";
    }
    a.decided_by = this.user();
    a.decided_at = now();
    a.decision_note = maskPII(note.trim());
    this.persist();
    return clone(result);
  }
  async delivery(number: string) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    const d = this.state.deliveries.find((d) => d.do_number === number);
    if (!d) throw new ApiError("NOT_FOUND", "Delivery order not found.");
    return clone(d);
  }
  async warehouse(number: string): Promise<WarehouseOrder> {
    this.sync();
    this.require(["WAREHOUSE"]);
    const d = this.state.deliveries.find((d) => d.do_number === number);
    if (!d) throw new ApiError("NOT_FOUND", "Delivery order not found.");
    return {
      do_number: d.do_number,
      customer_name: d.customer_name,
      items: d.lines.map((l) => ({
        sku_id: l.sku_id,
        display_name: l.display_name,
        quantity: l.quantity,
        unit: l.unit,
      })),
      approved_at: d.approved_at,
    };
  }
  async activity(entity?: string) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    return clone(
      this.state.activity.filter((a) => !entity || a.entity_id === entity),
    );
  }
  async audit(number: string): Promise<Audit> {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    const d = await this.delivery(number);
    return {
      delivery_order: d,
      ai_initial_snapshot: clone(this.state.initial[d.draft_id] ?? []),
      final_snapshot: clone(d),
      field_diffs: clone(this.state.diffs[d.draft_id] ?? []),
      timeline: await this.activity(d.draft_id),
    };
  }
  async aiStatus(): Promise<AiStatus> {
    return {
      state: "OFFLINE",
      fallback_available: true,
      last_checked_at: now(),
      message:
        "Local demo uses catalogue matching. No AI endpoint is connected.",
    };
  }
  async wake() {
    this.require(["CLERK", "OWNER"]);
    return this.aiStatus();
  }
  async discard(draftId: string, version: number, note: string) {
    this.sync();
    this.require(["CLERK", "OWNER"]);
    const d = this.get(draftId);
    if (d.version !== version)
      throw new ApiError(
        "STALE_VERSION",
        "Refresh the order before closing it.",
      );
    if (!["DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"].includes(d.status))
      throw new ApiError(
        "ORDER_LOCKED",
        "Submitted and completed orders cannot be discarded.",
      );
    if (!note.trim())
      throw new ApiError(
        "NOTE_REQUIRED",
        "Add a reason before closing this draft.",
      );
    d.status = "REJECTED";
    d.termination_reason = "CLERK_DISCARDED";
    d.termination_note = maskPII(note.trim());
    d.updated_at = now();
    this.event(d.draft_id, "DRAFT_DISCARDED", d.termination_note);
    this.persist();
    return this.projected(d);
  }
}
