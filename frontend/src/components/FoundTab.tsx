import { useId, useState } from "react";
import { createItem } from "../api";
import type { Item, Meta } from "../types";
import ErrorBox from "./ErrorBox";
import ImagePicker from "./ImagePicker";
import ItemCard from "./ItemCard";
import Spinner from "./Spinner";

function toDateString(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export default function FoundTab({ meta }: { meta: Meta }) {
  const uid = useId();
  const today = new Date();
  const minDate = new Date();
  minDate.setDate(minDate.getDate() - 60);
  const maxStr = toDateString(today);
  const minStr = toDateString(minDate);

  const [image, setImage] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState(meta.locations[0] ?? "");
  const [foundDate, setFoundDate] = useState(maxStr);
  const [dropoff, setDropoff] = useState(meta.dropoff_points[0] ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Item | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!image) {
      setError("Lütfen bir fotoğraf seçin.");
      return;
    }
    if (title.trim().length < 3 || title.trim().length > 80) {
      setError("Başlık 3 ile 80 karakter arasında olmalıdır.");
      return;
    }
    setLoading(true);
    setError(null);
    setCreated(null);
    try {
      const item = await createItem({
        image,
        title: title.trim(),
        description: description.trim(),
        location,
        found_date: foundDate,
        dropoff_point: dropoff,
      });
      setCreated(item);
      setImage(null);
      setTitle("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <form className="panel" onSubmit={onSubmit} aria-busy={loading}>
        <fieldset className="fieldset" disabled={loading}>
          <legend>Fotoğraf</legend>
          <ImagePicker
            label="Bulunan eşyanın fotoğrafı"
            file={image}
            maxMb={meta.max_upload_mb}
            required
            disabled={loading}
            onChange={setImage}
            onError={setError}
          />
        </fieldset>
        <fieldset className="fieldset" disabled={loading}>
          <legend>Eşya bilgileri</legend>
        <div className="field">
          <label htmlFor={`${uid}-title`}>Başlık</label>
          <input
            id={`${uid}-title`}
            type="text"
            required
            minLength={3}
            maxLength={80}
            value={title}
            placeholder="Siyah sırt çantası"
            disabled={loading}
            onChange={(e) => setTitle(e.target.value)}
          />
          <span className="hint">3 ile 80 karakter.</span>
        </div>
        <div className="field">
          <label htmlFor={`${uid}-desc`}>Açıklama (isteğe bağlı)</label>
          <textarea
            id={`${uid}-desc`}
            rows={3}
            maxLength={500}
            value={description}
            disabled={loading}
            onChange={(e) => setDescription(e.target.value)}
          />
          <span className="hint">En fazla 500 karakter.</span>
        </div>
        </fieldset>
        <fieldset className="fieldset" disabled={loading}>
          <legend>Nerede ve ne zaman bulundu</legend>
        <div className="row">
          <div className="field">
            <label htmlFor={`${uid}-loc`}>Bulunduğu yer</label>
            <select
              id={`${uid}-loc`}
              required
              value={location}
              disabled={loading}
              onChange={(e) => setLocation(e.target.value)}
            >
              {meta.locations.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor={`${uid}-date`}>Bulunma tarihi</label>
            <input
              id={`${uid}-date`}
              type="date"
              required
              min={minStr}
              max={maxStr}
              value={foundDate}
              disabled={loading}
              onChange={(e) => setFoundDate(e.target.value)}
            />
          </div>
        </div>
        </fieldset>
        <fieldset className="fieldset" disabled={loading}>
          <legend>Teslim</legend>
        <div className="field">
          <label htmlFor={`${uid}-drop`}>Teslim noktası</label>
          <select
            id={`${uid}-drop`}
            required
            value={dropoff}
            disabled={loading}
            onChange={(e) => setDropoff(e.target.value)}
          >
            {meta.dropoff_points.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <span className="hint">Eşyayı bu noktaya bırakın.</span>
        </div>
        </fieldset>
        <div className="form-actions">
          <button className="btn" type="submit" disabled={loading}>
            {loading && <Spinner inline />}
            {loading ? "Yükleniyor…" : "İlanı Kaydet"}
          </button>
        </div>
      </form>

      <ErrorBox message={error} />
      {loading && <Spinner label="Fotoğraf işleniyor, lütfen bekleyin…" />}

      {created && !loading && (
        <div aria-live="polite">
          <h2 className="section-title">İlan kaydedildi</h2>
          <p>
            Otomatik etiketler: kategori <strong>{created.category}</strong>, renk{" "}
            <strong>{created.color}</strong>.{" "}
            {created.faces_blurred > 0
              ? `${created.faces_blurred} yüz bulanıklaştırıldı.`
              : "Fotoğrafta yüz bulunmadı."}
          </p>
          <div className="grid">
            <ItemCard item={created} showTags />
          </div>
        </div>
      )}
    </section>
  );
}
