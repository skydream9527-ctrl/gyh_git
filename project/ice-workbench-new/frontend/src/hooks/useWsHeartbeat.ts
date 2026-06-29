/**
 * Standalone WebSocket heartbeat manager.
 *
 * Usage: call `startHeartbeat(ws)` after WS opens, `stopHeartbeat()` on close.
 * Sends `{"type":"ping"}` every HEARTBEAT_INTERVAL_MS. If no message is received
 * within HEARTBEAT_TIMEOUT_MS after a ping, closes the socket with code 4000
 * to trigger the existing reconnect logic in useChatSocket.
 *
 * This is designed as a non-invasive addition — the existing useChatSocket
 * reconnect/backoff logic handles the 4000 close exactly like any other
 * recoverable disconnect. Integration requires adding 3 lines to useChatSocket:
 *   - import { useWsHeartbeat } from "./useWsHeartbeat"
 *   - const { startHeartbeat, stopHeartbeat } = useWsHeartbeat()
 *   - ws.onopen: startHeartbeat(ws)   (stopHeartbeat is auto on close)
 *
 * The server should respond to `{"type":"ping"}` with `{"type":"pong"}`.
 * Any incoming ws.onmessage resets the timeout (connection is alive).
 */
import { useCallback, useRef } from "react";
import { HEARTBEAT_INTERVAL_MS, HEARTBEAT_TIMEOUT_MS } from "./wsConnection";

export function useWsHeartbeat() {
  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const stopHeartbeat = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    wsRef.current = null;
  }, []);

  /** Call when any message is received from the server (resets the timeout). */
  const onActivity = useCallback(() => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(
    (ws: WebSocket) => {
      stopHeartbeat();
      wsRef.current = ws;

      intervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: "ping" }));
          } catch {
            // close handler will handle
          }
          // Start timeout
          if (timeoutRef.current !== null) {
            window.clearTimeout(timeoutRef.current);
          }
          timeoutRef.current = window.setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.close(4000, "heartbeat_timeout");
            }
          }, HEARTBEAT_TIMEOUT_MS);
        }
      }, HEARTBEAT_INTERVAL_MS);
    },
    [stopHeartbeat],
  );

  return { startHeartbeat, stopHeartbeat, onActivity };
}
