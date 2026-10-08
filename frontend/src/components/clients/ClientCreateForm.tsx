import { FormEvent } from "react";

type Props = {
  lang: "ru" | "en";
  pending: boolean;
  name: string;
  iin: string;
  phone: string;
  email: string;
  onNameChange: (v: string) => void;
  onIinChange: (v: string) => void;
  onPhoneChange: (v: string) => void;
  onEmailChange: (v: string) => void;
  onSubmit: (e: FormEvent) => void;
};

export function ClientCreateForm(props: Props) {
  const { lang, pending, name, iin, phone, email, onNameChange, onIinChange, onPhoneChange, onEmailChange, onSubmit } =
    props;
  return (
    <form className="panel" onSubmit={onSubmit} style={{ marginBottom: "1.25rem" }}>
      <p style={{ marginTop: 0 }}>{lang === "ru" ? "Новый клиент" : "New client"}</p>
      <div className="row">
        <label className="field">
          <span>{lang === "ru" ? "ФИО" : "Name"}</span>
          <input value={name} onChange={(e) => onNameChange(e.target.value)} required disabled={pending} />
        </label>
        <label className="field">
          <span>ИИН</span>
          <input value={iin} onChange={(e) => onIinChange(e.target.value)} required minLength={12} maxLength={12} disabled={pending} />
        </label>
        <label className="field">
          <span>{lang === "ru" ? "Телефон" : "Phone"}</span>
          <input value={phone} onChange={(e) => onPhoneChange(e.target.value)} disabled={pending} />
        </label>
        <label className="field">
          <span>Email</span>
          <input value={email} onChange={(e) => onEmailChange(e.target.value)} type="email" disabled={pending} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={pending}>
          {pending ? "…" : lang === "ru" ? "Создать" : "Create"}
        </button>
      </div>
    </form>
  );
}
