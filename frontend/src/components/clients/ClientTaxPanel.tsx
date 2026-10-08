type Props = {
  lang: "ru" | "en";
  pending: boolean;
  taxError: string | null;
  tax: Record<string, unknown> | null;
  onCheckTax: () => void;
};

export function ClientTaxPanel({ lang, pending, taxError, tax, onCheckTax }: Props) {
  return (
    <div className="panel" style={{ marginBottom: "1.25rem" }}>
      <p style={{ marginTop: 0 }}>{lang === "ru" ? "Налоговый статус (ЭСФ)" : "Tax status"}</p>
      <button className="btn" type="button" onClick={onCheckTax} disabled={pending}>
        {lang === "ru" ? "Проверить" : "Check"}
      </button>
      {taxError && <p className="error">{taxError}</p>}
      {tax && (
        <pre style={{ marginTop: "0.75rem", fontSize: "0.85rem", overflow: "auto" }}>{JSON.stringify(tax, null, 2)}</pre>
      )}
    </div>
  );
}
