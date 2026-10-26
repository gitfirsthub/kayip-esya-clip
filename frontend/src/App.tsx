import { useCallback, useEffect, useState } from "react";
import { getMeta } from "./api";
import AdminTab, { type AdminSession } from "./components/AdminTab";
import FoundTab from "./components/FoundTab";
import ErrorBox from "./components/ErrorBox";
import ItemsTab from "./components/ItemsTab";
import SearchTab from "./components/SearchTab";
import Spinner from "./components/Spinner";
import Tabs, { type TabDef } from "./components/Tabs";
import type { Meta } from "./types";

const TABS: TabDef[] = [
  { id: "search", label: "Eşyamı Kaybettim" },
  { id: "found", label: "Eşya Buldum" },
  { id: "items", label: "Tüm İlanlar" },
  { id: "admin", label: "Yönetici" },
];

export default function App() {
  const [active, setActive] = useState("search");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Yönetici tokenı yalnızca bellekte; sayfa yenilenince veya çıkışta silinir.
  const [session, setSession] = useState<AdminSession | null>(null);
  // Son kayıp bildiriminin takip kodu; yalnızca bellekte, sekme değişince silinmez.
  const [trackingCode, setTrackingCode] = useState<string | null>(null);

  const loadMeta = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setMeta(await getMeta());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Beklenmeyen bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMeta();
  }, [loadMeta]);

  return (
    <div className="app">
      <header className="header">
        <svg
          className="logo"
          width="44"
          height="44"
          viewBox="0 0 44 44"
          aria-hidden="true"
          focusable="false"
        >
          <rect width="44" height="44" rx="10" fill="#1f3a68" />
          <circle cx="20" cy="20" r="8" fill="none" stroke="#ffffff" strokeWidth="3" />
          <path d="M26 26l8 8" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <div className="header-text">
          <h1>Kampüs Kayıp Eşya</h1>
          <p className="tagline">
            Bulunan eşyaları ve kayıp ilanlarını yapay zekâ ile anlamsal olarak eşleştirerek eşyanı
            bulmana yardım ederiz.
          </p>
          <p className="privacy chip chip-info">
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path
                d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6l8-3z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
              />
              <path d="M8.5 12l2.5 2.5 4.5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Yüzler otomatik bulanıklaştırılır, iletişim bilgisi istenmez.
          </p>
        </div>
      </header>
      <main>
        <Tabs tabs={TABS} active={active} onChange={setActive} />
        <div role="tabpanel" id={`panel-${active}`} aria-labelledby={`tab-${active}`}>
          {loading && <Spinner label="Yükleniyor…" />}
          <ErrorBox message={error} />
          {error && (
            <button className="btn btn-secondary" type="button" onClick={() => void loadMeta()}>
              Tekrar dene
            </button>
          )}
          {meta && active === "search" && (
            <SearchTab meta={meta} trackingCode={trackingCode} onTrackingCode={setTrackingCode} />
          )}
          {meta && active === "found" && <FoundTab meta={meta} />}
          {meta && active === "items" && <ItemsTab />}
          {meta && active === "admin" && (
            <AdminTab session={session} onLogin={setSession} onLogout={() => setSession(null)} />
          )}
        </div>
      </main>
    </div>
  );
}
