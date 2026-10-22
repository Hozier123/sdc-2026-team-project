import { Eye, FileCheck2, LockKeyhole, ShieldCheck } from "lucide-react";
import { PageHeading, Pill } from "./ui";

export function PrivacyPage({ mode }: { mode: "demo" | "live" | "fixture" }) {
  return (
    <div className="privacy-page">
      <PageHeading
        title="Privacy & data"
        description="What this workspace keeps, shares and lets you control."
      />
      <section className="panel privacy-summary">
        <div className="privacy-emblem">
          <ShieldCheck size={27} />
        </div>
        <div>
          <Pill tone={mode === "live" ? "mint" : "amber"}>
            {mode === "demo"
              ? "Local demo · synthetic data"
              : mode === "fixture"
                ? "Fixture mock · synthetic responses"
                : "Connected API session"}
          </Pill>
          <h2>Your orders stay under human control.</h2>
          <p>
            {mode === "fixture"
              ? "A local fixture server returns fixed synthetic snapshots for interface checks. It does not parse real orders, call AI or manage inventory."
              : mode === "demo"
                ? "Use fictional customers and order messages here. This demo matches a local catalogue and does not call an AI service."
                : "Messages you submit are sent to your configured API. That service controls storage, access and any downstream model processing."}
          </p>
        </div>
      </section>
      <div className="privacy-grid">
        <section className="panel privacy-section">
          <div className="rail-title">
            <Eye size={17} /> WHAT WE USE
          </div>
          <h2>Only the order context.</h2>
          <p>
            Customer selection, order text, catalogue products, tier prices,
            stock and your saved decisions support order preparation and review.
          </p>
          <p>
            The local demo masks phone numbers, email addresses and identity
            numbers before saving. In API mode, the backend must mask message
            text before storing it or sending it to a model. Raw text is sent to
            that backend when you submit.
          </p>
          <p>
            This app does not automatically upload your document folders or
            connect to WhatsApp. Clarifications and replies are drafts you copy
            and send yourself.
          </p>
        </section>
        <section className="panel privacy-section">
          <div className="rail-title">
            <LockKeyhole size={17} /> WHO CAN SEE IT
          </div>
          <h2>A role for every action.</h2>
          <p>
            Clerks prepare orders and approve routine ones. Owners decide
            exceptions. Warehouse users receive a picking view without prices,
            totals, contacts or original messages.
          </p>
          <p>
            In API mode, the backend must enforce identity, tenant isolation and
            field filtering. The local role picker demonstrates these views; it
            is not production authentication.
          </p>
          <p>
            Your session token stays in this tab’s memory. It is not saved in a
            URL or local storage. Reloading returns to the local demo.
          </p>
        </section>
        <section className="panel privacy-section">
          <div className="rail-title">
            <FileCheck2 size={17} /> WHAT IS KEPT
          </div>
          <h2>Decisions with a record.</h2>
          <p>
            Saved demo drafts, delivery orders, customer phrase mappings and
            activity are stored in this browser. They do not automatically move
            to another device. Unsaved edits may be lost on reload.
          </p>
          <p>
            In API mode, retention and deletion depend on the backend operator’s
            policy. This frontend does not configure a retention period or
            provide a deletion service.
          </p>
          <p>
            Approved delivery orders are read-only. Contact your workspace
            operator to request access or correction of customer information.
            Customer phrase memory is a human-confirmed rule, not AI training.
          </p>
        </section>
        <section className="panel privacy-section">
          <div className="rail-title">
            <ShieldCheck size={17} /> BEFORE REAL USE
          </div>
          <h2>Make the handling clear.</h2>
          <p>
            Use synthetic data for this prototype. Before handling real customer
            information, the operator needs to explain processing purposes,
            providers, access, retention and correction channels to customers.
          </p>
          <p>
            Any model or hosting provider used by the connected backend may
            process data outside the customer’s country. Provider selection,
            data location and applicable requirements need review before
            deployment.
          </p>
          <p>
            The introduction uses remote background media; opening it requests
            those assets from their host. No order text is included in those
            media requests. This page explains the prototype’s handling and is
            not a certification of PDPA compliance.
          </p>
        </section>
      </div>
      <p className="privacy-footnote">
        Last updated 22 October 2026 · Real backend and model integrations still
        require verification.
      </p>
    </div>
  );
}
