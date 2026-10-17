import { FormEvent, useEffect, useState } from "react";
import { api, Client } from "../api";
import { ClientCreateForm } from "../components/clients/ClientCreateForm";
import { ClientsTable } from "../components/clients/ClientsTable";
import { ClientsToolbar } from "../components/clients/ClientsToolbar";
import { Modal, PageHead } from "../components/ui";
import { tr } from "../format";

type Props = { lang: "ru" | "en"; canWrite: boolean };

const PAGE_SIZE = 25;

export function ClientsPage({ lang, canWrite }: Props) {
  const [items, setItems] = useState<Client[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [name, setName] = useState("");
  const [iin, setIin] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [creating, setCreating] = useState(false);

  async function load(query?: string, pageNum = page) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listClients({ q: query, page: pageNum, page_size: PAGE_SIZE });
      setItems(res.items);
      setTotal(res.total);
      setPage(res.page);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch((err) => {
      setError(String(err));
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    try {
      await load(q, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await api.createClient({
        name,
        iin,
        phone: phone || undefined,
        email: email || undefined,
      });
      setName("");
      setIin("");
      setPhone("");
      setEmail("");
      setCreating(false);
      await load(q, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  async function goPage(next: number) {
    setPending(true);
    try {
      await load(q, next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setPending(false);
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHead
        title={tr(lang, "Клиенты", "Clients")}
        subtitle={`${total} ${tr(lang, "в базе", "in the database")}`}
        actions={
          canWrite && (
            <button className="btn btn-primary" type="button" onClick={() => setCreating(true)}>
              + {tr(lang, "Новый клиент", "New client")}
            </button>
          )
        }
      />
      <ClientsToolbar lang={lang} q={q} pending={pending} loading={loading} onQChange={setQ} onSearch={onSearch} />

      {canWrite && creating && (
        <Modal title={tr(lang, "Новый клиент", "New client")} onClose={() => setCreating(false)}>
        <ClientCreateForm
          lang={lang}
          pending={pending}
          name={name}
          iin={iin}
          phone={phone}
          email={email}
          onNameChange={setName}
          onIinChange={setIin}
          onPhoneChange={setPhone}
          onEmailChange={setEmail}
          onSubmit={onCreate}
        />
        {error && <p className="error">{error}</p>}
        </Modal>
      )}

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">{lang === "ru" ? "Загрузка клиентов…" : "Loading clients…"}</p>
      ) : items.length === 0 ? (
        <div className="panel">
          <p style={{ margin: 0 }}>{lang === "ru" ? "Клиентов пока нет" : "No clients yet"}</p>
          <p className="muted" style={{ marginBottom: 0 }}>
            {lang === "ru" ? "Создайте первого клиента или измените поиск." : "Create a client or adjust the search."}
          </p>
        </div>
      ) : (
        <div className="panel">
        <ClientsTable
          lang={lang}
          items={items}
          page={page}
          pageCount={pageCount}
          total={total}
          pageSize={PAGE_SIZE}
          pending={pending}
          onPage={goPage}
        />
        </div>
      )}
    </div>
  );
}
