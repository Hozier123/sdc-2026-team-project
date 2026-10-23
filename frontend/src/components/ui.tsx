import { useEffect, useId, useRef, type ReactNode } from "react";
import {
  Check,
  Copy,
  LoaderCircle,
  X,
  ArrowUpRight,
  Inbox,
  AlertCircle,
  LockKeyhole,
} from "lucide-react";
import {
  ApiError,
  STATUS,
  type DraftStatus,
  type Reason,
  money,
} from "../lib/types";
export const pretty = (text: string) =>
  text
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (s) => s.toUpperCase());
export const shortId = (id: string) => id.replace("DRF_", "").slice(0, 6);
export const time = (date: string) =>
  new Date(date).toLocaleTimeString("en-MY", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Kuala_Lumpur",
  });
export const dateLabel = (date: string) =>
  new Date(date).toLocaleDateString("en-MY", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kuala_Lumpur",
  });
export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <span className={`pill ${tone}`}>
      <i />
      {children}
    </span>
  );
}
export function Status({ status }: { status: DraftStatus }) {
  return (
    <Pill tone={STATUS[status]?.tone}>
      {STATUS[status]?.label ?? pretty(status)}
    </Pill>
  );
}
export function Spinner() {
  return <LoaderCircle size={16} className="spin" aria-hidden="true" />;
}
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}
export function ErrorNotice({
  error,
  retry,
  retryLabel = "Refresh and try again",
}: {
  error: unknown;
  retry?: () => void;
  retryLabel?: string;
}) {
  const denied =
    error instanceof ApiError &&
    ["FORBIDDEN_ACTION", "FORBIDDEN", "HTTP_403"].includes(error.error_code);
  const expired =
    error instanceof ApiError &&
    ["INVALID_TOKEN", "UNAUTHORIZED", "HTTP_401"].includes(error.error_code);
  const Icon = denied || expired ? LockKeyhole : AlertCircle;
  const message =
    error instanceof Error
      ? error.message
      : "Something went wrong. Please try again.";
  return (
    <div
      className={`error-notice${denied || expired ? " access-notice" : ""}`}
      role="alert"
    >
      <Icon size={18} aria-hidden="true" />
      <div>
        <strong>
          {denied
            ? "You don’t have access to this action"
            : expired
              ? "Your session has expired"
              : "Unable to complete this request"}
        </strong>
        <p>{message}</p>
        {(denied || expired) && (
          <p>
            {denied
              ? "Ask your workspace owner to check your role and permissions."
              : "Open Connect API in the sidebar to reconnect your session."}
          </p>
        )}
        {error instanceof ApiError && (
          <small>
            {error.error_code}
            {error.requestId ? ` · Request ${error.requestId}` : ""}
          </small>
        )}
        {retry && !denied && !expired && (
          <button className="button secondary small" onClick={retry}>
            {retryLabel} <ArrowUpRight size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
export function Empty({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty" role="status">
      <div className="empty-icon">
        <Inbox size={26} />
      </div>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {children}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const titleId = useId();
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const initial = useRef(document.activeElement as HTMLElement | null);
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const el = ref.current;
    const focusables = () =>
      Array.from(
        el?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]',
        ) ?? [],
      );
    focusables()[0]?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeRef.current();
      }
      if (e.key === "Tab") {
        const items = focusables(),
          first = items[0],
          last = items.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", key);
      initial.current?.focus();
    };
  }, []);
  return (
    <div
      className="modal-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header>
          <h2 id={titleId}>{title}</h2>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={19} />
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}
export function CopyButton({
  text,
  onCopy,
  onCopied,
  label = "Copy message",
}: {
  text: string;
  onCopy: (s: string) => void;
  onCopied?: () => void | Promise<void>;
  label?: string;
}) {
  return (
    <button
      className="button secondary small"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          onCopy("Copied to clipboard. Send it when you’re ready.");
          void Promise.resolve()
            .then(() => onCopied?.())
            .catch(() => undefined);
        } catch {
          onCopy(
            "Clipboard is unavailable. Select and copy the message manually.",
          );
        }
      }}
    >
      <Copy size={14} />
      {label}
    </button>
  );
}
export function Reasons({ reasons }: { reasons: Reason[] }) {
  return (
    <div className="reason-list">
      {reasons.map((r, i) => (
        <div className="reason" key={`${r.code}-${i}`}>
          <span className="reason-dot" />
          <div>
            <strong>
              {r.code === "PRICE_OVERRIDE_BELOW_TIER"
                ? "A price needs a decision"
                : r.code === "AMOUNT_OVER_THRESHOLD"
                  ? "Order exceeds the approval threshold"
                  : "Customer has a credit notice"}
            </strong>
            <p>
              {r.code === "PRICE_OVERRIDE_BELOW_TIER"
                ? `Tier price ${money(String(r.detail.tier_price ?? "0"))} → requested ${money(String(r.detail.applied_price ?? "0"))}`
                : r.code === "AMOUNT_OVER_THRESHOLD"
                  ? `Threshold ${money(String(r.detail.threshold_rm ?? r.detail.amount_threshold_rm ?? "0"))}`
                  : "The owner needs to review this customer’s order."}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
export function Stepper({ step }: { step: number }) {
  return (
    <div className="stepper" role="list" aria-label="Order progress">
      {["Receive message", "Review & check", "Approve", "Delivery order"].map(
        (s, i) => (
          <div
            key={s}
            role="listitem"
            aria-current={i === step ? "step" : undefined}
            className={i < step ? "complete" : i === step ? "current" : ""}
          >
            <span>
              {i < step ? <Check size={12} /> : String(i + 1).padStart(2, "0")}
            </span>
            <small>{s}</small>
            {i < 3 && <i />}
          </div>
        ),
      )}
    </div>
  );
}

export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {children}
    </div>
  );
}
