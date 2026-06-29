import fc from "fast-check";
import { describe, it, expect } from "vitest";
import { classifyClose, type CloseClassification } from "@/hooks/wsConnection";
import { fcParams } from "@/test/fcConfig";

// Feature: websocket-token-stability, Property 6: Disconnect classification totality
//
// For any observed close code, `classifyClose(code, hasRefresh)` returns
// exactly one of recoverable/fatal with the matching action:
//   - 4403                      → fatal,       action "permission_denied" (no reconnect)
//   - 4401 without refresh      → fatal,       action "clear_and_redirect" (no reconnect)
//   - 4401 with refresh         → recoverable, action "refresh_and_reconnect"
//   - 1006 / 1001 / 1011 and
//     every other code          → recoverable, action "reconnect"
//
// Totality: every generated code (full integer range, the WebSocket
// application range 1000-4999, and the special codes) yields a defined
// classification whose `kind` is "recoverable" XOR "fatal" with a matching
// `action.type`.
//
// Validates: Requirements 5.1, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6

describe("Feature: websocket-token-stability, Property 6: Disconnect classification totality", () => {
  // The set of action types that pair with each kind. Used to assert the
  // recoverable XOR fatal invariant by construction.
  const FATAL_ACTIONS = new Set(["permission_denied", "clear_and_redirect"]);
  const RECOVERABLE_ACTIONS = new Set(["refresh_and_reconnect", "reconnect"]);

  // The independent reference implementation of the classification table. The
  // property asserts `classifyClose` agrees with this table for every code.
  function expected(code: number, hasRefresh: boolean): CloseClassification {
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

  // Generator covering the full integer range, the WebSocket close-code range
  // (1000-4999), and the special codes called out by the spec, so the totality
  // claim is exercised across the whole input space rather than a narrow band.
  const closeCode = fc.oneof(
    { weight: 3, arbitrary: fc.integer() },
    { weight: 3, arbitrary: fc.integer({ min: 1000, max: 4999 }) },
    {
      weight: 2,
      arbitrary: fc.constantFrom(4403, 4401, 1006, 1001, 1011, 1000, 1005, 1012, 3000, 4000, 4999),
    },
  );

  it("classifies every close code into exactly one kind with the matching action", () => {
    fc.assert(
      fc.property(closeCode, fc.boolean(), (code, hasRefresh) => {
        const result = classifyClose(code, hasRefresh);

        // Totality: a classification is always defined.
        expect(result).toBeDefined();
        expect(result.action).toBeDefined();

        // Exactly one of recoverable / fatal (XOR), encoded as a valid kind.
        expect(result.kind === "recoverable" || result.kind === "fatal").toBe(true);

        // The action type pairs with the kind: fatal actions never appear under
        // recoverable and vice versa — this is the XOR invariant in practice.
        if (result.kind === "fatal") {
          expect(FATAL_ACTIONS.has(result.action.type)).toBe(true);
          expect(RECOVERABLE_ACTIONS.has(result.action.type)).toBe(false);
        } else {
          expect(RECOVERABLE_ACTIONS.has(result.action.type)).toBe(true);
          expect(FATAL_ACTIONS.has(result.action.type)).toBe(false);
        }

        // Agreement with the reference classification table.
        expect(result).toEqual(expected(code, hasRefresh));
      }),
      fcParams(),
    );
  });

  it("4403 is always fatal permission_denied regardless of refresh state (no reconnect)", () => {
    fc.assert(
      fc.property(fc.boolean(), (hasRefresh) => {
        const result = classifyClose(4403, hasRefresh);
        expect(result.kind).toBe("fatal");
        expect(result.action.type).toBe("permission_denied");
      }),
      fcParams(),
    );
  });

  it("4401 depends only on refresh presence: with → recoverable refresh_and_reconnect, without → fatal clear_and_redirect", () => {
    fc.assert(
      fc.property(fc.boolean(), (hasRefresh) => {
        const result = classifyClose(4401, hasRefresh);
        if (hasRefresh) {
          expect(result.kind).toBe("recoverable");
          expect(result.action.type).toBe("refresh_and_reconnect");
        } else {
          expect(result.kind).toBe("fatal");
          expect(result.action.type).toBe("clear_and_redirect");
        }
      }),
      fcParams(),
    );
  });

  it("1006/1001/1011 and every non-auth code are recoverable reconnect regardless of refresh state", () => {
    // Any code that is neither 4403 nor 4401 must be a recoverable plain reconnect.
    const nonAuthCode = fc
      .oneof(fc.integer(), fc.integer({ min: 1000, max: 4999 }), fc.constantFrom(1006, 1001, 1011, 1000))
      .filter((c) => c !== 4403 && c !== 4401);

    fc.assert(
      fc.property(nonAuthCode, fc.boolean(), (code, hasRefresh) => {
        const result = classifyClose(code, hasRefresh);
        expect(result.kind).toBe("recoverable");
        expect(result.action.type).toBe("reconnect");
      }),
      fcParams(),
    );
  });
});
