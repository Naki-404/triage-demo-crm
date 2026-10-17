import { ReactNode } from "react";
import { Lang, statusOf, tr } from "../format";

export function PageHead({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="row" style={{ marginBottom: 0 }}>{actions}</div>}
    </div>
  );
}

export function Kpi({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "up" | "down" }) {
  return (
    <div className="panel kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint && <div className={`delta ${tone ?? "muted"}`}>{hint}</div>}
    </div>
  );
}

export function StatusBadge({ kind, status, lang }: { kind: "contract" | "payment" | "installment"; status: string; lang: Lang }) {
  const s = statusOf(kind, status, lang);
  return <span className={`badge ${s.tone}`}>{s.label}</span>;
}

export function Pager({ lang, page, total, pageSize, onPage }: { lang: Lang; page: number; total: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="row" style={{ justifyContent: "space-between", marginTop: "1rem" }}>
      <span className="muted">
        {tr(lang, "Стр.", "Page")} {page} / {pages} · {total}
      </span>
      <div className="row" style={{ marginBottom: 0 }}>
        <button className="btn btn-sm" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          {tr(lang, "Назад", "Prev")}
        </button>
        <button className="btn btn-sm" type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          {tr(lang, "Вперёд", "Next")}
        </button>
      </div>
    </div>
  );
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="panel modal" onClick={(e) => e.stopPropagation()}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="btn btn-sm" type="button" onClick={onClose} aria-label="close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <p className="muted" style={{ margin: "0.5rem 0" }}>{text}</p>;
}
