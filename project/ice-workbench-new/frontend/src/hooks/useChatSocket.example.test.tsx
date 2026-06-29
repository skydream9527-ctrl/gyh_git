import { act, renderHook } from "@testing-library/react";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import http from "@/api/client";
import { useUIStore } from "@/stores/uiStore";
import { useChatSocket } from "@/hooks/useChatSocket";

// Feature: websocket-token-stability
//
// Example (NOT randomized) tests for the observable behavior of `useChatSocket`
// that the pure-helper property tests cannot reach: reconnect side effects,
// the refresh-then-reconnect / fatal-refresh / clear-and-redirect close paths,
// stream-interrupt finalization, and the pending-queue connecting/closed
// branches.
//
// Covers acceptance criteria:
//   Reconnect:       5.4, 5.6, 5.7, 5.8, 5.9, 6.2
//   Stream interrupt: 8.6, 12.4
//   Pending queue:    11.7, 11.8
//
// Approach
// --------
// `useChatSocket` is a side-effectful React hook: it opens a real `WebSocket`,
// schedules reconnects on `window.setTimeout`, pushes toasts through the UI
// store, refreshes tokens via `axios`, and redirects through `window.location`.
// We drive its *observable outputs* (status, phase, errorCode, finalized,
// closeInfo, toasts, redirect target, frames sent) end to end rather than
// asserting against the already-property-tested pure helpers.
//
// To do that deterministically we install:
//   * a `MockWebSocket` global whose `_open` / `_close` / `_message` test hooks
//     drive the hook's `onopen` / `onclose` / `onmessage` callbacks and whose
//     `sent` array captures every frame the hook writes;
//   * `axios.post` stubbed to control the token-refresh endpoint;
//   * `http.get` stubbed so the conversation-switch effect's run-events fetch
//     resolves quietly;
//   * a writable `window.location` so the 4401-no-refresh redirect is
//     observable;
//   * no-op `requestAnimationFrame` so stream flushing is driven only by the
//     deterministic synchronous flush in the close handler;
//   * fake timers so the 5s toast auto-dismiss and the backoff reconnect delays
//     advance under test control.

const ACCESS_KEY = "ice-access-token";
const REFRESH_KEY = "ice-refresh-token";

interface CloseEventLike {
  code: number;
  reason: string;
}

/** Minimal driveable WebSocket double. The hook only uses the constructor,
 *  `send`, `close`, the four `on*` handlers, and the readyState constants. */
class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: MockWebSocket[] = [];

  static last(): MockWebSocket {
    const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    if (!ws) throw new Error("no MockWebSocket has been constructed yet");
    return ws;
  }

  url: string;
  protocols: string | string[] | undefined;
  readyState: number = MockWebSocket.CONNECTING;
  sent: string[] = [];
  onopen: ((ev?: unknown) => void) | null = null;
  onclose: ((ev: CloseEventLike) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onerror: ((ev?: unknown) => void) | null = null;

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    this.protocols = protocols;
    MockWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
  }

  // --- test drivers -------------------------------------------------------
  _open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  _close(code: number, reason = ""): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, reason });
  }

  _message(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  /** Parsed view of the frames the hook wrote to this socket. */
  get sentEvents(): Array<Record<string, unknown>> {
    return this.sent.map((s) => JSON.parse(s) as Record<string, unknown>);
  }
}

let pushToastSpy: ReturnType<typeof vi.fn>;
let locationMock: { protocol: string; host: string; pathname: string; href: string };
const realLocation = window.location;

/** Flush the hook's async connect continuation (it `await`s `ensureFreshToken`
 *  before constructing the socket) plus any scheduled timers up to `ms`. */
async function flush(ms = 0): Promise<void> {
  await act(async () => {
    for (let i = 0; i < 4; i++) {
      await Promise.resolve();
    }
    await vi.advanceTimersByTimeAsync(ms);
    await Promise.resolve();
  });
}

function makeOpts(overrides: Partial<Parameters<typeof useChatSocket>[0]> = {}) {
  return {
    taskId: "task-1",
    conversationId: "conv-1" as string | null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  localStorage.clear();
  MockWebSocket.instances = [];

  vi.stubGlobal("WebSocket", MockWebSocket);
  // Drive stream flushing only through the synchronous close-handler flush.
  vi.stubGlobal("requestAnimationFrame", (_cb: FrameRequestCallback) => 0);
  vi.stubGlobal("cancelAnimationFrame", (_id: number) => {});

  // Observable, writable location for the redirect path.
  locationMock = { protocol: "http:", host: "localhost", pathname: "/workspace", href: "" };
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: locationMock,
  });

  // Conversation-switch effect fires a run-events fetch; keep it quiet.
  vi.spyOn(http, "get").mockResolvedValue({ data: { code: 0, data: { items: [] } } } as never);

  // Capture toasts while keeping the real auto-dismiss timer behavior so the 5s
  // dismissal (Req 5.7) is genuinely exercised.
  useUIStore.setState({ toasts: [] });
  pushToastSpy = vi.spyOn(useUIStore.getState(), "pushToast") as unknown as ReturnType<typeof vi.fn>;
});

afterEach(async () => {
  // Drain any pending backoff-reconnect timer inside act() so the connect
  // continuation's state updates don't trip React's act(...) warning during
  // teardown.
  await act(async () => {
    await vi.runOnlyPendingTimersAsync();
  });
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: realLocation,
  });
});

describe("Feature: websocket-token-stability — useChatSocket reconnect behaviors", () => {
  it("shows the '连接已恢复' toast on reconnect and auto-dismisses it after 5s (Req 5.4, 5.7)", async () => {
    localStorage.setItem(ACCESS_KEY, "access-1");
    const { result } = renderHook(() => useChatSocket(makeOpts()));
    await flush();

    // First open is NOT a reconnect → no toast.
    await act(async () => {
      MockWebSocket.last()._open();
    });
    expect(result.current.status).toBe("open");
    expect(pushToastSpy).not.toHaveBeenCalled();

    // Drop the connection (recoverable) then let the 1s backoff fire a reconnect.
    await act(async () => {
      MockWebSocket.last()._close(1006, "switching");
    });
    expect(result.current.status).toBe("closed");
    await flush(1000); // backoffDelay(0) === 1000ms → reconnect attempt constructs a new socket

    expect(MockWebSocket.instances.length).toBe(2);

    // Reaching open after a prior disconnect surfaces the recovery toast (Req 5.4).
    await act(async () => {
      MockWebSocket.last()._open();
    });
    expect(pushToastSpy).toHaveBeenCalledWith("success", "连接已恢复", 5000);
    expect(useUIStore.getState().toasts.some((t) => t.message === "连接已恢复")).toBe(true);

    // The toast auto-dismisses 5s after being shown (Req 5.7).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(useUIStore.getState().toasts.some((t) => t.message === "连接已恢复")).toBe(false);
  });

  it("refreshes the access token before reconnecting and reconnects with the refreshed token on 4401 (Req 5.6, 5.8)", async () => {
    localStorage.setItem(ACCESS_KEY, "stale-access");
    localStorage.setItem(REFRESH_KEY, "refresh-1");
    const postSpy = vi.spyOn(axios, "post").mockResolvedValue({
      data: { code: 0, data: { access_token: "refreshed-access", refresh_token: "refresh-2" } },
    } as never);

    const { result } = renderHook(() => useChatSocket(makeOpts()));
    await flush();
    await act(async () => {
      MockWebSocket.last()._open();
    });
    const postCallsBeforeClose = postSpy.mock.calls.length;

    // 4401 with a refresh token present → recoverable refresh-then-reconnect.
    await act(async () => {
      MockWebSocket.last()._close(4401, "token expired");
    });
    // Let the explicit refresh resolve and schedule the reconnect.
    await flush(0);
    // The refresh endpoint was hit again specifically for the reconnect (Req 5.6).
    expect(postSpy.mock.calls.length).toBeGreaterThan(postCallsBeforeClose);

    // Fire the backoff timer → a new socket opens using the refreshed token (Req 5.8).
    await flush(1000);
    expect(MockWebSocket.instances.length).toBe(2);
    expect(MockWebSocket.last().protocols).toEqual(["bearer", "refreshed-access"]);
    expect(result.current.errorCode).not.toBe("AUTH_FAILED");
  });

  it("treats a failed refresh after 4401 as fatal: surfaces AUTH_FAILED and stops reconnecting (Req 5.9)", async () => {
    localStorage.setItem(ACCESS_KEY, "stale-access");
    localStorage.setItem(REFRESH_KEY, "refresh-1");
    // Every refresh attempt fails (network/credential error).
    vi.spyOn(axios, "post").mockRejectedValue(new Error("refresh boom"));
    const onError = vi.fn();

    const { result } = renderHook(() => useChatSocket(makeOpts({ onError })));
    await flush();
    await act(async () => {
      MockWebSocket.last()._open();
    });
    expect(MockWebSocket.instances.length).toBe(1);

    await act(async () => {
      MockWebSocket.last()._close(4401, "token expired");
    });
    await flush(0); // refresh rejects → fatal classification

    expect(result.current.errorCode).toBe("AUTH_FAILED");
    expect(result.current.phase).toBe("error");
    expect(onError).toHaveBeenCalledWith("AUTH_FAILED", expect.any(String));

    // No further reconnect is scheduled even after the longest backoff window.
    await flush(30000);
    expect(MockWebSocket.instances.length).toBe(1);
  });

  it("on 4401 with no refresh token clears stored tokens and redirects to /login without reconnecting (Req 6.2)", async () => {
    localStorage.setItem(ACCESS_KEY, "access-only");
    // No refresh token in storage.
    const { result } = renderHook(() => useChatSocket(makeOpts()));
    await flush();
    await act(async () => {
      MockWebSocket.last()._open();
    });

    await act(async () => {
      MockWebSocket.last()._close(4401, "unauthorized");
    });

    // Redirect is synchronous in the close handler, well within the 2s budget.
    expect(locationMock.href).toBe("/login");
    expect(localStorage.getItem(ACCESS_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
    expect(result.current.closeInfo).toEqual({ code: 4401, reason: "unauthorized" });

    // No reconnect scheduled.
    await flush(30000);
    expect(MockWebSocket.instances.length).toBe(1);
  });
});

describe("Feature: websocket-token-stability — useChatSocket stream-interruption finalization", () => {
  it.each([
    {
      name: "streaming",
      drive: (ws: MockWebSocket) => ws._message({ type: "agent_message", message_id: "m1", content: "partial output" }),
      expectFinalized: true,
    },
    {
      name: "tool",
      drive: (ws: MockWebSocket) =>
        ws._message({
          type: "tool_call_start",
          tool_call_id: "tc1",
          tool_name: "search",
          display_name: "Search",
          arguments: { q: "x" },
        }),
      expectFinalized: true,
    },
    {
      name: "typing",
      drive: (ws: MockWebSocket) => ws._message({ type: "agent_typing", status: "start" }),
      expectFinalized: false,
    },
  ])(
    "disconnecting while phase is '$name' finalizes the partial and sets phase=error with STREAM_INTERRUPTED (Req 8.6, 12.4)",
    async ({ drive, expectFinalized }) => {
      localStorage.setItem(ACCESS_KEY, "access-1");
      const { result } = renderHook(() => useChatSocket(makeOpts()));
      await flush();
      await act(async () => {
        MockWebSocket.last()._open();
      });

      // Move the client into the streaming/tool/typing phase.
      await act(async () => {
        drive(MockWebSocket.last());
      });
      expect(["streaming", "tool", "typing"]).toContain(result.current.phase);

      // Connection drops mid-stream.
      await act(async () => {
        MockWebSocket.last()._close(1006, "network");
      });

      // Phase flips to error with the synthesized STREAM_INTERRUPTED code (Req 8.6, 12.4).
      expect(result.current.phase).toBe("error");
      expect(result.current.errorCode).toBe("STREAM_INTERRUPTED");
      // The live partial is cleared (finalized, not discarded).
      expect(result.current.partial).toBeNull();

      if (expectFinalized) {
        // Already-streamed content/tool calls are preserved in finalized history.
        expect(result.current.finalized.some((m) => m.role === "assistant")).toBe(true);
      }
    },
  );

  it("preserves the streamed text when finalizing an interrupted stream (Req 8.6)", async () => {
    localStorage.setItem(ACCESS_KEY, "access-1");
    const { result } = renderHook(() => useChatSocket(makeOpts()));
    await flush();
    await act(async () => {
      MockWebSocket.last()._open();
    });
    await act(async () => {
      MockWebSocket.last()._message({ type: "agent_message", message_id: "m9", content: "hello world" });
    });
    await act(async () => {
      MockWebSocket.last()._close(1011, "server error");
    });

    const assistant = result.current.finalized.find((m) => m.id === "m9");
    expect(assistant).toBeDefined();
    expect(assistant?.content).toBe("hello world");
    expect(result.current.closeInfo).toEqual({ code: 1011, reason: "server error" });
  });
});

describe("Feature: websocket-token-stability — useChatSocket pending queue", () => {
  it("enqueues a message sent during the CONNECTING handshake window without a disconnect banner, then flushes on open (Req 11.7)", async () => {
    localStorage.setItem(ACCESS_KEY, "access-1");
    const { result } = renderHook(() => useChatSocket(makeOpts()));
    await flush();

    const ws = MockWebSocket.last();
    expect(ws.readyState).toBe(MockWebSocket.CONNECTING);

    // Send while still connecting → queued, no banner.
    await act(async () => {
      result.current.send("typed during handshake");
    });
    expect(result.current.errorCode).not.toBe("WS_DISCONNECTED");
    expect(result.current.errorCode).toBeNull();
    expect(ws.sent).toHaveLength(0); // nothing sent yet — it is queued

    // On open the queued message is flushed.
    await act(async () => {
      ws._open();
    });
    const userMessages = ws.sentEvents.filter((e) => e.type === "user_message");
    expect(userMessages).toHaveLength(1);
    expect(userMessages[0].content).toBe("typed during handshake");
  });

  it("on a CLOSED connection enqueues, surfaces WS_DISCONNECTED, and initiates a reconnect (Req 11.8)", async () => {
    localStorage.setItem(ACCESS_KEY, "access-1");
    const { result } = renderHook(() => useChatSocket(makeOpts()));
    await flush();
    await act(async () => {
      MockWebSocket.last()._open();
    });

    // Force the socket into CLOSED, then send before the auto-reconnect fires.
    await act(async () => {
      MockWebSocket.last()._close(1006, "dropped");
    });
    expect(MockWebSocket.last().readyState).toBe(MockWebSocket.CLOSED);

    await act(async () => {
      result.current.send("sent while closed");
    });

    // Inline WS_DISCONNECTED error is surfaced (Req 11.8).
    expect(result.current.errorCode).toBe("WS_DISCONNECTED");

    // A reconnect is initiated: send() calls connect(), constructing a new socket.
    await flush(0);
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2);
    expect(result.current.status).toBe("connecting");

    // When the new socket opens, the queued message is delivered (Req 11.4/11.8 flush).
    await act(async () => {
      MockWebSocket.last()._open();
    });
    const userMessages = MockWebSocket.last().sentEvents.filter((e) => e.type === "user_message");
    expect(userMessages.some((m) => m.content === "sent while closed")).toBe(true);
  });
});
