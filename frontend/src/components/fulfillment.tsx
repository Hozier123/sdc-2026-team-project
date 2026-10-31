import { useEffect, useState } from "react";
import {
  Activity as ActivityIcon,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Check,
  CircleCheck,
  ClipboardCheck,
  FileCheck2,
  LockKeyhole,
  MessageSquareText,
  Plus,
  Printer,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  ApiError,
  money,
  type Activity,
  type Approval,
  type Audit,
  type DeliveryOrder,
  type DraftSummary,
  type Me,
  type Service,
  type WarehouseOrder,
} from "../lib/types";
import { useRequestScope, useResource } from "../lib/hooks";
import { pickingItems } from "../lib/review";
import { EXTRACTION, snapshotMode } from "../lib/extraction";
import { approvalSubmissionLabel } from "../lib/approval-display";
import type { Navigate, Notify } from "../lib/types";
import { PageHeading } from "./ui";
import {
  CopyButton,
  dateLabel,
  Empty,
  ErrorNotice,
  Loading,
  Modal,
  Pill,
  pretty,
  Reasons,
  shortId,
  Spinner,
  time,
} from "./ui";
export function ApprovalsPage({
  approvals,
  me,
  navigate,
}: {
  approvals: Approval[];
  me: Me;
  navigate: Navigate;
}) {
  const [filter, setFilter] = useState("PENDING");
  const filtered = approvals.filter(
    (a) => filter === "ALL" || a.status === filter,
  );
  return (
    <>
      <PageHeading title="Owner approvals" />
      <div className="info-banner blue compact-banner">
        <ShieldCheck size={17} />
        <strong>
          {me.role === "OWNER"
            ? "Stock and unresolved checks cannot be overridden."
            : "Read-only · owner decides."}
        </strong>
      </div>
      <section className="panel">
        <div className="queue-toolbar">
          <div className="tabs" role="tablist" aria-label="Approval status">
            {[
              ["PENDING", "Awaiting decision"],
              ["APPROVED", "Approved"],
              ["REJECTED", "Rejected"],
              ["ALL", "All requests"],
            ].map(([key, label]) => (
              <button
                key={key}
                role="tab"
                aria-selected={filter === key}
                className={filter === key ? "active" : ""}
                onClick={() => setFilter(key)}
              >
                {label}
                <span>
                  {key === "ALL"
                    ? approvals.length
                    : approvals.filter((a) => a.status === key).length}
                </span>
              </button>
            ))}
          </div>
        </div>
        {!filtered.length ? (
          <Empty
            title="No decisions waiting here"
            description="Orders that need a business decision will arrive with their context and a saved snapshot."
          />
        ) : (
          <div className="approval-list">
            {filtered.map((a) => (
              <button
                className="approval-card"
                key={a.approval_id}
                onClick={() => navigate(`approval/${a.approval_id}`)}
              >
                <span className="approval-icon">
                  <ShieldCheck size={21} />
                </span>
                <div className="approval-card-main">
                  <h3>
                    {a.customer.name}{" "}
                    <Pill
                      tone={
                        a.status === "PENDING"
                          ? "blue"
                          : a.status === "APPROVED"
                            ? "mint"
                            : "rose"
                      }
                    >
                      {a.status === "PENDING"
                        ? "Awaiting decision"
                        : pretty(a.status)}
                    </Pill>
                  </h3>
                  <p>
                    {a.reasons
                      .map((r) =>
                        r.code === "PRICE_OVERRIDE_BELOW_TIER"
                          ? "Price below customer tier"
                          : r.code === "AMOUNT_OVER_THRESHOLD"
                            ? "Above order threshold"
                            : "Customer credit notice",
                      )
                      .join(" · ")}
                  </p>
                  <small className="approval-request-meta">
                    <span>{approvalSubmissionLabel(a.requested_at)}</span>
                    <span title={a.draft_id}>
                      Draft #{shortId(a.draft_id)} · v{a.draft_version} ·{" "}
                      {a.line_count} product{a.line_count === 1 ? "" : "s"}
                    </span>
                    <span>Requested by {a.requested_by}</span>
                  </small>
                </div>
                <div className="approval-total">
                  <strong>{money(a.total_rm)}</strong>
                  <span>
                    Review request <ArrowUpRight size={14} />
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
export function ApprovalDetail({
  id,
  service,
  me,
  navigate,
  changed,
  notify,
}: {
  id: string;
  service: Service;
  me: Me;
  navigate: Navigate;
  changed: () => void;
  notify: Notify;
}) {
  const r = useResource(() => service.approval(id), [service, id]);
  const [reject, setReject] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [success, setSuccess] = useState<DeliveryOrder>();
  const beginDecision = useRequestScope([service, id]);
  async function decide(decision: "APPROVE" | "REJECT") {
    if (busy) return;
    const current = beginDecision();
    setBusy(true);
    setError(undefined);
    try {
      const result = await service.decide(id, decision, decision === "REJECT" ? note : "");
      changed();
      if (!current()) return;
      setReject(false);
      if ("do_number" in result) {
        setSuccess(result);
        notify("Owner approved. The delivery order is ready.");
        navigate(`delivery/${result.do_number}`);
      } else {
        r.refresh();
        notify("Decision recorded. The order is now closed.");
      }
    } catch (err) {
      if (current()) setError(err);
    } finally {
      if (current()) setBusy(false);
    }
  }
  if (r.loading && !r.value) return <Loading />;
  if (r.error) return <ErrorNotice error={r.error} retry={r.refresh} />;
  const a = r.value;
  if (!a) return null;
  const canApprove = a.allowed_actions.includes("OWNER_APPROVE"),
    canReject = a.allowed_actions.includes("OWNER_REJECT");
  return (
    <>
      <button className="back-button" onClick={() => navigate("approvals")}>
        <ArrowLeft size={14} /> Back to approvals
      </button>
      <PageHeading
        eyebrow={`OWNER REVIEW · VERSION ${a.draft_version}`}
        title={a.customer.name}
        description={`Draft #${shortId(a.draft_id)} · ${approvalSubmissionLabel(a.requested_at)} · Requested by ${a.requested_by}`}
      >
        <Pill
          tone={
            a.status === "PENDING"
              ? "blue"
              : a.status === "APPROVED"
                ? "mint"
                : "rose"
          }
        >
          {a.status === "PENDING" ? "Awaiting decision" : pretty(a.status)}
        </Pill>
      </PageHeading>
      {a.status === "PENDING" && !canApprove && !canReject && (
        <div className="info-banner blue">
          <LockKeyhole size={18} />
          <div>
            <strong>Read-only approval request</strong>
            <p>
              Only an authorized workspace owner can approve or reject this
              saved order.
            </p>
          </div>
        </div>
      )}
      {a.status !== "PENDING" && (
        <div
          className={`info-banner ${a.status === "REJECTED" ? "rose" : "mint"}`}
        >
          <CircleCheck size={19} />
          <div>
            <strong>{a.status === "REJECTED" ? "Order rejected · no delivery order generated" : "Decision recorded."}</strong>
            <p>{a.decision_note || "This request has already been decided."}</p>
            <button className="text-button" onClick={() => navigate(`activity/${encodeURIComponent(a.draft_id)}`)}>View order activity <ArrowUpRight size={14} /></button>
          </div>
          {success && (
            <button
              className="button primary"
              onClick={() => navigate(`delivery/${success.do_number}`)}
            >
              View delivery order
            </button>
          )}
        </div>
      )}
      <div className="approval-detail-grid">
        <div>
          <section className="panel approval-reasons">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">WHY IT REACHED YOU</span>
                <h2>Approval reasons</h2>
              </div>
              <ShieldCheck size={20} />
            </div>
            <Reasons reasons={a.reasons} />
          </section>
          <section className="panel snapshot-panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">THE SAVED ORDER</span>
                <h2>Saved order</h2>
              </div>
              <Pill>Locked v{a.draft_version}</Pill>
            </div>
            {a.snapshot ? (
              <>
                <pre className="message-evidence">
                  {a.snapshot.masked_customer_text}
                </pre>
                <div className="approval-lines">
                  <div className="approval-lines-head">
                    <span>PRODUCT</span>
                    <span>QUANTITY</span>
                    <span>UNIT PRICE</span>
                    <span>SUBTOTAL</span>
                  </div>
                  {a.snapshot.lines.map((l) => (
                    <div key={l.line_id}>
                      <span>
                        <strong>{l.description}</strong>
                        <small>
                          {l.pack_size}
                          {l.grade ? ` · ${l.grade}` : ""}
                        </small>
                      </span>
                      <span>
                        {l.effective_qty} {l.uom}
                      </span>
                      <span>
                        {money(l.effective_unit_price)}
                        {l.unit_price_override && (
                          <small className="old-price">
                            {money(l.tier_unit_price)}
                          </small>
                        )}
                      </span>
                      <strong>{money(l.subtotal_rm)}</strong>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <Empty
                title="The saved snapshot is unavailable"
                description="Refresh this request to load its approved version before making a decision."
              >
                <button className="button secondary" onClick={r.refresh}>
                  Refresh request
                </button>
              </Empty>
            )}
            <div className="order-total">
              <span>
                Order total{" "}
                <small>Approval is bound to version {a.draft_version}.</small>
              </span>
              <strong>{money(a.total_rm)}</strong>
            </div>
          </section>
          {!!a.field_diffs?.length && (
            <section className="panel diff-panel">
              <div className="panel-heading">
                <h2>Changes</h2>
                <Pill>Human decisions</Pill>
              </div>
              <DiffTable diffs={a.field_diffs} />
            </section>
          )}
        </div>
        <aside>
          <section className="panel checks-panel">
            <div className="rail-title">
              STOCK AT REVIEW <Boxes size={15} />
            </div>
            {a.stock_check?.lines.map((l) => (
              <div className="stock-check-row" key={l.line_id}>
                <span className={l.sufficient ? "mint-text" : "amber-text"}>
                  {l.sufficient ? <Check size={15} /> : <Boxes size={15} />}
                </span>
                <div>
                  <strong>
                    {a.snapshot?.lines.find((x) => x.line_id === l.line_id)
                      ?.description ?? l.sku_id}
                  </strong>
                  <small>
                    {l.effective_qty} requested · {l.available_qty} available
                  </small>
                </div>
              </div>
            ))}
            <div className="permission-note">
              <LockKeyhole size={16} />
              <p>Stock rechecked at approval.</p>
            </div>
          </section>
        </aside>
      </div>
      {!!error && (
        <ErrorNotice
          error={error}
          retry={
            error instanceof ApiError && error.error_code === "STOCK_CHANGED"
              ? () => {
                  r.refresh();
                  setError(undefined);
                }
              : undefined
          }
        />
      )}
      {(canApprove || canReject) && (
        <div className="review-actions">
          <div>
            <ShieldCheck size={18} />
            <span>
              Approving saved version {a.draft_version}
              <small>Products and prices are locked to this request.</small>
            </span>
          </div>
          <div className="action-buttons">
            {canReject && (
              <button
                className="button secondary danger-outline"
                disabled={busy}
                onClick={() => setReject(true)}
              >
                <X size={15} />
                Reject with reason
              </button>
            )}
            {canApprove && (
              <button
                className="button primary"
                disabled={busy || !a.snapshot}
                onClick={() => decide("APPROVE")}
              >
                {busy ? <Spinner /> : <FileCheck2 size={16} />}Approve &
                generate DO <ArrowRight size={15} />
              </button>
            )}
          </div>
        </div>
      )}
      {reject && (
        <Modal
          title="Why should this order be rejected?"
          onClose={() => !busy && setReject(false)}
        >
          <p className="modal-copy">
            The order will close with your reason in its activity record. The
            clerk can create a new draft if needed. Rejection generates no delivery order and does not deduct stock.
          </p>
          <label className="field-label">
            Reason for rejection
            <textarea
              rows={4}
              maxLength={500}
              required
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Explain the decision to the order clerk…"
            />
          </label>
          {!!error && <ErrorNotice error={error} />}
          <div className="modal-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setReject(false)}
            >
              Keep reviewing
            </button>
            <button
              className="button danger"
              disabled={busy || !note.trim()}
              onClick={() => decide("REJECT")}
            >
              {busy ? <Spinner /> : <X size={15} />}Reject order
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
export function DeliveriesPage({
  drafts,
  navigate,
}: {
  drafts: DraftSummary[];
  navigate: Navigate;
}) {
  const [search, setSearch] = useState("");
  const records = drafts.filter(
    (d) =>
      d.status === "DO_GENERATED" &&
      d.do_number &&
      `${d.do_number} ${d.customer_name}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeading title="Delivery orders">
        <button className="button primary" onClick={() => navigate("new")}>
          <Plus size={16} /> New order
        </button>
      </PageHeading>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Approved orders</h2>
          </div>
          <label className="search-field">
            <Search size={15} />
            <input
              aria-label="Find delivery order"
              placeholder="Find customer or DO…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
        </div>
        {records.length ? (
          <div className="delivery-list">
            {records.map((d) => (
              <button
                key={d.draft_id}
                onClick={() => navigate(`delivery/${d.do_number}`)}
              >
                <span className="delivery-icon">
                  <FileCheck2 size={22} />
                </span>
                <div>
                  <strong>{d.do_number}</strong>
                  <span>{d.customer_name}</span>
                </div>
                <small>
                  {dateLabel(d.updated_at)} · {time(d.updated_at)}
                </small>
                <Pill tone="mint">Approved</Pill>
                <ArrowUpRight size={18} />
              </button>
            ))}
          </div>
        ) : (
          <Empty
            title={
              search
                ? "No matching delivery orders"
                : "A clear record, once it’s approved."
            }
            description={
              search
                ? "Try a different customer or delivery order number."
                : "Approve an order to generate its delivery order, reply draft and activity record."
            }
          />
        )}
      </section>
    </>
  );
}
export function DeliveryPage({
  id,
  service,
  notify,
  navigate,
}: {
  id: string;
  service: Service;
  notify: Notify;
  navigate: Navigate;
}) {
  const r = useResource(() => service.delivery(id), [service, id]);
  const [audit, setAudit] = useState(false);
  if (r.loading) return <Loading />;
  if (r.error) return <ErrorNotice error={r.error} retry={r.refresh} />;
  const d = r.value;
  if (!d) return null;
  return (
    <>
      <div className="no-print">
        <button
          className="back-button"
          onClick={() => navigate("delivery-orders")}
        >
          <ArrowLeft size={14} /> Back to delivery orders
        </button>
        <div className="success-heading">
          <span className="success-symbol">
            <Check size={24} />
          </span>
          <div>
            <span className="eyebrow">DO GENERATED</span>
            <h1>Delivery order ready</h1>
          </div>
        </div>
      </div>
      <div className="delivery-detail-grid">
        <section className="delivery-document">
          <div className="document-header">
            <div className="document-brand">
              <span>✦</span>
              <strong>
                KiraOrder<small>FOR ORBYTE</small>
              </strong>
            </div>
            <div>
              <span>DELIVERY ORDER</span>
              <h2>{d.do_number}</h2>
              <small>{dateLabel(d.approved_at)}</small>
            </div>
          </div>
          <div className="document-parties">
            <div>
              <small>DELIVER TO</small>
              <h3>{d.customer_name}</h3>
              <span>
                Approved order · {d.lines.length} product
                {d.lines.length === 1 ? "" : "s"}
              </span>
            </div>
            <div>
              <small>APPROVED BY</small>
              <h4>{d.approved_by}</h4>
              <span>
                {time(d.approved_at)} MYT ·{" "}
                {d.approval_mode === "DIRECT"
                  ? "Direct approval"
                  : d.approval_mode === "OWNER_SELF_APPROVED"
                    ? "Owner self-approved"
                    : "Owner approved"}
              </span>
            </div>
          </div>
          <div className="do-table">
            <div className="do-table-head">
              <span>ITEM / DESCRIPTION</span>
              <span>QTY</span>
              <span>UNIT PRICE</span>
              <span>AMOUNT</span>
            </div>
            {d.lines.map((l, i) => (
              <div className="do-line" key={l.line_id}>
                <span>
                  <small>{String(i + 1).padStart(2, "0")}</small>
                  <strong>{l.display_name}</strong>
                </span>
                <span>
                  {l.quantity} {l.unit}
                </span>
                <span>{money(l.applied_unit_price)}</span>
                <strong>{money(l.subtotal_rm)}</strong>
              </div>
            ))}
          </div>
          <div className="document-total">
            <span>
              Total <small>MYR</small>
            </span>
            <strong>{money(d.final_total_rm)}</strong>
          </div>
          <div className="document-signatures">
            <div>
              <small>PREPARED BY</small>
              <span>{d.prepared_by}</span>
            </div>
            <div>
              <small>APPROVED BY</small>
              <span>{d.approved_by}</span>
            </div>
            <div>
              <small>SAVED VERSION</small>
              <span>
                v{d.draft_version} · #{shortId(d.draft_id)}
              </span>
            </div>
          </div>
          <div className="document-footer">
            <ShieldCheck size={13} />
            <span>Approved record</span>
          </div>
        </section>
        <aside className="delivery-side no-print">
          <section className="panel document-actions">
            <div className="rail-title">
              YOUR DELIVERY ORDER <FileCheck2 size={15} />
            </div>
            <button className="button primary" onClick={() => window.print()}>
              <Printer size={16} />
              Print / save as PDF
            </button>
            <button className="button secondary" onClick={() => setAudit(true)}>
              <ActivityIcon size={16} />
              View change record
            </button>
            <button className="button secondary" onClick={() => navigate(`activity/${encodeURIComponent(d.draft_id)}`)}>
              <ArrowUpRight size={16} /> Open order activity
            </button>
            <div className="permission-note">
              <LockKeyhole size={15} />
              <p>Approved record · read-only.</p>
            </div>
          </section>
          <section className="panel clarification-card">
            <div className="rail-title">
              <MessageSquareText size={15} /> CUSTOMER REPLY
            </div>
            <h3>Reply draft</h3>
            <span className="language-label">
              Message draft ·{" "}
              {(
                { en: "English", ms: "Bahasa Melayu", zh: "中文" } as Record<
                  string,
                  string
                >
              )[d.reply_draft.language] ?? d.reply_draft.language}
            </span>
            <pre tabIndex={0}>{d.reply_draft.message}</pre>
            <CopyButton
              text={d.reply_draft.message}
              onCopy={notify}
              label="Copy customer reply"
            />
            <p className="micro-copy">
              Send manually. WhatsApp is not connected.
            </p>
          </section>
          {d.escalation_reasons.length > 0 && (
            <section className="panel escalation-card">
              <div className="rail-title">
                APPROVAL CONTEXT <ShieldCheck size={14} />
              </div>
              <Reasons reasons={d.escalation_reasons} />
            </section>
          )}
        </aside>
      </div>
      {audit && (
        <AuditModal id={id} service={service} onClose={() => setAudit(false)} />
      )}
    </>
  );
}
function DiffTable({ diffs }: { diffs: Audit["field_diffs"] }) {
  return (
    <div className="diff-table">
      <div className="diff-table-head">
        <span>FIELD</span>
        <span>INITIAL</span>
        <span>CONFIRMED</span>
      </div>
      {diffs.map((d, i) => (
        <div key={`${d.line_id}-${d.field_path}-${i}`}>
          <span>
            {pretty(d.field_path)}
            <small>{d.line_id ? `Line ${d.line_id.slice(-6)}` : "Order"}</small>
          </span>
          <span>{d.before == null ? "Not specified" : String(d.before)}</span>
          <span className="mint-text">
            {d.after == null ? "Not specified" : String(d.after)}
          </span>
        </div>
      ))}
    </div>
  );
}
function AuditModal({
  id,
  service,
  onClose,
}: {
  id: string;
  service: Service;
  onClose: () => void;
}) {
  const r = useResource(() => service.audit(id), [id, service]);
  return (
    <Modal title="The decisions behind this order" onClose={onClose} wide>
      {r.loading ? (
        <Loading />
      ) : r.error ? (
        <ErrorNotice error={r.error} retry={r.refresh} />
      ) : (
        r.value && (
          <>
            <p className="modal-copy">
              {r.value.delivery_order.do_number} · saved version {r.value.delivery_order.draft_version}
              {snapshotMode(r.value.ai_initial_snapshot) && <> · Extraction: {EXTRACTION[snapshotMode(r.value.ai_initial_snapshot)!].label}</>}
            </p>
            <span className="section-kicker">
              EXTRACTION → HUMAN CONFIRMATION
            </span>
            {r.value.field_diffs.length ? (
              <DiffTable diffs={r.value.field_diffs} />
            ) : (
              <div className="all-clear">
                <Check size={15} /> No product fields changed after initial
                extraction.
              </div>
            )}
            <span className="section-kicker audit-trail-label">
              THE APPROVAL TRAIL
            </span>
            <div className="timeline">
              {r.value.timeline.map((a) => (
                <div key={a.activity_id}>
                  <span className="timeline-dot" />
                  <section>
                    <strong>{pretty(a.action)}</strong>
                    <p>{a.detail}</p>
                    <small>
                      {a.actor}{a.actor_role ? ` · ${a.actor_role}` : ""} · {dateLabel(a.created_at)} ·{" "}
                      {time(a.created_at)} MYT
                    </small>
                  </section>
                </div>
              ))}
            </div>
          </>
        )
      )}
    </Modal>
  );
}
const ACTIVITY_RESULTS: Record<string, string> = {
  OWNER_REQUESTED: "Awaiting owner decision",
  OWNER_REJECTED: "Closed without a delivery order",
  OWNER_APPROVED: "Approved and delivery order generated",
  DO_CREATED: "Delivery order generated",
  DO_GENERATED: "Delivery order generated",
  INVENTORY_DEDUCTED: "Stock deducted",
};

export function ActivityPage({
  activity,
  drafts,
  navigate,
  initialQuery = "",
  scopeId,
}: {
  activity: Activity[];
  drafts: DraftSummary[];
  navigate: Navigate;
  initialQuery?: string;
  scopeId?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const filtered = activity.filter((a) =>
    `${a.action} ${a.actor} ${a.actor_role ?? ""} ${a.detail} ${a.entity_id} ${a.do_number ?? ""} ${drafts.find(d => d.draft_id === a.entity_id)?.do_number ?? ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <>
      <PageHeading
        title={scopeId ? "Order activity" : "Activity log"}
        description={scopeId ? `Order #${shortId(scopeId)} · actions, decisions and results` : undefined}
      >
        {scopeId && <button className="button secondary small" onClick={() => navigate("activity")}>All activity</button>}
      </PageHeading>
      <section className="panel activity-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent events</h2>
          </div>
          <label className="search-field">
            <Search size={15} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search activity"
              placeholder="Search activity…"
            />
          </label>
        </div>
        {query && <div className="activity-filter-summary"><span>Filtered by {query}</span><button className="text-button" onClick={() => { setQuery(""); navigate("activity"); }}>Clear filter <X size={13} /></button></div>}
        {filtered.length ? (
          <div className="activity-table">
            {filtered.map((a) => {
              const d = drafts.find((d) => d.draft_id === a.entity_id || (!!a.do_number && d.do_number === a.do_number));
              const deliveryNumber = a.do_number ?? d?.do_number;
              const result = ACTIVITY_RESULTS[a.action];
              return (
                <div className="activity-event" key={a.activity_id}>
                  <span
                    className={`event-icon ${a.action === "DO_GENERATED" ? "mint" : a.action === "OWNER_REQUESTED" ? "blue" : ""}`}
                  >
                    {a.action === "DO_GENERATED" ? (
                      <FileCheck2 size={17} />
                    ) : a.action === "OWNER_REQUESTED" ? (
                      <ShieldCheck size={17} />
                    ) : (
                      <ActivityIcon size={17} />
                    )}
                  </span>
                  <div>
                    <strong>
                      {pretty(a.action)}
                      {(d || deliveryNumber || a.entity_id) && (
                        <button
                          className="activity-customer"
                          onClick={() =>
                            navigate(
                              deliveryNumber
                                ? `delivery/${encodeURIComponent(deliveryNumber)}`
                                : `order/${encodeURIComponent(d?.draft_id ?? a.entity_id)}`,
                            )
                          }
                        >
                          {deliveryNumber ?? d?.customer_name ?? a.entity_id} <ArrowUpRight size={11} />
                        </button>
                      )}
                    </strong>
                    {a.detail && <p>{a.detail}</p>}
                    {result && <p className="activity-result">Result: {result}</p>}
                    <small>{a.actor}{a.actor_role ? ` · ${a.actor_role}` : ""}</small>
                  </div>
                  <time dateTime={a.created_at}>
                    <span>{time(a.created_at)} MYT</span>
                    <small>{dateLabel(a.created_at)}</small>
                  </time>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty
            title="No matching activity"
            description="Try another search. Saved order actions appear here automatically."
          />
        )}
      </section>
    </>
  );
}
export function WarehousePage({
  service,
  notify,
}: {
  service: Service;
  notify: Notify;
}) {
  const [number, setNumber] = useState(
    service.mode === "demo" ? "DO-T1-0001" : "",
  );
  const [order, setOrder] = useState<WarehouseOrder>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [picked, setPicked] = useState<string[]>([]);
  const items = pickingItems(order?.items ?? []);
  return (
    <>
      <PageHeading title="Warehouse" />
      <div className="info-banner blue">
        <LockKeyhole size={18} />
        <div>
          <strong>Read-only picking list</strong>
          <p>Prices and contacts must be excluded by the API. Unexpected response fields block this view.</p>
        </div>
      </div>
      <section className="panel warehouse-lookup no-print">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError(undefined);
            setOrder(undefined);
            setPicked([]);
            try {
              setOrder(await service.warehouse(number.trim()));
            } catch (err) {
              setError(err);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label className="field-label">
            Delivery order number
            <input
              required
              aria-label="Delivery order number"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="Enter an approved DO number"
            />
          </label>
          <button className="button primary" disabled={busy || !number.trim()}>
            {busy ? <Spinner /> : <Search size={16} />} Find picking list
          </button>
        </form>
      </section>
      {!!error && <ErrorNotice error={error} />}{" "}
      {order ? (
        <section className="panel picking-list">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">{order.do_number}</span>
              <h2>{order.customer_name}</h2>
              <p>
                Approved {dateLabel(order.approved_at)} at{" "}
                {time(order.approved_at)} MYT
              </p>
            </div>
            <button
              className="button secondary small no-print"
              onClick={() => window.print()}
            >
              <Printer size={15} />
              Print picking list
            </button>
          </div>
          {items.map((l) => (
            <label
              className={`pick-row ${picked.includes(l.picking_id) ? "picked" : ""}`}
              key={l.picking_id}
            >
              <input
                type="checkbox"
                checked={picked.includes(l.picking_id)}
                onChange={(e) =>
                  setPicked((p) =>
                    e.target.checked
                      ? [...p, l.picking_id]
                      : p.filter((id) => id !== l.picking_id),
                  )
                }
              />
              <div>
                <strong>{l.display_name}</strong>
                <small>
                  {l.sku_id}
                  {l.picking_note ? ` · ${l.picking_note}` : ""}
                </small>
              </div>
              <span>
                {l.quantity} <small>{l.unit}</small>
              </span>
            </label>
          ))}
          <div className="panel-footnote">
            <Check size={13} />
            {picked.length} / {items.length} items checked locally · These
            checkboxes are a temporary checklist.
          </div>
        </section>
      ) : (
        <Empty
          title="An approved order, a simple list."
          description="Enter the delivery order number to see exactly what to prepare."
        />
      )}
    </>
  );
}
