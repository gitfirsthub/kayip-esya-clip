import { useId, useState } from "react";
import { createLostReport, searchItems } from "../api";
import type { Meta, SearchResponse } from "../types";
import ErrorBox from "./ErrorBox";
import ImagePicker from "./ImagePicker";
import ItemCard from "./ItemCard";
import Spinner from "./Spinner";
import TrackingBox from "./TrackingBox";

export default function SearchTab({ meta }: { meta: Meta }) {
  const uid = useId();
  const [query, setQuery] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [reporting, setReporting] = useState(false);
  const [trackingCode, setTrackingCode] = useState<string | null>(null);

  async function onReport() {
    if (!query.trim() && !image) {
      setError("Bildirim için bir açıklama yazın veya fotoğraf yükleyin.");
      return;
    }
    setReporting(true);
    setError(null);
    try {
      const res = await createLostReport({ query: query.trim(), image, location });
      setTrackingCode(res.tracking_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setReporting(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() && !image) {
      setError("Aramak için bir açıklama yazın veya fotoğraf yükleyin.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await searchItems({
        query: query.trim(),
        image,
        location,
        category,
      });
      setResponse(res);
    } catch (err) {
      setResponse(null);
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  const strong = response?.results.filter((r) => r.match_level !== "düşük") ?? [];
  const weak = response?.results.filter((r) => r.match_level === "düşük") ?? [];

  return (
    <section>
      <form className="panel" onSubmit={onSubmit} aria-busy={loading}>
        <div className="field">
          <label htmlFor={`${uid}-q`}>Kayıp eşyanızı tarif edin</label>
          <textarea
            id={`${uid}-q`}
            rows={3}
            maxLength={200}
            value={query}
            placeholder="lacivert termos, üzerinde çıkartma var"
            disabled={loading}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <ImagePicker
          label="Benzer bir fotoğraf (isteğe bağlı)"
          file={image}
          maxMb={meta.max_upload_mb}
          disabled={loading}
          onChange={setImage}
          onError={setError}
        />
        <div className="row">
          <div className="field">
            <label htmlFor={`${uid}-loc`}>Yer</label>
            <select
              id={`${uid}-loc`}
              value={location}
              disabled={loading}
              onChange={(e) => setLocation(e.target.value)}
            >
              <option value="">Tümü</option>
              {meta.locations.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor={`${uid}-cat`}>Kategori</label>
            <select
              id={`${uid}-cat`}
              value={category}
              disabled={loading}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">Tümü</option>
              {meta.categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Aranıyor…" : "Ara"}
        </button>
        <button
          className="btn btn-secondary"
          type="button"
          disabled={loading || reporting}
          onClick={() => void onReport()}
        >
          {reporting ? "Kaydediliyor…" : "Bulunursa haber almak için bildirim bırak"}
        </button>
      </form>

      {trackingCode && (
        <div className="panel tracking-code" role="status">
          <p>Takip kodunuz:</p>
          <p className="code">{trackingCode}</p>
          <p className="desc">
            Bu kodu not alın; bir daha gösterilmez. İletişim bilgisi toplanmaz. Eşyanıza benzer bir ilan
            eklenince aşağıdaki kutudan kodunuzla kontrol edebilirsiniz.
          </p>
        </div>
      )}

      <ErrorBox message={error} />
      {loading && <Spinner label="Aranıyor…" />}

      {!loading && response && (
        <div aria-live="polite">
          {strong.length === 0 && (
            <p className="empty">
              {weak.length === 0
                ? "Eşleşen ilan bulunamadı. Açıklamayı değiştirmeyi, filtreleri kaldırmayı veya bir fotoğraf eklemeyi deneyin."
                : "Güçlü bir eşleşme bulunamadı. Aşağıdaki daha az benzer sonuçlara göz atabilirsiniz."}
            </p>
          )}
          {strong.length > 0 && (
            <>
              <h2 className="section-title">Sonuçlar ({strong.length})</h2>
              <div className="grid">
                {strong.map((r) => (
                  <ItemCard key={r.item.id} item={r.item} score={r.score} level={r.match_level} />
                ))}
              </div>
            </>
          )}
          {weak.length > 0 && (
            <details className="weak">
              <summary>Daha az benzer sonuçlar ({weak.length})</summary>
              <div className="grid">
                {weak.map((r) => (
                  <ItemCard key={r.item.id} item={r.item} score={r.score} level={r.match_level} />
                ))}
              </div>
            </details>
          )}
        </div>
      )}

      <TrackingBox />
    </section>
  );
}
