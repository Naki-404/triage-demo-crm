import { request } from "./api/client";
import type {
  Client,
  ClientList,
  Contract,
  ContractDetail,
  ContractRow,
  Course,
  Dashboard,
  DueRow,
  Enrollment,
  Installment,
  Note,
  Package,
  Paged,
  Payment,
  PaymentRow,
  User,
} from "./api/types";

export type {
  Client,
  ClientList,
  Contract,
  ContractDetail,
  ContractRow,
  Course,
  Dashboard,
  DueRow,
  Enrollment,
  Installment,
  Note,
  Package,
  Paged,
  Payment,
  PaymentRow,
  User,
};

export type SimulateScenario = {
  id: string;
  title_ru: string;
  title_en: string;
  description_ru: string;
  description_en: string;
  attack: string;
  default_events: number;
  max_events: number;
};

export type SimulateResult = {
  scenario: string;
  attack: string;
  events: number;
  request_ids: string[];
  shipped: boolean;
};

export type CustomLogIn = {
  message: string;
  level?: "info" | "warning" | "error";
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";
  path?: string;
  status_code?: number;
  action?: string;
  attack?: string;
  client_ip?: string;
  user_id?: string;
  query?: string;
  body?: string;
  user_agent?: string;
  count?: number;
};

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "" && v !== false)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
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
  simulateCatalog: () => request<{ scenarios: SimulateScenario[] }>("/api/stand/simulate"),
  simulate: (scenario: string, count?: number) =>
    request<SimulateResult>("/api/stand/simulate", {
      method: "POST",
      body: JSON.stringify(count ? { scenario, count } : { scenario }),
    }),
  simulateCustom: (body: CustomLogIn) =>
    request<SimulateResult>("/api/stand/simulate/custom", {
      method: "POST",
      body: JSON.stringify(body),
    }),
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
  listPackages: () => request<Package[]>("/api/packages"),
  createContract: (body: { client_id: number; number: string; enrollment_ids: number[]; discount_pct?: number }) =>
    request<Contract>("/api/contracts", { method: "POST", body: JSON.stringify(body) }),
  planInstallments: (contractId: number, months: 3 | 6 | 12) =>
    request<Installment[]>(`/api/contracts/${contractId}/installments`, { method: "POST", body: JSON.stringify({ months }) }),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  contracts: (opts: { status?: string; q?: string; overdue?: boolean; page?: number; page_size?: number }) =>
    request<Paged<ContractRow>>(`/api/contracts${qs(opts)}`),
  contract: (id: number) => request<ContractDetail>(`/api/contracts/${id}`),
  signContract: (id: number) => request<ContractDetail>(`/api/contracts/${id}/sign`, { method: "POST" }),
  takePayment: (id: number, amount_kzt: string, method: "cash" | "kaspi" | "card") =>
    request<ContractDetail>(`/api/contracts/${id}/payments`, { method: "POST", body: JSON.stringify({ amount_kzt, method }) }),
  payments: (opts: { status?: string; q?: string; page?: number; page_size?: number }) =>
    request<Paged<PaymentRow> & { sum_kzt: string }>(`/api/payments${qs(opts)}`),
};
