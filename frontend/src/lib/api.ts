import {
  ApiError,
  type Activity,
  type AiStatus,
  type Approval,
  type Audit,
  type Customer,
  type DeliveryOrder,
  type Draft,
  type DraftSummary,
  type Me,
  type PageResult,
  type SaveRequest,
  type Service,
  type WarehouseOrder,
  type Gate0,
} from "./types";
import { assertQuantities } from "./review";
import type { CatalogProductsResponse } from "./catalog";
import { validateApiBase } from "./connection";
import {
  approvalView,
  draftView,
  fieldDiffView,
  summaryView,
  savePayload,
} from "./wire";

/**
 * Real Gate 0 backend base used when VITE_API_BASE_URL is not set.
 * The fixture mock (npm run mock:api) is a separate, opt-in address that must be
 * typed in explicitly; nothing here ever defaults to it.
 */
export const DEFAULT_API_BASE = "http://127.0.0.1:8000/api/v1";

type WireActivity = {
  activity_id: string | number;
  entity_id?: string | null;
  draft_id?: string | null;
  event_type: string;
  payload?: Record<string, unknown>;
  actor_user_id?: string | null;
  actor_role?: string | null;
  created_at: string;
};
const activityView = (a: WireActivity): Activity => ({
  activity_id: String(a.activity_id),
  entity_id: a.entity_id ?? a.draft_id ?? (typeof a.payload?.draft_id === "string" ? a.payload.draft_id : ""),
  action: a.event_type,
  actor: a.actor_user_id ?? a.actor_role ?? "Actor unavailable",
  actor_role: a.actor_role,
  do_number: typeof a.payload?.do_number === "string" ? a.payload.do_number : null,
  created_at: a.created_at,
  detail:
    typeof a.payload?.message === "string"
      ? a.payload.message
      : typeof a.payload?.note === "string"
        ? a.payload.note
        : a.event_type.toLowerCase().replaceAll("_", " "),
});
export class HttpService implements Service {
  readonly mode = "live" as const;
  fixture = false;
  constructor(
    private base: string,
    private token: string,
  ) {
    this.base = validateApiBase(base);
  }
  private async request<T>(
    path: string,
    method = "GET",
    body?: unknown,
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(`${this.base}${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${this.token}`,
          Accept: "application/json",
          ...(body ? { "Content-Type": "application/json" } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
        cache: "no-store",
        credentials: "omit",
        redirect: "error",
      });
      this.fixture = response.headers.get("X-KiraOrder-Fixture") === "true";
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        throw new ApiError(
          "INVALID_RESPONSE",
          "The API returned a non-JSON response.",
          {},
          response.headers.get("X-Request-ID") ?? undefined,
        );
      }
      if (!response.ok) {
        const error = payload as {
          error_code?: string;
          message?: string;
          details?: Record<string, unknown>;
        };
        throw new ApiError(
          error.error_code ?? `HTTP_${response.status}`,
          error.message ?? "The request could not be completed.",
          error.details ?? {},
          response.headers.get("X-Request-ID") ?? undefined,
        );
      }
      return payload as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (error instanceof DOMException && error.name === "AbortError")
        throw new ApiError(
          "TIMEOUT",
          "The API took too long to respond. Refresh the order before retrying.",
        );
      throw new ApiError(
        "NETWORK_ERROR",
        "Cannot reach the API. Check the address, connection and CORS configuration.",
      );
    } finally {
      clearTimeout(timeout);
    }
  }
  private async list<T>(path: string) {
    const result: T[] = [];
    let cursor: string | null = null;
    const seen = new Set<string>();
    do {
      const p: PageResult<T> = await this.request<PageResult<T>>(
        `${path}${path.includes("?") ? "&" : "?"}limit=50${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
      );
      result.push(...p.items);
      cursor = p.next_cursor ?? null;
      if (cursor && seen.has(cursor))
        throw new ApiError(
          "INVALID_RESPONSE",
          "The API returned a repeated page cursor.",
        );
      if (cursor) seen.add(cursor);
    } while (cursor);
    return result;
  }
  async me() {
    const m = await this.request<
      Omit<Me, "tenant"> & {
        tenant: { tenant_id?: string; id?: string; name: string };
      }
    >("/me");
    return {
      ...m,
      tenant: {
        id: m.tenant.id ?? m.tenant.tenant_id ?? "",
        name: m.tenant.name,
      },
    };
  }
  customers() {
    return this.list<Customer>("/customers");
  }
  catalogProducts(): Promise<CatalogProductsResponse> {
    // Keep the full envelope: generic list() discards limit/truncated.
    return this.request<CatalogProductsResponse>("/catalog/products");
  }
  async drafts() {
    return (await this.list<Gate0["DraftSummary"]>("/orders/drafts")).map(
      summaryView,
    );
  }
  async draft(id: string) {
    return draftView(
      await this.request<Gate0["OrderDraft"]>(
        `/orders/drafts/${encodeURIComponent(id)}`,
      ),
    );
  }
  async parse(customerId: string, text: string, lang: string) {
    const body = {
      customer_id: customerId,
      message_text: text,
      language_hint: lang === "auto" ? null : lang,
    } satisfies Gate0["ParseDraftRequest"];
    return draftView(
      await this.request<Gate0["OrderDraft"]>(
        "/orders/parse-draft",
        "POST",
        body,
      ),
    );
  }
  async save(id: string, request: SaveRequest) {
    assertQuantities(request.lines);
    return draftView(
      await this.request<Gate0["OrderDraft"]>(
        `/orders/drafts/${encodeURIComponent(id)}/lines`,
        "PUT",
        savePayload(request) satisfies Gate0["SaveLinesRequest"],
      ),
    );
  }
  approve(id: string, version: number) {
    return this.request<DeliveryOrder | Approval>(
      `/orders/${encodeURIComponent(id)}/approve`,
      "POST",
      { expected_version: version },
    );
  }
  async approvals() {
    return (await this.list<Gate0["ApprovalRequest"]>("/approvals")).map(
      approvalView,
    );
  }
  async approval(id: string) {
    return approvalView(
      await this.request<Gate0["ApprovalDetail"]>(
        `/approvals/${encodeURIComponent(id)}`,
      ),
    );
  }
  decide(id: string, decision: "APPROVE" | "REJECT", note: string) {
    return this.request<DeliveryOrder | Gate0["ApprovalDecisionResult"]>(
      `/approvals/${encodeURIComponent(id)}/decide`,
      "POST",
      { decision, ...(note.trim() ? { note: note.trim() } : {}) },
    );
  }
  delivery(id: string) {
    return this.request<DeliveryOrder>(
      `/delivery-orders/${encodeURIComponent(id)}`,
    );
  }
  async warehouse(id: string) {
    const order = await this.request<WarehouseOrder>(
      `/warehouse/delivery-orders/${encodeURIComponent(id)}`,
    );
    // Fail visibly on an overbroad server response; hiding fields in JSX is insufficient.
    const rootKeys = new Set(["do_number", "customer_name", "items", "approved_at"]);
    const itemKeys = new Set(["sku_id", "display_name", "quantity", "unit", "picking_note"]);
    if (!order || !Array.isArray(order.items) || Object.keys(order).some(key => !rootKeys.has(key)) || order.items.some(item => !item || Object.keys(item).some(key => !itemKeys.has(key))))
      throw new ApiError("WAREHOUSE_RESPONSE_NOT_REDACTED", "The warehouse response contains unexpected fields. Ask the backend owner to verify price and contact redaction before continuing.");
    return order;
  }
  async activity(entity?: string) {
    const items = await this.list<WireActivity>(
      `/activity${entity ? `?entity_id=${encodeURIComponent(entity)}` : ""}`,
    );
    return items.map(activityView);
  }
  async audit(id: string) {
    const result = await this.request<Gate0["AuditDetail"]>(
      `/orders/${encodeURIComponent(id)}/audit-detail`,
    );
    const final = {
      ...result.final_snapshot,
      related_do_number: result.final_snapshot.related_do_number ?? null,
    };
    return {
      delivery_order: final,
      ai_initial_snapshot: result.ai_initial_snapshot,
      final_snapshot: final,
      field_diffs: result.field_diffs.map(fieldDiffView),
      timeline: result.events.map((a, i) =>
        activityView({ ...a, activity_id: i }),
      ),
    };
  }
  aiStatus() {
    return this.request<AiStatus>("/ai/status");
  }
  wake() {
    return this.request<AiStatus>("/ai/wake", "POST");
  }
  async clarificationCopied(id: string, version: number) {
    await this.request<{ recorded: boolean }>(
      `/orders/drafts/${encodeURIComponent(id)}/clarification-copied`,
      "POST",
      { expected_version: version },
    );
  }
  async discard(id: string, version: number, note: string) {
    const result = await this.request<Gate0["OrderDraft"]>(
      `/orders/drafts/${encodeURIComponent(id)}/discard`,
      "POST",
      { expected_version: version, note },
    );
    return draftView(result);
  }
}
