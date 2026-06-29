// 轻量 API 客户端：基于 fetch，统一解析后端错误信封 {code,message,error_code,data}。
const BASE = "/api/v1";

export interface Envelope<T = unknown> {
  code: number;
  message: string;
  error_code: string;
  data: T;
}

export class ApiError extends Error {
  constructor(public code: number, public errorCode: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("idw_token");
  const res = await fetch(BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  const body = (await res.json()) as Envelope<T>;
  if (!res.ok || (body.error_code && body.error_code !== "OK")) {
    throw new ApiError(body.code ?? res.status, body.error_code ?? "INTERNAL", body.message);
  }
  return body.data;
}

export const apiGet = <T>(path: string) => request<T>(path);
export const apiPost = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(data ?? {}) });
export const apiPut = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "PUT", body: JSON.stringify(data ?? {}) });
export const apiDelete = <T>(path: string) =>
  request<T>(path, { method: "DELETE" });
