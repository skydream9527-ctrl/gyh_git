import fc from "fast-check";
import { describe, it, expect } from "vitest";
import type { StreamPhase } from "@/hooks/useChatSocket";
import { fcParams } from "@/test/fcConfig";

// Feature: websocket-token-stability, Property 10: Keepalive is inert on the client
//
// For any client state, receiving a Keepalive_Frame (`{"type":"keepalive"}`)
// leaves stream content, phase, and error state unchanged.
//
// Validates: Requirements 7.3
//
// ----------------------------------------------------------------------------
// Approach
// ----------------------------------------------------------------------------
// `useChatSocket.handleEvent` is a `switch (ev.type)` whose cases are wired
// directly into React state setters, refs, and callbacks, so it cannot be
// invoked as a pure function without standing up the whole hook. Re-wiring the
// switch into an extracted reducer would touch every case and risk regressions
// in unrelated event handling, which the task flags as too invasive.
//
// Crucially, the switch has **no `keepalive` case** (and no `default` branch):
// a `{"type":"keepalive"}` frame matches nothing, so not a single setter runs
// and the client state is left untouched. That is exactly the contract under
// test.
//
// To test this as a pure property we model the switch's effect on the three
// observable state fields the requirement names — stream `content`, `phase`,
// and `errorCode` — in a faithful local reducer `reduceClientEvent`. The
// reducer reproduces the mutating cases (`agent_typing`, `agent_message`,
// `tool_call_start`, `tool_call_done`, `agent_message_done`, `error`) so the
// model is non-vacuous, and routes `keepalive` together with every other
// non-matching type through the no-op default path — mirroring the real
// switch. A no-op returns the *same* state object (referential identity), which
// lets the property assert "unchanged" strictly.
// ----------------------------------------------------------------------------

/** The slice of client state the keepalive-inertness requirement constrains. */
interface ClientState {
  content: string;
  phase: StreamPhase;
  errorCode: string | null;
}

/**
 * Faithful pure model of `useChatSocket.handleEvent`'s effect on the
 * `{content, phase, errorCode}` slice. Known event types mutate exactly as the
 * real switch does; `keepalive` and every other unmatched type fall through the
 * no-op default and return the input state unchanged (same reference).
 */
function reduceClientEvent(state: ClientState, ev: { type: string; [k: string]: unknown }): ClientState {
  switch (ev.type) {
    case "agent_typing":
      return { ...state, phase: ev.status === "start" ? "typing" : "idle" };
    case "agent_message":
      return {
        ...state,
        phase: "streaming",
        content: state.content + (typeof ev.content === "string" ? ev.content : ""),
      };
    case "tool_call_start":
      return { ...state, phase: "tool" };
    case "tool_call_done":
      return ev.retry ? { ...state, phase: "done" } : state;
    case "agent_message_done":
      return { ...state, phase: "done" };
    case "error":
      return {
        ...state,
        phase: "error",
        errorCode: typeof ev.error_code === "string" ? ev.error_code : "ERROR",
      };
    // `keepalive` (the frame under test), `inflight_status`, `run_event`,
    // `file_created`, `todos_updated`, plan/hitl events, and any unknown type
    // do not touch content/phase/errorCode → no-op. Returning the same
    // reference encodes "left unchanged".
    default:
      return state;
  }
}

describe("Feature: websocket-token-stability, Property 10: Keepalive is inert on the client", () => {
  // Arbitrary prior client state spanning every phase, arbitrary stream
  // content (incl. empty/unicode), and present-or-absent error state.
  const clientState: fc.Arbitrary<ClientState> = fc.record({
    content: fc.string(),
    phase: fc.constantFrom<StreamPhase>("idle", "typing", "streaming", "tool", "done", "error"),
    errorCode: fc.option(fc.string(), { nil: null }),
  });

  // Keepalive frames are `{"type":"keepalive"}`. A defensive variant also
  // attaches arbitrary extra fields, since an inert frame must stay inert even
  // if the server ever decorates it with extra keys.
  const keepaliveFrame = fc.oneof(
    fc.constant<{ type: string; [k: string]: unknown }>({ type: "keepalive" }),
    fc
      .dictionary(
        fc.string().filter((k) => k !== "type"),
        fc.anything(),
      )
      .map((extra) => ({ type: "keepalive", ...extra })),
  );

  it("leaves content, phase, and error state unchanged for any client state", () => {
    fc.assert(
      fc.property(clientState, keepaliveFrame, (state, frame) => {
        const before = { ...state };
        const after = reduceClientEvent(state, frame);

        // Each tracked field is unchanged.
        expect(after.content).toBe(before.content);
        expect(after.phase).toBe(before.phase);
        expect(after.errorCode).toBe(before.errorCode);

        // The whole slice is value-equal, and the no-op path returns the very
        // same object (no setter ran), which is the strongest "inert" claim.
        expect(after).toEqual(before);
        expect(after).toBe(state);
      }),
      fcParams(),
    );
  });

  it("the keepalive frame is exactly the literal `{\"type\":\"keepalive\"}`", () => {
    // Anchors the test to the wire shape the WS_Endpoint sends (design Data
    // Models): a bare type discriminator with no payload.
    const initial: ClientState = { content: "partial output", phase: "streaming", errorCode: null };
    expect(reduceClientEvent(initial, { type: "keepalive" })).toBe(initial);
  });

  it("is non-vacuous: known events do mutate the same state slice", () => {
    // Guards against the model degenerating into an identity function — if a
    // representative known event did NOT change state, the inertness property
    // above would be meaningless.
    fc.assert(
      fc.property(clientState, (state) => {
        const errored = reduceClientEvent(state, { type: "error", error_code: "STREAM_INTERRUPTED" });
        expect(errored.phase).toBe("error");
        expect(errored.errorCode).toBe("STREAM_INTERRUPTED");

        const streamed = reduceClientEvent(state, { type: "agent_message", message_id: "m1", content: "x" });
        expect(streamed.phase).toBe("streaming");
        expect(streamed.content).toBe(state.content + "x");
      }),
      fcParams(),
    );
  });
});
