import fc from "fast-check";
import { describe, it, expect } from "vitest";
import {
  reconnectWarningVisible,
  RECONNECT_WARNING_THRESHOLD,
} from "@/hooks/wsConnection";
import { fcParams } from "@/test/fcConfig";

// Feature: websocket-token-stability, Property 7: Reconnect warning threshold
//
// For any run of consecutive failed reconnect attempts,
// `reconnectWarningVisible(consecutiveFailures, threshold)` is true if and only
// if the count is at least `threshold` (the default RECONNECT_WARNING_THRESHOLD
// is 5). The warning clears (becomes false) when an attempt reaches the open
// state, which resets the consecutive-failure count to 0.
//
// Validates: Requirements 5.5

describe("Feature: websocket-token-stability, Property 7: Reconnect warning threshold", () => {
  it("the configured threshold is 5", () => {
    expect(RECONNECT_WARNING_THRESHOLD).toBe(5);
  });

  it("visible iff consecutiveFailures >= threshold for any run length and threshold", () => {
    fc.assert(
      fc.property(
        // Include 0 and large failure runs.
        fc.integer({ min: 0, max: 1000 }),
        fc.integer({ min: 1, max: 50 }),
        (failures, threshold) => {
          expect(reconnectWarningVisible(failures, threshold)).toBe(failures >= threshold);
        },
      ),
      fcParams(),
    );
  });

  it("uses the >= 5 rule against the default threshold for any run length", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1000 }),
        (failures) => {
          expect(reconnectWarningVisible(failures, RECONNECT_WARNING_THRESHOLD)).toBe(
            failures >= 5,
          );
        },
      ),
      fcParams(),
    );
  });

  it("boundary: n === threshold-1 is false and n === threshold is true", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 50 }),
        (threshold) => {
          // Just below the threshold: warning hidden.
          expect(reconnectWarningVisible(threshold - 1, threshold)).toBe(false);
          // Exactly at the threshold: warning shown.
          expect(reconnectWarningVisible(threshold, threshold)).toBe(true);
          // One above the threshold remains visible.
          expect(reconnectWarningVisible(threshold + 1, threshold)).toBe(true);
        },
      ),
      fcParams(),
    );
  });

  it("clears (false) when an attempt reaches open and the count resets to 0", () => {
    fc.assert(
      fc.property(
        // Any prior failure run, however large, that may have shown the warning.
        fc.integer({ min: 0, max: 1000 }),
        fc.integer({ min: 1, max: 50 }),
        (priorFailures, threshold) => {
          // Reaching the open state resets the consecutive-failure count to 0,
          // so the warning is no longer visible regardless of the prior run.
          void reconnectWarningVisible(priorFailures, threshold);
          const afterOpen = 0;
          expect(reconnectWarningVisible(afterOpen, threshold)).toBe(false);
        },
      ),
      fcParams(),
    );
  });
});
