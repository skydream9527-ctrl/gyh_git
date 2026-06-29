import { create } from "zustand";
import { authApi } from "@/api/endpoints";
import { clearTokens, setTokens } from "@/api/client";
import type { UserPublic } from "@/types/api";

/**
 * 支持三种登录方式：
 *  1) 米盾代理（自动）—— /users/me 通过 X-Proxy-UserDetail 识别身份；
 *  2) 账号密码 —— POST /auth/login 返回 access/refresh JWT，浏览器本地保存；
 *  3) 测试样例账号 —— 走相同的账号密码通道（admin / zhangmingyuan / lisihan 密码 test123）。
 */
interface AuthState {
  user: UserPublic | null;
  loading: boolean;
  error: string | null;
  /** 账号密码登录（同时覆盖测试样例）。成功后 setTokens 并刷新 user。 */
  login: (email: string, password: string) => Promise<void>;
  /**
   * 自助注册 — 现在走管理员审批流。成功后**不会**自动登录；
   * 返回 `{status: "pending", message}` 供 UI 展示"待审批"提示。
   */
  register: (
    email: string,
    name: string,
    password: string,
    xiaomi_email?: string,
  ) => Promise<{ status: "pending"; message: string }>;
  bootstrapMe: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  error: null,
  async login(email: string, password: string) {
    set({ loading: true, error: null });
    try {
      const resp = await authApi.login(email, password);
      if (resp.tokens.refresh_token) {
        // Legacy mode: both tokens in body
        setTokens(resp.tokens.access_token, resp.tokens.refresh_token);
      } else {
        // Cookie mode: refresh token in httpOnly cookie, only save access
        localStorage.setItem("ice-access-token", resp.tokens.access_token);
      }
      set({ user: resp.user });
    } catch (err) {
      const e = err as { message?: string; errorCode?: string };
      const msg = e.message || "登录失败";
      set({ error: msg });
      throw new Error(msg);
    } finally {
      set({ loading: false });
    }
  },
  async register(email: string, name: string, password: string, xiaomi_email?: string) {
    set({ loading: true, error: null });
    try {
      const resp = await authApi.register(email, name, password, xiaomi_email);
      // No token write: backend returns `{status: "pending", ...}`. The caller
      // is responsible for showing the "submitted, wait for admin approval"
      // screen. Do NOT mutate `user` — that would flip the SPA to logged-in
      // mode and send them to the dashboard.
      return { status: "pending" as const, message: resp.message };
    } catch (err) {
      const e = err as { message?: string; errorCode?: string };
      const msg = e.message || "注册失败";
      set({ error: msg });
      throw new Error(msg);
    } finally {
      set({ loading: false });
    }
  },
  async bootstrapMe() {
    try {
      const me = await authApi.me();
      set({ user: me });
    } catch {
      clearTokens();
      set({ user: null });
    }
  },
  logout() {
    clearTokens();
    set({ user: null });
  },
}));
