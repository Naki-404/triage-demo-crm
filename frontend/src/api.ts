export type User = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "manager" | "viewer";
  is_active: boolean;
};

export type Client = {
  id: number;
  name: string;
  iin: string;
  phone: string | null;
  email: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
};

export type ClientList = {
  items: Client[];
  total: number;
  page: number;
  page_size: number;
};

export type Note = {
  id: number;
  client_id: number;
  author_id: number;
  body: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res as unknown as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<{ status: string }>("/api/auth/logout", { method: "POST" }),
  me: () => request<User>("/api/auth/me"),
  standPublic: () => request<{ crm_mode: string; stand_ui: boolean }>("/api/stand/public"),
  stand: () => request<Record<string, boolean | string>>("/api/stand"),
  patchStand: (body: Record<string, unknown>) =>
    request<Record<string, boolean | string>>("/api/stand", { method: "PATCH", body: JSON.stringify(body) }),
  listClients: (opts?: { q?: string; page?: number; page_size?: number }) => {
    const page = opts?.page ?? 1;
    const page_size = opts?.page_size ?? 25;
    const q = opts?.q ? `&q=${encodeURIComponent(opts.q)}` : "";
    return request<ClientList>(`/api/customers?page=${page}&page_size=${page_size}${q}`);
  },
  getClient: (id: number) => request<Client>(`/api/customers/${id}`),
  createClient: (body: { name: string; iin: string; phone?: string; email?: string }) =>
    request<Client>("/api/customers", { method: "POST", body: JSON.stringify(body) }),
  listNotes: (clientId: number) => request<Note[]>(`/api/customers/${clientId}/notes`),
  createNote: (clientId: number, body: string) =>
    request<Note>(`/api/customers/${clientId}/notes`, { method: "POST", body: JSON.stringify({ body }) }),
  getTax: (clientId: number) => request<Record<string, unknown>>(`/api/customers/${clientId}/tax`),
  exportUrl: (fmt: "csv" | "xlsx") => `/api/customers/export?fmt=${fmt}`,
};
