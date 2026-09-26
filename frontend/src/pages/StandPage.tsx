import { useEffect, useState } from "react";
import { api } from "../api";

type Props = { lang: "ru" | "en" };

export function StandPage({ lang }: Props) {
  const [snap, setSnap] = useState<Record<string, boolean | string> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setSnap(await api.stand());
  }

  useEffect(() => {
    reload().catch((err) => setError(String(err)));
  }, []);

  async function toggle(key: string, value: boolean) {
    try {
      setSnap(await api.patchStand({ [key]: value }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  if (!snap) return <p className="muted">…</p>;

  const faults = Object.keys(snap).filter((k) => k.startsWith("FAULT_"));

  return (
    <div className="panel">
      <h2 style={{ fontFamily: "var(--display)", marginTop: 0 }}>
        {lang === "ru" ? "Режим стенда" : "Stand mode"}
      </h2>
      <p className="muted">
        CRM_MODE: {String(snap.crm_mode)}
      </p>
      {error && <p className="error">{error}</p>}
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
  );
}
