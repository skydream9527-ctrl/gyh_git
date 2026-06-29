import fc from "fast-check";
import { describe, it, expect } from "vitest";
import { pushPending, PENDING_QUEUE_MAX } from "@/hooks/wsConnection";
import { fcParams } from "@/test/fcConfig";

// Feature: websocket-token-stability, Property 8: Pending queue bound and order
//
// For any sequence of sends issued while the connection is not open,
// `pushPending(queue, payload, max)` retains at most the `max` most recently
// enqueued messages (discarding the oldest on overflow) and preserves enqueue
// order so the queue can be flushed oldest-first on reconnect. The fold starts
// from an empty queue. Because the helper is pure, folding it over a send
// sequence models the client appending each outbound message while not open.
//
// Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6

describe("Feature: websocket-token-stability, Property 8: Pending queue bound and order", () => {
  // Arbitrary payloads (strings); allow duplicates to ensure we reason about
  // positions, not value identity.
  const payloads = fc.array(fc.string(), { maxLength: 50 });

  // Fold pushPending over a sequence of sends starting from [].
  const fold = (sends: readonly string[], max: number): string[] =>
    sends.reduce<string[]>((q, p) => pushPending(q, p, max), []);

  it("with max=5: length <= 5 and retains exactly the last 5 enqueued in original order", () => {
    fc.assert(
      fc.property(payloads, (sends) => {
        const result = fold(sends, PENDING_QUEUE_MAX);

        // Bound: never holds more than the cap.
        expect(result.length).toBeLessThanOrEqual(PENDING_QUEUE_MAX);

        // Retained items are exactly the last `max` enqueued, in original
        // relative order (oldest-first), so flush order is preserved.
        const expected = sends.slice(Math.max(0, sends.length - PENDING_QUEUE_MAX));
        expect(result).toEqual(expected);
      }),
      fcParams(),
    );
  });

  it("with arbitrary max: length <= max and retains exactly the last max enqueued in order", () => {
    fc.assert(
      fc.property(payloads, fc.integer({ min: 0, max: 12 }), (sends, max) => {
        const result = fold(sends, max);

        // Bound holds for any non-negative cap.
        expect(result.length).toBeLessThanOrEqual(max);

        // Retained tail equals the last `max` enqueued in their original order.
        const expected = sends.slice(Math.max(0, sends.length - max));
        expect(result).toEqual(expected);
      }),
      fcParams(),
    );
  });

  it("preserves enqueue order: result is always a contiguous suffix of the send sequence", () => {
    // Order preservation for oldest-first flush: the retained queue is exactly
    // the suffix of what was enqueued, never reordered.
    fc.assert(
      fc.property(payloads, fc.integer({ min: 0, max: 12 }), (sends, max) => {
        const result = fold(sends, max);
        const suffix = sends.slice(sends.length - result.length);
        expect(result).toEqual(suffix);
      }),
      fcParams(),
    );
  });

  it("does not mutate the input queue", () => {
    fc.assert(
      fc.property(
        fc.array(fc.string(), { maxLength: 10 }),
        fc.string(),
        fc.integer({ min: 0, max: 12 }),
        (queue, payload, max) => {
          const snapshot = [...queue];
          const result = pushPending(queue, payload, max);

          // Input array is untouched (non-mutation).
          expect(queue).toEqual(snapshot);
          // A fresh array is returned, not the same reference.
          expect(result).not.toBe(queue);
        },
      ),
      fcParams(),
    );
  });
});
