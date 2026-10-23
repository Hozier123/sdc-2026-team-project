import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleCheck,
  ClipboardPaste,
  Copy,
  FileCheck2,
  LockKeyhole,
  MessageSquareText,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import {
  ApiError,
  money,
  toInput,
  type Candidate,
  type Draft,
  type Issue,
  type Line,
  type LineInput,
  type Me,
  type Resolution,
  type Service,
} from "../lib/types";
import { useRequestScope, useResource } from "../lib/hooks";
import {
  assertQuantities,
  invalidQuantities,
  rebaseInputs,
} from "../lib/review";
import {
  CopyButton,
  Empty,
  ErrorNotice,
  Loading,
  Modal,
  Pill,
  Reasons,
  shortId,
  Spinner,
  Status,
  Stepper,
  time,
} from "./ui";
import type { Navigate, Notify } from "../lib/types";
import { PageHeading } from "./ui";
import { CustomerSelect, LanguageSelect, UnitSelect } from "./FormSelect";
interface PageProps {
  service: Service;
  navigate: Navigate;
  complete: Navigate;
  setDirty: (v: boolean) => void;
  changed: () => void;
  notify: Notify;
}
export function NewOrder({
  service,
  navigate,
  complete,
  setDirty,
  changed,
  notify,
}: PageProps) {
  const customerResource = useResource(() => service.customers(), [service]);
  const [customer, setCustomer] = useState("");
  const [text, setText] = useState("");
  const [lang, setLang] = useState("auto");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const beginRequest = useRequestScope([service]);
  useEffect(() => {
    setDirty(!!text.trim());
    return () => setDirty(false);
  }, [text, setDirty]);
  const selected = customerResource.value?.find(
    (c) => c.customer_id === customer,
  );
  const samples =
    service.mode === "demo"
      ? [
          {
            title: "The everyday order",
            tag: "Ready to approve",
            body: "Tepung 4 ctn\nMinyak 2 ctn",
            tone: "mint",
          },
          {
            title: "A specification to clarify",
            tag: "Ask the customer",
            body: "Boss, Milo 5 pkt\nTepung 3 ctn\nMinyak 2 ctn",
            tone: "amber",
          },
          {
            title: "A price to decide",
            tag: "Ask the owner",
            body: "Tepung 5 ctn, kalau RM95 boleh?",
            tone: "blue",
          },
          {
            title: "Check before promising",
            tag: "Stock check",
            body: "Ayam A1 5 ctn, kalau ada",
            tone: "amber",
          },
        ]
      : [];
  return (
    <div className="new-order-page">
      <button className="back-button" onClick={() => navigate("workspace")}>
        <ArrowLeft size={14} /> Back to overview
      </button>
      <PageHeading title="New order" />
      <Stepper step={0} />
      <div className="new-order-grid">
        <form
          className="panel new-order-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (busy || !customer || !text.trim()) return;
            const current = beginRequest();
            setBusy(true);
            setError(undefined);
            try {
              const d = await service.parse(customer, text, lang);
              changed();
              if (!current()) return;
              setText("");
              setDirty(false);
              complete(`order/${d.draft_id}`);
              notify(
                "Order draft created. Review the details before approving.",
              );
            } catch (err) {
              if (current()) setError(err);
            } finally {
              if (current()) setBusy(false);
            }
          }}
        >
          <div className="form-section-heading">
            <span className="numbered-icon">01</span>
            <div>
              <h2>Customer</h2>
            </div>
          </div>
          {customerResource.loading ? (
            <Loading label="Loading customers…" />
          ) : customerResource.error ? (
            <ErrorNotice
              error={customerResource.error}
              retry={customerResource.refresh}
            />
          ) : (
            <CustomerSelect
              customers={customerResource.value ?? []}
              disabled={busy}
              value={customer}
              onChange={setCustomer}
            />
          )}
          {selected && (
            <div className="customer-context">
              <UserRound size={16} />
              <span>Tier {selected.tier} pricing</span>
              {selected.has_credit_notice ? (
                <Pill tone="blue">Owner review required</Pill>
              ) : (
                <span className="mint-text">
                  <Check size={13} /> No credit notice
                </span>
              )}
            </div>
          )}
          <div className="form-section-heading second">
            <span className="numbered-icon">02</span>
            <div>
              <h2>Message</h2>
            </div>
          </div>
          <div className="message-input-top">
            <label htmlFor="order-message">Customer’s message</label>
            <LanguageSelect disabled={busy} value={lang} onChange={setLang} />
          </div>
          <div className="message-composer">
            <textarea
              id="order-message"
              disabled={busy}
              required
              maxLength={4000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={"Boss, Milo 5 pkt\nTepung 3 ctn\nMinyak 2 ctn"}
              rows={8}
            />
            <div>
              <span>
                <MessageSquareText size={13} /> English, Malay, 中文 — or a mix.
              </span>
              <span>{text.length.toLocaleString()} / 4,000</span>
            </div>
          </div>
          <div className="privacy-line">
            <ShieldCheck size={14} />
            <span>
              Phone numbers, emails and identity numbers are masked before
              saving.
            </span>
          </div>
          {!!error && <ErrorNotice error={error} />}
          <div className="form-bottom">
            <span>
              {service.mode === "demo" ? (
                <>
                  <i className="amber-dot" /> Offline catalogue match · non-AI
                </>
              ) : (
                <>
                  <Sparkles size={13} /> Your API handles extraction and checks
                </>
              )}
            </span>
            <button
              className="button primary"
              disabled={
                busy || !customer || !text.trim() || customerResource.loading
              }
            >
              {busy ? <Spinner /> : <Sparkles size={16} />}{" "}
              {busy ? "Preparing draft…" : "Create order draft"}{" "}
              {!busy && <ArrowRight size={16} />}
            </button>
          </div>
        </form>
        <aside className="new-order-aside">
          {samples.length > 0 ? (
            <section className="panel sample-panel">
              <span className="section-kicker">DEMO MESSAGES</span>
              <h3>Examples</h3>
              {samples.map((s) => (
                <button
                  key={s.title}
                  className="sample-card"
                  disabled={busy}
                  onClick={() => {
                    setText(s.body);
                    if (!customer)
                      setCustomer(
                        customerResource.value?.[0]?.customer_id ?? "",
                      );
                  }}
                >
                  <div>
                    <span className={`sample-dot ${s.tone}`} />
                    <strong>{s.title}</strong>
                    <ArrowUpRight size={14} />
                  </div>
                  <small>{s.tag}</small>
                  <pre>{s.body}</pre>
                </button>
              ))}
            </section>
          ) : (
            <section className="panel sample-panel">
              <span className="section-kicker">BEFORE YOU START</span>
              <h3>Message format</h3>
              <p>Include product, quantity, unit and conditions.</p>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
const ISSUE_COPY: Record<string, { title: string; body: string }> = {
  MULTIPLE_PACK_SIZES: {
    title: "Which pack size?",
    body: "More than one specification matches. Confirm the size with the customer, then choose a product.",
  },
  MULTIPLE_GRADES: {
    title: "Which grade?",
    body: "The message doesn’t identify a grade. Ask the customer and choose the correct item.",
  },
  MISSING_UOM: {
    title: "Confirm the order unit",
    body: "The unit is missing. Confirm how the quantity should be supplied.",
  },
  LOW_CONFIDENCE_MATCH: {
    title: "This item needs a closer look",
    body: "The message could not be matched confidently. Confirm the product, quantity and unit.",
  },
  INSUFFICIENT_STOCK: {
    title: "There isn’t enough stock",
    body: "Confirm a smaller quantity with the customer, then update the product line. No role can approve insufficient stock.",
  },
};
export function OrderDetail({
  id,
  service,
  me,
  navigate,
  complete,
  setDirty,
  changed,
  notify,
}: PageProps & { id: string; me: Me }) {
  const resource = useResource(() => service.draft(id), [service, id]);
  const [inputs, setInputs] = useState<LineInput[]>([]);
  const [deleted, setDeleted] = useState<string[]>([]);
  const [resolutions, setResolutions] = useState<Resolution[]>([]);
  const [edit, setEdit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [discard, setDiscard] = useState(false);
  const [note, setNote] = useState("");
  const [history, setHistory] = useState(false);
  const [conflictOpen, setConflictOpen] = useState(false);
  const [conflictError, setConflictError] = useState<unknown>();
  const [recovered, setRecovered] = useState(false);
  const retained = useRef<{
    inputs: LineInput[];
    deleted: string[];
    resolutions: Resolution[];
  } | null>(null);
  const beginRequest = useRequestScope([service, id]);
  const draft = resource.value;
  useEffect(() => {
    if (draft) {
      const edits = retained.current;
      retained.current = null;
      setInputs(edits?.inputs ?? draft.lines.map(toInput));
      setDeleted(edits?.deleted ?? []);
      setResolutions(edits?.resolutions ?? []);
      setEdit(!!edits);
      setDirty(!!edits);
    }
  }, [draft, setDirty]);
  useEffect(() => () => setDirty(false), [setDirty]);
  const mark = () => {
    setEdit(true);
    setDirty(true);
    setError(undefined);
  };
  const update = (line: string, patch: Partial<LineInput>) => {
    mark();
    setInputs((old) =>
      old.map((l) => (l.line_id === line ? { ...l, ...patch } : l)),
    );
  };
  const choose = (l: Line, c: Candidate) => {
    update(l.line_id, {
      sku_id: c.sku_id,
      family_id: c.family_id,
      pack_size: c.pack_size,
      grade: c.grade ?? null,
      uom: c.base_unit,
      confirmed_qty:
        inputs.find((i) => i.line_id === l.line_id)?.confirmed_qty ??
        l.requested_qty,
      match_source: "MANUAL_SELECTED",
    });
  };
  const saveResolution = (r: Resolution) => {
    mark();
    setResolutions((old) => [
      ...old.filter((i) => i.issue_id !== r.issue_id),
      r,
    ]);
  };
  const handleError = (err: unknown) => {
    setError(err);
    if (
      err instanceof ApiError &&
      err.error_code === "ALREADY_APPROVED" &&
      typeof err.details.do_number === "string"
    ) {
      setDirty(false);
      complete(`delivery/${err.details.do_number}`);
      changed();
    }
  };
  async function save() {
    if (busy) return;
    try {
      assertQuantities(
        inputs.filter((line) => !deleted.includes(line.line_id)),
      );
    } catch (err) {
      setError(err);
      return;
    }
    const current = beginRequest();
    setBusy(true);
    setError(undefined);
    try {
      const d = await service.save(id, {
        expected_version: draft!.version,
        lines: inputs.filter((l) => !deleted.includes(l.line_id)),
        deleted_line_ids: deleted,
        resolutions,
      });
      changed();
      if (!current()) return;
      resource.setValue(d);
      setRecovered(false);
      setDirty(false);
      setEdit(false);
      notify(
        `Version ${d.version} saved. ${d.blocking_issues.length ? "Review the remaining checks." : "All blocking checks are clear."}`,
      );
    } catch (e) {
      if (current()) handleError(e);
    } finally {
      if (current()) setBusy(false);
    }
  }
  async function approve() {
    if (busy) return;
    const current = beginRequest();
    setBusy(true);
    setError(undefined);
    try {
      const result = await service.approve(id, draft!.version);
      changed();
      if (!current()) return;
      setDirty(false);
      if ("do_number" in result) {
        complete(`delivery/${result.do_number}`);
        notify("Delivery order approved and generated.");
      } else {
        resource.refresh();
        notify("The saved order is now with the owner.");
      }
    } catch (e) {
      if (current()) handleError(e);
    } finally {
      if (current()) setBusy(false);
    }
  }
  if (resource.loading && !draft) return <Loading />;
  if (resource.error)
    return <ErrorNotice error={resource.error} retry={resource.refresh} />;
  if (!draft) return null;
  const editable = draft.allowed_actions.includes("EDIT_DRAFT");
  const unresolved = draft.issues.filter((i) => i.blocking && !i.resolved);
  const approveAction = draft.allowed_actions.includes(
    "APPROVE_AND_GENERATE_DO",
  );
  const ownerAction = draft.allowed_actions.includes("SUBMIT_FOR_OWNER");
  const savedCount = draft.lines.length - deleted.length;
  const invalid = invalidQuantities(
    inputs.filter((line) => !deleted.includes(line.line_id)),
  );
  const canApprove = (approveAction || ownerAction) && !edit;
  return (
    <>
      <button className="back-button" onClick={() => navigate("inbox")}>
        <ArrowLeft size={14} /> Back to order inbox
      </button>
      <div className="detail-heading">
        <div>
          <span className="eyebrow">
            ORDER #{shortId(id)}{" "}
            <span className="version-label">v{draft.version}</span>
          </span>
          <h1>{draft.customer.name}</h1>
          <div className="detail-meta">
            <span>Tier {draft.customer.tier}</span>
            <i />
            <span>{time(draft.created_at)} MYT</span>
            <i />
            <span>
              {draft.ai_mode === "FALLBACK"
                ? "Offline match · non-AI"
                : draft.ai_mode === "ALIAS_ONLY"
                  ? "Customer memory · non-AI"
                  : draft.ai_mode === "MIXED"
                    ? "Mixed extraction sources"
                    : "AI extraction"}
            </span>
          </div>
        </div>
        <div className="detail-heading-actions">
          <Status status={draft.status} />
          <button
            className="icon-button"
            title="Refresh saved order"
            aria-label="Refresh saved order"
            disabled={busy || edit}
            onClick={resource.refresh}
          >
            <RefreshCw size={16} />
          </button>
          <button
            className="button secondary small"
            onClick={() => setHistory(true)}
          >
            Activity
          </button>
        </div>
      </div>
      <Stepper
        step={
          draft.status === "DO_GENERATED"
            ? 3
            : draft.status === "PENDING_OWNER_APPROVAL"
              ? 2
              : 1
        }
      />
      {draft.status === "PENDING_OWNER_APPROVAL" && (
        <div className="info-banner blue">
          <ShieldCheck size={19} />
          <div>
            <strong>The owner has the next move.</strong>
            <p>
              Version {draft.version} is submitted and locked. View the approval
              queue for its decision.
            </p>
          </div>
          <button className="text-button" onClick={() => navigate("approvals")}>
            View approvals <ArrowRight size={14} />
          </button>
        </div>
      )}
      {draft.status === "DO_GENERATED" && (
        <div className="info-banner mint">
          <FileCheck2 size={19} />
          <div>
            <strong>This order is approved.</strong>
            <p>
              Your delivery order is ready and the approved record is locked.
            </p>
          </div>
          <button
            className="button primary small"
            onClick={() => navigate(`delivery/${draft.do_number}`)}
          >
            View delivery order <ArrowUpRight size={14} />
          </button>
        </div>
      )}
      {draft.status === "REJECTED" && (
        <div className="info-banner rose">
          <LockKeyhole size={18} />
          <div>
            <strong>This order is closed.</strong>
            <p>{draft.termination_note ?? "Create a new draft to continue."}</p>
          </div>
          <button className="text-button" onClick={() => navigate("new")}>
            Create a new order <Plus size={14} />
          </button>
        </div>
      )}
      {recovered && (
        <div className="info-banner blue">
          <ShieldCheck size={18} />
          <p>
            The latest order is loaded and your edits are kept. Review all
            changes, then save again.
          </p>
        </div>
      )}
      <fieldset className="review-fields" disabled={busy}>
        <div className="review-layout">
          <div className="review-main">
            <section className="panel original-message">
              <div className="panel-heading">
                <div className="inline-heading">
                  <MessageSquareText size={17} />
                  <h2>The customer’s words</h2>
                </div>
                <Pill>Masked original</Pill>
              </div>
              <MessageEvidence draft={draft} />
              <div className="message-caption">
                <ShieldCheck size={12} /> Original wording preserved. Private
                contact details masked.
              </div>
            </section>
            <section className="panel products-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">CHECK THE DETAILS</span>
                  <h2>
                    Products & quantities{" "}
                    <span className="count-bubble">{savedCount}</span>
                  </h2>
                </div>
                {edit ? (
                  <Pill tone="amber">Unsaved changes</Pill>
                ) : (
                  <span className="saved-label">
                    <Check size={13} /> Saved v{draft.version}
                  </span>
                )}
              </div>
              <div className="product-rows">
                {draft.lines
                  .filter((l) => !deleted.includes(l.line_id))
                  .map((line, index) => {
                    const input = inputs.find(
                      (i) => i.line_id === line.line_id,
                    );
                    if (!input) return null;
                    const selected = line.candidate_skus.find(
                      (c) => c.sku_id === input.sku_id,
                    );
                    const issue = draft.issues.find(
                      (i) =>
                        i.line_id === line.line_id && i.blocking && !i.resolved,
                    );
                    const changedLine =
                      JSON.stringify(input) !== JSON.stringify(toInput(line));
                    return (
                      <article
                        className={`product-row ${issue ? "needs-check" : ""}`}
                        key={line.line_id}
                      >
                        <div className="product-topline">
                          <span className="line-number">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <div>
                            <h3>
                              {selected?.display_name ??
                                line.description ??
                                "Unrecognized item"}
                            </h3>
                            <p>“{line.source_span}”</p>
                          </div>
                          {issue && (
                            <span className="check-label">
                              <AlertCircle size={13} />{" "}
                              {issue.code === "INSUFFICIENT_STOCK"
                                ? "Stock check"
                                : "Check needed"}
                            </span>
                          )}
                          {editable && (
                            <button
                              className="icon-button delete-line"
                              disabled={savedCount <= 1 || busy}
                              title={
                                savedCount <= 1
                                  ? "Keep at least one product"
                                  : "Remove product"
                              }
                              aria-label={`Remove ${line.description}`}
                              onClick={() => {
                                mark();
                                setDeleted((old) => [...old, line.line_id]);
                              }}
                            >
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                        {line.candidate_skus.length > 0 && !line.sku_id && (
                          <div className="candidate-grid">
                            {line.candidate_skus.map((c) => (
                              <button
                                type="button"
                                key={c.sku_id}
                                className={`candidate ${input.sku_id === c.sku_id ? "selected" : ""}`}
                                disabled={!editable || busy}
                                onClick={() => choose(line, c)}
                              >
                                <span className="radio-dot">
                                  {input.sku_id === c.sku_id && (
                                    <Check size={11} />
                                  )}
                                </span>
                                <div>
                                  <strong>{c.display_name}</strong>
                                  <span>
                                    {c.pack_size}
                                    {c.grade ? ` · Grade ${c.grade}` : ""}
                                  </span>
                                  <small>
                                    {money(c.tier_unit_price)} / {c.base_unit}{" "}
                                    <i /> {c.available_qty} in stock
                                  </small>
                                </div>
                              </button>
                            ))}
                          </div>
                        )}
                        <div className="line-fields">
                          <label>
                            Quantity
                            <input
                              type="number"
                              min={1}
                              max={100000}
                              step={1}
                              disabled={!editable || busy}
                              value={
                                Number.isNaN(input.confirmed_qty)
                                  ? ""
                                  : (input.confirmed_qty ?? line.requested_qty)
                              }
                              aria-label={`Quantity for ${line.description}`}
                              aria-invalid={
                                invalid.some(
                                  (item) => item.line_id === line.line_id,
                                ) || undefined
                              }
                              aria-describedby={
                                invalid.some(
                                  (item) => item.line_id === line.line_id,
                                )
                                  ? `quantity-error-${line.line_id}`
                                  : undefined
                              }
                              onChange={(e) =>
                                update(line.line_id, {
                                  confirmed_qty:
                                    e.target.value === ""
                                      ? NaN
                                      : Number(e.target.value),
                                })
                              }
                            />
                            {invalid.some(
                              (item) => item.line_id === line.line_id,
                            ) && (
                              <small
                                className="inline-error"
                                id={`quantity-error-${line.line_id}`}
                                role="alert"
                              >
                                Enter a whole quantity from 1 to 100,000.
                              </small>
                            )}
                          </label>
                          <label>
                            Unit
                            {editable && !line.uom ? (
                              <UnitSelect
                                label={`Unit for ${line.description}`}
                                value={input.uom ?? ""}
                                disabled={busy}
                                onChange={(value) =>
                                  update(line.line_id, {
                                    uom: value || null,
                                  })
                                }
                                units={[
                                  ...new Set(
                                    line.candidate_skus
                                      .map((c) => c.base_unit)
                                      .concat(
                                        [
                                          "ctn",
                                          "pkt",
                                          "tray",
                                          "papan",
                                          "box",
                                          "roll",
                                          "btl",
                                          "can",
                                          "tin",
                                          "unit",
                                        ],
                                        input.uom ? [input.uom] : [],
                                      ),
                                  ),
                                ]}
                              />
                            ) : (
                              <span className="readonly-field">
                                {input.uom ?? "—"}
                              </span>
                            )}
                          </label>
                          <label>
                            Available stock
                            <span
                              className={`readonly-field ${issue?.code === "INSUFFICIENT_STOCK" ? "amber-text" : ""}`}
                            >
                              {selected?.available_qty ??
                                line.available_qty ??
                                "—"}{" "}
                              {input.uom ?? ""}
                            </span>
                          </label>
                          <label>
                            Tier unit price
                            <span className="readonly-field">
                              {money(
                                selected?.tier_unit_price ??
                                  line.tier_unit_price,
                              )}
                            </span>
                          </label>
                          <label className="line-subtotal">
                            Subtotal
                            <span className="readonly-field">
                              {changedLine
                                ? "Save to update"
                                : money(line.subtotal_rm)}
                            </span>
                          </label>
                        </div>
                        {editable && input.sku_id && (
                          <details className="price-details">
                            <summary>
                              Price adjustment <ChevronDown size={12} />
                              {input.unit_price_override && (
                                <Pill tone="blue">
                                  {money(input.unit_price_override)}
                                </Pill>
                              )}
                            </summary>
                            <div className="price-adjustment">
                              <label>
                                Agreed unit price (RM)
                                <input
                                  type="text"
                                  inputMode="decimal"
                                  placeholder={
                                    selected?.tier_unit_price ??
                                    line.tier_unit_price ??
                                    "0.00"
                                  }
                                  value={input.unit_price_override ?? ""}
                                  disabled={busy}
                                  onChange={(e) =>
                                    update(line.line_id, {
                                      unit_price_override:
                                        e.target.value || null,
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Why was the price changed?
                                <input
                                  maxLength={500}
                                  value={input.override_reason ?? ""}
                                  disabled={busy}
                                  placeholder="Customer confirmed a unit price…"
                                  onChange={(e) =>
                                    update(line.line_id, {
                                      override_reason: e.target.value || null,
                                    })
                                  }
                                />
                              </label>
                            </div>
                            <p className="micro-copy">
                              Below-tier prices require the owner’s approval
                              after saving.
                            </p>
                          </details>
                        )}
                        {editable &&
                          input.match_source === "MANUAL_SELECTED" &&
                          input.sku_id && (
                            <label className="checkbox-label">
                              <input
                                type="checkbox"
                                checked={!!input.save_to_alias_cache}
                                onChange={(e) =>
                                  update(line.line_id, {
                                    save_to_alias_cache: e.target.checked,
                                    alias_scope: "CUSTOMER",
                                  })
                                }
                              />{" "}
                              Remember this phrase for {draft.customer.name}{" "}
                              only
                            </label>
                          )}
                        {line.saved_alias && (
                          <div className="memory-note">
                            <Sparkles size={12} /> Customer phrase remembered ·{" "}
                            {line.saved_alias.scope.toLowerCase()} scope
                          </div>
                        )}
                      </article>
                    );
                  })}
              </div>
              {deleted.length > 0 && (
                <div className="deleted-note">
                  {deleted.length} product{deleted.length === 1 ? "" : "s"} will
                  be removed when you save.
                  <button
                    className="text-button"
                    onClick={() => {
                      mark();
                      setDeleted([]);
                    }}
                  >
                    Undo removals
                  </button>
                </div>
              )}
              <div className="order-total">
                <span>
                  Order total{" "}
                  <small>
                    {edit
                      ? "Save your changes to refresh the total."
                      : draft.totals.is_complete
                        ? "Catalogue prices · MYR"
                        : "Awaiting a complete product selection"}
                  </small>
                </span>
                <strong>
                  {edit ? "Pending save" : money(draft.totals.order_total)}
                </strong>
              </div>
            </section>
            {draft.ignored_spans?.length > 0 && (
              <div className="info-banner amber">
                <AlertCircle size={17} />
                <div>
                  <strong>Some wording wasn’t included in the order.</strong>
                  <p>{draft.ignored_spans.map((s) => s.text).join(" · ")}</p>
                </div>
              </div>
            )}
            {draft.conditions.some(
              (i) => i.condition_kind !== "STOCK" && !i.resolved,
            ) &&
              editable && (
                <section className="panel conditions-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="section-kicker">
                        THE CUSTOMER’S CONDITIONS
                      </span>
                      <h2>Customer conditions</h2>
                    </div>
                  </div>
                  {draft.conditions
                    .filter((i) => i.condition_kind !== "STOCK" && !i.resolved)
                    .map((issue) => (
                      <ConditionEditor
                        key={issue.issue_id}
                        issue={issue}
                        draft={draft}
                        inputs={inputs}
                        deleted={deleted}
                        busy={busy}
                        resolution={resolutions.find(
                          (r) => r.issue_id === issue.issue_id,
                        )}
                        onResolve={saveResolution}
                        onPrice={(targets, price, note) => {
                          targets.forEach((t) =>
                            update(t, {
                              unit_price_override: price,
                              override_reason: note,
                            }),
                          );
                        }}
                      />
                    ))}
                </section>
              )}
          </div>
          <aside className="review-rail">
            <section className="panel checks-panel">
              <div className="rail-title">
                THE RIGHT NEXT STEP <ShieldCheck size={15} />
              </div>
              <div
                className={`check-summary ${unresolved.length ? "amber-text" : "mint-text"}`}
              >
                {unresolved.length ? (
                  <AlertCircle size={22} />
                ) : (
                  <CircleCheck size={22} />
                )}
                <div>
                  <strong>
                    {unresolved.length
                      ? `${unresolved.length} ${unresolved.length === 1 ? "check needs" : "checks need"} you`
                      : "The blocking checks are clear"}
                  </strong>
                </div>
              </div>
              {draft.issues.map((issue) => (
                <div
                  className={`check-item ${issue.resolved ? "resolved" : ""}`}
                  key={issue.issue_id}
                >
                  <span
                    className={`check-item-icon ${issue.resolved ? "mint" : "amber"}`}
                  >
                    {issue.resolved ? (
                      <Check size={13} />
                    ) : (
                      <MessageSquareText size={13} />
                    )}
                  </span>
                  <div>
                    <span className="check-owner">
                      {issue.condition_kind === "STOCK"
                        ? "SYSTEM CHECK"
                        : issue.resolved
                          ? "RESOLVED"
                          : issue.ask === "CUSTOMER"
                            ? "ASK THE CUSTOMER"
                            : issue.ask === "OWNER"
                              ? "ASK THE OWNER"
                              : "YOUR DECISION"}
                    </span>
                    <strong>
                      {issue.condition_kind === "STOCK"
                        ? issue.resolved
                          ? "The stock condition is met"
                          : "Stock condition checked"
                        : issue.condition_kind === "PRICE"
                          ? "A price was requested"
                          : issue.condition_kind
                            ? "A delivery condition"
                            : (ISSUE_COPY[issue.code]?.title ??
                              issue.code.replaceAll("_", " ").toLowerCase())}
                    </strong>
                    {!issue.resolved && (
                      <p>
                        {ISSUE_COPY[issue.code]?.body ??
                          "Confirm the condition below, then save your decision."}
                      </p>
                    )}
                    {issue.code === "INSUFFICIENT_STOCK" && (
                      <small className="amber-text">
                        Requested {String(issue.data_used.effective_qty)} ·
                        Available {String(issue.data_used.available_qty)}
                      </small>
                    )}
                  </div>
                </div>
              ))}
              {!draft.issues.length && (
                <div className="all-clear">
                  <Check size={15} /> Products, quantities and stock checked.
                </div>
              )}
            </section>
            {draft.clarification_draft && (
              <section className="panel clarification-card">
                <div className="rail-title">
                  <MessageSquareText size={15} /> CLARIFICATION
                </div>
                <h3>Clarification</h3>
                <span className="language-label">
                  {(
                    {
                      ms: "Bahasa Melayu",
                      en: "English",
                      zh: "中文",
                    } as Record<string, string>
                  )[draft.clarification_draft.language] ??
                    draft.clarification_draft.language}{" "}
                  · Message draft
                </span>
                <pre tabIndex={0}>{draft.clarification_draft.message}</pre>
                <CopyButton
                  text={draft.clarification_draft.message}
                  onCopy={notify}
                  onCopied={() =>
                    service.clarificationCopied?.(id, draft.version)
                  }
                  label="Copy clarification"
                />
                <p className="micro-copy">
                  Send manually; record the customer’s answer.
                </p>
              </section>
            )}
            {draft.escalation_preview.length > 0 && (
              <section className="panel escalation-card">
                <div className="rail-title">
                  <ShieldCheck size={14} /> OWNER’S DECISION
                </div>
                <Reasons reasons={draft.escalation_preview} />
              </section>
            )}
          </aside>
        </div>
      </fieldset>
      {!!error && (
        <ErrorNotice
          error={error}
          retry={
            error instanceof ApiError &&
            ["STALE_VERSION", "STOCK_CHANGED"].includes(error.error_code)
              ? () => {
                  setConflictError(undefined);
                  setConflictOpen(true);
                }
              : undefined
          }
          retryLabel="Review latest version"
        />
      )}
      {editable && (
        <div className="review-actions">
          <div>
            <ShieldCheck size={17} />
            <span>
              {edit
                ? "Save your changes before approving."
                : unresolved.length
                  ? `${unresolved.length} ${unresolved.length === 1 ? "check" : "checks"} to resolve before approval.`
                  : ownerAction
                    ? "This saved version will go to the owner."
                    : "You’re approving the current saved version."}
              <small>
                Version {draft.version} ·{" "}
                {edit ? "Unsaved changes" : "Saved and checked"}
              </small>
            </span>
          </div>
          <div className="action-buttons">
            {service.discard &&
              draft.allowed_actions.includes("CANCEL_DRAFT") && (
                <button
                  className="icon-button discard-button"
                  aria-label="Discard order draft"
                  disabled={busy}
                  onClick={() => setDiscard(true)}
                >
                  <Trash2 size={16} />
                </button>
              )}
            {edit && (
              <button
                className="button ghost"
                disabled={busy}
                onClick={() => {
                  setInputs(draft.lines.map(toInput));
                  setDeleted([]);
                  setResolutions([]);
                  setEdit(false);
                  setDirty(false);
                }}
              >
                Reset edits
              </button>
            )}
            <button
              className="button secondary"
              disabled={busy || !edit || !!invalid.length}
              onClick={save}
            >
              {busy ? <Spinner /> : <Save size={15} />}Save changes
            </button>
            <button
              className="button primary"
              disabled={busy || !canApprove}
              onClick={approve}
            >
              {busy ? (
                <Spinner />
              ) : ownerAction ? (
                <ShieldCheck size={15} />
              ) : (
                <FileCheck2 size={15} />
              )}{" "}
              {ownerAction ? "Send to owner" : "Approve & generate DO"}{" "}
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      )}
      {conflictOpen && (
        <Modal
          title="Review the latest order"
          onClose={() => !busy && setConflictOpen(false)}
        >
          <p className="modal-copy">
            This saved order has changed. Keep your edits for review against the
            latest version, or discard them and load the saved order. Nothing is
            saved or approved automatically.
          </p>
          {!!conflictError && <ErrorNotice error={conflictError} />}
          <div className="modal-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setConflictOpen(false)}
            >
              Cancel
            </button>
            {[true, false].map((keep) => (
              <button
                key={String(keep)}
                className={`button ${keep ? "primary" : "danger"}`}
                disabled={busy}
                onClick={async () => {
                  const current = beginRequest();
                  setConflictError(undefined);
                  setBusy(true);
                  try {
                    const latest = await service.draft(id);
                    if (!current()) return;
                    if (keep)
                      retained.current = {
                        inputs: rebaseInputs(draft, latest, inputs),
                        deleted: deleted.filter((lineId) =>
                          latest.lines.some((line) => line.line_id === lineId),
                        ),
                        resolutions: resolutions.filter((resolution) =>
                          latest.issues.some(
                            (issue) =>
                              issue.issue_id === resolution.issue_id &&
                              !issue.resolved,
                          ),
                        ),
                      };
                    resource.setValue(latest);
                    setRecovered(keep);
                    setConflictOpen(false);
                    setError(undefined);
                  } catch (err) {
                    if (current()) {
                      setConflictError(err);
                    }
                  } finally {
                    if (current()) setBusy(false);
                  }
                }}
              >
                {keep ? "Keep edits & load latest" : "Discard edits & reload"}
              </button>
            ))}
          </div>
        </Modal>
      )}
      {discard && (
        <Modal
          title="Close this draft?"
          onClose={() => !busy && setDiscard(false)}
        >
          <p className="modal-copy">
            Closing a draft keeps its history. To order again, create a new
            draft. Add a reason for the record.
          </p>
          <label className="field-label">
            Reason
            <textarea
              rows={3}
              maxLength={500}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Duplicate message, customer cancelled…"
            />
          </label>
          {!!error && <ErrorNotice error={error} />}
          <div className="modal-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setDiscard(false)}
            >
              Keep draft
            </button>
            <button
              className="button danger"
              disabled={busy || !note.trim()}
              onClick={async () => {
                setBusy(true);
                try {
                  await service.discard!(id, draft.version, note);
                  setDiscard(false);
                  setDirty(false);
                  changed();
                  resource.refresh();
                  notify("Draft closed. Its activity record is preserved.");
                } catch (e) {
                  setError(e);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? <Spinner /> : <Trash2 size={15} />}Close draft
            </button>
          </div>
        </Modal>
      )}
      {history && (
        <OrderActivity
          service={service}
          id={id}
          onClose={() => setHistory(false)}
        />
      )}
    </>
  );
}
function MessageEvidence({ draft }: { draft: Draft }) {
  const chars = Array.from(draft.masked_message);
  const spans = draft.issues
    .filter((i) => !i.resolved && i.span_start != null && i.span_end != null)
    .map((i) => ({ start: i.span_start!, end: i.span_end! }));
  return (
    <pre className="message-evidence">
      {chars.map((c, i) =>
        spans.some((s) => i >= s.start && i < s.end) ? (
          <mark key={i}>{c}</mark>
        ) : (
          c
        ),
      )}
    </pre>
  );
}
function ConditionEditor({
  issue,
  draft,
  inputs,
  deleted,
  busy,
  resolution,
  onResolve,
  onPrice,
}: {
  issue: Issue;
  draft: Draft;
  inputs: LineInput[];
  deleted: string[];
  busy: boolean;
  resolution?: Resolution;
  onResolve: (r: Resolution) => void;
  onPrice: (targets: string[], price: string, note: string) => void;
}) {
  const [choice, setChoice] = useState<"tier" | "accept" | "false">("tier");
  const [targets, setTargets] = useState<string[]>(
    issue.candidate_line_ids.length === 1 ? issue.candidate_line_ids : [],
  );
  const [price, setPrice] = useState("");
  const [note, setNote] = useState("");
  const [validation, setValidation] = useState("");
  const activeLines = draft.lines.filter((l) => !deleted.includes(l.line_id));
  return (
    <div className="condition-editor">
      <div className="condition-title">
        <Pill tone={issue.condition_kind === "PRICE" ? "blue" : "amber"}>
          {issue.condition_kind === "PRICE"
            ? "Price condition"
            : "Delivery condition"}
        </Pill>
        {resolution && (
          <span className="mint-text">
            <Check size={13} /> Decision ready to save
          </span>
        )}
      </div>
      <blockquote>“{issue.span}”</blockquote>
      <p className="micro-copy">
        The customer’s words are evidence. A quoted price is never applied
        automatically.
      </p>
      <div className="decision-options">
        <button
          className={choice === "tier" ? "selected" : ""}
          disabled={busy}
          onClick={() => setChoice("tier")}
        >
          <span className="radio-dot" />
          {issue.condition_kind === "PRICE"
            ? "Customer agrees to tier price"
            : "Condition confirmed with customer"}
        </button>
        {issue.condition_kind === "PRICE" && (
          <button
            className={choice === "accept" ? "selected" : ""}
            disabled={busy}
            onClick={() => setChoice("accept")}
          >
            <span className="radio-dot" />
            Accept a requested discount <small>Owner decides</small>
          </button>
        )}
        <button
          className={choice === "false" ? "selected" : ""}
          disabled={busy}
          onClick={() => setChoice("false")}
        >
          <span className="radio-dot" />
          This isn’t a condition
        </button>
      </div>
      {choice === "accept" && (
        <>
          <label className="field-label">
            Which products does this unit price apply to?
          </label>
          <div className="target-list">
            {activeLines.map((l) => (
              <label className="checkbox-label" key={l.line_id}>
                <input
                  type="checkbox"
                  checked={targets.includes(l.line_id)}
                  disabled={busy}
                  onChange={(e) =>
                    setTargets((t) =>
                      e.target.checked
                        ? [...t, l.line_id]
                        : t.filter((x) => x !== l.line_id),
                    )
                  }
                />
                {l.description} · {l.pack_size ?? "Choose specification first"}
              </label>
            ))}
          </div>
          <label className="field-label">
            Confirmed price per catalogue unit (RM)
            <input
              type="text"
              inputMode="decimal"
              placeholder="Enter the agreed unit price"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              disabled={busy}
            />
          </label>
        </>
      )}
      <label className="field-label">
        {choice === "accept"
          ? "Why was this price agreed?"
          : "What did you confirm?"}
        <textarea
          rows={2}
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={
            choice === "tier"
              ? "Customer confirmed the catalogue price / delivery condition…"
              : choice === "false"
                ? "Explain why this is not a condition…"
                : "Customer confirmed this price per carton…"
          }
          disabled={busy}
        />
      </label>
      {validation && (
        <div className="inline-error" role="alert">
          {validation}
        </div>
      )}
      <button
        className="button secondary small"
        disabled={
          busy ||
          !note.trim() ||
          (choice === "accept" &&
            (!targets.length || !/^\d+(?:\.\d{1,2})?$/.test(price)))
        }
        onClick={() => {
          setValidation("");
          if (choice === "accept") {
            if (!targets.length) {
              setValidation("Select a target product.");
              return;
            }
            if (
              targets.some((t) => !inputs.find((l) => l.line_id === t)?.sku_id)
            ) {
              setValidation(
                "Choose a product specification before agreeing its price.",
              );
              return;
            }
            onPrice(targets, price, note);
          }
          onResolve({
            issue_id: issue.issue_id,
            choice:
              choice === "accept"
                ? "ACCEPT_REQUESTED_PRICE"
                : choice === "false"
                  ? "NOT_A_CONDITION"
                  : "CONFIRMED_WITH_CUSTOMER",
            target_line_ids: choice === "accept" ? targets : [],
            ...(choice === "accept"
              ? { confirmed_unit_price: price, price_basis: "UNIT" as const }
              : {}),
            note,
          });
        }}
      >
        <Check size={14} />
        {resolution ? "Update decision" : "Record decision"}
      </button>
      <small className="record-hint">
        Save changes to apply this decision.
      </small>
    </div>
  );
}
function OrderActivity({
  service,
  id,
  onClose,
}: {
  service: Service;
  id: string;
  onClose: () => void;
}) {
  const r = useResource(() => service.activity(id), [service, id]);
  return (
    <Modal title="This order’s paper trail" onClose={onClose}>
      {r.loading ? (
        <Loading />
      ) : r.error ? (
        <ErrorNotice error={r.error} retry={r.refresh} />
      ) : (
        <div className="timeline">
          {!r.value?.length && (
            <Empty
              title="No activity yet"
              description="Saved changes and decisions for this order will appear here."
            />
          )}
          {r.value?.map((a) => (
            <div key={a.activity_id}>
              <span className="timeline-dot" />
              <section>
                <strong>{a.action.toLowerCase().replaceAll("_", " ")}</strong>
                <p>{a.detail}</p>
                <small>
                  {a.actor} · {time(a.created_at)} MYT
                </small>
              </section>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
