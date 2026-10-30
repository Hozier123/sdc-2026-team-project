import { useState } from "react";
import { LogOut, ShieldCheck, Zap } from "lucide-react";
import { HttpService } from "../lib/api";
import { defaultApiBase } from "../lib/connection";
import { useRequestScope } from "../lib/hooks";
import type { Me, Service } from "../lib/types";
import { ErrorNotice, Modal, Pill, Spinner } from "./ui";

export function ConnectionModal({ current, dirty, initialBase, reconnect, onConnect, onDemo, onClose }: {
  current: "demo" | "live";
  dirty: boolean;
  initialBase?: string;
  reconnect: boolean;
  onConnect: (service: Service, identity: Me, base: string) => void;
  onDemo: () => void;
  onClose: () => void;
}) {
  const [base, setBase] = useState(initialBase ?? defaultApiBase(import.meta.env.VITE_API_BASE_URL, import.meta.env.DEV));
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const begin = useRequestScope([]);
  return (
    <Modal className="connection-modal" title={reconnect ? "Reconnect your API session" : "Your workspace connection"} onClose={onClose}>
      <p className="modal-copy">
        Connect to the backend for orders, approvals and activity records. Your company, role and permissions are verified by the API session.
      </p>
      <Pill tone={reconnect || current === "demo" ? "amber" : "mint"}>
        {reconnect ? "Session required" : current === "demo" ? "Local demo active" : "API session active"}
      </Pill>
      <form className="form-stack" onSubmit={async (event) => {
        event.preventDefault();
        if (busy) return;
        if (dirty) {
          setError(new Error("Save or discard your changes before switching connections."));
          return;
        }
        const currentRequest = begin();
        setBusy(true);
        setError(undefined);
        try {
          const service = new HttpService(base, token.trim());
          const identity = await service.me();
          if (currentRequest()) {
            setToken("");
            onConnect(service, identity, base.trim());
          }
        } catch (failure) {
          if (currentRequest()) setError(failure);
        } finally {
          if (currentRequest()) setBusy(false);
        }
      }}>
        <label>API base URL
          <input type="url" required disabled={busy} value={base} onChange={(e) => setBase(e.target.value)} placeholder="https://your-api.example/api/v1" autoComplete="off" spellCheck={false} />
        </label>
        <label>Session token
          <input type="password" required disabled={busy} value={token} onChange={(e) => setToken(e.target.value)} placeholder="Your API session token" autoComplete="off" spellCheck={false} />
        </label>
        <div className="permission-note"><ShieldCheck size={17} /><p>
          The token stays in memory. After a reload, reconnect with your session token to read saved backend orders. To change role or company, connect with that role’s session token.
        </p></div>
        {!!error && <ErrorNotice error={error} />}
        <div className="modal-actions">
          <button type="button" className="button secondary" disabled={dirty || busy} onClick={onDemo}>
            <LogOut size={15} /> {current === "live" || reconnect ? "Return to local demo" : "Continue local demo"}
          </button>
          <button className="button primary" disabled={busy || !token.trim() || !base.trim()}>
            {busy ? <Spinner /> : <Zap size={15} />} {busy ? "Verifying session…" : "Connect API"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
