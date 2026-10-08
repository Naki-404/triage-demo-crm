import { Contract, Enrollment, Payment } from "../../api";

type Props = {
  lang: "ru" | "en";
  enrollments: Enrollment[];
  contracts: Contract[];
  payments: Payment[];
};

export function ClientCommercePanels({ lang, enrollments, contracts, payments }: Props) {
  return (
    <>
      <div className="panel" style={{ marginBottom: "1.25rem" }}>
        <p style={{ marginTop: 0 }}>{lang === "ru" ? "Записи на курсы" : "Enrollments"}</p>
        {enrollments.length === 0 ? (
          <p className="muted">{lang === "ru" ? "Пока нет" : "None"}</p>
        ) : (
          <ul style={{ paddingLeft: "1.1rem", margin: 0 }}>
            {enrollments.map((e) => (
              <li key={e.id}>
                course #{e.course_id} · {e.price_kzt} ₸ · −{e.discount_pct}%
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel" style={{ marginBottom: "1.25rem" }}>
        <p style={{ marginTop: 0 }}>{lang === "ru" ? "Договоры" : "Contracts"}</p>
        {contracts.length === 0 ? (
          <p className="muted">{lang === "ru" ? "Договора нет" : "No contracts"}</p>
        ) : (
          <ul style={{ paddingLeft: "1.1rem", margin: 0 }}>
            {contracts.map((c) => (
              <li key={c.id}>
                {c.number} · {c.status} · {c.total_kzt} ₸
              </li>
            ))}
          </ul>
        )}
        {payments.length > 0 && (
          <>
            <p style={{ marginTop: "1rem" }}>{lang === "ru" ? "Оплаты" : "Payments"}</p>
            <ul style={{ paddingLeft: "1.1rem", margin: 0 }}>
              {payments.map((p) => (
                <li key={p.id}>
                  {p.amount_kzt} ₸ · {p.status}
                  {p.card_last4 ? ` · ****${p.card_last4}` : ""}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </>
  );
}
