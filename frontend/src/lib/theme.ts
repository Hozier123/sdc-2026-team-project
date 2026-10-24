import { useSyncExternalStore } from "react";
import { flushSync } from "react-dom";

type Theme = "dark" | "light";
const themeEvent = "kiraorder-theme-change";
const root = document.documentElement;

/**
 * One slow, progressive handoff: the incoming theme spreads out of the control
 * that asked for it, so the change is gradual instead of a single-frame swap.
 * `--theme-reveal-ms` keeps the CSS animation and the fallback timer together.
 */
const REVEAL_MS = 900;
const FALLBACK_SETTLE_MS = REVEAL_MS + 140;

let requested: Theme | null = null;
let revision = 0;
let active: ViewTransition | null = null;
let fallbackTimer: ReturnType<typeof setTimeout> | undefined;
let guardTimer: ReturnType<typeof setTimeout> | undefined;
let holding = false;
const holdListeners = new Set<() => void>();

root.style.setProperty("--theme-reveal-ms", `${REVEAL_MS}ms`);

function setHolding(next: boolean) {
  if (holding === next) return;
  holding = next;
  holdListeners.forEach((listener) => listener());
}
function subscribeHold(listener: () => void) {
  holdListeners.add(listener);
  return () => {
    holdListeners.delete(listener);
  };
}

/**
 * Moving pictures stop for the length of the handoff. Both captured frames then
 * show the same picture, so the reveal never ends on a jump back to live motion.
 */
export function useThemeHold() {
  return useSyncExternalStore(subscribeHold, () => holding, () => false);
}

const readTheme = (): Theme => root.dataset.theme === "light" ? "light" : "dark";
function subscribe(listener: () => void) {
  window.addEventListener(themeEvent, listener);
  const observer = new MutationObserver(listener);
  observer.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  return () => {
    window.removeEventListener(themeEvent, listener);
    observer.disconnect();
  };
}
export function useTheme() {
  return useSyncExternalStore(subscribe, readTheme, () => "dark" as const);
}

/** The soft edge travels out from the switch, reaching the farthest corner by the end. */
function revealFrom(origin?: Element | null) {
  const rect = origin?.getBoundingClientRect();
  const inside = rect && rect.width > 0 && rect.height > 0;
  const x = inside ? rect.left + rect.width / 2 : window.innerWidth / 2;
  const y = inside ? rect.top + rect.height / 2 : window.innerHeight / 2;
  const reach = Math.ceil(
    Math.hypot(
      Math.max(x, window.innerWidth - x) + 2,
      Math.max(y, window.innerHeight - y) + 2,
    ),
  );
  root.style.setProperty("--theme-reveal-x", `${Math.round(x)}px`);
  root.style.setProperty("--theme-reveal-y", `${Math.round(y)}px`);
  root.style.setProperty("--theme-reveal-extent", `${reach}px`);
}

/** Keep React, CSS and the 3D scene in the same captured theme frame. */
export function toggleTheme(origin?: Element | null) {
  const next: Theme = (requested ?? readTheme()) === "light" ? "dark" : "light";
  requested = next;
  const current = ++revision;
  active?.skipTransition();
  clearTimeout(fallbackTimer);
  clearTimeout(guardTimer);
  const commit = () => {
    if (current !== revision) return;
    flushSync(() => {
      root.dataset.theme = next;
      document.querySelector('meta[name="theme-color"]')?.setAttribute("content", next === "light" ? "#f4f6f5" : "#090e15");
      try { localStorage.setItem("kiraorder-theme", next); } catch { /* Persistence is optional. */ }
      window.dispatchEvent(new Event(themeEvent));
    });
  };
  const finish = () => {
    if (current !== revision) return;
    clearTimeout(guardTimer);
    delete root.dataset.themeTransition;
    setHolding(false);
    requested = null;
    active = null;
  };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduced && !document.hidden && typeof document.startViewTransition === "function") {
    revealFrom(origin);
    root.dataset.themeTransition = "native";
    // Freeze first, so the outgoing frame is captured from the settled scene.
    flushSync(() => setHolding(true));
    let transition: ViewTransition | null = null;
    try {
      transition = document.startViewTransition(commit);
    } catch {
      transition = null; // An engine that refuses the transition still gets the theme.
    }
    if (transition) {
      active = transition;
      // A skipped transition still applies the most recent requested theme.
      void transition.ready.catch(() => {});
      void transition.finished.then(finish, finish);
      // Never keep the scene held if a browser drops the transition's end event.
      guardTimer = setTimeout(finish, REVEAL_MS + 1500);
    } else {
      delete root.dataset.themeTransition;
      commit();
      finish();
    }
  } else {
    if (!reduced) root.dataset.themeTransition = "fallback";
    else delete root.dataset.themeTransition;
    setHolding(false);
    commit();
    if (reduced) finish();
    else fallbackTimer = setTimeout(finish, FALLBACK_SETTLE_MS);
  }
}
