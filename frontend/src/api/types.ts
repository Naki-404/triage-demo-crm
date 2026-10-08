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
