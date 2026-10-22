import { useEffect } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown, Languages, Sparkles, UserRound } from "lucide-react";
import type { Customer } from "../lib/types";
import { useChoiceMenu } from "./useChoiceMenu";

type Option = {
  value: string;
  label: string;
  detail?: string;
  initials?: string;
  notice?: boolean;
};

function FormSelect({
  label, value, options, onChange, disabled = false, kind = "customer", required = false,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  disabled?: boolean;
  kind?: "customer" | "language" | "unit";
  required?: boolean;
}) {
  const compact = kind === "language";
  const unit = kind === "unit";
  const { open, position, trigger, menu, id, close, toggle, onTriggerKeyDown, onMenuKeyDown } = useChoiceMenu(
    compact ? "end" : "start",
    { matchTrigger: !compact && !unit, maxWidth: unit ? 224 : compact ? 288 : 480, itemRole: "option" },
  );
  const selected = options.find(option => option.value === value) ?? options[0];
  useEffect(() => {
    if (disabled) close();
  }, [disabled]);
  return (
    <span className={`form-select ${compact ? "form-select-compact" : `form-select-${kind}`}`}>
      <button
        type="button"
        ref={trigger}
        role="combobox"
        aria-label={label}
        aria-describedby={`${id}-value`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-required={required || undefined}
        disabled={disabled}
        className={`form-select-trigger ${!value ? "is-placeholder" : ""}`}
        onClick={toggle}
        onKeyDown={onTriggerKeyDown}
      >
        {compact ? <Languages size={16} aria-hidden="true" /> : !unit && (
          <span className="form-select-avatar" aria-hidden="true">
            {selected?.initials || <UserRound size={17} />}
          </span>
        )}
        <span className="form-select-value" id={`${id}-value`}>{selected?.label}</span>
        {!compact && selected?.detail && <span className="form-select-tier">{selected.detail}</span>}
        <ChevronDown className="form-select-chevron" size={15} aria-hidden="true" />
      </button>
      {open && !disabled && createPortal(
        <div
          ref={menu}
          className={`company-menu form-select-menu ${kind}-menu`}
          style={{ ...position, visibility: position ? "visible" : "hidden" }}
          onKeyDown={onMenuKeyDown}
        >
          <div className="form-select-menu-heading">{unit ? "Unit" : compact ? "Message language" : "Customers"}</div>
          <div id={id} role="listbox" aria-label={label}>
            {options.map(option => (
              <button
                type="button"
                role="option"
                tabIndex={-1}
                aria-selected={option.value === value}
                data-label={option.label}
                key={option.value}
                className={`form-select-option ${!option.value ? "form-select-clear" : ""}`}
                onClick={() => { onChange(option.value); close(true); }}
              >
                {!unit && <span className={`form-select-avatar ${compact ? "language-avatar" : ""}`} aria-hidden="true">
                  {option.initials || (compact ? <Sparkles size={17} /> : <UserRound size={17} />)}
                </span>}
                <span className="form-select-option-copy">
                  <span className="form-select-option-label">{option.label}</span>
                  {(option.detail || option.notice) && (
                    <span className="form-select-option-meta">
                      {option.detail && <span>{option.detail}</span>}
                      {option.notice && <span className="form-select-notice">Credit notice</span>}
                    </span>
                  )}
                </span>
                {option.value === value && <Check className="form-select-check" size={17} aria-hidden="true" />}
              </button>
            ))}
          </div>
        </div>, document.body,
      )}
    </span>
  );
}

export function CustomerSelect({ customers, ...props }: {
  customers: Customer[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return <FormSelect
    {...props}
    label="Customer"
    required
    options={[
      { value: "", label: "Select a customer" },
      ...customers.map(customer => ({
        value: customer.customer_id,
        label: customer.name,
        detail: `Tier ${customer.tier}`,
        initials: customer.name.split(/\s+/).slice(0, 2).map(word => word[0]).join(""),
        notice: customer.has_credit_notice,
      })),
    ]}
  />;
}

export function LanguageSelect(props: { value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return <FormSelect {...props} label="Message language" kind="language" options={[
    { value: "auto", label: "Auto-detect language" },
    { value: "en", label: "English", initials: "EN" },
    { value: "ms", label: "Bahasa Melayu", initials: "MS" },
    { value: "zh", label: "中文", initials: "中" },
  ]} />;
}

export function UnitSelect({ units, ...props }: {
  label: string;
  units: string[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return <FormSelect {...props} kind="unit" required options={[
    { value: "", label: "Confirm unit" },
    ...units.map(value => ({ value, label: value })),
  ]} />;
}
