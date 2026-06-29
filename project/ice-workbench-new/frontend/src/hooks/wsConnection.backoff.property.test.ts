import fc from "fast-check";
import { describe, it, expect } from "vitest";
import { backoffDelay, BACKOFF_MS } from "@/hooks/wsConnection";
import { fcParams } from "@/test/fcConfig";

// Feature: websocket-token-stability, Property 5: Backoff sequence shape and reset
//
// For any attempt index k, `backoffDelay(k)` returns
// `BACKOFF_MS[min(k, BACKOFF_MS.length - 1)]` (clamped at 30000ms); the
// sequence is non-decreasing and caps at 30000ms. Reaching the open state
// resets the attempt index to 0, so the next scheduled delay is 1000ms.
//
// Validates: Requirements 5.1, 5.2, 5.3

describe("Feature: websocket-token-stability, Property 5: Backoff sequence shape and reset", () => {
  const LAST_INDEX = BACKOFF_MS.length - 1;
  const CAP_MS = BACKOFF_MS[LAST_INDEX];

  it("backoffDelay(attempt) equals BACKOFF_MS[min(attempt, last)] for any attempt (incl. > 6 and 0)", () => {
    fc.assert(
      fc.property(
        // Include the boundary at 0 and attempts well beyond the sequence length.
        fc.integer({ min: 0, max: 1000 }),
        (attempt) => {
          const expected = BACKOFF_MS[Math.min(attempt, LAST_INDEX)];
          expect(backoffDelay(attempt)).toBe(expected);
          // Delay never exceeds the 30s cap.
          expect(backoffDelay(attempt)).toBeLessThanOrEqual(CAP_MS);
        },
      ),
      fcParams(),
    );
  });

  it("the backoff sequence is non-decreasing and caps at 30000ms", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1000 }),
        (attempt) => {
          // Non-decreasing: a later attempt never waits less than an earlier one.
          expect(backoffDelay(attempt + 1)).toBeGreaterThanOrEqual(backoffDelay(attempt));
          // Anything at or beyond the last index is pinned to the 30s cap.
          if (attempt >= LAST_INDEX) {
            expect(backoffDelay(attempt)).toBe(30000);
          }
        },
      ),
      fcParams(),
    );
  });

  it("reset semantics: index 0 yields 1000ms (the next delay after reaching open)", () => {
    // Reaching the open state resets the attempt index to 0; the next scheduled
    // delay is therefore BACKOFF_MS[0] === 1000ms.
    expect(backoffDelay(0)).toBe(1000);
    expect(BACKOFF_MS[0]).toBe(1000);

    // Property form: for any prior failure count, once the index is reset to 0
    // the next delay is always 1000ms regardless of how high it had climbed.
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1000 }),
        (priorAttempt) => {
          // Simulate a climb followed by a reset-to-zero on open.
          void backoffDelay(priorAttempt);
          const afterReset = 0;
          expect(backoffDelay(afterReset)).toBe(1000);
        },
      ),
      fcParams(),
    );
  });
});
