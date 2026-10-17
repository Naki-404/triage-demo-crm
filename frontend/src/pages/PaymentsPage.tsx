import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, PaymentRow } from "../api";
import { Empty, PageHead, Pager, StatusBadge } from "../components/ui";
import { dateTime, kzt, Lang, tr } from "../format";

const PAGE_SIZE = 30;
const STATUSES: [string, string, string][] = [
  ["", "Все", "All"],
  ["paid", "Оплачено", "Paid"],
  ["failed", "Отклонено", "Failed"],
];

export function PaymentsPage({ lang }: { lang: Lang }) {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const page = Number(params.get("page") ?? 1);
  const [q, setQ] = useState(params.get("q") ?? "");
  const [rows, setRows] = useState<PaymentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [sum, setSum] = useState("0");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .payments({ status, q: params.get("q") ?? undefined, page, page_size: PAGE_SIZE })
      .then((res) => {
        setRows(res.items);
        setTotal(res.total);
        setSum(res.sum_kzt);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Error"))
      .finally(() => setLoading(false));
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  function update(next: Record<string, string | null>) {
    const merged = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) {
      if (v) merged.set(k, v);
      else merged.delete(k);
    }
    if (!("page" in next)) merged.delete("page");
    setParams(merged);
  }

  function onSearch(e: FormEvent) {
    e.preventDefault();
    update({ q: q.trim() || null });
  }

  return (
    <div>
      <PageHead
        title={tr(lang, "Оплаты", "Payments")}
        subtitle={`${total} ${tr(lang, "операций на сумму", "transactions totalling")} ${kzt(sum)}`}
      />
      <div className="filters">
        <div className="chips">
          {STATUSES.map(([value, ru, en]) => (
            <button key={value} type="button" className={`chip${status === value ? " active" : ""}`} onClick={() => update({ status: value || null })}>
              {tr(lang, ru, en)}
            </button>
          ))}
        </div>
        <form onSubmit={onSearch} className="row" style={{ marginBottom: 0, marginLeft: "auto" }}>
          <input placeholder={tr(lang, "Договор или клиент", "Contract or client")} value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn" type="submit">
            {tr(lang, "Найти", "Search")}
          </button>
        </form>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="panel">
        {loading ? (
          <p className="muted">{tr(lang, "Загрузка…", "Loading…")}</p>
        ) : rows.length === 0 ? (
          <Empty text={tr(lang, "Оплат не найдено", "No payments found")} />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{tr(lang, "Дата", "Date")}</th>
                  <th>{tr(lang, "Клиент", "Client")}</th>
                  <th>{tr(lang, "Договор", "Contract")}</th>
                  <th>{tr(lang, "Карта", "Card")}</th>
                  <th>{tr(lang, "Статус", "Status")}</th>
                  <th className="num">{tr(lang, "Сумма", "Amount")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td className="nowrap">{dateTime(p.paid_at ?? p.created_at)}</td>
                    <td>
                      <Link to={`/clients/${p.client_id}`}>{p.client_name}</Link>
                    </td>
                    <td className="nowrap">
                      <Link to={`/contracts/${p.contract_id}`}>{p.contract_number}</Link>
                    </td>
                    <td className="muted nowrap">{p.card_last4 ? `•••• ${p.card_last4}` : tr(lang, "касса", "desk")}</td>
                    <td>
                      <StatusBadge kind="payment" status={p.status} lang={lang} />
                    </td>
                    <td className="num">{kzt(p.amount_kzt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager lang={lang} page={page} total={total} pageSize={PAGE_SIZE} onPage={(p) => update({ page: String(p) })} />
      </div>
    </div>
  );
}
