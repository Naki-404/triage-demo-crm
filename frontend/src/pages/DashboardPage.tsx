import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Dashboard } from "../api";
import { Empty, Kpi, PageHead, StatusBadge } from "../components/ui";
import { dateTime, kzt, Lang, monthLabel, shortDate, tr } from "../format";

export function DashboardPage({ lang }: { lang: Lang }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch((err) => setError(err instanceof Error ? err.message : "Error"));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">{tr(lang, "Загрузка…", "Loading…")}</p>;

  const month = Number(data.revenue_month_kzt);
  const prev = Number(data.revenue_prev_month_kzt);
  const delta = prev ? Math.round(((month - prev) / prev) * 100) : null;
  const peak = Math.max(1, ...data.revenue_by_month.map((m) => Number(m.amount_kzt)));

  return (
    <div>
      <PageHead title={tr(lang, "Обзор", "Overview")} subtitle={tr(lang, "Продажи и оплаты Bilim Academy", "Bilim Academy sales and payments")} />

      <div className="grid-kpi">
        <Kpi
          label={tr(lang, "Клиенты", "Clients")}
          value={data.clients_total}
          hint={`+${data.clients_new_30d} ${tr(lang, "за 30 дней", "in 30 days")}`}
          tone="up"
        />
        <Kpi
          label={tr(lang, "Активные договоры", "Active contracts")}
          value={data.contracts_active}
          hint={`${data.contracts_draft} ${tr(lang, "черновиков", "drafts")}`}
        />
        <Kpi
          label={tr(lang, "Выручка за месяц", "Revenue this month")}
          value={kzt(month)}
          hint={delta === null ? undefined : `${delta >= 0 ? "▲" : "▼"} ${Math.abs(delta)}% ${tr(lang, "к прошлому", "vs last")}`}
          tone={delta !== null && delta < 0 ? "down" : "up"}
        />
        <Kpi
          label={tr(lang, "Просрочено", "Overdue")}
          value={kzt(data.overdue_kzt)}
          hint={
            <Link to="/contracts?overdue=1">
              {data.overdue_count} {tr(lang, "платежей", "installments")} →
            </Link>
          }
          tone="down"
        />
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>{tr(lang, "Выручка по месяцам", "Revenue by month")}</h3>
          <div className="bars">
            {data.revenue_by_month.map((m) => (
              <div className="bar" key={m.month} title={kzt(m.amount_kzt)}>
                <span className="amount">{Math.round(Number(m.amount_kzt) / 1000)}k</span>
                <div className="fill" style={{ height: `${(Number(m.amount_kzt) / peak) * 100}%` }} />
                <span className="muted">{monthLabel(m.month, lang)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <h3>{tr(lang, "Популярные курсы", "Top courses")}</h3>
          {data.top_courses.length === 0 ? (
            <Empty text={tr(lang, "Записей пока нет", "No enrollments yet")} />
          ) : (
            <ul className="list-plain">
              {data.top_courses.map((c) => (
                <li key={c.code}>
                  <span>
                    <span className="muted">{c.code}</span> {c.title}
                  </span>
                  <strong>{c.enrollments}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.4rem" }}>
            <h3 style={{ margin: 0 }}>{tr(lang, "Последние оплаты", "Recent payments")}</h3>
            <Link to="/payments">{tr(lang, "Все оплаты →", "All payments →")}</Link>
          </div>
          {data.recent_payments.length === 0 ? (
            <Empty text={tr(lang, "Оплат пока нет", "No payments yet")} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <tbody>
                  {data.recent_payments.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link to={`/clients/${p.client_id}`}>{p.client_name}</Link>
                        <div className="muted" style={{ fontSize: "0.8rem" }}>
                          <Link to={`/contracts/${p.contract_id}`}>{p.contract_number}</Link> · {dateTime(p.paid_at ?? p.created_at)}
                        </div>
                      </td>
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
        </div>
        <div className="panel">
          <h3>{tr(lang, "Ближайшие платежи по графику", "Upcoming installments")}</h3>
          {data.upcoming.length === 0 ? (
            <Empty text={tr(lang, "Нет открытых платежей", "Nothing due")} />
          ) : (
            <ul className="list-plain">
              {data.upcoming.map((d) => (
                <li key={d.installment_id}>
                  <span>
                    <Link to={`/contracts/${d.contract_id}`}>{d.client_name}</Link>
                    <div className={d.overdue ? "down" : "muted"} style={{ fontSize: "0.8rem" }}>
                      {shortDate(d.due_date)} · {tr(lang, "платёж", "payment")} {d.seq}
                      {d.overdue ? ` · ${tr(lang, "просрочен", "overdue")}` : ""}
                    </div>
                  </span>
                  <strong>{kzt(d.amount_kzt)}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
