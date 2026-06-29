/**
 * Pure WebSocket connection helpers for the chat socket.
 *
 * This module holds the framework-free, side-effect-free logic that drives the
 * chat WebSocket connection in `useChatSocket.ts`: subprotocol-bearer argument
 * construction, exponential backoff, close-code classification, the bounded
 * pending-message queue, and the reconnect-warning predicate.
 *
 * Everything here is a pure function so it can be exhaustively unit- and
 * property-tested in isolation (see the `wsConnection` property tests). The
 * stateful `useChatSocket` hook consumes these helpers; it does not duplicate
 * their logic.
 *
 * Behavior mirrors the existing `useChatSocket` semantics:
 *  - connections open with subprotocols `["bearer", token]` (literal "bearer"
 *    first), and the URL never carries a `?token=` query parameter;
 *  - backoff follows 1s, 2s, 4s, 8s, 16s, then 30s for every later attempt;
 *  - 4403 is fatal (PERMISSION_DENIED); 4401 is fatal without a refresh token
 *    (clear tokens + redirect) and recoverable with one (refresh + reconnect);
 *    1006/1001/1011 and every other code are recoverable.
 */

/** Reconnect backoff delays in milliseconds. The index clamps at the last
 *  entry, so the 6th and every later attempt waits 30s. (Requirements 5.2, 5.3) */
export const BACKOFF_MS: readonly number[] = [1000, 2000, 4000, 8000, 16000, 30000];

/** Number of consecutive failed reconnect attempts after which a persistent
 *  reconnect warning is surfaced to the user. (Requirement 5.5) */
export const RECONNECT_WARNING_THRESHOLD = 5;

/** Maximum number of outbound messages retained in the pending queue while the
 *  connection is not open. Oldest entries are discarded on overflow.
 *  (Requirements 11.2, 11.3) */
export const PENDING_QUEUE_MAX = 5;

/** Application-level heartbeat interval in milliseconds. The client sends a
 *  `{"type":"ping"}` every HEARTBEAT_INTERVAL_MS; the server should reply with
 *  `{"type":"pong"}`. If no pong is received within HEARTBEAT_TIMEOUT_MS, the
 *  connection is considered dead and will be closed + reconnected. */
export const HEARTBEAT_INTERVAL_MS = 25000;
export const HEARTBEAT_TIMEOUT_MS = 10000;

/** Arguments for constructing a `WebSocket`. `subprotocols` is `undefined` when
 *  no token is available so the client offers no subprotocol entries. */
export interface WsArgs {
  url: string;
  subprotocols: string[] | undefined;
}

/**
 * Discriminated union describing what the client should do in response to a
 * close, as classified by {@link classifyClose}.
 *
 *  - `permission_denied`: surface a PERMISSION_DENIED error, do not reconnect.
 *  - `clear_and_redirect`: clear stored tokens and redirect to login, do not
 *    reconnect.
 *  - `refresh_and_reconnect`: refresh the access token, then reconnect.
 *  - `reconnect`: schedule a normal backoff reconnect.
 */
export type CloseAction =
  | { type: "permission_denied" }
  | { type: "clear_and_redirect" }
  | { type: "refresh_and_reconnect" }
  | { type: "reconnect" };

/** Result of classifying a WebSocket close event. */
export interface CloseClassification {
  kind: "recoverable" | "fatal";
  action: CloseAction;
}

/**
 * Build the `WebSocket` constructor arguments for a chat connection.
 *
 * When a non-empty `token` is supplied, the subprotocols are exactly
 * `["bearer", token]` with the literal `"bearer"` first; otherwise no
 * subprotocols are offered. The returned URL is the input URL unchanged and
 * never carries a `token` query parameter — callers must not embed the token in
 * the URL. (Requirements 1.1, 1.2, 1.3)
 */
export function buildWsArgs(url: string, token: string | null | undefined): WsArgs {
  const hasToken = typeof token === "string" && token.length > 0;
  return {
    url,
    subprotocols: hasToken ? ["bearer", token as string] : undefined,
  };
}

/**
 * Return the backoff delay (ms) for the given zero-based reconnect attempt
 * index, clamped to the last entry of {@link BACKOFF_MS}. (Requirements 5.2, 5.3)
 */
export function backoffDelay(attempt: number): number {
  const idx = Math.min(Math.max(attempt, 0), BACKOFF_MS.length - 1);
  return BACKOFF_MS[idx];
}

/**
 * Classify a WebSocket close code into a recoverable/fatal disposition plus the
 * action the client should take. Totals over every possible close code.
 * (Requirements 6.1, 6.2, 6.3, 6.4, 6.5)
 *
 *  - 4403 → fatal, `permission_denied`
 *  - 4401 without a refresh token → fatal, `clear_and_redirect`
 *  - 4401 with a refresh token → recoverable, `refresh_and_reconnect`
 *  - 1006 / 1001 / 1011 and every other code → recoverable, `reconnect`
 */
export function classifyClose(code: number, hasRefresh: boolean): CloseClassification {
  if (code === 4403) {
    return { kind: "fatal", action: { type: "permission_denied" } };
  }
  if (code === 4401) {
    return hasRefresh
      ? { kind: "recoverable", action: { type: "refresh_and_reconnect" } }
      : { kind: "fatal", action: { type: "clear_and_redirect" } };
  }
  return { kind: "recoverable", action: { type: "reconnect" } };
}

/**
 * Pure FIFO push that appends `payload` to `queue` and keeps at most the last
 * `max` entries, discarding the oldest on overflow. Returns a new array; the
 * input queue is not mutated. (Requirements 11.2, 11.3)
 */
export function pushPending(queue: readonly string[], payload: string, max: number): string[] {
  const next = [...queue, payload];
  return max >= 0 && next.length > max ? next.slice(next.length - max) : next;
}

/**
 * Whether the reconnect warning should be visible: true iff the number of
 * consecutive failed reconnect attempts is at least `threshold`. (Requirement 5.5)
 */
export function reconnectWarningVisible(consecutiveFailures: number, threshold: number): boolean {
  return consecutiveFailures >= threshold;
}
