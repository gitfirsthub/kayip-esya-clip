# İlerleme

| Faz | Durum | Tarih | Not |
|---|---|---|---|
| 0 Kurulum | ✅ | 2026-10-25 | Kurallar, plan, hook'lar, agent'lar ve komutlar eklendi; venv: `.venv` (Python 3.12.10); hook ve commit-msg testleri geçti |
| 1 Backend iskeleti | ✅ | 2026-10-26 | /health, hata yakalayıcılar, model indirme betiği ve Dockerfile eklendi; 6 test geçti; imaj internetsiz ayağa kalktı |
| 2 ML çekirdeği | ✅ | 2026-10-26 | image_io, ClipEncoder/FakeEncoder, YuNet yüz bulanıklaştırma (kapalı-güvenli), tagger, SQLite deposu + vektör arama, smoke ve try_blur betikleri; 44 test geçti; imaj internetsiz açılıyor (face_blur=true). "siyah sırt çantası top-3" kontrolü Faz 6'ya ertelendi (demo_data yok) |
| 3 API | ✅ | 2026-10-26 | /api/meta, /api/items (POST/GET/liste), /api/search, admin PATCH/DELETE, /uploads statik; 83 test geçti; imaj gerçek modelle curl ile denendi (aşağıdaki Ölçümler) |
| 4 Frontend | ✅ (tarayıcı kontrolü kullanıcıda) | 2026-10-26 | React 19.3.1 + Vite 8.3.5 + TS 7.0.2; üç sekme (arama, yükleme, liste); `npm run build` ve `tsc` hatasız; nginx imajı build oldu, SPA fallback 200; backend ile CORS preflight geçti; spec-guard kritik ihlal yok |
| 5 Compose | ✅ (tarayıcı kontrolü kullanıcıda) | 2026-10-26 | docker-compose.yml (PLAN tanımı), .env.example notları; `.env`siz temiz klonda tek komutla ayağa kalktı; meta/yükleme/arama curl ile geçti; amd64 backend build'i başarılı; spec-guard kritik kod ihlali yok |
| 6 Eval | ✅ | 2026-10-26 | 21 ilan + 42 TR/42 EN metin + 7 görsel sorgu; seed_demo.py, eval_retrieval.py, EVAL.md; TR metin R@5 0.857 / R@1 0.524; eşikler 0.315/0.255; 83 test geçti; spec-guard kritik ihlal yok |
| 7 Ek: kayıp bildirimi | ✅ (tarayıcı kontrolü kullanıcıda) | 2026-10-26 | POST /api/lost-reports, GET /api/lost-reports/{kod}/matches, yeni ilanla otomatik eşleşme, "Takip kodumla kontrol et" kutusu; 98 test geçti; tsc ve build hatasız; spec-guard kritik ihlal yok |
| 8 Denetim | ⬜ | | |
| 9 Dokümantasyon | ⬜ | | |

## Açık sorular (kullanıcıya)
- campus.json'daki yer isimleri GTÜ'ye uygun mu?

## Notlar
- Faz 2 doğrulaması tamamlandı: kullanıcı try_blur.py ile kendi yüzünde denedi, yüz tamamen bulanıklaştı. Commit'lerin 5 güne yayılma şartı kullanıcı kararıyla dikkate alınmıyor.
- Faz 2 kararları (kullanıcı onaylı): aynı-uzay doğrulaması dokulu sentetik nesnelerle yapıldı (düz beyaz kare CLIP'in kendi İngilizce kodlayıcısında da başarısız; görsel kodlayıcı sınırlaması). "diğer" kategorisi istem matrisinden çıkarıldı, yalnızca güven < 0.35'te dönen yedek etiket. `backend/scripts/try_blur.py` kullanıcının isteğiyle eklendi (PLAN dosya listesi dışında). `.gitignore`'da `data/` → `/data/` (campus.json takip edilsin diye).
- Faz 2: model yüklüyken yüz tespiti hata verirse `FaceBlurError` fırlatılır (görsel bulanıklaştırılmadan geçmez).
- Faz 2 commit'leri kod paralel yazıldıktan sonra adım adım (her biri kendi testiyle) ama kısa aralıkla atıldı; spec-guard bunu "toplu commit" gibi görünebilir diye uyardı. Sonraki fazlarda her adım bitince hemen commit atılacak.
- Faz 8'deki yasaklı kelime grep'i `.claude/hooks/spec_guard.py` dosyasını da yakalar (yasak listesi o dosyada). Faz 8'de `--exclude-dir=.claude` eklenmesi kullanıcıya sorulacak.

- Faz 3 kararları (kullanıcı onaylı): yüz modeli yokken POST /api/items 503 döner (bulanıklaştırılmamış görsel saklanmaz); image_url göreli `/uploads/<uuid>.jpg`; geçersiz location/category/status filtresi 422; sözleşmede olmayan hata metinleri (413, 415, 403, 503, alan 422'leri) onaylanan Türkçe metinlerle uygulandı. Tarih kontrolü Türkiye saatiyle (UTC+3) yapılır. Aramada geçersiz `include_returned` / `top_k` 422 döner. Test görselleri Pillow ile kodda üretilir.

- Faz 4 kararları: `@types/react` ve `@types/react-dom` (yalnızca tip paketleri) kullanıcı onayıyla eklendi. Sürümler `^` olmadan sabit. Arama `top_k` ve `include_returned` göndermiyor (varsayılanlar: 12, false); teslim edilmiş ilanlar yalnızca Tüm İlanlar'da görünür. Sekme değişince form durumu sıfırlanır. Dockerfile'da `ARG VITE_API_URL` varsayılanı `http://localhost:8000`; Faz 5'te compose build arg olarak geçirecek.

- Faz 5 kararları: compose'ta `BACKEND_PORT` yalnızca host portunu belirler (konteyner içi 8000 sabit). `HF_HUB_OFFLINE` ve `TRANSFORMERS_OFFLINE` compose `environment` bloğunda sabit "1" (spec-guard uyarısı; `.env` ezemesin diye). `tmpfs: /tmp` (Fikir Havuzu) HENÜZ eklenmedi, onay bekliyor. Frontend nginx'inde `/api` proxy'si YOK; tarayıcı API'ye doğrudan `VITE_API_URL` ile gider (docker-tester'ın "nginx üzerinden 200" bulgusu SPA fallback'ti, yanlış okumaydı).

- Faz 6 kararları: İlk demo seti internetten alınmıştı (Reddit r/LostAndFound ekran görüntüleri, katalog görselleri, yüz+isim+TC no içeren kartlar); tespit edildi, kullanılmadı, kullanıcı yeni fotoğrafları kendi çekti. raw/'da eski setten 4 dosya hâlâ duruyor (kullanılmıyor, git'e girmiyor; kullanıcının silmesi önerildi). `09.39.09 (1)` isim okunduğu için hariç. Sigara paketi + çakmak ve anahtar kodu görünen anahtarlar kullanıcı kararıyla sette tutuldu. Sorguları yapay zekâ yazdı, kullanıcı tek tek gözden geçirmedi. Seed/eval taslağı ayrıca onaylatılmadan çalıştırıldı (kullanıcı "seed/eval'i tamamla" dedi). "siyah sırt çantası top-3" kontrolü uygulanamadı (sette siyah sırt çantası yok).
- Faz 6 açık konular (kullanıcıya): (a) YuNet saat kadranını yüz sandı (`watch_green_dial` bulanık); (b) API metin ve görsel arama için ortak eşik kullanıyor, görsel aramada yanlış ilanlar da "yüksek" görünüyor; (c) spec-guard: `earbud_case_white_open` ve `queries/094013_3` görsellerinde belirgin el var; `ballpoint_pen_white` üzerindeki baskı yazısının kişi/kullanıcı adı olmadığı doğrulanmalı.

- Faz 7 kararları (kullanıcı onaylı, plan modunda): takip kodu 31 harfli karışmayan alfabeyle (`secrets.token_urlsafe` süzülerek) 8 karakter, DB'de yalnızca SHA-256 özeti. Görsel bildirimler için ayrı eşik `MATCH_IMAGE_MEDIUM=0.80` eklendi (Fikir Havuzu maddesi onaylandı; yalnızca bildirim eşleşmesinde kullanılır, `/api/search` değişmedi). 0.80 GEÇİCİ: EVAL'de doğru görsel 0.759–0.953, en iyi yanlış 0.726–0.866, n=7. Bildirim oluşturulurken mevcut ilanlar da taranır. Bildirimde isteğe bağlı `location` filtresi plan onayıyla eklendi. Metin ve görsel embedding'i ayrı saklanır; eşleşme = metin ≥ MATCH_MEDIUM VEYA görsel ≥ MATCH_IMAGE_MEDIUM. Eşleştirme hatası ilan kaydını bozmaz (loglanır). Bildirim görseli diske yazılmaz.
- Faz 7 kullanıcı kararları (tarayıcı testinden sonra): `tmpfs: /tmp` compose'a eklendi; "Eşyamı Kaybettim" sekmesine kişisel veri uyarısı eklendi; bildirimlerde süre aşımı/silme olmaması README'de belirtilecek (README henüz yok, Faz 9'da `docs-writer`'a not: gizlilik bölümüne "bildirimler ve embedding'leri süresiz saklanır, silme/TTL yoktur" yazılacak).
- Faz 7 spec-guard notları: (a) `/tmp` spool açığı: tmpfs ile kapatıldı. (b) `query_text` serbest metin; kullanıcı telefon yazarsa saklanır, arayüzde uyarı/maskeleme PLAN dışı, sorulacak. (c) Bildirimler süresiz saklanır, silme/TTL ucu yok; README'de belirtilecek. (d) `/matches` için hız sınırı yok (alan ~8,5e11).

## Fikir Havuzu (kapsam dışı, onay bekleyen)
- Faz 6: görsel arama için ayrı eşik (MATCH_IMAGE_HIGH/MEDIUM) (Faz 7'de yalnızca bildirim eşleşmesi için MATCH_IMAGE_MEDIUM uygulandı, `/api/search` hâlâ ortak eşik); görsel skorlar 0.73–0.95 arasında, metin eşikleri anlamsız kalıyor. API değişikliği, onay gerekir.
- Faz 5 spec-guard notları: (a) `.env.example` içindeki `ADMIN_TOKEN=change-me` tahmin edilebilir; README'de `openssl rand -hex 16` önerisi (Faz 9) veya backend'in `change-me`yi reddetmesi. (b) YuNet indirmesine SHA-256 doğrulaması. (c) Frontend servisine healthcheck. (d) `VITE_API_URL` derleme zamanında gömülür; değiştirmek için yeniden build gerekir, README'ye yazılacak (Faz 9).
- Faz 3 spec-guard uyarısı (CLAUDE.md madde 6): Starlette `UploadFile` 1 MB üstü yüklemeleri sistem tmp'sine (`SpooledTemporaryFile`) yazabilir; bu geçici kopya bulanıklaştırılmamış olabilir. Kodda ele alınmadı. Öneri: Faz 5'te compose'a `tmpfs: /tmp` ekle (kalıcı diske hiç yazılmaz), README'ye bilinen sınırlama olarak yaz. Kullanıcı onayı bekliyor.
- Faz 3 spec-guard notu: `ADMIN_TOKEN=change-me` örnek değerdir; README'de değiştirilmesi gerektiği yazılacak (Faz 9).
- Faz 5: BACKEND_PORT backend'de okunmuyor (CMD 8000 sabit); compose'da portu eşle veya .env.example'dan çıkar (spec-guard notu).

## Ölçümler (build süresi, imaj boyutu, gecikmeler)
- Faz 7 temiz klon (commit 79d0e56, `.env`siz, M4 Pro, docker-tester; 8000/3000 dolu olduğundan BACKEND_PORT=18000, FRONTEND_PORT=13000, VITE_API_URL ile): `build --no-cache` 336 sn; `up -d` ~11 sn, /health ilk denemede ok, restart sonrası 6 sn. İmajlar: backend 4.11 GB, frontend 93.6 MB; bellek backend 457 MiB. Gecikmeler: /api/meta 6 ms; POST /api/items 88–119 ms (eşleştirme dahil); metin arama 27–33 ms; görsel arama 72–77 ms; POST /api/lost-reports metin 37–41 ms, görselli 97 ms. Uçtan uca GEÇTİ: rapor → kod (8 karakter, yasak karakter yok) → ilan ekle → /matches'te görünür (mavi şemsiye 0.3161 yüksek, kırmızı 0.2759 orta, gri çanta eşleşmedi); ilanlar varken yeni rapor anında eşleşti; geçersiz kod 422, bilinmeyen 404, küçük harf kabul; restart sonrası rapor ve eşleşmeler korundu. Görselli rapor: mavi 1.0, kırmızı 0.9396 eşleşti, gri çanta 0.596 elendi (0.80 eşiği).
- Faz 7 bulgusu: `/api/search` görsel aramada hâlâ metin eşiklerini kullanıyor; üç ilan da (alakasız gri çanta 0.596 dahil) "yüksek" etiketi aldı. Bildirim eşleşmesi ayrı eşik kullandığı için etkilenmedi. Fikir Havuzu maddesi aynen duruyor, `/api/search` değiştirilmedi.
- Faz 5 (Apple M4 Pro, Docker 8 GB): temiz klonda `docker compose build --no-cache` 216 sn (soğuk, torch + modeller inerek); `buildx --platform linux/amd64 ./backend` 235 sn, x86_64 torch tekerleği (`manylinux_2_28_x86_64`) indi, YuNet indi; amd64 imajı ÇALIŞTIRILMADI (yalnızca build). İmajlar: backend 4.11 GB (sıkıştırılmış ~1.34 GB), frontend 93.6 MB.
- Faz 5 temiz klon (`.env`siz, önbellekli build 7.8 sn): /health ilk denemede ok; /api/meta 12 ms; POST /api/items 201 116 ms (şemsiye 0.997, mavi); metinle arama 37 ms (skor 0.323 yüksek), görselle arama 75 ms (skor 1.0); backend restart sonrası item_count korundu (app_data); kullanıcı uid 10001; HF_HUB_OFFLINE=1.
- Faz 4: frontend imajı 93.6 MB (nginx:alpine + dist); derlenmiş JS 234.9 kB (gzip 73.3 kB), CSS 3.8 kB.
- Faz 1: ilk backend build'i 223 sn (torch CPU + 2 model + YuNet indirme); imaj 4.11 GB (chown katmanı kaldırıldıktan sonra; öncesi 6.16 GB). Kod değişikliğiyle yeniden build 1 sn, model katmanı CACHED.
- Faz 1: `docker run --network none` ile /health 200 (`docker exec` ile doğrulandı; `--network none` ile host portu yayınlanamaz); ağlı çalıştırmada localhost:8000/health 200, models_loaded=true, face_blur=true.
- Faz 1 notu: `check_models` açılışta modelleri yükleyip atıyor (yavaş açılış); Faz 2'de encoder yüklemesine taşınacak. item_count şimdilik sabit 0.
- Faz 2 (Apple M4 Pro, 12 çekirdek, 24 GiB, macOS arm64, torch 2.14.1, TORCH_NUM_THREADS=4; smoke_ml.py):
  - ClipEncoder yükleme (iki model + ısınma): 3374 ms; modeller yüklendikten sonra tepe RSS 1028 MB.
  - Tek görsel kodlama (1024×768, ısınma sonrası 10 tekrar): ort 34.1 ms, maks 35.1 ms (hedef < 1 sn).
  - load_and_sanitize (4000×3000 JPEG → 1024): ort 146.6 ms. Tek metin kodlama: ort 24.6 ms.
  - 1000 öğede arama (top_k=12, 100 tekrar): ort 0.27 ms, maks 0.56 ms; filtreli 0.06 ms (hedef < 300 ms). Metin kodlama + arama: ort 25.2 ms.
  - Uygulama açılışı (venv, TestClient): /health 200'e 4.6 sn. Docker `--network none`: 7 sn'de 200, face_blur=true.
  - Şablon karşılaştırması (13 renkte dokulu sentetik nesne, renk doğruluğu): tr 9/13, en 10/13, avg 11/13 → avg seçildi.
  - Faz 3 (docker, gerçek modeller, sentetik mavi şemsiye görseli, M4 Pro): `POST /api/items` 201, 0.149 sn, kategori=şemsiye (0.9996), renk=mavi, faces_blurred=0. `POST /api/search -F "query=mavi şemsiye"` 200, skor 0.3183 → "yüksek", took_ms 26.2. Aynı görselle arama: skor 1.0, took_ms 73.2. "siyah sırt çantası" sorgusu aynı ilana 0.2124 → "düşük". Boş arama 422 sözleşme metni; token'sız DELETE 403.
- Faz 6 (M4 Pro, docker, gerçek modeller, 21 ilan): metin arama took_ms medyan ~29 ms, görsel ~73 ms, en yüksek 79 ms. TR metin R@1/R@5/MRR 0.524/0.857/0.657; EN 0.595/0.857/0.717; görsel (n=7) 0.857/1.000/0.886. demo_data/images 4.6 MB (28 JPEG, ≤1024 px, EXIF yok).
