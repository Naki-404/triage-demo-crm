import { request } from "./api/client";
import type {
  Client,
  ClientList,
  Contract,
  Course,
  Enrollment,
  Note,
  Payment,
  User,
} from "./api/types";

export type { Client, ClientList, Contract, Course, Enrollment, Note, Payment, User };

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
