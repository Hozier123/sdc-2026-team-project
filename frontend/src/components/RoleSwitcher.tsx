import { createPortal } from "react-dom";
import {
  Boxes,
  Check,
  ChevronDown,
  ClipboardCheck,
  ShieldCheck,
} from "lucide-react";
import type { Role } from "../lib/types";
import { useChoiceMenu } from "./useChoiceMenu";

const roles = [
  {
    id: "CLERK" as Role,
    label: "Order clerk",
    description: "Create and review orders",
    Icon: ClipboardCheck,
    tone: "clerk",
  },
  {
    id: "OWNER" as Role,
    label: "Owner",
    description: "Review and decide approvals",
    Icon: ShieldCheck,
    tone: "owner",
  },
  {
    id: "WAREHOUSE" as Role,
    label: "Warehouse",
    description: "Pick and dispatch deliveries",
    Icon: Boxes,
    tone: "warehouse",
  },
];

export function RoleSwitcher({
  role,
  onChange,
}: {
  role: Role;
  onChange: (role: Role) => void;
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
  } = useChoiceMenu("end");
  const selected = roles.find((item) => item.id === role)!;
  return (
    <>
      <button
        ref={trigger}
        className="role-trigger"
        aria-label={`Switch demo role: ${selected.label}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={toggle}
        onKeyDown={onTriggerKeyDown}
      >
        <span>
          {selected.label}
          <span className="role-trigger-demo"> · demo</span>
        </span>
        <ChevronDown size={12} aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div
            ref={menu}
            id={id}
            className="company-menu role-menu"
            style={{ ...position, visibility: position ? "visible" : "hidden" }}
            onKeyDown={onMenuKeyDown}
          >
            <div className="company-menu-heading">
              <span>Switch role</span>
              <span className="company-demo-tag">Demo</span>
            </div>
            <div role="menu" aria-label="Demo roles">
              {roles.map(({ id, label, description, Icon, tone }) => (
                <button
                  key={id}
                  role="menuitemradio"
                  aria-checked={role === id}
                  className="company-option"
                  onClick={() => {
                    if (role !== id) onChange(id);
                    close(true);
                  }}
                >
                  <span
                    className={`role-option-icon ${tone}`}
                    aria-hidden="true"
                  >
                    <Icon size={18} />
                  </span>
                  <span className="company-summary">
                    <strong>{label}</strong>
                    <small>{description}</small>
                  </span>
                  {role === id && (
                    <Check
                      className="company-selected"
                      size={17}
                      aria-hidden="true"
                    />
                  )}
                </button>
              ))}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
