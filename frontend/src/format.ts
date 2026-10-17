export type Lang = "ru" | "en";

/** Pick the string for the current language. */
export function tr(lang: Lang, ru: string, en: string): string {
  return lang === "ru" ? ru : en;
}

const money = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });

export function kzt(value: string | number | null | undefined): string {
  const n = typeof value === "string" ? Number(value) : value ?? 0;
  return `${money.format(Number.isFinite(n) ? n : 0)} ₸`;
}

export function shortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString("ru-RU");
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

export function monthLabel(ym: string, lang: Lang): string {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(lang === "ru" ? "ru-RU" : "en-GB", { month: "short" });
}

const CONTRACT_STATUS: Record<string, [string, string, string]> = {
  draft: ["Черновик", "Draft", "muted"],
  active: ["Активен", "Active", "info"],
  completed: ["Оплачен", "Paid off", "ok"],
  cancelled: ["Расторгнут", "Cancelled", "danger"],
};
const PAYMENT_STATUS: Record<string, [string, string, string]> = {
  paid: ["Оплачено", "Paid", "ok"],
  pending: ["В обработке", "Pending", "muted"],
  failed: ["Отклонено", "Failed", "danger"],
  refunded: ["Возврат", "Refunded", "warn"],
};
const INSTALLMENT_STATUS: Record<string, [string, string, string]> = {
  scheduled: ["По графику", "Scheduled", "muted"],
  paid: ["Оплачен", "Paid", "ok"],
  overdue: ["Просрочен", "Overdue", "danger"],
  cancelled: ["Отменён", "Cancelled", "muted"],
};

export function statusOf(kind: "contract" | "payment" | "installment", status: string, lang: Lang): { label: string; tone: string } {
  const table = kind === "contract" ? CONTRACT_STATUS : kind === "payment" ? PAYMENT_STATUS : INSTALLMENT_STATUS;
  const row = table[status];
  return row ? { label: lang === "ru" ? row[0] : row[1], tone: row[2] } : { label: status, tone: "muted" };
}
