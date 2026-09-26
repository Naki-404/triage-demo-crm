import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Client, Note } from "../api";

type Props = { lang: "ru" | "en"; canWrite?: boolean };

export function ClientCardPage({ lang, canWrite = false }: Props) {
  const { id } = useParams();
  const [client, setClient] = useState<Client | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteBody, setNoteBody] = useState("");
  const [tax, setTax] = useState<Record<string, unknown> | null>(null);
  const [taxError, setTaxError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const num = Number(id);

  useEffect(() => {
    if (!num) return;
    setError(null);
    api
      .getClient(num)
      .then(setClient)
      .catch((err) => setError(err instanceof Error ? err.message : "Error"));
    api
      .listNotes(num)
      .then(setNotes)
      .catch(() => setNotes([]));
  }, [num]);

  async function onAddNote(e: FormEvent) {
    e.preventDefault();
    if (!num || !noteBody.trim()) return;
    setPending(true);
    setError(null);
    try {
      const note = await api.createNote(num, noteBody.trim());
      setNotes((prev) => [note, ...prev]);
      setNoteBody("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  async function onCheckTax() {
    if (!num) return;
    setPending(true);
    setTaxError(null);
    try {
      const res = await api.getTax(num);
      setTax(res);
    } catch (err) {
      setTax(null);
      setTaxError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  if (error && !client) return <p className="error">{error}</p>;
  if (!client) return <p className="muted">{lang === "ru" ? "Загрузка…" : "Loading…"}</p>;

  return (
    <div>
      <div className="panel" style={{ marginBottom: "1.25rem" }}>
        <p>
          <Link to="/">{lang === "ru" ? "← Клиенты" : "← Clients"}</Link>
        </p>
        <h2 style={{ fontFamily: "var(--display)", marginTop: 0 }}>{client.name}</h2>
        <p>
          <span className="muted">ИИН</span> {client.iin}
        </p>
        <p>
          <span className="muted">{lang === "ru" ? "Телефон" : "Phone"}</span> {client.phone || "—"}
        </p>
        <p>
          <span className="muted">Email</span> {client.email || "—"}
        </p>
      </div>

      {canWrite && (
        <div className="panel" style={{ marginBottom: "1.25rem" }}>
          <p style={{ marginTop: 0 }}>{lang === "ru" ? "Налоговый статус" : "Tax status"}</p>
          <button className="btn" type="button" onClick={onCheckTax} disabled={pending}>
            {lang === "ru" ? "Проверить" : "Check"}
          </button>
          {taxError && <p className="error">{taxError}</p>}
          {tax && (
            <pre style={{ marginTop: "0.75rem", fontSize: "0.85rem", overflow: "auto" }}>{JSON.stringify(tax, null, 2)}</pre>
          )}
        </div>
      )}

      <div className="panel">
        <p style={{ marginTop: 0 }}>{lang === "ru" ? "Заметки" : "Notes"}</p>
        {error && <p className="error">{error}</p>}
        {canWrite && (
          <form className="row" onSubmit={onAddNote}>
            <label className="field" style={{ flex: 1, marginBottom: 0 }}>
              <span>{lang === "ru" ? "Новая заметка" : "New note"}</span>
              <input value={noteBody} onChange={(e) => setNoteBody(e.target.value)} required disabled={pending} />
            </label>
            <button className="btn btn-primary" type="submit" disabled={pending || !noteBody.trim()}>
              {lang === "ru" ? "Добавить" : "Add"}
            </button>
          </form>
        )}
        {notes.length === 0 ? (
          <p className="muted">{lang === "ru" ? "Заметок нет" : "No notes yet"}</p>
        ) : (
          <ul style={{ paddingLeft: "1.1rem", margin: "0.75rem 0 0" }}>
            {notes.map((n) => (
              <li key={n.id} style={{ marginBottom: "0.65rem" }}>
                <div>{n.body}</div>
                <div className="muted" style={{ fontSize: "0.8rem" }}>
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
