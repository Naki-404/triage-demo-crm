import { Link } from "react-router-dom";
import { Client } from "../../api";

type Props = {
  lang: "ru" | "en";
  items: Client[];
  page: number;
  pageCount: number;
  total: number;
  pageSize: number;
  pending: boolean;
  onPage: (next: number) => void;
};

export function ClientsTable({ lang, items, page, pageCount, total, pageSize, pending, onPage }: Props) {
  return (
    <>
      <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>{lang === "ru" ? "Клиент" : "Client"}</th>
            <th>ИИН</th>
            <th>{lang === "ru" ? "Телефон" : "Phone"}</th>
            <th>Email</th>
            <th>{lang === "ru" ? "Добавлен" : "Added"}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id}>
              <td>
                <Link to={`/clients/${c.id}`}>{c.name}</Link>
              </td>
              <td className="muted nowrap">{c.iin}</td>
              <td className="nowrap">{c.phone || "—"}</td>
              <td className="muted">{c.email || "—"}</td>
              <td className="muted nowrap">{new Date(c.created_at).toLocaleDateString("ru-RU")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {total > pageSize && (
        <div className="row" style={{ justifyContent: "space-between", marginTop: "1rem" }}>
          <span className="muted">
            {lang === "ru" ? "Стр." : "Page"} {page} / {pageCount} · {total}
          </span>
          <div className="row" style={{ marginBottom: 0 }}>
            <button className="btn" type="button" disabled={pending || page <= 1} onClick={() => onPage(page - 1)}>
              {lang === "ru" ? "Назад" : "Prev"}
            </button>
            <button className="btn" type="button" disabled={pending || page >= pageCount} onClick={() => onPage(page + 1)}>
              {lang === "ru" ? "Вперёд" : "Next"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
