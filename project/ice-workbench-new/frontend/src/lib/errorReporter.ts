/**
 * Frontend error reporter — captures uncaught errors and unhandled promise
 * rejections, throttles duplicates, and POSTs to /api/v1/client-errors.
 *
 * Design choices:
 *  - Fire-and-forget: report failures are silently swallowed (never disrupt UX).
 *  - Throttle: same message within 60s is reported only once (prevents storm).
 *  - Auth-optional: login page has no token; the endpoint accepts unauthenticated.
 *  - build version injected at init for tracing (set from import.meta.env or package version).
 */

import { getAccessToken } from "@/api/client";

const THROTTLE_MS = 60_000;
const ENDPOINT = "/api/v1/client-errors";

let _initialized = false;
let _buildVersion = "";
const _seen = new Map<string, number>(); // message -> last reported timestamp

interface ErrorPayload {
  message: string;
  stack?: string | null;
  route?: string | null;
  level?: string;
  build?: string | null;
  user_agent?: string | null;
  task_id?: string | null;
  context?: Record<string, unknown> | null;
}

function _shouldReport(message: string): boolean {
  const now = Date.now();
  const last = _seen.get(message);
  if (last && now - last < THROTTLE_MS) return false;
  _seen.set(message, now);
  // Cap map size to prevent memory leak in pathological loops
  if (_seen.size > 200) {
    const oldest = _seen.keys().next().value;
    if (oldest) _seen.delete(oldest);
  }
  return true;
}

function _send(payload: ErrorPayload): void {
  try {
    const body = JSON.stringify({
      ...payload,
      route: payload.route ?? location.pathname,
      build: payload.build ?? _buildVersion,
      user_agent: payload.user_agent ?? navigator.userAgent,
    });
    // Use fetch (not axios) to avoid circular dependency with client.ts interceptors
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    fetch(ENDPOINT, { method: "POST", headers, body, keepalive: true }).catch(() => {});
  } catch {
    // swallow — reporter must never throw
  }
}

/**
 * Report an error programmatically (e.g., from ErrorBoundary.componentDidCatch).
 */
export function reportError(
  error: unknown,
  extra?: { route?: string; task_id?: string; context?: Record<string, unknown> },
): void {
  const message = error instanceof Error ? error.message : String(error);
  if (!_shouldReport(message)) return;
  const stack = error instanceof Error ? error.stack ?? null : null;
  _send({
    message,
    stack,
    level: "ERROR",
    route: extra?.route,
    task_id: extra?.task_id,
    context: extra?.context,
  });
}

/**
 * Initialize global error listeners. Call once at app boot (main.tsx).
 */
export function initErrorReporter(buildVersion?: string): void {
  if (_initialized) return;
  _initialized = true;
  _buildVersion = buildVersion || "";

  window.addEventListener("error", (event) => {
    const message = event.message || "Unknown error";
    if (!_shouldReport(message)) return;
    _send({
      message,
      stack: event.error?.stack ?? `${event.filename}:${event.lineno}:${event.colno}`,
      level: "ERROR",
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const message = reason instanceof Error ? reason.message : String(reason ?? "Unhandled rejection");
    if (!_shouldReport(message)) return;
    _send({
      message,
      stack: reason instanceof Error ? reason.stack ?? null : null,
      level: "ERROR",
    });
  });
}
