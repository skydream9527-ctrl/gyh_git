import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAuthStore } from "./authStore";

// Mock the api/client module
vi.mock("@/api/client", () => ({
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
  default: {},
  api: vi.fn(),
}));

// Mock the api/endpoints module
vi.mock("@/api/endpoints", () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn(),
  },
}));

import { setTokens, clearTokens } from "@/api/client";
import { authApi } from "@/api/endpoints";

const mockSetTokens = vi.mocked(setTokens);
const mockClearTokens = vi.mocked(clearTokens);
const mockLogin = vi.mocked(authApi.login);
const mockRegister = vi.mocked(authApi.register);
const mockMe = vi.mocked(authApi.me);

describe("authStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state
    useAuthStore.setState({ user: null, loading: false, error: null });
  });

  describe("initial state", () => {
    it("starts with user null, loading false, no error", () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe("login", () => {
    const mockUser = {
      id: "u1",
      email: "test@test.com",
      name: "Test",
      auth_role: "user" as const,
      feishu_bound: false,
    };

    it("sets tokens and user on successful login (legacy mode)", async () => {
      mockLogin.mockResolvedValue({
        user: mockUser,
        tokens: {
          access_token: "acc-123",
          refresh_token: "ref-456",
          token_type: "bearer",
          expires_in: 3600,
        },
      });

      await useAuthStore.getState().login("test@test.com", "pass");

      expect(mockSetTokens).toHaveBeenCalledWith("acc-123", "ref-456");
      expect(useAuthStore.getState().user).toEqual(mockUser);
      expect(useAuthStore.getState().loading).toBe(false);
      expect(useAuthStore.getState().error).toBeNull();
    });

    it("stores only access token in cookie mode (no refresh_token in body)", async () => {
      mockLogin.mockResolvedValue({
        user: mockUser,
        tokens: {
          access_token: "acc-789",
          refresh_token: undefined as any,
          token_type: "bearer",
          expires_in: 3600,
        },
      });

      await useAuthStore.getState().login("test@test.com", "pass");

      expect(mockSetTokens).not.toHaveBeenCalled();
      expect(localStorage.getItem("ice-access-token")).toBe("acc-789");
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });

    it("sets error and throws on login failure", async () => {
      mockLogin.mockRejectedValue({ message: "密码错误" });

      await expect(useAuthStore.getState().login("x", "y")).rejects.toThrow("密码错误");

      expect(useAuthStore.getState().error).toBe("密码错误");
      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().loading).toBe(false);
    });

    it("sets loading true during login, false after", async () => {
      let resolveLogin: (v: any) => void;
      mockLogin.mockReturnValue(new Promise((r) => { resolveLogin = r; }));

      const loginPromise = useAuthStore.getState().login("a", "b");
      expect(useAuthStore.getState().loading).toBe(true);

      resolveLogin!({
        user: mockUser,
        tokens: { access_token: "a", refresh_token: "r", token_type: "bearer", expires_in: 60 },
      });
      await loginPromise;

      expect(useAuthStore.getState().loading).toBe(false);
    });
  });

  describe("register", () => {
    it("returns pending status without setting user", async () => {
      mockRegister.mockResolvedValue({
        status: "pending",
        user: { id: "u2", email: "new@test.com", name: "New", auth_role: "user", feishu_bound: false },
        message: "等待管理员审批",
      });

      const result = await useAuthStore.getState().register("new@test.com", "New", "pass123");

      expect(result).toEqual({ status: "pending", message: "等待管理员审批" });
      // user should NOT be set (no auto-login on register)
      expect(useAuthStore.getState().user).toBeNull();
    });

    it("sets error and throws on register failure", async () => {
      mockRegister.mockRejectedValue({ message: "邮箱已存在" });

      await expect(
        useAuthStore.getState().register("dup@test.com", "Dup", "pass"),
      ).rejects.toThrow("邮箱已存在");

      expect(useAuthStore.getState().error).toBe("邮箱已存在");
    });
  });

  describe("bootstrapMe", () => {
    it("sets user on successful /me fetch", async () => {
      const user = { id: "u1", email: "me@x.com", name: "Me", auth_role: "admin" as const, feishu_bound: true };
      mockMe.mockResolvedValue(user);

      await useAuthStore.getState().bootstrapMe();

      expect(useAuthStore.getState().user).toEqual(user);
    });

    it("clears tokens and nulls user on /me failure", async () => {
      mockMe.mockRejectedValue(new Error("401"));

      await useAuthStore.getState().bootstrapMe();

      expect(mockClearTokens).toHaveBeenCalled();
      expect(useAuthStore.getState().user).toBeNull();
    });
  });

  describe("logout", () => {
    it("clears tokens and sets user to null", () => {
      useAuthStore.setState({
        user: { id: "u1", email: "x", name: "X", auth_role: "user", feishu_bound: false },
      });

      useAuthStore.getState().logout();

      expect(mockClearTokens).toHaveBeenCalled();
      expect(useAuthStore.getState().user).toBeNull();
    });
  });
});
