import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ContractRow } from "../api";
import { Empty, PageHead, Pager, StatusBadge } from "../components/ui";
import { kzt, Lang, shortDate, tr } from "../format";

const PAGE_SIZE = 25;
const STATUSES: [string, string, string][] = [
  ["", "Все", "All"],
  ["active", "Активные", "Active"],
  ["draft", "Черновики", "Drafts"],
  ["completed", "Оплачены", "Paid off"],
  ["cancelled", "Расторгнуты", "Cancelled"],
];

export function ContractsPage({ lang }: { lang: Lang }) {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const overdue = params.get("overdue") === "1";
  const page = Number(params.get("page") ?? 1);
  const [q, setQ] = useState(params.get("q") ?? "");
  const [rows, setRows] = useState<ContractRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .contracts({ status, overdue, q: params.get("q") ?? undefined, page, page_size: PAGE_SIZE })
      .then((res) => {
        setRows(res.items);
        setTotal(res.total);
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
      <PageHead title={tr(lang, "Договоры", "Contracts")} subtitle={`${total} ${tr(lang, "договоров", "contracts")}`} />
      <div className="filters">
        <div className="chips">
          {STATUSES.map(([value, ru, en]) => (
            <button key={value} type="button" className={`chip${status === value && !overdue ? " active" : ""}`} onClick={() => update({ status: value || null, overdue: null })}>
              {tr(lang, ru, en)}
            </button>
          ))}
          <button type="button" className={`chip${overdue ? " active" : ""}`} onClick={() => update({ overdue: overdue ? null : "1", status: null })}>
            {tr(lang, "С просрочкой", "Overdue")}
          </button>
        </div>
        <form onSubmit={onSearch} className="row" style={{ marginBottom: 0, marginLeft: "auto" }}>
          <input placeholder={tr(lang, "Номер или клиент", "Number or client")} value={q} onChange={(e) => setQ(e.target.value)} />
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
          <Empty text={tr(lang, "Договоров не найдено", "No contracts found")} />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{tr(lang, "Номер", "Number")}</th>
                  <th>{tr(lang, "Клиент", "Client")}</th>
                  <th>{tr(lang, "Статус", "Status")}</th>
                  <th className="num">{tr(lang, "Сумма", "Total")}</th>
                  <th style={{ width: "18%" }}>{tr(lang, "Оплачено", "Paid")}</th>
                  <th>{tr(lang, "След. платёж", "Next due")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => {
                  const pct = Math.min(100, Math.round((Number(c.paid_kzt) / Math.max(Number(c.total_kzt), 1)) * 100));
                  return (
                    <tr key={c.id}>
                      <td className="nowrap">
                        <Link to={`/contracts/${c.id}`}>{c.number}</Link>
                        <div className="muted" style={{ fontSize: "0.8rem" }}>
                          {shortDate(c.signed_at ?? c.created_at)}
                        </div>
                      </td>
                      <td>
                        <Link to={`/clients/${c.client_id}`}>{c.client_name}</Link>
                      </td>
                      <td>
                        <StatusBadge kind="contract" status={c.status} lang={lang} />
                      </td>
                      <td className="num">{kzt(c.total_kzt)}</td>
                      <td>
                        <div className="progress" title={`${pct}%`}>
                          <span style={{ width: `${pct}%` }} />
                        </div>
                        <div className="muted" style={{ fontSize: "0.78rem", marginTop: "0.2rem" }}>
                          {kzt(c.paid_kzt)}
                        </div>
                      </td>
                      <td className={c.overdue ? "down nowrap" : "nowrap"}>{c.next_due ? shortDate(c.next_due) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <Pager lang={lang} page={page} total={total} pageSize={PAGE_SIZE} onPage={(p) => update({ page: String(p) })} />
      </div>
    </div>
  );
}
