import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DependencyList,
} from "react";
import type { AiStatus, Service } from "./types";

const warmups = new WeakMap<Service, Promise<AiStatus>>();

// A service object is one API session. Strict Mode and route changes share its attempt.
export function useAiControl(
  service: Service,
  enabled: boolean,
  refresh: () => void,
  notify: (message: string) => void,
) {
  const [state, setState] = useState({ service, busy: false });
  const beginRequest = useRequestScope([service, enabled]);
  useEffect(() => {
    if (!enabled || service.mode !== "live") return;
    let active = true;
    let promise = warmups.get(service);
    if (!promise) {
      promise = service.wake();
      warmups.set(service, promise);
    }
    setState({ service, busy: true });
    promise.then(
      () => {
        if (!active) return;
        setState({ service, busy: false });
        refresh();
      },
      () => {
        if (!active) return;
        setState({ service, busy: false });
        notify(
          "AI warm-up did not complete. Use the AI status button to retry.",
        );
        refresh();
      },
    );
    return () => {
      active = false;
    };
  }, [service, enabled, refresh, notify]);
  const wake = async () => {
    if (!enabled || (state.service === service && state.busy)) return;
    const current = beginRequest();
    setState({ service, busy: true });
    try {
      const result = await service.wake();
      if (!current()) return;
      notify(result.message);
      refresh();
    } catch (error) {
      if (current())
        notify(error instanceof Error ? error.message : "Could not wake AI.");
    } finally {
      if (current()) setState({ service, busy: false });
    }
  };
  return { busy: enabled && state.service === service && state.busy, wake };
}

// Writes may complete on the server after leaving. Only the current view may navigate.
export function useRequestScope(deps: DependencyList) {
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    deps,
  );
  return () => {
    const current = ++generation.current;
    return () => current === generation.current;
  };
}
export function useResource<T>(
  loader: () => Promise<T>,
  deps: DependencyList,
  enabled = true,
) {
  const [result, setResult] = useState<{
    keys: DependencyList;
    value?: T;
    error?: unknown;
    loading: boolean;
  }>({ keys: deps, loading: enabled });
  const matches = (keys: DependencyList) =>
    keys.length === deps.length &&
    keys.every((key, i) => Object.is(key, deps[i]));
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    setResult((previous) => ({
      keys: deps,
      value: matches(previous.keys) ? previous.value : undefined,
      loading: true,
    }));
    loader()
      .then((v) => {
        if (active) setResult({ keys: deps, value: v, loading: false });
      })
      .catch((e) => {
        if (active)
          setResult((previous) => ({ ...previous, error: e, loading: false }));
      });
    return () => {
      active = false;
    };
  }, [...deps, version, enabled]);
  const current = enabled && matches(result.keys);
  return {
    value: current ? result.value : undefined,
    error: current ? result.error : undefined,
    loading: enabled && (!current || result.loading),
    refresh,
    setValue: (value: T) => setResult({ keys: deps, value, loading: false }),
  };
}
