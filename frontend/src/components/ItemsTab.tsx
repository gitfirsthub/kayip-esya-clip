import { useEffect, useId, useState } from "react";
import { listItems } from "../api";
import type { ItemList, ItemStatus } from "../types";
import ErrorBox from "./ErrorBox";
import ItemCard from "./ItemCard";
import Spinner from "./Spinner";

const PAGE_SIZE = 20;

export default function ItemsTab() {
  const uid = useId();
  const [status, setStatus] = useState<"" | ItemStatus>("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ItemList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listItems({ status: status || undefined, limit: PAGE_SIZE, offset })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [status, offset, attempt]);

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section>
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
            }}
          >
            <option value="">Tümü</option>
            <option value="bekliyor">Bekliyor</option>
            <option value="teslim_edildi">Teslim edildi</option>
          </select>
        </div>
      </div>

      <ErrorBox message={error} />
      {error && (
        <button className="btn btn-secondary" type="button" onClick={() => setAttempt((a) => a + 1)}>
          Tekrar dene
        </button>
      )}
      {loading && <Spinner label="İlanlar yükleniyor…" />}

      {!loading && data && (
        <div aria-live="polite">
          {data.items.length === 0 ? (
            <p className="empty">Henüz ilan bulunmuyor.</p>
          ) : (
            <>
              <p>Toplam {total} ilan</p>
              <div className="grid">
                {data.items.map((item) => (
                  <ItemCard key={item.id} item={item} showTags />
                ))}
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
