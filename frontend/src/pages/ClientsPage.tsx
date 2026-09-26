import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Client } from "../api";

type Props = { lang: "ru" | "en"; canWrite: boolean };

const PAGE_SIZE = 25;

export function ClientsPage({ lang, canWrite }: Props) {
  const [items, setItems] = useState<Client[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [name, setName] = useState("");
  const [iin, setIin] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  async function load(query?: string, pageNum = page) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listClients({ q: query, page: pageNum, page_size: PAGE_SIZE });
      setItems(res.items);
      setTotal(res.total);
      setPage(res.page);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch((err) => {
      setError(String(err));
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    try {
      await load(q, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await api.createClient({
        name,
        iin,
        phone: phone || undefined,
        email: email || undefined,
      });
      setName("");
      setIin("");
      setPhone("");
      setEmail("");
      await load(q, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  async function goPage(next: number) {
    setPending(true);
    try {
      await load(q, next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="toolbar">
        <form className="row" onSubmit={onSearch}>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>{lang === "ru" ? "Поиск" : "Search"}</span>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="name / IIN" disabled={pending} />
          </label>
          <button className="btn" type="submit" disabled={pending || loading}>
            {lang === "ru" ? "Найти" : "Find"}
          </button>
        </form>
        <div className="row">
          <a className="btn" href={api.exportUrl("csv")}>
            CSV
          </a>
          <a className="btn" href={api.exportUrl("xlsx")}>
            XLSX
          </a>
        </div>
      </div>

      {canWrite && (
        <form className="panel" onSubmit={onCreate} style={{ marginBottom: "1.25rem" }}>
          <p style={{ marginTop: 0 }}>{lang === "ru" ? "Новый клиент" : "New client"}</p>
          <div className="row">
            <label className="field">
              <span>{lang === "ru" ? "ФИО" : "Name"}</span>
              <input value={name} onChange={(e) => setName(e.target.value)} required disabled={pending} />
            </label>
            <label className="field">
              <span>ИИН</span>
              <input value={iin} onChange={(e) => setIin(e.target.value)} required minLength={12} maxLength={12} disabled={pending} />
            </label>
            <label className="field">
              <span>{lang === "ru" ? "Телефон" : "Phone"}</span>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} disabled={pending} />
            </label>
            <label className="field">
              <span>Email</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" disabled={pending} />
            </label>
            <button className="btn btn-primary" type="submit" disabled={pending}>
              {pending ? (lang === "ru" ? "…" : "…") : lang === "ru" ? "Создать" : "Create"}
            </button>
          </div>
        </form>
      )}

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">{lang === "ru" ? "Загрузка клиентов…" : "Loading clients…"}</p>
      ) : items.length === 0 ? (
        <div className="panel">
          <p style={{ margin: 0 }}>{lang === "ru" ? "Клиентов пока нет" : "No clients yet"}</p>
          <p className="muted" style={{ marginBottom: 0 }}>
            {lang === "ru" ? "Создайте первого клиента или измените поиск." : "Create a client or adjust the search."}
          </p>
        </div>
      ) : (
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
          {total > PAGE_SIZE && (
            <div className="row" style={{ justifyContent: "space-between", marginTop: "1rem" }}>
              <span className="muted">
                {lang === "ru" ? "Стр." : "Page"} {page} / {pageCount} · {total}
              </span>
              <div className="row" style={{ marginBottom: 0 }}>
                <button className="btn" type="button" disabled={pending || page <= 1} onClick={() => goPage(page - 1)}>
                  {lang === "ru" ? "Назад" : "Prev"}
                </button>
                <button className="btn" type="button" disabled={pending || page >= pageCount} onClick={() => goPage(page + 1)}>
                  {lang === "ru" ? "Вперёд" : "Next"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
