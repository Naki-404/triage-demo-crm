import { FormEvent, useState } from "react";
import { api, User } from "../api";

type Props = {
  onLogin: (user: User) => void;
  lang: "ru" | "en";
};

const copy = {
  ru: {
    title: "Вход",
    user: "Логин",
    pass: "Пароль",
    submit: "Войти",
  },
  en: {
    title: "Sign in",
    user: "Username",
    pass: "Password",
    submit: "Sign in",
  },
};

export function LoginPage({ onLogin, lang }: Props) {
  const t = copy[lang];
  const [username, setUsername] = useState("manager");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(username, password);
      onLogin(res.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="panel login-panel" onSubmit={onSubmit}>
        <p className="brand">Qazaq CRM</p>
        <p className="muted">{t.title}</p>
        <label className="field">
          <span>{t.user}</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label className="field">
          <span>{t.pass}</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {t.submit}
        </button>
      </form>
    </div>
  );
}
