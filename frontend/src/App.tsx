import { useEffect, useState } from "react";
import { Navigate, Route, Routes, Link } from "react-router-dom";
import { api, User } from "./api";
import { LoginPage } from "./pages/LoginPage";
import { ClientsPage } from "./pages/ClientsPage";
import { ClientCardPage } from "./pages/ClientCardPage";
import { StandPage } from "./pages/StandPage";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [standUi, setStandUi] = useState(false);
  const [lang, setLang] = useState<"ru" | "en">("ru");

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
            {lang === "ru" ? "Загрузка…" : "Loading…"}
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage lang={lang} onLogin={setUser} />;
  }

  const canWrite = user.role === "admin" || user.role === "manager";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="brand">Qazaq CRM</p>
          <p className="muted" style={{ margin: 0 }}>
            {user.username} · {user.role}
          </p>
        </div>
        <nav className="nav">
          <Link to="/">{lang === "ru" ? "Клиенты" : "Clients"}</Link>
          {standUi && user.role === "admin" && (
            <Link to="/stand">{lang === "ru" ? "Стенд" : "Stand"}</Link>
          )}
          <button className="btn" type="button" onClick={() => setLang(lang === "ru" ? "en" : "ru")}>
            {lang === "ru" ? "EN" : "RU"}
          </button>
          <button
            className="btn"
            type="button"
            onClick={async () => {
              await api.logout();
              setUser(null);
            }}
          >
            {lang === "ru" ? "Выйти" : "Log out"}
          </button>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<ClientsPage lang={lang} canWrite={canWrite} />} />
        <Route path="/clients/:id" element={<ClientCardPage lang={lang} canWrite={canWrite} />} />
        <Route
          path="/stand"
          element={standUi && user.role === "admin" ? <StandPage lang={lang} /> : <Navigate to="/" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
