import { Link } from "react-router-dom";
import { api, Client } from "../../api";

type Props = { lang: "ru" | "en"; client: Client };

export function ClientProfilePanel({ lang, client }: Props) {
  return (
    <div className="panel" style={{ marginBottom: "1.25rem" }}>
      <p>
        <Link to="/">{lang === "ru" ? "← Клиенты" : "← Clients"}</Link>
      </p>
      <h2 style={{ fontFamily: "var(--display)", marginTop: 0 }}>{client.name}</h2>
      <p>
        <span className="muted">ИИН</span> {client.iin}
      </p>
      <p>
        <span className="muted">{lang === "ru" ? "Дата рождения" : "Birth date"}</span> {client.birth_date || "—"}
      </p>
      <p>
        <span className="muted">{lang === "ru" ? "Телефон" : "Phone"}</span> {client.phone || "—"}
      </p>
      <p>
        <span className="muted">Email</span> {client.email || "—"}
      </p>
      <p>
        <a className="btn" href={api.exportUrl("csv")}>
          {lang === "ru" ? "Экспорт CSV" : "Export CSV"}
        </a>
      </p>
    </div>
  );
}
