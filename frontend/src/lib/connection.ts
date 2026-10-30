// Only a reconnect flag is persisted. Credentials and identity never leave memory.
export const RECONNECT_KEY = "kiraorder.reconnect-required.v1";

export function reconnectRequired(storage: Pick<Storage, "getItem">) {
  try {
    return storage.getItem(RECONNECT_KEY) === "true";
  } catch {
    return false;
  }
}

export function rememberConnection(storage: Pick<Storage, "setItem" | "removeItem">, live: boolean) {
  try {
    if (live) storage.setItem(RECONNECT_KEY, "true");
    else storage.removeItem(RECONNECT_KEY);
  } catch {
    // Storage can be disabled. The active session still remains memory-only.
  }
}

export function defaultApiBase(configured: string | undefined, development: boolean) {
  return configured?.trim() || (development ? "http://127.0.0.1:8000/api/v1" : "");
}

export function validateApiBase(base: string) {
  const url = new URL(base.trim());
  if (url.username || url.password || url.search || url.hash)
    throw new Error("Use an API base URL without credentials, query parameters or fragments.");
  if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)))
    throw new Error("Use HTTPS or a local development API.");
  return url.href.replace(/\/+$/, "");
}
