import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ContractDetail } from "../api";
import { Empty, Modal, PageHead, StatusBadge } from "../components/ui";
import { dateTime, kzt, Lang, shortDate, tr } from "../format";

export function ContractPage({ lang, canWrite }: { lang: Lang; canWrite: boolean }) {
  const { id } = useParams();
  const num = Number(id);
  const [c, setC] = useState<ContractDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<"cash" | "kaspi" | "card">("kaspi");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!num) return;
    api.contract(num).then(setC).catch((err) => setError(err instanceof Error ? err.message : "Error"));
  }, [num]);

  async function run(action: () => Promise<ContractDetail>, ok: string) {
    setPending(true);
    setError(null);
    try {
      setC(await action());
      setNotice(ok);
      setPaying(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  function openPayment() {
    const next = c?.installments.find((i) => i.status !== "paid" && i.status !== "cancelled");
    const rest = c ? Number(c.total_kzt) - Number(c.paid_kzt) : 0;
    setAmount(String(next ? Number(next.amount_kzt) : rest));
    setPaying(true);
  }

  function onPay(e: FormEvent) {
    e.preventDefault();
    run(() => api.takePayment(num, amount, method), tr(lang, "Оплата принята", "Payment recorded"));
  }

  if (error && !c) return <p className="error">{error}</p>;
  if (!c) return <p className="muted">{tr(lang, "Загрузка…", "Loading…")}</p>;

  const rest = Number(c.total_kzt) - Number(c.paid_kzt);
  return (
    <div>
      <p style={{ margin: "0 0 0.5rem" }}>
        <Link to="/contracts">← {tr(lang, "Договоры", "Contracts")}</Link>
      </p>
      <PageHead
        title={`${tr(lang, "Договор", "Contract")} ${c.number}`}
        subtitle={c.client_name}
        actions={
          canWrite && (
            <>
              {c.status === "draft" && (
                <button className="btn btn-primary" type="button" disabled={pending} onClick={() => run(() => api.signContract(num), tr(lang, "Договор подписан", "Contract signed"))}>
                  {tr(lang, "Подписать", "Sign")}
                </button>
              )}
              {c.status === "active" && rest > 0 && (
                <button className="btn btn-primary" type="button" onClick={openPayment}>
                  {tr(lang, "Принять оплату", "Take payment")}
                </button>
              )}
              <a className="btn" href={`/api/contracts/${c.id}/export/1c`}>
                {tr(lang, "Выгрузка в 1С", "Export to 1C")}
              </a>
            </>
          )
        }
      />
      {notice && <div className="notice ok">{notice}</div>}
      {error && <p className="error">{error}</p>}

      <div className="grid-2">
        <div className="panel">
          <h3>{tr(lang, "Условия", "Terms")}</h3>
          <dl className="dl">
            <dt>{tr(lang, "Статус", "Status")}</dt>
            <dd>
              <StatusBadge kind="contract" status={c.status} lang={lang} />
            </dd>
            <dt>{tr(lang, "Клиент", "Client")}</dt>
            <dd>
              <Link to={`/clients/${c.client_id}`}>{c.client_name}</Link>
            </dd>
            <dt>{tr(lang, "Сумма", "Total")}</dt>
            <dd>{kzt(c.total_kzt)}</dd>
            <dt>{tr(lang, "Скидка", "Discount")}</dt>
            <dd>{c.discount_pct ? `${c.discount_pct}%` : "—"}</dd>
            <dt>{tr(lang, "Оплачено", "Paid")}</dt>
            <dd>{kzt(c.paid_kzt)}</dd>
            <dt>{tr(lang, "Остаток", "Balance")}</dt>
            <dd className={c.overdue ? "down" : undefined}>{kzt(rest)}</dd>
            <dt>{tr(lang, "Подписан", "Signed")}</dt>
            <dd>{shortDate(c.signed_at)}</dd>
          </dl>
        </div>
        <div className="panel">
          <h3>{tr(lang, "Курсы в договоре", "Courses")}</h3>
          {c.enrollments.length === 0 ? (
            <Empty text="—" />
          ) : (
            <ul className="list-plain">
              {c.enrollments.map((e) => (
                <li key={e.id}>
                  <span>
                    <span className="muted">{e.course_code}</span> {e.course_title}
                    {e.discount_pct ? <span className="muted"> · −{e.discount_pct}%</span> : null}
                  </span>
                  <strong>{kzt(e.price_kzt)}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>{tr(lang, "График платежей", "Installment schedule")}</h3>
          {c.installments.length === 0 ? (
            <Empty text={tr(lang, "Оплата одним платежом", "Paid in one payment")} />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>№</th>
                  <th>{tr(lang, "Срок", "Due")}</th>
                  <th className="num">{tr(lang, "Сумма", "Amount")}</th>
                  <th>{tr(lang, "Статус", "Status")}</th>
                </tr>
              </thead>
              <tbody>
                {c.installments.map((i) => (
                  <tr key={i.id}>
                    <td>{i.seq}</td>
                    <td className={i.overdue ? "down" : undefined}>{shortDate(i.due_date)}</td>
                    <td className="num">{kzt(i.amount_kzt)}</td>
                    <td>
                      <StatusBadge kind="installment" status={i.overdue && i.status === "scheduled" ? "overdue" : i.status} lang={lang} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="panel">
          <h3>{tr(lang, "Оплаты", "Payments")}</h3>
          {c.payments.length === 0 ? (
            <Empty text={tr(lang, "Оплат ещё не было", "No payments yet")} />
          ) : (
            <ul className="list-plain">
              {c.payments.map((p) => (
                <li key={p.id}>
                  <span>
                    {dateTime(p.paid_at ?? p.created_at)}
                    <div className="muted" style={{ fontSize: "0.8rem" }}>
                      {p.card_last4 ? `•••• ${p.card_last4}` : tr(lang, "в кассе", "at the desk")}
                    </div>
                  </span>
                  <span style={{ textAlign: "right" }}>
                    <strong>{kzt(p.amount_kzt)}</strong>
                    <div>
                      <StatusBadge kind="payment" status={p.status} lang={lang} />
                    </div>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {paying && (
        <Modal title={tr(lang, "Принять оплату", "Take payment")} onClose={() => setPaying(false)}>
          <form onSubmit={onPay}>
            <label className="field">
              <span>{tr(lang, "Сумма, ₸", "Amount, ₸")}</span>
              <input type="number" min="1" step="0.01" max={rest} value={amount} onChange={(e) => setAmount(e.target.value)} required />
            </label>
            <label className="field">
              <span>{tr(lang, "Способ", "Method")}</span>
              <select value={method} onChange={(e) => setMethod(e.target.value as "cash" | "kaspi" | "card")}>
                <option value="kaspi">Kaspi</option>
                <option value="card">{tr(lang, "Карта в офисе", "Card at the desk")}</option>
                <option value="cash">{tr(lang, "Наличные", "Cash")}</option>
              </select>
            </label>
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              {tr(lang, "Остаток по договору:", "Contract balance:")} {kzt(rest)}
            </p>
            <button className="btn btn-primary" type="submit" disabled={pending}>
              {tr(lang, "Провести", "Record")}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
