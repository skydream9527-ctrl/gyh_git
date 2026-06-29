import axios, { AxiosError, AxiosResponse } from "axios";
import type { ApiEnvelope } from "@/types/api";

const TOKEN_KEY = "ice-access-token";
const REFRESH_KEY = "ice-refresh-token";

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

const http = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

http.interceptors.request.use((cfg) => {
  const token = getAccessToken();
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`;
  }
  return cfg;
});

http.interceptors.response.use(
  (resp: AxiosResponse<ApiEnvelope>) => resp,
  async (err: AxiosError<ApiEnvelope>) => {
    if (err.response?.status === 401 && err.config && !(err.config as any)._retried) {
      // Cookie mode: backend sets httpOnly cookie, no localStorage refresh token.
      // Legacy mode: refresh_token lives in localStorage.
      const refresh = localStorage.getItem(REFRESH_KEY);
      const useCookie = !refresh; // if no localStorage token, assume cookie mode

      if (refresh || useCookie) {
        try {
          const r = await axios.post<ApiEnvelope<{ access_token: string; refresh_token?: string }>>(
            "/api/v1/auth/refresh",
            useCookie ? {} : { refresh_token: refresh },
            useCookie ? { withCredentials: true } : undefined,
          );
          const newAccess = r.data.data.access_token;
          const newRefresh = r.data.data.refresh_token;
          if (newRefresh) {
            // Legacy mode: server returned refresh token in body
            setTokens(newAccess, newRefresh);
          } else {
            // Cookie mode: refresh token is in httpOnly cookie, just save access
            localStorage.setItem(TOKEN_KEY, newAccess);
          }
          (err.config as any)._retried = true;
          err.config.headers.Authorization = `Bearer ${newAccess}`;
          return http.request(err.config);
        } catch {
          clearTokens();
          if (location.pathname !== "/login") {
            location.href = "/login";
          }
        }
      } else if (location.pathname !== "/login") {
        location.href = "/login";
      }
    }
    return Promise.reject(err);
  },
);

export interface ApiError extends Error {
  errorCode?: string;
  status?: number;
  detail?: unknown;
  /** 后端中间件分配的 request_id（响应头 X-Request-Id 或 envelope.request_id）。
   * 报错时贴这个 ID，admin 可在 /admin/diagnostics 反查到所有相关事件。 */
  requestId?: string;
}

function pickRequestId(resp: AxiosResponse | undefined, body: unknown): string | undefined {
  // axios 把响应头键统一小写化，所以只查小写形式即可。
  const headerId = resp?.headers?.["x-request-id"] as string | undefined;
  const bodyId =
    body && typeof body === "object" && "request_id" in (body as Record<string, unknown>)
      ? ((body as Record<string, unknown>).request_id as string | undefined)
      : undefined;
  return headerId || bodyId;
}

export async function api<T>(promise: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  try {
    const resp = await promise;
    if (resp.data.code !== 0) {
      const e = new Error(resp.data.message) as ApiError;
      e.errorCode = resp.data.error_code;
      e.requestId = pickRequestId(resp, resp.data);
      throw e;
    }
    return resp.data.data;
  } catch (err) {
    if (axios.isAxiosError<ApiEnvelope>(err) && err.response) {
      const body = err.response.data;
      const e = new Error(body?.message || err.message) as ApiError;
      e.errorCode = body?.error_code;
      e.status = err.response.status;
      e.detail = body?.data;
      e.requestId = pickRequestId(err.response, body);
      throw e;
    }
    throw err;
  }
}

export default http;
