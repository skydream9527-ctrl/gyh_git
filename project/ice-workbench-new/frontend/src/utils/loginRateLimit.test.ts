import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { checkLoginLimit, recordLoginFailure, clearLoginLimit } from "./loginRateLimit";

describe("loginRateLimit", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("checkLoginLimit", () => {
    it("returns 0 for a fresh email (no prior failures)", () => {
      expect(checkLoginLimit("user@test.com")).toBe(0);
    });

    it("returns 0 for empty email", () => {
      expect(checkLoginLimit("")).toBe(0);
    });

    it("returns 0 when under the attempt threshold", () => {
      recordLoginFailure("user@test.com");
      recordLoginFailure("user@test.com");
      recordLoginFailure("user@test.com");
      recordLoginFailure("user@test.com");
      // 4 failures — still under 5
      expect(checkLoginLimit("user@test.com")).toBe(0);
    });

    it("returns remaining seconds when at or over threshold", () => {
      vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));

      for (let i = 0; i < 5; i++) {
        recordLoginFailure("user@test.com");
      }

      // Advance 1 minute (60s) — should still be locked (window is 5 min)
      vi.setSystemTime(new Date("2026-01-01T00:01:00Z"));
      const remaining = checkLoginLimit("user@test.com");
      // 5 min = 300s, 60s elapsed → 240s remaining
      expect(remaining).toBe(240);
    });

    it("returns 0 after the window expires", () => {
      vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));

      for (let i = 0; i < 5; i++) {
        recordLoginFailure("user@test.com");
      }

      // Advance past 5 minute window
      vi.setSystemTime(new Date("2026-01-01T00:05:01Z"));
      expect(checkLoginLimit("user@test.com")).toBe(0);
    });

    it("is case-insensitive on email", () => {
      recordLoginFailure("User@Test.COM");
      recordLoginFailure("user@test.com");
      recordLoginFailure("USER@TEST.COM");
      recordLoginFailure("User@test.com");
      recordLoginFailure("user@TEST.com");

      expect(checkLoginLimit("USER@test.COM")).toBeGreaterThan(0);
    });
  });

  describe("recordLoginFailure", () => {
    it("increments count on each call within window", () => {
      vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));

      recordLoginFailure("a@b.com");
      recordLoginFailure("a@b.com");
      recordLoginFailure("a@b.com");

      // Still under limit
      expect(checkLoginLimit("a@b.com")).toBe(0);
    });

    it("resets window when called after window expires", () => {
      vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
      for (let i = 0; i < 5; i++) recordLoginFailure("a@b.com");

      // After window expires, a new failure starts a fresh window
      vi.setSystemTime(new Date("2026-01-01T00:06:00Z"));
      recordLoginFailure("a@b.com");

      // Only 1 failure in new window — should be allowed
      expect(checkLoginLimit("a@b.com")).toBe(0);
    });

    it("does nothing for empty email", () => {
      expect(() => recordLoginFailure("")).not.toThrow();
      expect(checkLoginLimit("")).toBe(0);
    });
  });

  describe("clearLoginLimit", () => {
    it("removes the rate limit for an email", () => {
      for (let i = 0; i < 5; i++) recordLoginFailure("locked@x.com");
      expect(checkLoginLimit("locked@x.com")).toBeGreaterThan(0);

      clearLoginLimit("locked@x.com");
      expect(checkLoginLimit("locked@x.com")).toBe(0);
    });

    it("is safe to call for non-existent email", () => {
      expect(() => clearLoginLimit("nobody@x.com")).not.toThrow();
    });
  });
});
