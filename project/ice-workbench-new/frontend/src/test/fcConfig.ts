import fc from "fast-check";

// Shared fast-check configuration for this feature's property tests.
//
// The design (and tasks.md) require every property test for
// websocket-token-stability to run a minimum of 100 iterations. Importing
// `FC_NUM_RUNS` / `fcParams` keeps that contract in one place so individual
// property tests don't each hardcode the count.
//
// Usage:
//   import fc from "fast-check";
//   import { fcParams } from "@/test/fcConfig";
//   it("Property N: ...", () => {
//     fc.assert(fc.property(arb, predicate), fcParams());
//   });
export const FC_NUM_RUNS = 100;

/**
 * Default parameters for this feature's property tests. Pass overrides to
 * extend (e.g. a fixed `seed` for reproducing a counterexample) while keeping
 * the 100-iteration floor unless explicitly raised.
 */
export function fcParams(
  overrides: fc.Parameters<unknown> = {},
): fc.Parameters<unknown> {
  return { numRuns: FC_NUM_RUNS, ...overrides };
}
