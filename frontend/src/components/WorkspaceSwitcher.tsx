import { createPortal } from "react-dom";
import { useChoiceMenu } from "./useChoiceMenu";
import { Check, ChevronDown, Building2 } from "lucide-react";

const companies = [
  { id: "T1", name: "Bintang Wholesale", initials: "BW" },
  { id: "T2", name: "Bina Hardware", initials: "BH" },
];

export function WorkspaceSwitcher({
  tenant,
  companyName,
  mode,
  onChange,
}: {
  tenant: string;
  companyName?: string;
  mode: "demo" | "live";
  onChange: (id: string) => void;
}) {
  const {
    open,
    position,
    trigger,
    menu,
    id,
    close,
    toggle,
    onTriggerKeyDown,
    onMenuKeyDown,
  } = useChoiceMenu();
  const name = companyName ?? "Your workspace";
  const initials =
    mode === "demo"
      ? companies.find((c) => c.id === tenant)?.initials
      : name
          .split(/\s+/)
          .slice(0, 2)
          .map((s) => s[0])
          .join("");
  return (
    <div className="company-switcher">
      <button
        ref={trigger}
        className="company-trigger"
        aria-label={`Switch company: ${name}`}
        aria-haspopup={mode === "demo" ? "menu" : undefined}
        aria-expanded={mode === "demo" ? open : undefined}
        aria-controls={open ? id : undefined}
        disabled={mode !== "demo"}
        onClick={toggle}
        onKeyDown={mode === "demo" ? onTriggerKeyDown : undefined}
      >
        <span
          className={`company-avatar ${tenant === "T2" ? "hardware" : ""}`}
          aria-hidden="true"
        >
          {initials || <Building2 size={18} />}
        </span>
        <span className="company-summary">
          <strong title={name}>{name}</strong>
          <small>
            {mode === "demo" ? "Demo company" : "Company workspace"}
          </small>
        </span>
        {mode === "demo" && (
          <ChevronDown
            size={15}
            className="company-chevron"
            aria-hidden="true"
          />
        )}
      </button>
      {open &&
        createPortal(
          <div
            ref={menu}
            id={id}
            className="company-menu"
            style={{ ...position, visibility: position ? "visible" : "hidden" }}
            onKeyDown={onMenuKeyDown}
          >
            <div className="company-menu-heading">
              <span>Switch company</span>
              <span className="company-demo-tag">Demo</span>
            </div>
            <div role="menu" aria-label="Company workspaces">
              {companies.map((company) => (
                <button
                  key={company.id}
                  role="menuitemradio"
                  aria-checked={tenant === company.id}
                  className="company-option"
                  onClick={() => {
                    if (company.id !== tenant) onChange(company.id);
                    close(true);
                  }}
                >
                  <span
                    className={`company-avatar ${company.id === "T2" ? "hardware" : ""}`}
                    aria-hidden="true"
                  >
                    {company.initials}
                  </span>
                  <span className="company-summary">
                    <strong>{company.name}</strong>
                    <small>
                      {tenant === company.id
                        ? "Current company"
                        : "Switch to this company"}
                    </small>
                  </span>
                  {tenant === company.id && (
                    <Check
                      size={17}
                      className="company-selected"
                      aria-hidden="true"
                    />
                  )}
                </button>
              ))}
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
