const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("docsprint_token");
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ── Auth ──
export const authApi = {
  register: (email: string, password: string) =>
    request<import("./types").AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<import("./types").AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<import("./types").User>("/api/v1/auth/me"),
};

// ── Documents ──
export const documentsApi = {
  upload: (file: File, mode: string, prompt?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);
    if (prompt) form.append("prompt", prompt);
    return request<import("./types").DocumentUploadResponse>(
      "/api/v1/documents/upload",
      {
        method: "POST",
        body: form,
      }
    );
  },

  list: (skip = 0, limit = 20) =>
    request<import("./types").DocumentListResponse>(
      `/api/v1/documents?skip=${skip}&limit=${limit}`
    ),

  get: (id: number) =>
    request<import("./types").DocumentDetailResponse>(
      `/api/v1/documents/${id}`
    ),

  getResult: (id: number) =>
    request<import("./types").DocumentResultResponse>(
      `/api/v1/documents/${id}/result`
    ),
};

// ── Jobs ──
export const jobsApi = {
  list: (skip = 0, limit = 20) =>
    request<import("./types").JobListResponse>(
      `/api/v1/jobs?skip=${skip}&limit=${limit}`
    ),

  get: (id: number) =>
    request<import("./types").JobResponse>(`/api/v1/jobs/${id}`),
};

// ── Usage ──
export const usageApi = {
  get: () => request<import("./types").UsageResponse>("/api/v1/usage"),

  history: () =>
    request<import("./types").UsageHistoryResponse>("/api/v1/usage/history"),
};