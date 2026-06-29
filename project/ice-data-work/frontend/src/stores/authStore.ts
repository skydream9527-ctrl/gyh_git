import { create } from "zustand";
import { apiGet, apiPost } from "@/api/client";

export interface User {
  id: string;
  name: string;
  platform_role: "super_admin" | "admin" | "user";
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, name?: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("idw_token"),
  loading: false,
  error: "",

  login: async (username, password) => {
    set({ loading: true, error: "" });
    try {
      const result = await apiPost<{ token: string; user: User }>("/auth/login", {
        username,
        password,
      });
      localStorage.setItem("idw_token", result.token);
      set({ user: result.user, token: result.token, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "登录失败";
      set({ loading: false, error: msg });
      throw e;
    }
  },

  register: async (username, password, name) => {
    set({ loading: true, error: "" });
    try {
      const result = await apiPost<{ token: string; user: User }>("/auth/register", {
        username,
        password,
        name: name || username,
      });
      localStorage.setItem("idw_token", result.token);
      set({ user: result.user, token: result.token, loading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "注册失败";
      set({ loading: false, error: msg });
      throw e;
    }
  },

  fetchMe: async () => {
    const token = localStorage.getItem("idw_token");
    if (!token) return;
    set({ loading: true });
    try {
      const user = await apiGet<User>("/users/me");
      set({ user, loading: false });
    } catch {
      // token 无效则清除
      localStorage.removeItem("idw_token");
      set({ user: null, token: null, loading: false });
    }
  },

  logout: () => {
    localStorage.removeItem("idw_token");
    set({ user: null, token: null });
  },

  clearError: () => set({ error: "" }),
}));
