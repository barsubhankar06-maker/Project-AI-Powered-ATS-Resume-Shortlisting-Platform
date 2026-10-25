// Minimal typed API client. The access token and active organization are kept
// in localStorage and attached to every request. All business logic lives on
// the server; this file never holds secrets.

const TOKEN_KEY = "talentlens_token";
const ORG_KEY = "talentlens_org";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const orgStore = {
  get: () => localStorage.getItem(ORG_KEY),
  set: (id: string) => localStorage.setItem(ORG_KEY, id),
  clear: () => localStorage.removeItem(ORG_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function detailFrom(body: any): string {
  if (!body) return "Request failed";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ");
  }
  return "Request failed";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as any) };
  const token = tokenStore.get();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const org = orgStore.get();
  if (org) headers["X-Org-Id"] = org;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`/api${path}`, { ...options, headers });
  if (res.status === 204) return undefined as T;
  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : await res.text();
  if (!res.ok) {
    if (res.status === 401) tokenStore.clear();
    throw new ApiError(detailFrom(body), res.status);
  }
  return body as T;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: any) =>
    request<T>(p, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  patch: <T>(p: string, body?: any) => request<T>(p, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
  postForm: <T>(p: string, form: FormData) => request<T>(p, { method: "POST", body: form }),
};
