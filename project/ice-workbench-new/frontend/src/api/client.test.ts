import { describe, it, expect, beforeEach } from "vitest";
import { getAccessToken, setTokens, clearTokens } from "./client";

describe("client token management", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("setTokens", () => {
    it("stores access and refresh tokens in localStorage", () => {
      setTokens("access-123", "refresh-456");

      expect(localStorage.getItem("ice-access-token")).toBe("access-123");
      expect(localStorage.getItem("ice-refresh-token")).toBe("refresh-456");
    });

    it("overwrites existing tokens", () => {
      setTokens("old-access", "old-refresh");
      setTokens("new-access", "new-refresh");

      expect(localStorage.getItem("ice-access-token")).toBe("new-access");
      expect(localStorage.getItem("ice-refresh-token")).toBe("new-refresh");
    });
  });

  describe("getAccessToken", () => {
    it("returns null when no token stored", () => {
      expect(getAccessToken()).toBeNull();
    });

    it("returns the stored access token", () => {
      localStorage.setItem("ice-access-token", "my-token");
      expect(getAccessToken()).toBe("my-token");
    });
  });

  describe("clearTokens", () => {
    it("removes both tokens from localStorage", () => {
      setTokens("a", "r");
      clearTokens();

      expect(localStorage.getItem("ice-access-token")).toBeNull();
      expect(localStorage.getItem("ice-refresh-token")).toBeNull();
    });

    it("is safe to call when no tokens exist", () => {
      expect(() => clearTokens()).not.toThrow();
    });
  });
});
