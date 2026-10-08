import { FormEvent } from "react";
import { api } from "../../api";

type Props = {
  lang: "ru" | "en";
  q: string;
  pending: boolean;
  loading: boolean;
  onQChange: (value: string) => void;
  onSearch: (e: FormEvent) => void;
};

export function ClientsToolbar({ lang, q, pending, loading, onQChange, onSearch }: Props) {
  return (
    <div className="toolbar">
      <form className="row" onSubmit={onSearch}>
        <label className="field" style={{ marginBottom: 0 }}>
          <span>{lang === "ru" ? "Поиск" : "Search"}</span>
          <input value={q} onChange={(e) => onQChange(e.target.value)} placeholder="name / IIN" disabled={pending} />
        </label>
        <button className="btn" type="submit" disabled={pending || loading}>
          {lang === "ru" ? "Найти" : "Find"}
        </button>
      </form>
      <div className="row">
        <a className="btn" href={api.exportUrl("csv")}>
          CSV
        </a>
        <a className="btn" href={api.exportUrl("xlsx")}>
          XLSX
        </a>
      </div>
    </div>
  );
}
