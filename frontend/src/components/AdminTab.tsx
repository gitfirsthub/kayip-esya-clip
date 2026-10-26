import { useEffect, useId, useState } from "react";
import { adminDelete, adminList, adminMe, adminSetStatus } from "../api";
import type { ItemList, ItemStatus } from "../types";
import EmptyState from "./EmptyState";
import ErrorBox from "./ErrorBox";
import ItemCard from "./ItemCard";
import SkeletonGrid from "./Skeleton";
import Spinner from "./Spinner";

const PAGE_SIZE = 20;

// Token yalnızca bellekte (React durumu) tutulur; App sekmeler arası geçişte korur.
export interface AdminSession {
  token: string;
  scope: string | null;
}

interface Props {
  session: AdminSession | null;
  onLogin: (session: AdminSession) => void;
  onLogout: () => void;
}

const FALLBACK_ERROR = "Beklenmeyen bir hata oluştu.";

function LoginForm({ onLogin }: { onLogin: (s: AdminSession) => void }) {
  const uid = useId();
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = token.trim();
    if (!value) {
      setError("Lütfen yönetici anahtarını yazın.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const me = await adminMe(value);
      setToken("");
      onLogin({ token: value, scope: me.scope });
    } catch (err) {
      setError(err instanceof Error ? err.message : FALLBACK_ERROR);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <form className="panel" onSubmit={onSubmit} aria-busy={loading}>
        <fieldset className="fieldset" disabled={loading}>
          <legend>Yönetici girişi</legend>
          <div className="field">
            <label htmlFor={`${uid}-token`}>Yönetici anahtarı</label>
            <input
              id={`${uid}-token`}
              type="password"
              autoComplete="off"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
            <span className="hint">
              Teslim noktanıza verilen anahtarı yazın. Sayfa yenilenince veya çıkış yapınca silinir.
            </span>
          </div>
        </fieldset>
        <div className="form-actions">
          <button className="btn" type="submit" disabled={loading}>
            {loading && <Spinner inline />}
            {loading ? "Doğrulanıyor…" : "Giriş"}
          </button>
        </div>
      </form>
      <ErrorBox message={error} />
    </section>
  );
}

function AdminPanel({
  session,
  onLogout,
}: {
  session: AdminSession;
  onLogout: () => void;
}) {
  const uid = useId();
  const { token, scope } = session;
  const [status, setStatus] = useState<"" | ItemStatus>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ItemList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminList(token, { status: status || undefined, limit: PAGE_SIZE, offset })
      .then((res) => {
        if (cancelled) return;
        if (res.items.length === 0 && offset > 0) {
          setOffset(Math.max(0, offset - PAGE_SIZE));
          return;
        }
        setData(res);
        setError(null);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setData(null);
        setError(err instanceof Error ? err.message : FALLBACK_ERROR);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, status, offset, attempt]);

  async function run(id: string, action: () => Promise<unknown>) {
    setBusyId(id);
    setError(null);
    try {
      await action();
      setConfirmId(null);
      setAttempt((a) => a + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : FALLBACK_ERROR);
    } finally {
      setBusyId(null);
    }
  }

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section>
      <div className="admin-head">
        <h2 className="section-title">{scope ?? "Tüm noktalar"} yönetimi</h2>
        <button className="btn btn-secondary" type="button" onClick={onLogout}>
          Çıkış
        </button>
      </div>
      <p className="hint admin-hint">Sahibine teslim edilen eşyayı kaldırabilirsiniz.</p>

      <div className="panel">
        <div className="field">
          <label htmlFor={`${uid}-status`}>Durum</label>
          <select
            id={`${uid}-status`}
            value={status}
            disabled={loading}
            onChange={(e) => {
              setStatus(e.target.value as "" | ItemStatus);
              setOffset(0);
              setConfirmId(null);
            }}
          >
            <option value="">Tümü</option>
            <option value="bekliyor">Bekliyor</option>
            <option value="teslim_edildi">Teslim edildi</option>
          </select>
        </div>
      </div>

      <ErrorBox message={error} />
      {error && !data && (
        <button className="btn btn-secondary" type="button" onClick={() => setAttempt((a) => a + 1)}>
          Tekrar dene
        </button>
      )}
      {loading && !data && (
        <>
          <Spinner label="İlanlar yükleniyor…" />
          <SkeletonGrid />
        </>
      )}

      {data && (
        <div aria-live="polite" aria-busy={loading}>
          {data.items.length === 0 ? (
            <EmptyState title="Bu noktaya teslim edilmiş ilan yok.">
              Yeni ilanlar burada görünür.
            </EmptyState>
          ) : (
            <>
              <p>Toplam {total} ilan</p>
              <div className="grid">
                {data.items.map((item) => {
                  const busy = busyId === item.id;
                  const next: ItemStatus = item.status === "bekliyor" ? "teslim_edildi" : "bekliyor";
                  return (
                    <ItemCard
                      key={item.id}
                      item={item}
                      showTags
                      actions={
                        confirmId === item.id ? (
                          <div className="confirm" role="group" aria-label="Kaldırma onayı">
                            <p className="confirm-text">Emin misiniz?</p>
                            <div className="confirm-buttons">
                              <button
                                className="btn btn-danger"
                                type="button"
                                disabled={busy}
                                onClick={() => void run(item.id, () => adminDelete(token, item.id))}
                              >
                                {busy && <Spinner inline />}
                                Evet, kaldır
                              </button>
                              <button
                                className="btn btn-secondary"
                                type="button"
                                disabled={busy}
                                autoFocus
                                onClick={() => setConfirmId(null)}
                              >
                                Vazgeç
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="confirm-buttons">
                            <button
                              className="btn"
                              type="button"
                              disabled={busy || busyId !== null}
                              onClick={() =>
                                void run(item.id, () => adminSetStatus(token, item.id, next))
                              }
                            >
                              {busy && <Spinner inline />}
                              {item.status === "bekliyor"
                                ? "Teslim edildi olarak işaretle"
                                : "Bekliyora al"}
                            </button>
                            <button
                              className="btn btn-secondary"
                              type="button"
                              disabled={busyId !== null}
                              onClick={() => setConfirmId(item.id)}
                            >
                              Kaldır
                            </button>
                          </div>
                        )
                      }
                    />
                  );
                })}
              </div>
              <nav className="pager" aria-label="Sayfalama">
                <button
                  className="btn btn-secondary"
                  type="button"
                  disabled={loading || offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Önceki
                </button>
                <span>
                  Sayfa {page} / {pageCount}
                </span>
                <button
                  className="btn btn-secondary"
                  type="button"
                  disabled={loading || offset + PAGE_SIZE >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Sonraki
                </button>
              </nav>
            </>
          )}
        </div>
      )}
    </section>
  );
}

export default function AdminTab({ session, onLogin, onLogout }: Props) {
  if (!session) return <LoginForm onLogin={onLogin} />;
  return <AdminPanel session={session} onLogout={onLogout} />;
}
