import { useId, useState } from "react";
import { getReportMatches } from "../api";
import type { ReportMatches } from "../types";
import ErrorBox from "./ErrorBox";
import ItemCard from "./ItemCard";
import Spinner from "./Spinner";

export default function TrackingBox() {
  const uid = useId();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReportMatches | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) {
      setError("Lütfen takip kodunuzu yazın.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await getReportMatches(code.trim()));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="tracking-box">
      <form className="panel" onSubmit={onSubmit} aria-busy={loading}>
        <div className="field">
          <label htmlFor={`${uid}-code`}>Takip kodumla kontrol et</label>
          <input
            id={`${uid}-code`}
            type="text"
            maxLength={8}
            autoComplete="off"
            value={code}
            placeholder="K7M2QX9A"
            disabled={loading}
            onChange={(e) => setCode(e.target.value)}
          />
        </div>
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Kontrol ediliyor…" : "Kontrol et"}
        </button>
      </form>

      <ErrorBox message={error} />
      {loading && <Spinner label="Kontrol ediliyor…" />}

      {!loading && result && (
        <div aria-live="polite">
          {result.matches.length === 0 ? (
            <p className="empty">Henüz eşleşen bir ilan yok. Daha sonra tekrar kontrol edin.</p>
          ) : (
            <>
              <h2 className="section-title">Eşleşen ilanlar ({result.matches.length})</h2>
              <div className="grid">
                {result.matches.map((m) => (
                  <ItemCard key={m.item.id} item={m.item} score={m.score} level={m.match_level} />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
