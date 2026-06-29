import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { fcParams } from "@/test/fcConfig";
import { buildWsArgs } from "@/hooks/wsConnection";

// Property test for the websocket-token-stability feature.
//
// Property 3: No token in the connection URL — for any client connection, with
// or without a token, the URL built by `buildWsArgs` contains no `token` query
// parameter. The token (when present) rides on the WebSocket subprotocol, never
// the URL, so JWTs stop leaking into server/proxy access logs.
//
// Validates: Requirements 1.2, 1.3

/**
 * Build a representative chat WebSocket URL from arbitrary conversation/task
 * identifiers. This mirrors how `useChatSocket` composes the endpoint path and
 * gives the property realistic, varied URLs (including ones that already carry
 * unrelated query parameters) to assert against.
 */
function buildChatUrl(base: string, conv: string, task: string, extraQuery: string): string {
  const u = new URL(`${base}/api/v1/ws/conversations/${encodeURIComponent(conv)}`);
  if (task.length > 0) {
    u.searchParams.set("task_id", task);
  }
  if (extraQuery.length > 0) {
    u.searchParams.set("ts", extraQuery);
  }
  return u.toString();
}

describe("Feature: websocket-token-stability, Property 3: No token in the connection URL", () => {
  it("never includes a token query parameter for any token/conv/task input", () => {
    const wsBaseArb = fc.constantFrom(
      "ws://localhost:5173",
      "ws://127.0.0.1:8000",
      "wss://workbench.example.com",
    );
    // Token may be absent (undefined/null/empty) or any arbitrary string,
    // covering both the "with token" and "without token" cases.
    const tokenArb = fc.oneof(
      fc.constant(undefined),
      fc.constant(null),
      fc.constant(""),
      fc.string(),
    );

    fc.assert(
      fc.property(
        wsBaseArb,
        tokenArb,
        fc.string(),
        fc.string(),
        fc.string(),
        (base, token, conv, task, extra) => {
          const url = buildChatUrl(base, conv, task, extra);
          const args = buildWsArgs(url, token as string | null | undefined);

          // The built URL must parse and must not contain a `token` query param.
          const parsed = new URL(args.url);
          expect(parsed.searchParams.has("token")).toBe(false);
          // Defensive: no case-variant `token` key either.
          for (const key of parsed.searchParams.keys()) {
            expect(key.toLowerCase()).not.toBe("token");
          }
        },
      ),
      fcParams(),
    );
  });
});
