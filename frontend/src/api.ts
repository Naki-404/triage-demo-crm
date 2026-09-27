export type User = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "manager" | "viewer";
  is_active: boolean;
  max_discount_pct?: number;
};

export type Client = {
  id: number;
  name: string;
  iin: string;
  phone: string | null;
  email: string | null;
  birth_date?: string | null;
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

export type Course = {
  id: number;
  code: string;
  title: string;
  price_kzt: string;
};

export type Contract = {
  id: number;
  number: string;
  client_id: number;
  status: string;
  total_kzt: string;
  discount_pct: number;
};

export type Payment = {
  id: number;
  contract_id: number;
  amount_kzt: string;
  status: string;
  card_last4: string | null;
  paid_at: string | null;
};

export type Enrollment = {
  id: number;
  client_id: number;
  course_id: number;
  price_kzt: string;
  discount_pct: number;
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
  standPublic: () => request<{ crm_mode: string; stand_ui: boolean; company?: string }>("/api/stand/public"),
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
  createClient: (body: { name: string; iin: string; phone?: string; email?: string; birth_date?: string }) =>
    request<Client>("/api/customers", { method: "POST", body: JSON.stringify(body) }),
  listNotes: (clientId: number) => request<Note[]>(`/api/customers/${clientId}/notes`),
  createNote: (clientId: number, body: string) =>
    request<Note>(`/api/customers/${clientId}/notes`, { method: "POST", body: JSON.stringify({ body }) }),
  getTax: (clientId: number) => request<Record<string, unknown>>(`/api/customers/${clientId}/tax`),
  exportUrl: (fmt: "csv" | "xlsx") => `/api/customers/export?fmt=${fmt}`,
  listCourses: () => request<Course[]>("/api/courses"),
  listContracts: (clientId: number) => request<Contract[]>(`/api/clients/${clientId}/contracts`),
  listPayments: (contractId: number) => request<Payment[]>(`/api/contracts/${contractId}/payments`),
  listEnrollments: (clientId: number) => request<Enrollment[]>(`/api/clients/${clientId}/enrollments`),
  enroll: (body: { client_id: number; course_id: number; discount_pct?: number }) =>
    request<Enrollment[]>("/api/enrollments", { method: "POST", body: JSON.stringify(body) }),
};
