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
  description?: string | null;
  price_kzt: string;
};

export type Contract = {
  id: number;
  number: string;
  client_id: number;
  status: string;
  total_kzt: string;
  discount_pct: number;
  created_at?: string;
  signed_at?: string | null;
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
  contract_id: number | null;
  package_id: number | null;
  price_kzt: string;
  discount_pct: number;
  created_at: string;
};

export type Package = {
  id: number;
  code: string;
  title: string;
  price_kzt: string;
  is_active: boolean;
  course_ids: number[];
};

export type PaymentRow = {
  id: number;
  contract_id: number;
  contract_number: string;
  client_id: number;
  client_name: string;
  amount_kzt: string;
  status: string;
  card_last4: string | null;
  paid_at: string | null;
  created_at: string;
};

export type DueRow = {
  installment_id: number;
  contract_id: number;
  contract_number: string;
  client_id: number;
  client_name: string;
  seq: number;
  due_date: string;
  amount_kzt: string;
  overdue: boolean;
};

export type Dashboard = {
  clients_total: number;
  clients_new_30d: number;
  contracts_active: number;
  contracts_draft: number;
  revenue_month_kzt: string;
  revenue_prev_month_kzt: string;
  overdue_count: number;
  overdue_kzt: string;
  revenue_by_month: { month: string; amount_kzt: string }[];
  top_courses: { code: string; title: string; enrollments: number }[];
  recent_payments: PaymentRow[];
  upcoming: DueRow[];
};

export type ContractRow = {
  id: number;
  number: string;
  client_id: number;
  client_name: string;
  status: string;
  total_kzt: string;
  paid_kzt: string;
  discount_pct: number;
  created_at: string;
  signed_at: string | null;
  next_due: string | null;
  overdue: boolean;
};

export type Installment = {
  id: number;
  seq: number;
  due_date: string;
  amount_kzt: string;
  status: string;
  overdue: boolean;
};

export type ContractDetail = ContractRow & {
  installments: Installment[];
  payments: PaymentRow[];
  enrollments: { id: number; course_code: string; course_title: string; price_kzt: string; discount_pct: number }[];
};

export type Paged<T> = { items: T[]; total: number; page: number; page_size: number };
