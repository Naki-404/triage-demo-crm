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
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>{lang === "ru" ? "Имя" : "Name"}</th>
            <th>ИИН</th>
            <th>{lang === "ru" ? "Телефон" : "Phone"}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id}>
              <td>
                <Link to={`/clients/${c.id}`}>{c.id}</Link>
              </td>
              <td>{c.name}</td>
              <td>{c.iin}</td>
              <td>{c.phone || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
