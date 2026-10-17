import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, Client, Contract, Course, Enrollment, Note } from "../api";
import { ClientNotesPanel } from "../components/clients/ClientNotesPanel";
import { ClientTaxPanel } from "../components/clients/ClientTaxPanel";
import { Empty, Modal, PageHead, StatusBadge } from "../components/ui";
import { kzt, Lang, shortDate, tr } from "../format";

type Props = { lang: Lang; canWrite?: boolean };
type Tab = "contracts" | "enrollments" | "notes";

export function ClientCardPage({ lang, canWrite = false }: Props) {
  const { id } = useParams();
  const num = Number(id);
  const navigate = useNavigate();
  const [client, setClient] = useState<Client | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [tab, setTab] = useState<Tab>("contracts");
  const [noteBody, setNoteBody] = useState("");
  const [tax, setTax] = useState<Record<string, unknown> | null>(null);
  const [taxError, setTaxError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [modal, setModal] = useState<"enroll" | "contract" | null>(null);
  const [courseId, setCourseId] = useState<number | "">("");
  const [discount, setDiscount] = useState(0);
  const [picked, setPicked] = useState<number[]>([]);
  const [months, setMonths] = useState<0 | 3 | 6 | 12>(0);

  const reload = useCallback(() => {
    if (!num) return;
    api.getClient(num).then(setClient).catch((err) => setError(err instanceof Error ? err.message : "Error"));
    api.listNotes(num).then(setNotes).catch(() => setNotes([]));
    api.listContracts(num).then(setContracts).catch(() => setContracts([]));
    api.listEnrollments(num).then(setEnrollments).catch(() => setEnrollments([]));
  }, [num]);

  useEffect(() => {
    reload();
    api.listCourses().then(setCourses).catch(() => setCourses([]));
  }, [reload]);

  const courseById = useMemo(() => new Map(courses.map((c) => [c.id, c])), [courses]);
  const unbilled = enrollments.filter((e) => !e.contract_id);
  const pickedTotal = unbilled.filter((e) => picked.includes(e.id)).reduce((sum, e) => sum + Number(e.price_kzt), 0);

  async function act(fn: () => Promise<void>) {
    setPending(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  function onAddNote(e: FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    act(async () => {
      const note = await api.createNote(num, noteBody.trim());
      setNotes((prev) => [note, ...prev]);
      setNoteBody("");
    });
  }

  function onCheckTax() {
    setTaxError(null);
    act(async () => {
      try {
        setTax(await api.getTax(num));
      } catch (err) {
        setTax(null);
        setTaxError(err instanceof Error ? err.message : "Error");
      }
    });
  }

  function onEnroll(e: FormEvent) {
    e.preventDefault();
    if (!courseId) return;
    act(async () => {
      await api.enroll({ client_id: num, course_id: Number(courseId), discount_pct: discount || undefined });
      setModal(null);
      setCourseId("");
      setDiscount(0);
      setTab("enrollments");
      reload();
    });
  }

  function onContract(e: FormEvent) {
    e.preventDefault();
    if (picked.length === 0) return;
    act(async () => {
      const number = `BA-${new Date().getFullYear()}-${num}-${Date.now().toString().slice(-5)}`;
      const contract = await api.createContract({ client_id: num, number, enrollment_ids: picked });
      if (months) await api.planInstallments(contract.id, months);
      setModal(null);
      navigate(`/contracts/${contract.id}`);
    });
  }

  if (error && !client) return <p className="error">{error}</p>;
  if (!client) return <p className="muted">{tr(lang, "Загрузка…", "Loading…")}</p>;

  const active = contracts.filter((c) => c.status === "active").length;
  return (
    <div>
      <p style={{ margin: "0 0 0.5rem" }}>
        <Link to="/clients">← {tr(lang, "Клиенты", "Clients")}</Link>
      </p>
      <PageHead
        title={client.name}
        subtitle={`${tr(lang, "Клиент с", "Client since")} ${shortDate(client.created_at)} · ${active} ${tr(lang, "активных договоров", "active contracts")}`}
        actions={
          canWrite && (
            <>
              <button className="btn" type="button" onClick={() => setModal("enroll")}>
                {tr(lang, "Записать на курс", "Enroll")}
              </button>
              <button
                className="btn btn-primary"
                type="button"
                disabled={unbilled.length === 0}
                title={unbilled.length === 0 ? tr(lang, "Сначала запишите на курс", "Enroll first") : undefined}
                onClick={() => {
                  setPicked(unbilled.map((e) => e.id));
                  setMonths(0);
                  setModal("contract");
                }}
              >
                {tr(lang, "Оформить договор", "New contract")}
              </button>
            </>
          )
        }
      />
      {error && <p className="error">{error}</p>}

      <div className="grid-2">
        <div className="panel">
          <h3>{tr(lang, "Профиль", "Profile")}</h3>
          <dl className="dl">
            <dt>ИИН</dt>
            <dd>{client.iin}</dd>
            <dt>{tr(lang, "Дата рождения", "Birth date")}</dt>
            <dd>{shortDate(client.birth_date)}</dd>
            <dt>{tr(lang, "Телефон", "Phone")}</dt>
            <dd>{client.phone || "—"}</dd>
            <dt>Email</dt>
            <dd>{client.email || "—"}</dd>
          </dl>
        </div>
        {canWrite ? (
          <ClientTaxPanel lang={lang} pending={pending} taxError={taxError} tax={tax} onCheckTax={onCheckTax} />
        ) : (
          <div />
        )}
      </div>

      <div className="tabs">
        {(
          [
            ["contracts", `${tr(lang, "Договоры", "Contracts")} · ${contracts.length}`],
            ["enrollments", `${tr(lang, "Записи на курсы", "Enrollments")} · ${enrollments.length}`],
            ["notes", `${tr(lang, "Заметки", "Notes")} · ${notes.length}`],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button key={key} type="button" className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "contracts" && (
        <div className="panel">
          {contracts.length === 0 ? (
            <Empty text={tr(lang, "Договоров пока нет", "No contracts yet")} />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>{tr(lang, "Номер", "Number")}</th>
                  <th>{tr(lang, "Статус", "Status")}</th>
                  <th>{tr(lang, "Дата", "Date")}</th>
                  <th className="num">{tr(lang, "Сумма", "Total")}</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <Link to={`/contracts/${c.id}`}>{c.number}</Link>
                    </td>
                    <td>
                      <StatusBadge kind="contract" status={c.status} lang={lang} />
                    </td>
                    <td className="muted">{shortDate(c.signed_at ?? c.created_at)}</td>
                    <td className="num">{kzt(c.total_kzt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "enrollments" && (
        <div className="panel">
          {enrollments.length === 0 ? (
            <Empty text={tr(lang, "Записей нет", "No enrollments")} />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>{tr(lang, "Курс", "Course")}</th>
                  <th>{tr(lang, "Записан", "Enrolled")}</th>
                  <th>{tr(lang, "Договор", "Contract")}</th>
                  <th className="num">{tr(lang, "Цена", "Price")}</th>
                </tr>
              </thead>
              <tbody>
                {enrollments.map((e) => {
                  const course = courseById.get(e.course_id);
                  return (
                    <tr key={e.id}>
                      <td>
                        {course ? course.title : `#${e.course_id}`}
                        {e.discount_pct ? <span className="muted"> · −{e.discount_pct}%</span> : null}
                      </td>
                      <td className="muted">{shortDate(e.created_at)}</td>
                      <td>{e.contract_id ? <Link to={`/contracts/${e.contract_id}`}>#{e.contract_id}</Link> : <span className="badge warn">{tr(lang, "без договора", "not billed")}</span>}</td>
                      <td className="num">{kzt(e.price_kzt)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "notes" && (
        <ClientNotesPanel
          lang={lang}
          canWrite={canWrite}
          notes={notes}
          noteBody={noteBody}
          pending={pending}
          error={null}
          onNoteBodyChange={setNoteBody}
          onAddNote={onAddNote}
        />
      )}

      {modal === "enroll" && (
        <Modal title={tr(lang, "Запись на курс", "Enroll in a course")} onClose={() => setModal(null)}>
          <form onSubmit={onEnroll}>
            <label className="field">
              <span>{tr(lang, "Курс", "Course")}</span>
              <select value={courseId} onChange={(e) => setCourseId(e.target.value ? Number(e.target.value) : "")} required>
                <option value="">—</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title} · {kzt(c.price_kzt)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>{tr(lang, "Скидка, %", "Discount, %")}</span>
              <input type="number" min={0} max={100} value={discount} onChange={(e) => setDiscount(Number(e.target.value))} />
            </label>
            {error && <p className="error">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={pending || !courseId}>
              {tr(lang, "Записать", "Enroll")}
            </button>
          </form>
        </Modal>
      )}

      {modal === "contract" && (
        <Modal title={tr(lang, "Новый договор", "New contract")} onClose={() => setModal(null)}>
          <form onSubmit={onContract}>
            <p className="muted" style={{ marginTop: 0 }}>{tr(lang, "Курсы без договора:", "Courses not billed yet:")}</p>
            {unbilled.map((e) => (
              <label key={e.id} className="row" style={{ marginBottom: "0.4rem", alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={picked.includes(e.id)}
                  onChange={(ev) => setPicked(ev.target.checked ? [...picked, e.id] : picked.filter((x) => x !== e.id))}
                />
                <span style={{ flex: 1 }}>{courseById.get(e.course_id)?.title ?? `#${e.course_id}`}</span>
                <strong>{kzt(e.price_kzt)}</strong>
              </label>
            ))}
            <label className="field" style={{ marginTop: "0.75rem" }}>
              <span>{tr(lang, "Оплата", "Payment plan")}</span>
              <select value={months} onChange={(e) => setMonths(Number(e.target.value) as 0 | 3 | 6 | 12)}>
                <option value={0}>{tr(lang, "Одним платежом", "One payment")}</option>
                <option value={3}>{tr(lang, "Рассрочка 3 мес.", "3 installments")}</option>
                <option value={6}>{tr(lang, "Рассрочка 6 мес.", "6 installments")}</option>
                <option value={12}>{tr(lang, "Рассрочка 12 мес.", "12 installments")}</option>
              </select>
            </label>
            <p>
              {tr(lang, "Итого:", "Total:")} <strong>{kzt(pickedTotal)}</strong>
              {months ? <span className="muted"> · {kzt(pickedTotal / months)} / {tr(lang, "мес.", "mo")}</span> : null}
            </p>
            {error && <p className="error">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={pending || picked.length === 0}>
              {tr(lang, "Оформить", "Create")}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
