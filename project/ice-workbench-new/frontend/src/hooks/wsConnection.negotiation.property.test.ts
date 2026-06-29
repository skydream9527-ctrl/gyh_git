import fc from "fast-check";
import { describe, it, expect } from "vitest";
import { buildWsArgs } from "@/hooks/wsConnection";
import { fcParams } from "@/test/fcConfig";

// Feature: websocket-token-stability, Property 4: Subprotocol negotiation contract
//
// Client side of the negotiation contract: for any non-empty token, the
// Workbench_Client constructs the connection with subprotocols exactly
// ["bearer", token] (the literal "bearer" first, the token second); when no
// token is available it offers no subprotocols (undefined). The token value is
// never offered as the first/negotiated entry.
//
// Validates: Requirements 1.1, 1.3
describe("Feature: websocket-token-stability, Property 4: Subprotocol negotiation contract", () => {
  const URL = "wss://example.test/api/v1/ws/conversations/c1";

  it("non-empty token → subprotocols exactly ['bearer', token] (literal 'bearer' first)", () => {
    // Non-empty tokens, including whitespace-only and strings that themselves
    // contain the word "bearer", to guard against accidental ordering bugs.
    const nonEmptyToken = fc.oneof(
      fc.string({ minLength: 1 }).filter((s) => s.length > 0),
      fc.constant(" "),
      fc.constant("\t\n"),
      fc.constant("bearer"),
      fc.constant("Bearer realtoken"),
    );

    fc.assert(
      fc.property(nonEmptyToken, (token) => {
        const { url, subprotocols } = buildWsArgs(URL, token);

        // URL is passed through unchanged.
        expect(url).toBe(URL);

        // Subprotocols are offered as an exact two-entry array.
        expect(Array.isArray(subprotocols)).toBe(true);
        expect(subprotocols).toEqual(["bearer", token]);

        // Reinforce the contract: literal "bearer" first, token second, no
        // extra entries, and the token is never the negotiated (first) value.
        const subs = subprotocols as string[];
        expect(subs).toHaveLength(2);
        expect(subs[0]).toBe("bearer");
        expect(subs[1]).toBe(token);
      }),
      fcParams(),
    );
  });

  it("absent/empty token → no subprotocols offered (undefined)", () => {
    const absentToken = fc.constantFrom<string | null | undefined>("", null, undefined);

    fc.assert(
      fc.property(absentToken, (token) => {
        const { url, subprotocols } = buildWsArgs(URL, token);

        expect(url).toBe(URL);
        expect(subprotocols).toBeUndefined();
      }),
      fcParams(),
    );
  });
});
