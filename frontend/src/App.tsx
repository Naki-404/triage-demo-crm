import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { api, User } from "./api";
import { Lang, tr } from "./format";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ClientsPage } from "./pages/ClientsPage";
import { ClientCardPage } from "./pages/ClientCardPage";
import { ContractsPage } from "./pages/ContractsPage";
import { ContractPage } from "./pages/ContractPage";
import { PaymentsPage } from "./pages/PaymentsPage";
import { CoursesPage } from "./pages/CoursesPage";
import { StandPage } from "./pages/StandPage";

const ROLE_LABEL: Record<string, [string, string]> = {
  admin: ["Администратор", "Administrator"],
  manager: ["Менеджер", "Manager"],
  viewer: ["Наблюдатель", "Viewer"],
};

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [standUi, setStandUi] = useState(false);
  const [lang, setLang] = useState<Lang>("ru");

  useEffect(() => {
    Promise.all([api.me().catch(() => null), api.standPublic().catch(() => ({ stand_ui: false }))])
      .then(([me, stand]) => {
        setUser(me);
        setStandUi(Boolean(stand && "stand_ui" in stand && stand.stand_ui));
      })
      .finally(() => setReady(true));
  }, []);

  if (!ready) {
    return (
      <div className="login-page">
        <div className="panel login-panel" style={{ textAlign: "center" }}>
          <p className="brand" style={{ marginBottom: "0.75rem" }}>
            Qazaq CRM
          </p>
          <div className="skeleton-block" aria-hidden />
          <p className="muted" style={{ marginTop: "1rem" }}>
            {tr(lang, "Загрузка…", "Loading…")}
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage lang={lang} onLogin={setUser} />;
  }

  const canWrite = user.role === "admin" || user.role === "manager";
  const nav: [string, string, string, string][] = [
    ["/", "◧", "Обзор", "Overview"],
    ["/clients", "☺", "Клиенты", "Clients"],
    ["/contracts", "▤", "Договоры", "Contracts"],
    ["/payments", "₸", "Оплаты", "Payments"],
    ["/courses", "✦", "Курсы", "Courses"],
  ];
  if (standUi && user.role === "admin") nav.push(["/stand", "⚙", "Стенд", "Stand"]);
  const role = ROLE_LABEL[user.role] ?? [user.role, user.role];

  return (
    <div className="layout">
      <aside className="sidebar">
        <p className="brand">Qazaq CRM</p>
        <p className="muted org">Bilim Academy · {tr(lang, "отдел продаж", "sales")}</p>
        {nav.map(([to, icon, ru, en]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
            <span className="nav-icon" aria-hidden>
              {icon}
            </span>
            {tr(lang, ru, en)}
          </NavLink>
        ))}
        <div className="who">
          <div style={{ fontWeight: 700 }}>{user.username}</div>
          <div className="muted">{tr(lang, role[0], role[1])}</div>
          <div className="row">
            <button className="btn btn-sm" type="button" onClick={() => setLang(lang === "ru" ? "en" : "ru")}>
              {lang === "ru" ? "EN" : "RU"}
            </button>
            <button
              className="btn btn-sm"
              type="button"
              onClick={async () => {
                await api.logout();
                setUser(null);
              }}
            >
              {tr(lang, "Выйти", "Log out")}
            </button>
          </div>
        </div>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<DashboardPage lang={lang} />} />
          <Route path="/clients" element={<ClientsPage lang={lang} canWrite={canWrite} />} />
          <Route path="/clients/:id" element={<ClientCardPage lang={lang} canWrite={canWrite} />} />
          <Route path="/contracts" element={<ContractsPage lang={lang} />} />
          <Route path="/contracts/:id" element={<ContractPage lang={lang} canWrite={canWrite} />} />
          <Route path="/payments" element={<PaymentsPage lang={lang} />} />
          <Route path="/courses" element={<CoursesPage lang={lang} />} />
          <Route
            path="/stand"
            element={standUi && user.role === "admin" ? <StandPage lang={lang} /> : <Navigate to="/" replace />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
