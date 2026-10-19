import { FormEvent, useEffect, useState } from "react";
import { api, type CustomLogIn, type SimulateScenario, type SimulateResult } from "../api";

type Props = { lang: "ru" | "en" };

const EMPTY_CUSTOM: CustomLogIn = {
  message: "",
  level: "warning",
  method: "POST",
  path: "/api/custom",
  status_code: 500,
  action: "stand.custom_log",
  attack: "",
  client_ip: "",
  user_id: "",
  query: "",
  body: "",
  user_agent: "",
  count: 1,
};

export function StandPage({ lang }: Props) {
  const [snap, setSnap] = useState<Record<string, boolean | string> | null>(null);
  const [scenarios, setScenarios] = useState<SimulateScenario[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [last, setLast] = useState<SimulateResult | null>(null);
  const [mode, setMode] = useState<"clean" | "experiment" | "vuln">("clean");
  const [custom, setCustom] = useState<CustomLogIn>(EMPTY_CUSTOM);

  async function reload() {
    const [stand, catalog] = await Promise.all([api.stand(), api.simulateCatalog()]);
    setSnap(stand);
    setScenarios(catalog.scenarios);
    const m = String(stand.crm_mode || "clean");
    if (m === "experiment" || m === "vuln" || m === "clean") setMode(m);
  }

  useEffect(() => {
    reload().catch((err) => setError(String(err)));
  }, []);

  async function setCrmMode(next: "clean" | "experiment" | "vuln") {
    try {
      setError(null);
      setSnap(await api.patchStand({ crm_mode: next }));
      setMode(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function toggle(key: string, value: boolean) {
    try {
      setError(null);
      setSnap(await api.patchStand({ crm_mode: mode === "clean" ? "experiment" : mode, [key]: value }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function runScenario(id: string, count?: number) {
    try {
      setBusy(id);
      setError(null);
      const result = await api.simulate(id, count);
      setLast(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(null);
    }
  }

  async function sendCustom(e: FormEvent) {
    e.preventDefault();
    if (!custom.message.trim()) {
      setError(lang === "ru" ? "Введите текст сообщения лога." : "Enter a log message.");
      return;
    }
    try {
      setBusy("custom");
      setError(null);
      const payload: CustomLogIn = {
        message: custom.message.trim(),
        level: custom.level || "warning",
        method: custom.method || "POST",
        path: custom.path || "/api/custom",
        status_code: Number(custom.status_code) || 500,
        action: custom.action || "stand.custom_log",
        count: Number(custom.count) || 1,
      };
      if (custom.attack?.trim()) payload.attack = custom.attack.trim();
      if (custom.client_ip?.trim()) payload.client_ip = custom.client_ip.trim();
      if (custom.user_id?.trim()) payload.user_id = custom.user_id.trim();
      if (custom.query?.trim()) payload.query = custom.query.trim();
      if (custom.body?.trim()) payload.body = custom.body.trim();
      if (custom.user_agent?.trim()) payload.user_agent = custom.user_agent.trim();
      const result = await api.simulateCustom(payload);
      setLast(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(null);
    }
  }

  function setField<K extends keyof CustomLogIn>(key: K, value: CustomLogIn[K]) {
    setCustom((prev) => ({ ...prev, [key]: value }));
  }

  if (!snap) return <p className="muted">…</p>;

  const faults = Object.keys(snap).filter((k) => k.startsWith("FAULT_"));
  const vulns = Object.keys(snap).filter((k) => k.startsWith("VULN_"));

  return (
    <div className="stack">
      <div className="panel">
        <h2 style={{ fontFamily: "var(--display)", marginTop: 0 }}>
          {lang === "ru" ? "Режим стенда" : "Stand mode"}
        </h2>
        <p className="muted">
          {lang === "ru"
            ? "Лабораторный режим: переключатели дефектов и генерация логов атак для CSIP."
            : "Lab mode: fault switches and attack-log injection for CSIP."}
        </p>
        <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          {(["clean", "experiment", "vuln"] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={`btn btn-sm${mode === m ? " btn-accent" : ""}`}
              onClick={() => setCrmMode(m)}
            >
              {m}
            </button>
          ))}
        </div>
        <p className="muted">
          CRM_MODE: <strong>{String(snap.crm_mode)}</strong>
        </p>
        {error && <p className="error">{error}</p>}
        {last && (
          <p className="ok">
            {lang === "ru" ? "Отправлено" : "Shipped"}: {last.events} × {last.scenario} ({last.attack})
          </p>
        )}
      </div>

      <div className="panel">
        <h3 style={{ fontFamily: "var(--display)", marginTop: 0 }}>
          {lang === "ru" ? "Ручная отправка лога" : "Manual log"}
        </h3>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          {lang === "ru"
            ? "Свой текст и поля ECS — без заготовки. Уйдёт в файл/Elasticsearch и в Sentry (если DSN задан)."
            : "Your own message and ECS fields — no preset. Shipped to file/Elasticsearch and Sentry when DSN is set."}
        </p>
        <form className="custom-log-form" onSubmit={sendCustom}>
          <label className="field">
            <span>{lang === "ru" ? "Сообщение *" : "Message *"}</span>
            <textarea
              rows={3}
              value={custom.message}
              onChange={(e) => setField("message", e.target.value)}
              placeholder={
                lang === "ru"
                  ? "Например: repeated 403 on /api/admin after role change"
                  : "e.g. repeated 403 on /api/admin after role change"
              }
              required
            />
          </label>
          <div className="form-grid">
            <label className="field">
              <span>level</span>
              <select value={custom.level} onChange={(e) => setField("level", e.target.value as CustomLogIn["level"])}>
                <option value="info">info</option>
                <option value="warning">warning</option>
                <option value="error">error</option>
              </select>
            </label>
            <label className="field">
              <span>method</span>
              <input value={custom.method} onChange={(e) => setField("method", e.target.value)} />
            </label>
            <label className="field">
              <span>path</span>
              <input value={custom.path} onChange={(e) => setField("path", e.target.value)} />
            </label>
            <label className="field">
              <span>status_code</span>
              <input
                type="number"
                min={100}
                max={599}
                value={custom.status_code}
                onChange={(e) => setField("status_code", Number(e.target.value))}
              />
            </label>
            <label className="field">
              <span>action</span>
              <input value={custom.action} onChange={(e) => setField("action", e.target.value)} />
            </label>
            <label className="field">
              <span>attack / ATT&CK</span>
              <input
                value={custom.attack}
                onChange={(e) => setField("attack", e.target.value)}
                placeholder="T1110"
              />
            </label>
            <label className="field">
              <span>client_ip</span>
              <input
                value={custom.client_ip}
                onChange={(e) => setField("client_ip", e.target.value)}
                placeholder="203.0.113.10"
              />
            </label>
            <label className="field">
              <span>user_id</span>
              <input value={custom.user_id} onChange={(e) => setField("user_id", e.target.value)} />
            </label>
            <label className="field">
              <span>count</span>
              <input
                type="number"
                min={1}
                max={20}
                value={custom.count}
                onChange={(e) => setField("count", Number(e.target.value))}
              />
            </label>
          </div>
          <label className="field">
            <span>query</span>
            <input
              value={custom.query}
              onChange={(e) => setField("query", e.target.value)}
              placeholder={"name=x' OR '1'='1"}
            />
          </label>
          <label className="field">
            <span>body</span>
            <textarea
              rows={2}
              value={custom.body}
              onChange={(e) => setField("body", e.target.value)}
              placeholder='{"role":"admin"}'
            />
          </label>
          <label className="field">
            <span>user_agent</span>
            <input value={custom.user_agent} onChange={(e) => setField("user_agent", e.target.value)} />
          </label>
          <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
            <button type="submit" className="btn btn-accent" disabled={busy === "custom"}>
              {busy === "custom"
                ? lang === "ru"
                  ? "Отправка…"
                  : "Sending…"
                : lang === "ru"
                  ? "Отправить лог"
                  : "Send log"}
            </button>
            <button type="button" className="btn btn-sm" onClick={() => setCustom(EMPTY_CUSTOM)}>
              {lang === "ru" ? "Очистить" : "Clear"}
            </button>
          </div>
        </form>
      </div>

      <div className="panel">
        <h3 style={{ fontFamily: "var(--display)", marginTop: 0 }}>
          {lang === "ru" ? "Заготовки атак" : "Attack presets"}
        </h3>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          {lang === "ru"
            ? "Готовые пакеты событий. Для своего текста используйте форму выше."
            : "Ready-made event packs. Use the form above for free-form text."}
        </p>
        <div className="sim-grid">
          {scenarios.map((s) => (
            <div key={s.id} className="sim-card">
              <div className="sim-card-head">
                <strong>{lang === "ru" ? s.title_ru : s.title_en}</strong>
                <span className="pill">{s.attack}</span>
              </div>
              <p className="muted" style={{ margin: "0.35rem 0 0.75rem", fontSize: "0.9rem" }}>
                {lang === "ru" ? s.description_ru : s.description_en}
              </p>
              <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-accent"
                  disabled={busy === s.id}
                  onClick={() => runScenario(s.id)}
                >
                  {busy === s.id
                    ? lang === "ru"
                      ? "Отправка…"
                      : "Sending…"
                    : lang === "ru"
                      ? `Симулировать (${s.default_events})`
                      : `Simulate (${s.default_events})`}
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={busy === s.id}
                  onClick={() => runScenario(s.id, 1)}
                >
                  {lang === "ru" ? "1 событие" : "1 event"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {faults.length > 0 && (
        <div className="panel">
          <h3 style={{ fontFamily: "var(--display)", marginTop: 0 }}>FAULT_*</h3>
          <p className="muted">{lang === "ru" ? "Нужен режим experiment." : "Requires experiment mode."}</p>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {faults.map((key) => (
              <li key={key} style={{ marginBottom: "0.5rem" }}>
                <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={Boolean(snap[key])}
                    onChange={(e) => toggle(key, e.target.checked)}
                  />
                  {key}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      {vulns.length > 0 && (
        <div className="panel">
          <h3 style={{ fontFamily: "var(--display)", marginTop: 0 }}>VULN_*</h3>
          <p className="muted">{lang === "ru" ? "Нужен режим vuln." : "Requires vuln mode."}</p>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {vulns.map((key) => (
              <li key={key} style={{ marginBottom: "0.5rem" }}>
                <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={Boolean(snap[key])}
                    onChange={(e) => toggle(key, e.target.checked)}
                  />
                  {key}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
