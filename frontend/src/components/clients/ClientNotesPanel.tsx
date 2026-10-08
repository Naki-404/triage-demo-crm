import { FormEvent } from "react";
import { Note } from "../../api";

type Props = {
  lang: "ru" | "en";
  canWrite: boolean;
  notes: Note[];
  noteBody: string;
  pending: boolean;
  error: string | null;
  onNoteBodyChange: (v: string) => void;
  onAddNote: (e: FormEvent) => void;
};

export function ClientNotesPanel(props: Props) {
  const { lang, canWrite, notes, noteBody, pending, error, onNoteBodyChange, onAddNote } = props;
  return (
    <div className="panel">
      <p style={{ marginTop: 0 }}>{lang === "ru" ? "Заметки" : "Notes"}</p>
      {error && <p className="error">{error}</p>}
      {canWrite && (
        <form className="row" onSubmit={onAddNote}>
          <label className="field" style={{ flex: 1, marginBottom: 0 }}>
            <span>{lang === "ru" ? "Новая заметка" : "New note"}</span>
            <input value={noteBody} onChange={(e) => onNoteBodyChange(e.target.value)} required disabled={pending} />
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
  );
}
