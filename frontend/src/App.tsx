import {
  Component,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Boxes,
  Check,
  CheckCheck,
  ChevronDown,
  CircleHelp,
  ClipboardCheck,
  FileCheck2,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  MessageSquareText,
  Plus,
  PlugZap,
  Radio,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  X,
  Zap,
  Activity as ActivityIcon,
} from "lucide-react";
import { DemoService } from "./lib/demo";
import { DEFAULT_API_BASE, HttpService } from "./lib/api";
import { useAiControl, useRequestScope, useResource } from "./lib/hooks";
import { PrivacyPage } from "./components/PrivacyPage";
import { WorkspaceSwitcher } from "./components/WorkspaceSwitcher";
import { RoleSwitcher } from "./components/RoleSwitcher";
import {
  type Activity,
  type AiStatus,
  type Approval,
  type DraftSummary,
  type Me,
  type Role,
  type Service,
  STATUS,
} from "./lib/types";
import {
  CopyButton,
  dateLabel,
  Empty,
  ErrorNotice,
  Loading,
  Modal,
  Pill,
  shortId,
  Spinner,
  Status,
  time,
} from "./components/ui";
import { NewOrder, OrderDetail } from "./components/orders";
import { overviewQueue, validRoute } from "./lib/review";
const PlanetGreeting = lazy(() => import("./components/PlanetGreeting"));
import {
  ApprovalDetail,
  ApprovalsPage,
  DeliveryPage,
  DeliveriesPage,
  WarehousePage,
  ActivityPage,
} from "./components/fulfillment";

import type { Navigate, Notify } from "./lib/types";
import { PageHeading } from "./components/ui";
export const APP_VERSION = "1.4.0";
const links = [
  { path: "workspace", label: "Overview", Icon: LayoutDashboard },
  { path: "new", label: "New order", Icon: Plus },
  { path: "inbox", label: "Order inbox", Icon: Inbox },
  { path: "approvals", label: "Owner approvals", Icon: ClipboardCheck },
  { path: "delivery-orders", label: "Delivery orders", Icon: FileCheck2 },
  { path: "activity", label: "Activity log", Icon: ActivityIcon },
];
const hash = () =>
  decodeURIComponent(location.hash.replace(/^#\/?/, "")) || "intro";

function ResourceView<T>({
  resource,
  children,
}: {
  resource: {
    value?: T;
    error?: unknown;
    loading: boolean;
    refresh: () => void;
  };
  children: (value: T) => ReactNode;
}) {
  if (resource.error)
    return <ErrorNotice error={resource.error} retry={resource.refresh} />;
  if (resource.value === undefined) return <Loading />;
  return children(resource.value);
}
class Boundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    return this.state.error ? (
      <div className="crash">
        <h1>Let’s get back to clarity.</h1>
        <p>
          This screen could not be displayed. Your saved orders are still in the
          local workspace.
        </p>
        <button
          className="button primary"
          onClick={() => {
            location.hash = "/workspace";
            location.reload();
          }}
        >
          Reload workspace
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
export default function App() {
  return (
    <Boundary>
      <Workspace />
    </Boundary>
  );
}
function Workspace() {
  const [route, setRoute] = useState(hash);
  const routeRef = useRef(route);
  routeRef.current = route;
  const [demoRole, setDemoRole] = useState<Role>("CLERK");
  const [tenant, setTenant] = useState("T1");
  const demo = useMemo(
    () => new DemoService(demoRole, tenant, localStorage),
    [demoRole, tenant],
  );
  const [live, setLive] = useState<Service | null>(null);
  const service: Service = live ?? demo;
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty;
  const [pending, setPending] = useState<string | null>(null);
  const [sidebar, setSidebar] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!sidebar) return;
    const previous = document.activeElement as HTMLElement | null;
    const panel = sidebarRef.current;
    const items = () =>
      Array.from(
        panel?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), select:not(:disabled), a[href]",
        ) ?? [],
      );
    items()[0]?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setSidebar(false);
      }
      if (event.key !== "Tab") return;
      const controls = items(),
        first = controls[0],
        last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [sidebar]);
  const [settings, setSettings] = useState(false);
  const [permissionsOpen, setPermissionsOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);
  const notify = useCallback((message: string) => setNotice(message), []);
  const changed = useCallback(() => setRevision((v) => v + 1), []);
  const forceNav = useCallback((path: string) => {
    setDirty(false);
    dirtyRef.current = false;
    setPending(null);
    setRoute(path);
    routeRef.current = path;
    location.hash = `/${path}`;
    setSidebar(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, []);
  const navigate: Navigate = useCallback(
    (path) => {
      if (dirtyRef.current && path !== routeRef.current) {
        setPending(path);
        return;
      }
      forceNav(path);
    },
    [forceNav],
  );
  useEffect(() => {
    const onHash = () => {
      const next = hash();
      if (next === routeRef.current) return;
      if (dirtyRef.current) {
        setPending(next);
        history.replaceState(null, "", `#/${routeRef.current}`);
        return;
      }
      forceNav(next);
    };
    addEventListener("hashchange", onHash);
    return () => removeEventListener("hashchange", onHash);
  }, [forceNav]);
  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => {
      if (dirtyRef.current) {
        event.preventDefault();
      }
    };
    addEventListener("beforeunload", before);
    return () => removeEventListener("beforeunload", before);
  }, []);
  useEffect(() => {
    if (notice) {
      const timeout = setTimeout(() => setNotice(""), 5500);
      return () => clearTimeout(timeout);
    }
  }, [notice]);
  const identity = useResource(() => service.me(), [service]);
  const me = identity.value;
  const business = !!me && me.role !== "WAREHOUSE";
  const draftsResource = useResource(
    () => service.drafts(),
    [service, revision, me?.role],
    business,
  );
  const approvalsResource = useResource(
    () => service.approvals(),
    [service, revision, me?.role],
    business,
  );
  const activityResource = useResource(
    () => service.activity(),
    [service, revision, me?.role],
    business,
  );
  const aiResource = useResource(() => service.aiStatus(), [service], !!me);
  const ai = aiResource.value;
  const wakeEnabled =
    !!me?.permissions.includes("WAKE_AI") &&
    route !== "intro" &&
    route !== "privacy";
  const { busy: wakeBusy, wake } = useAiControl(
    service,
    wakeEnabled,
    aiResource.refresh,
    notify,
  );
  const active = route.split("/")[0];
  const routeValid =
    validRoute(route) && (active !== "warehouse" || me?.role === "WAREHOUSE");
  const selectedNavigation = settings
    ? "connection"
    : permissionsOpen
      ? "permissions"
      : active === "order"
        ? "inbox"
        : active === "approval"
          ? "approvals"
          : active === "delivery"
            ? "delivery-orders"
            : active;
  const setRole = (role: Role) => {
    if (dirty) {
      notify("Save your changes before switching demo roles.");
      return;
    }
    setDemoRole(role);
    forceNav(role === "WAREHOUSE" ? "warehouse" : "workspace");
  };
  if (route === "intro")
    return (
      <Suspense fallback={<Loading label="Loading introduction…" />}>
        <PlanetGreeting onEnter={() => navigate("workspace")} />
      </Suspense>
    );
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to main content
      </a>
      {sidebar && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setSidebar(false)}
        />
      )}
      <aside
        ref={sidebarRef}
        id="workspace-navigation"
        className={`sidebar ${sidebar ? "open" : ""}`}
      >
        <button
          className="brand"
          onClick={() => navigate("workspace")}
          aria-label="KiraOrder overview"
        >
          <span className="brand-glyph">✦</span>
          <span>
            KiraOrder<small>FOR ORBYTE</small>
          </span>
        </button>
        <WorkspaceSwitcher
          tenant={tenant}
          companyName={me?.tenant.name}
          mode={service.mode}
          onChange={(nextTenant) => {
            if (dirty) {
              notify("Save your changes before switching workspaces.");
              return;
            }
            setTenant(nextTenant);
            forceNav(demoRole === "WAREHOUSE" ? "warehouse" : "workspace");
          }}
        />
        <div className="nav-caption">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {me?.role === "WAREHOUSE" ? (
            <button
              className={`nav-item ${selectedNavigation === "warehouse" ? "selected" : ""}`}
              aria-current={
                selectedNavigation === "warehouse" ? "page" : undefined
              }
              onClick={() => navigate("warehouse")}
            >
              <Boxes size={18} />
              <span>Warehouse</span>
            </button>
          ) : (
            links
              .filter(
                ({ path }) =>
                  path !== "new" || me?.permissions.includes("EDIT_DRAFT"),
              )
              .map(({ path, label, Icon }) => (
                <button
                  key={path}
                  className={`nav-item ${selectedNavigation === path ? "selected" : ""}`}
                  aria-current={
                    selectedNavigation === path ? "page" : undefined
                  }
                  onClick={() => navigate(path)}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                  {path === "inbox" &&
                    !!draftsResource.value?.filter(
                      (d) => d.status === "DISAMBIGUATION_REQUIRED",
                    ).length && (
                      <em>
                        {
                          draftsResource.value!.filter(
                            (d) => d.status === "DISAMBIGUATION_REQUIRED",
                          ).length
                        }
                      </em>
                    )}
                  {path === "approvals" &&
                    !!approvalsResource.value?.filter(
                      (a) => a.status === "PENDING",
                    ).length && (
                      <em className="blue">
                        {
                          approvalsResource.value!.filter(
                            (a) => a.status === "PENDING",
                          ).length
                        }
                      </em>
                    )}
                </button>
              ))
          )}
        </nav>
        <div className="sidebar-section">
          <div className="nav-caption">SETTINGS</div>
          <nav aria-label="Workspace settings">
            <button
              className={`nav-item ${selectedNavigation === "connection" ? "selected" : ""}`}
              aria-haspopup="dialog"
              aria-expanded={settings}
              onClick={() => {
                setSidebar(false);
                setSettings(true);
              }}
            >
              <PlugZap size={18} />
              <span>
                {service.mode === "demo" ? "Connect API" : "API connection"}
              </span>
              <i
                className={`connection-light ${service.mode === "live" ? "connected" : ""}`}
                aria-label={
                  service.mode === "live" ? "Connected" : "Not connected"
                }
              />
            </button>
            <button
              className={`nav-item ${selectedNavigation === "permissions" ? "selected" : ""}`}
              aria-haspopup="dialog"
              aria-expanded={permissionsOpen}
              onClick={() => {
                setSidebar(false);
                setPermissionsOpen(true);
              }}
            >
              <ShieldCheck size={18} />
              <span>Roles & permissions</span>
            </button>
          </nav>
        </div>
        <div className="sidebar-bottom">
          <button
            className={`nav-item ${selectedNavigation === "privacy" ? "selected" : ""}`}
            aria-current={selectedNavigation === "privacy" ? "page" : undefined}
            onClick={() => navigate("privacy")}
          >
            <ShieldCheck size={18} />
            <span>Privacy & data</span>
          </button>
          <button className="nav-item" onClick={() => navigate("intro")}>
            <CircleHelp size={18} />
            <span>About KiraOrder</span>
            <ArrowUpRight size={14} />
          </button>
          <div className="sidebar-footer">
            <span className="tiny-star">✦</span> FOR ORBYTE
            <span className="app-version" title="Workbench design iteration">
              v{APP_VERSION}
            </span>
          </div>
        </div>
      </aside>
      <div className="app-main" inert={sidebar || undefined}>
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              aria-expanded={sidebar}
              aria-controls="workspace-navigation"
              onClick={() => setSidebar(true)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <span>/</span>
            <strong>
              {active === "privacy"
                ? "Privacy & data"
                : me?.role === "WAREHOUSE"
                  ? "Warehouse"
                  : (links.find((l) => l.path === active)?.label ??
                    (active === "new"
                      ? "New order"
                      : active === "order"
                        ? "Review order"
                        : active === "approval"
                          ? "Review approval"
                          : "Delivery order"))}
            </strong>
          </div>
          <div className="topbar-actions">
            <button
              className={`ai-indicator ${ai?.state === "READY" ? "ready" : ""}`}
              onClick={aiResource.error ? aiResource.refresh : wake}
              disabled={
                wakeBusy ||
                (!aiResource.error && !me?.permissions.includes("WAKE_AI"))
              }
              title={
                aiResource.error
                  ? "AI status unavailable. Click to retry."
                  : ai?.message
              }
            >
              {wakeBusy ? <Spinner /> : <span className="status-light" />}
              <span>
                {service.mode === "demo"
                  ? "Offline match"
                  : wakeBusy
                    ? "AI warming…"
                    : aiResource.error
                      ? "AI unavailable · Retry"
                      : aiResource.loading
                        ? "Checking AI…"
                        : ai?.state === "READY"
                          ? "AI ready"
                          : "AI " + (ai?.state.toLowerCase() ?? "status")}
              </span>
              {service.mode === "demo" && <small>non-AI</small>}
            </button>
            <span className="top-divider" />
            <div className="identity">
              <button
                aria-label="View role permissions"
                title={me?.permission_summary}
                onClick={() => setPermissionsOpen(true)}
                className={`user-avatar ${me?.role === "OWNER" ? "owner" : ""}`}
              >
                {me?.display_name
                  ?.split(" ")
                  .map((s) => s[0])
                  .slice(0, 2)
                  .join("") ?? "S"}
              </button>
              <div className="identity-meta">
                <strong>{me?.display_name ?? "Loading"}</strong>
                {service.mode === "demo" ? (
                  <RoleSwitcher role={demoRole} onChange={setRole} />
                ) : (
                  <small>
                    {me?.role &&
                      {
                        CLERK: "Order clerk",
                        OWNER: "Owner",
                        WAREHOUSE: "Warehouse",
                      }[me.role]}
                  </small>
                )}
              </div>
            </div>
          </div>
        </header>
        <main id="main-content" className="page-content" tabIndex={-1}>
          {active === "privacy" ? (
            <PrivacyPage mode={service.fixture ? "fixture" : service.mode} />
          ) : identity.loading && !me ? (
            <Loading label="Loading your workspace…" />
          ) : identity.error ? (
            <ErrorNotice error={identity.error} retry={identity.refresh} />
          ) : me ? (
            <>
              {(service.mode === "demo" || service.fixture) && (
                <div className="demo-strip">
                  <span className="demo-dot" />{" "}
                  {service.fixture ? "FIXTURE MOCK" : "LOCAL DEMO"}{" "}
                  <span>
                    ·{" "}
                    {service.fixture
                      ? "Synthetic responses · no real backend"
                      : "Synthetic data"}
                  </span>
                </div>
              )}
              {me.role === "WAREHOUSE" ? (
                <WarehousePage
                  key={service.mode + tenant}
                  service={service}
                  notify={notify}
                />
              ) : (
                <>
                  {routeValid && active === "workspace" && (
                    <ResourceView resource={draftsResource}>
                      {(drafts) => (
                        <Overview
                          me={me}
                          drafts={drafts}
                          activityResource={activityResource}
                          navigate={navigate}
                        />
                      )}
                    </ResourceView>
                  )}
                  {routeValid && active === "inbox" && (
                    <ResourceView resource={draftsResource}>
                      {(drafts) => (
                        <InboxPage
                          drafts={drafts}
                          navigate={navigate}
                          filter={route.split("/")[1] ?? "all"}
                        />
                      )}
                    </ResourceView>
                  )}
                  {routeValid && active === "new" && (
                    <NewOrder
                      service={service}
                      navigate={navigate}
                      complete={forceNav}
                      setDirty={setDirty}
                      changed={changed}
                      notify={notify}
                    />
                  )}
                  {routeValid && active === "order" && route.split("/")[1] && (
                    <OrderDetail
                      key={route + tenant + service.mode + me.role}
                      id={route.split("/")[1]}
                      service={service}
                      me={me}
                      navigate={navigate}
                      complete={forceNav}
                      setDirty={setDirty}
                      changed={changed}
                      notify={notify}
                    />
                  )}
                  {routeValid && active === "approvals" && (
                    <ResourceView resource={approvalsResource}>
                      {(approvals) => (
                        <ApprovalsPage
                          approvals={approvals}
                          me={me}
                          navigate={navigate}
                        />
                      )}
                    </ResourceView>
                  )}
                  {routeValid &&
                    active === "approval" &&
                    route.split("/")[1] && (
                      <ApprovalDetail
                        key={route + me.role}
                        id={route.split("/")[1]}
                        service={service}
                        me={me}
                        navigate={navigate}
                        changed={changed}
                        notify={notify}
                      />
                    )}
                  {routeValid && active === "delivery-orders" && (
                    <ResourceView resource={draftsResource}>
                      {(drafts) => (
                        <DeliveriesPage drafts={drafts} navigate={navigate} />
                      )}
                    </ResourceView>
                  )}
                  {routeValid &&
                    active === "delivery" &&
                    route.split("/")[1] && (
                      <DeliveryPage
                        key={route}
                        id={route.split("/")[1]}
                        service={service}
                        notify={notify}
                        navigate={navigate}
                      />
                    )}
                  {routeValid && active === "activity" && (
                    <ResourceView resource={activityResource}>
                      {(activity) => (
                        <ActivityPage
                          activity={activity}
                          drafts={draftsResource.value ?? []}
                          navigate={navigate}
                        />
                      )}
                    </ResourceView>
                  )}
                  {!routeValid && (
                    <Empty
                      title="This page isn’t in your workspace"
                      description="Return to your overview to find your orders."
                    >
                      <button
                        className="button primary"
                        onClick={() => navigate("workspace")}
                      >
                        Back to overview
                      </button>
                    </Empty>
                  )}
                </>
              )}
            </>
          ) : null}
        </main>
      </div>
      {notice && (
        <div className="toast" role="status">
          <Check size={16} />
          <span>{notice}</span>
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={15} />
          </button>
        </div>
      )}
      {pending && (
        <Modal title="Leave without saving?" onClose={() => setPending(null)}>
          <p className="modal-copy">
            Your latest changes haven’t been saved. Stay here to finish
            reviewing, or leave and discard these changes.
          </p>
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() => setPending(null)}
            >
              Keep reviewing
            </button>
            <button className="button danger" onClick={() => forceNav(pending)}>
              Discard changes & leave
            </button>
          </div>
        </Modal>
      )}
      {permissionsOpen && (
        <Modal
          title="Your permissions"
          onClose={() => setPermissionsOpen(false)}
        >
          <p className="modal-copy">{me?.permission_summary}</p>
          <div className="modal-actions">
            <button
              className="button primary"
              onClick={() => setPermissionsOpen(false)}
            >
              Done
            </button>
          </div>
        </Modal>
      )}
      {settings && (
        <ConnectionModal
          current={service.mode}
          dirty={dirty}
          onClose={() => setSettings(false)}
          onConnect={(s) => {
            setLive(s);
            setSettings(false);
            forceNav("workspace");
          }}
          onDemo={() => {
            setLive(null);
            setSettings(false);
            forceNav("workspace");
          }}
        />
      )}
    </div>
  );
}

function Overview({
  me,
  drafts,
  activityResource,
  navigate,
}: {
  me: Me;
  drafts: DraftSummary[];
  activityResource: ReturnType<typeof useResource<Activity[]>>;
  navigate: Navigate;
}) {
  const needs = drafts.filter((d) => d.status === "DISAMBIGUATION_REQUIRED"),
    ready = drafts.filter((d) => d.status === "READY_FOR_APPROVAL"),
    pending = drafts.filter((d) => d.status === "PENDING_OWNER_APPROVAL"),
    done = drafts.filter((d) => d.status === "DO_GENERATED");
  const queue = overviewQueue(drafts);
  const next = queue.find(d =>
    ["DISAMBIGUATION_REQUIRED", "READY_FOR_APPROVAL"].includes(d.status),
  );
  const activityLabel: Record<string, string> = {
    DRAFT_PARSED: "Draft created",
    DRAFT_SAVED: "Draft saved",
    OWNER_REQUESTED: "Owner review requested",
    DO_GENERATED: "DO generated",
    OWNER_REJECTED: "Order rejected",
  };
  return (
    <>
      <div className="overview-heading desk-heading">
        <div>
          <h1>
            Overview<span className="mint-text">.</span>
          </h1>
          <p>
            {me.display_name} <span>·</span>{" "}
            {dateLabel(new Date().toISOString())}
          </p>
          <p className="desk-summary">
            {needs.length
              ? `${needs.length} ${needs.length === 1 ? "order needs" : "orders need"} your decision before moving forward.`
              : "Your order queue is up to date."}
          </p>
        </div>
        <button className="button primary" onClick={() => navigate("new")}>
          <Plus size={17} />
          New order
          <ArrowUpRight size={16} />
        </button>
      </div>
      <div className="stats-grid desk-stats">
        {[
          {
            label: "Needs a decision",
            n: needs.length,
            Icon: MessageSquareText,
            tone: "amber",
            filter: "needs",
          },
          {
            label: "Ready to approve",
            n: ready.length,
            Icon: CheckCheck,
            tone: "mint",
            filter: "ready",
          },
          {
            label: "With owner",
            n: pending.length,
            Icon: ShieldCheck,
            tone: "blue",
            filter: "owner",
          },
          {
            label: "Delivery orders",
            n: done.length,
            Icon: FileCheck2,
            tone: "neutral",
            filter: "done",
          },
        ].map(({ label, n, Icon, tone, filter }) => (
          <button
            key={label}
            className={`stat-card ${tone}`}
            onClick={() =>
              navigate(
                filter === "done" ? "delivery-orders" : `inbox/${filter}`,
              )
            }
          >
            <div>
              <span>{label}</span>
              <Icon size={17} aria-hidden="true" />
            </div>
            <strong>{String(n).padStart(2, "0")}</strong>
          </button>
        ))}
      </div>
      <div className="overview-grid desk-grid">
        <section className="next-card desk-next">
          <div className="rail-title">
            Up next · Oldest first
            <ArrowUpRight size={14} />
          </div>
          {next ? (
            <>
              <div className="next-content">
                <h3>{next.customer_name}</h3>
                <Status status={next.status} />
                <p className="next-context">
                {next.status === "DISAMBIGUATION_REQUIRED"
                  ? `${next.open_blocking_issue_count} ${next.open_blocking_issue_count === 1 ? "check" : "checks"} to resolve.`
                  : "All checks complete."}
                </p>
              </div>
              <button
                className="button secondary small"
                onClick={() => navigate(`order/${next.draft_id}`)}
              >
                Review order
                <ArrowRight size={14} />
              </button>
            </>
          ) : (
            <>
              <h3>No pending orders</h3>
              <button className="text-button" onClick={() => navigate("new")}>
                New order
                <Plus size={14} />
              </button>
            </>
          )}
        </section>
        <section className="panel queue-panel">
          <div className="panel-heading">
            <div>
              <h2>Orders</h2>
              <p className="queue-caption">Your open orders, in one place.</p>
            </div>
            <button className="text-button" onClick={() => navigate("inbox")}>
              View all
              <ArrowRight size={14} />
            </button>
          </div>
          <OrderQueue
            drafts={queue.slice(0, 6)}
            navigate={navigate}
            compact
          />
        </section>
        <section className="panel recent-activity">
          <div className="rail-title">
            Recent activity
            <ActivityIcon size={14} />
          </div>
          <ResourceView resource={activityResource}>
            {(activity) =>
              activity.length ? (
                activity.slice(0, 3).map((a, i) => (
                  <div className="mini-activity" key={a.activity_id}>
                    <span className={`activity-dot dot-${i}`} />
                    <div>
                      <strong>
                        {activityLabel[a.action] ??
                          a.action.toLowerCase().replaceAll("_", " ")}
                      </strong>
                      <small>
                        {a.actor}
                        <i />
                        {time(a.created_at)}
                      </small>
                    </div>
                  </div>
                ))
              ) : (
                <p className="micro-copy">No activity yet.</p>
              )
            }
          </ResourceView>
          <button
            className="text-button"
            onClick={() => navigate("activity")}
          >
            View all
            <ArrowUpRight size={13} />
          </button>
        </section>
      </div>
    </>
  );
}
export function OrderQueue({
  drafts,
  navigate,
  compact = false,
}: {
  drafts: DraftSummary[];
  navigate: Navigate;
  compact?: boolean;
}) {
  if (!drafts.length)
    return (
      <Empty
        title="All clear here"
        description="No orders match this view. Try another filter or start a new order."
      />
    );
  return (
    <div className={`order-table ${compact ? "compact" : ""}`}>
      <div className="order-table-head">
        <span>CUSTOMER / MESSAGE</span>
        <span>STATUS</span>
        <span>RECEIVED</span>
        <span />
      </div>
      {drafts.map((d) => (
        <button
          className="order-row"
          key={d.draft_id}
          onClick={() =>
            navigate(
              d.do_number ? `delivery/${d.do_number}` : `order/${d.draft_id}`,
            )
          }
        >
          <div className="customer-cell">
            <span
              className={`customer-avatar ${d.status === "DISAMBIGUATION_REQUIRED" ? "warm" : d.status === "PENDING_OWNER_APPROVAL" ? "cool" : ""}`}
            >
              {d.customer_name
                .split(" ")
                .map((s) => s[0])
                .slice(0, 2)
                .join("")}
            </span>
            <div>
              <strong>
                {d.customer_name}
                <small>#{shortId(d.draft_id)}</small>
              </strong>
              <p>{d.message_preview.replaceAll("\n", " · ")}</p>
            </div>
          </div>
          <div className="row-state">
            <Status status={d.status} />
            {d.open_blocking_issue_count > 0 && (
              <small>
                {d.open_blocking_issue_count}{" "}
                {d.open_blocking_issue_count === 1 ? "check" : "checks"} to
                resolve
              </small>
            )}
          </div>
          <span className="row-time">{time(d.created_at ?? d.updated_at)}</span>
          <ArrowUpRight className="row-arrow" size={17} />
        </button>
      ))}
    </div>
  );
}
function InboxPage({
  drafts,
  navigate,
  filter,
}: {
  drafts: DraftSummary[];
  navigate: Navigate;
  filter: string;
}) {
  const [query, setQuery] = useState("");
  const filterMap: Record<string, string> = {
    needs: "DISAMBIGUATION_REQUIRED",
    ready: "READY_FOR_APPROVAL",
    owner: "PENDING_OWNER_APPROVAL",
    done: "DO_GENERATED",
    closed: "REJECTED",
  };
  const shown = drafts.filter(
    (d) =>
      (filter === "all" || d.status === filterMap[filter]) &&
      `${d.customer_name} ${d.message_preview} ${d.draft_id}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  return (
    <>
      <PageHeading
        title="Order inbox"
        description="Find an order, resolve its checks, and keep it moving."
      >
        <button className="button primary" onClick={() => navigate("new")}>
          <Plus size={17} /> New order
        </button>
      </PageHeading>
      <section className="panel">
        <div className="queue-toolbar">
          <div className="tabs" role="group" aria-label="Filter orders">
            {[
              ["all", "All orders"],
              ["needs", "Needs a decision"],
              ["ready", "Ready"],
              ["owner", "With owner"],
              ["closed", "Closed"],
            ].map(([key, label]) => (
              <button
                key={key}
                aria-pressed={filter === key}
                className={filter === key ? "active" : ""}
                onClick={() =>
                  navigate(key === "all" ? "inbox" : `inbox/${key}`)
                }
              >
                {label}
                <span>
                  {key === "all"
                    ? drafts.length
                    : drafts.filter((d) => d.status === filterMap[key]).length}
                </span>
              </button>
            ))}
          </div>
          <label className="search-field">
            <Search size={15} />
            <input
              placeholder="Search orders…"
              aria-label="Search orders"
              type="search"
              name="order-search"
              autoComplete="off"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setQuery("");
              }}
            />
            {query && (
              <button aria-label="Clear search" onClick={() => setQuery("")}>
                <X size={13} />
              </button>
            )}
          </label>
        </div>
        <div
          className="queue-results"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          <span>
            {shown.length} {shown.length === 1 ? "order" : "orders"}
            {query.trim() ? " match your search" : " in this view"}
          </span>
          {(query || filter !== "all") && (
            <button
              className="text-button"
              onClick={() => {
                setQuery("");
                navigate("inbox");
              }}
            >
              Clear filters
              <X size={13} aria-hidden="true" />
            </button>
          )}
        </div>
        {shown.length ? (
          <OrderQueue drafts={shown} navigate={navigate} />
        ) : (
          <Empty
            title={
              query.trim() ? "No matching orders" : "No orders in this view"
            }
            description={
              query.trim()
                ? "Try a customer name, a product, or an order ID. You can also clear your filters."
                : "Choose another status to see your orders, or start a new order."
            }
          >
            <button
              className="button secondary small"
              onClick={() => {
                setQuery("");
                navigate("inbox");
              }}
            >
              Show all orders
            </button>
          </Empty>
        )}
      </section>
    </>
  );
}
function ConnectionModal({
  current,
  dirty,
  onConnect,
  onDemo,
  onClose,
}: {
  current: "demo" | "live";
  dirty: boolean;
  onConnect: (s: Service) => void;
  onDemo: () => void;
  onClose: () => void;
}) {
  const [base, setBase] = useState(
    (import.meta as ImportMeta & { env: Record<string, string> }).env
      .VITE_API_BASE_URL ?? DEFAULT_API_BASE,
  );
  const [token, setToken] = useState("");
  const beginConnection = useRequestScope([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  return (
    <Modal title="Your workspace connection" onClose={onClose}>
      <p className="modal-copy">
        Connect a Gate 0 API to use real orders. Your role and permissions come
        from the API session.
      </p>
      <Pill tone={current === "demo" ? "amber" : "mint"}>
        {current === "demo" ? "Local demo active" : "API connected"}
      </Pill>
      <form
        className="form-stack"
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy) return;
          if (dirty) {
            setError(
              new Error(
                "Save or discard your changes before switching connections.",
              ),
            );
            return;
          }
          setBusy(true);
          const currentRequest = beginConnection();
          setError(undefined);
          try {
            const s = new HttpService(base, token);
            await s.me();
            if (currentRequest()) onConnect(s);
          } catch (err) {
            if (currentRequest()) setError(err);
          } finally {
            if (currentRequest()) setBusy(false);
          }
        }}
      >
        <label>
          API base URL
          <input
            type="url"
            disabled={busy}
            required
            value={base}
            onChange={(e) => setBase(e.target.value)}
            placeholder="https://your-api.example/api/v1"
          />
        </label>
        <label>
          Session token
          <input
            type="password"
            disabled={busy}
            required
            autoComplete="off"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Your API session token"
          />
        </label>
        <div className="permission-note">
          <ShieldCheck size={17} />
          <p>
            The token stays in memory for this tab session. Reloading returns to
            the local demo. No document files are uploaded.
          </p>
        </div>
        {!!error && <ErrorNotice error={error} />}
        <div className="modal-actions">
          {current === "live" && (
            <button
              type="button"
              className="button secondary"
              disabled={dirty || busy}
              onClick={onDemo}
            >
              <LogOut size={15} /> Return to demo
            </button>
          )}
          <button className="button primary" disabled={busy}>
            {busy ? <Spinner /> : <Zap size={15} />}Connect API
          </button>
        </div>
      </form>
    </Modal>
  );
}
