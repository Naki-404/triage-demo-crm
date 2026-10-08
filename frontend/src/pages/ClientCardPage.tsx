import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Client, Contract, Enrollment, Note, Payment } from "../api";
import { ClientCommercePanels } from "../components/clients/ClientCommercePanels";
import { ClientNotesPanel } from "../components/clients/ClientNotesPanel";
import { ClientProfilePanel } from "../components/clients/ClientProfilePanel";
import { ClientTaxPanel } from "../components/clients/ClientTaxPanel";

type Props = { lang: "ru" | "en"; canWrite?: boolean };

export function ClientCardPage({ lang, canWrite = false }: Props) {
  const { id } = useParams();
  const [client, setClient] = useState<Client | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
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
    api
      .listContracts(num)
      .then(async (list) => {
        setContracts(list);
        if (list[0]) {
          const pays = await api.listPayments(list[0].id).catch(() => []);
          setPayments(pays);
        } else {
          setPayments([]);
        }
      })
      .catch(() => setContracts([]));
    api
      .listEnrollments(num)
      .then(setEnrollments)
      .catch(() => setEnrollments([]));
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
      <ClientProfilePanel lang={lang} client={client} />
      <ClientCommercePanels lang={lang} enrollments={enrollments} contracts={contracts} payments={payments} />
      {canWrite && (
        <ClientTaxPanel lang={lang} pending={pending} taxError={taxError} tax={tax} onCheckTax={onCheckTax} />
      )}
      <ClientNotesPanel
        lang={lang}
        canWrite={canWrite}
        notes={notes}
        noteBody={noteBody}
        pending={pending}
        error={error}
        onNoteBodyChange={setNoteBody}
        onAddNote={onAddNote}
      />
    </div>
  );
}
