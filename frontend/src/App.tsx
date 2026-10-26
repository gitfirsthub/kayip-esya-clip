import { useCallback, useEffect, useState } from "react";
import { getMeta } from "./api";
import FoundTab from "./components/FoundTab";
import ErrorBox from "./components/ErrorBox";
import SearchTab from "./components/SearchTab";
import Spinner from "./components/Spinner";
import Tabs, { type TabDef } from "./components/Tabs";
import type { Meta } from "./types";

const TABS: TabDef[] = [
  { id: "search", label: "Eşyamı Kaybettim" },
  { id: "found", label: "Eşya Buldum" },
];

export default function App() {
  const [active, setActive] = useState("search");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        <h1>Kampüs Kayıp Eşya</h1>
        <p>
          Bulunan eşyaları ve kayıp ilanlarını yapay zekâ ile anlamsal olarak eşleştirerek eşyanı
          bulmana yardım ederiz.
        </p>
        <p className="privacy">Yüzler otomatik bulanıklaştırılır, iletişim bilgisi istenmez.</p>
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
          {meta && active === "search" && <SearchTab meta={meta} />}
          {meta && active === "found" && <FoundTab meta={meta} />}
        </div>
      </main>
    </div>
  );
}
