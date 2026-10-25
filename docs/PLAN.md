# Faz Planı

Zaman çizelgesi: 25 Ekim Paz (Faz 0–3), 26 Ekim Pzt (Faz 4–7), 27 Ekim Salı 15:00'e kadar (Faz 8–9). 17:30 sunum.
Her fazın "Kabul" maddeleri sağlanmadan sonraki faza geçilmez.

## Ortam değişkenleri (tek kaynak; .env.example bununla aynı olur)
BACKEND_PORT=8000
FRONTEND_PORT=3000
CORS_ORIGINS=http://localhost:3000
VITE_API_URL=http://localhost:8000          # frontend build arg (derleme zamanında gömülür)
DATA_DIR=/data
MODEL_CACHE_DIR=/models
IMAGE_MODEL=clip-ViT-B-32
TEXT_MODEL=sentence-transformers/clip-ViT-B-32-multilingual-v1
FACE_MODEL_PATH=/models/face_detection_yunet_2023mar.onnx
FACE_BLUR_ENABLED=true
FACE_SCORE_THRESHOLD=0.6
MAX_UPLOAD_MB=8
MAX_IMAGE_SIDE=1024
TORCH_NUM_THREADS=4
MATCH_HIGH=0.30                              # Faz 6'da eval ile ayarlanacak
MATCH_MEDIUM=0.24
ADMIN_TOKEN=change-me                        # boşsa yönetici uçları kapalı (403)
LOG_LEVEL=INFO

## API sözleşmesi
- GET /health → 200 {"status":"ok","models_loaded":true,"face_blur":true,"item_count":N,"version":"x.y.z"}; modeller yüklenirken 503 {"status":"loading"}.
- GET /api/meta → {"locations":[...], "dropoff_points":[...], "categories":[...], "colors":[...], "max_upload_mb":8}
- POST /api/items (multipart; bulunan eşya kaydı):
  image (zorunlu; jpeg/png/webp; ≤ MAX_UPLOAD_MB), title (3–80 karakter), description (0–500), location (meta.locations'tan), found_date (YYYY-MM-DD, gelecek olamaz, en fazla 60 gün geçmiş), dropoff_point (meta.dropoff_points'ten).
  İşlem sırası: tür ve boyut doğrulama → Pillow açma ve verify → EXIF transpose → EXIF silme → en uzun kenarı MAX_IMAGE_SIDE'a küçültme → YuNet yüz bulanıklaştırma → JPEG (q=85) kaydetme → görsel embedding'i → zero-shot kategori ve renk etiketi → SQLite. Yanıt: 201 + Item.
  Item: {id, title, description, location, found_date, dropoff_point, image_url, category, category_score, color, faces_blurred, status:"bekliyor"|"teslim_edildi", created_at}
- GET /api/items?status=&location=&category=&limit=20&offset=0 → {items:[...], total}; yeniden eskiye.
- GET /api/items/{id} → Item | 404 {"detail":"İlan bulunamadı."}
- POST /api/search (multipart): query (0–200), image (opsiyonel), location (opsiyonel filtre), category (opsiyonel filtre), include_returned (bool, varsayılan false), top_k (1–50, varsayılan 12).
  query ve image'den en az biri zorunlu, yoksa 422 {"detail":"Aramak için bir açıklama yazın veya fotoğraf yükleyin."}.
  İkisi birden varsa: s = 0.5*cos(q_text, item) + 0.5*cos(q_img, item). Yanıt: {results:[{item, score, match_level:"yüksek"|"orta"|"düşük"}], took_ms}. Arama görseli diske KAYDEDİLMEZ.
- PATCH /api/items/{id}/status  header X-Admin-Token, body {"status":"teslim_edildi"|"bekliyor"} → Item | 403
- DELETE /api/items/{id}  header X-Admin-Token → 204 | 403
- /uploads/<dosya>.jpg statik (yalnızca bulanıklaştırılmış kopyalar)
- Hata biçimi her yerde {"detail":"<Türkçe mesaj>"}; 413 (dosya büyük), 415 (tür desteklenmiyor), 400 (görsel açılamadı), 422 (doğrulama), 503 (model yükleniyor), 500 (genel; iz dökümü sızdırılmaz).

## Kampüs verisi (backend/app/data/campus.json; kullanıcı doğrulayacak)
locations: ["Merkez Kütüphane","Merkez Amfi","Yemekhane","Kafeterya","Mühendislik Fakültesi","Temel Bilimler Fakültesi","Mimarlık Fakültesi","Spor Salonu","Ring / Otobüs Durağı","Yurtlar","Diğer"]
dropoff_points: ["Güvenlik Birimi (Ana Kapı)","Öğrenci İşleri","Kütüphane Danışma","Bölüm Sekreterliği"]
categories (zero-shot, TR ad + EN istem): telefon/phone, cüzdan/wallet, anahtar/keys, sırt çantası/backpack, el çantası/handbag, laptop/laptop, tablet/tablet, kulaklık/headphones or earbuds, şarj aleti/charger and cable, su şişesi-termos/water bottle or thermos, mont-ceket/jacket or coat, şemsiye/umbrella, gözlük/glasses, kitap-defter/book or notebook, kart-kimlik/card or ID card, saat/wristwatch, takı/jewelry, hesap makinesi/calculator, diğer/other
colors: siyah, beyaz, gri, kırmızı, mavi, lacivert, yeşil, sarı, turuncu, mor, pembe, kahverengi, bej

---

## Faz 1: Backend iskeleti, /health, Dockerfile (Sonnet)
Dosyalar: backend/app/{__init__,main,config,schemas,errors}.py, backend/requirements.txt, backend/Dockerfile, backend/.dockerignore, backend/scripts/download_models.py, backend/tests/test_health.py, .env.example
- config.py: pydantic-settings Settings (yukarıdaki değişkenler); `get_settings()` ile önbelleğe alınır.
- main.py: FastAPI lifespan; modeller yüklenene kadar app.state.ready=False; CORS (CORS_ORIGINS virgülle ayrılmış); global exception handler (500'de genel Türkçe mesaj, iz dökümü yalnızca loga); request validation handler'ı Türkçe mesaj üretir; docs_url açık kalabilir ama debug=False.
- download_models.py: build sırasında iki sentence-transformers modelini MODEL_CACHE_DIR'e indirir (SentenceTransformer(..., cache_folder=...)), YuNet ONNX'i FACE_MODEL_PATH'e indirir. ONNX kaynağı: https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx. Dosya git-LFS pointer'ı olabilir: boyut < 100 KB ise veya "version https://git-lfs" ile başlıyorsa https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx adresini dene; yine olmazsa build HATA ile dursun (sessizce geçmesin).
- Dockerfile: python:3.12-slim; ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1; torch'u önce `--index-url https://download.pytorch.org/whl/cpu` ile ve venv'dekiyle aynı sürümde kur (ARG TORCH_VERSION); sonra requirements.txt; sonra download_models.py (katman önbelleği için kod COPY'den ÖNCE); en son kod; ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 (indirmeden SONRA); root olmayan kullanıcı; `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`; HEALTHCHECK python urllib ile /health.
- .dockerignore: venv'ler, __pycache__, tests/, data/, .pytest_cache
Kabul: `pytest backend/tests -q` geçer; `docker build -t kayip-backend ./backend` başarılı; `docker run -p 8000:8000 kayip-backend` sonrası /health 200 döner; imajın internetsiz çalıştığı `docker run --network none` ile doğrulanır (model yükleme internet istemez).

## Faz 2: ML çekirdeği (Opus, ml-engineer agent'ı)
Dosyalar: backend/app/ml/{encoder,face_blur,tagger,image_io}.py, backend/app/store.py, backend/app/data/campus.json, backend/tests/test_{image_io,face_blur,store,tagger}.py, backend/scripts/smoke_ml.py
- image_io.py: `load_and_sanitize(bytes) -> PIL.Image` (verify ve yeniden açma, EXIF transpose, RGB'ye çevirme, EXIF'siz, MAX_IMAGE_SIDE'a küçültme); bozuk dosyada `InvalidImageError`. Pillow decompression-bomb koruması açık kalır.
- encoder.py: `ClipEncoder` (image_model, text_model, cache, threads); `encode_images(list[Image]) -> np.ndarray[float32, N×512]` ve `encode_texts(list[str])`, ikisi de normalize; başlangıçta tek bir sahte girdiyle ısınma; torch.set_num_threads; `torch.inference_mode()`. Testler için aynı arayüzde `FakeEncoder` (deterministik hash tabanlı vektörler).
- face_blur.py: `FaceBlurrer(model_path, score_threshold)`; `blur(Image) -> (Image, n_faces)`; YuNet giriş boyutunu her görsele göre setInputSize ile ayarla; kutuyu %20 genişlet; güçlü Gaussian blur (çekirdek kutu boyutuna oranlı, tek sayı) ve pikselleştirme. Model yoksa veya FACE_BLUR_ENABLED=false ise uygulama ÇÖKMEZ; /health'te face_blur=false raporlanır ve log uyarısı yazılır.
- tagger.py: kategori ve renk istem embedding'leri başlangıçta bir kez hesaplanır ("a photo of a {en}" ve "bir {tr} fotoğrafı" şablonlarının ortalaması, normalize). `tag(img_emb) -> (category, score, color)`; softmax(100*cos) ile güven puanı; kategori güveni < 0.35 ise "diğer".
- store.py: SQLite (WAL); items tablosu (PLAN'daki Item alanları + embedding BLOB); thread-safe yazma kilidi; bellekte (N×512) matris ve id listesi; `add`, `get`, `list`, `update_status`, `delete`, `search(vec, filters, top_k)`, yani numpy dot + filtre maskesi + argpartition.
- smoke_ml.py: venv'de gerçek modellerle hızlı kontrol: 3 sahte renkli görsel ve 3 Türkçe sorgu; süreleri ve benzerlik matrisini yazdırır.
Kabul: testler geçer; smoke_ml.py venv'de çalışır; tek görsel kodlama CPU'da < 1 sn; "siyah sırt çantası" sorgusu, kullanıcının çektiği bir sırt çantası fotoğrafında en üst 3'te (kullanıcı fotoğrafları yoksa bu kontrol Faz 6'ya ertelenir ve ILERLEME'ye not düşülür).

## Faz 3: API uçları, doğrulama, testler (Sonnet)
Dosyalar: backend/app/api/{items,search,meta,admin}.py, backend/app/deps.py, backend/tests/test_api_*.py
- PLAN'daki sözleşme birebir uygulanır. Ağır CPU işleri (encode, blur) `run_in_threadpool` ile çalışır; event loop bloklanmaz.
- Yükleme boyutu stream okunurken sınırlanır (MAX_UPLOAD_MB aşılınca 413). İçerik türü yalnızca başlıktan değil Pillow formatından da doğrulanır.
- Yönetici uçları `secrets.compare_digest` ile token karşılaştırır; ADMIN_TOKEN boşsa 403.
- Testler FakeEncoder ve geçici DATA_DIR ile FastAPI dependency override kullanır: başarılı yükleme, görselsiz yükleme 422, metin dosyası 415, bozuk jpeg 400, büyük dosya 413, gelecek tarih 422, boş arama 422, metinle arama sonuç döner, görselle arama sonuç döner, filtreler, admin 403/200, 404'ler, model hazır değilken 503.
Kabul: `pytest -q` tamamı yeşil; docker imajıyla curl üzerinden bir yükleme ve bir arama elle denenir ve çıktılar ILERLEME'ye yazılır.

## Faz 4: Frontend (Sonnet, frontend-dev agent'ı)
Dosyalar: frontend/{package.json,vite.config.ts,tsconfig.json,index.html,Dockerfile,nginx.conf,.dockerignore}, frontend/src/{main.tsx,App.tsx,api.ts,types.ts,styles.css}, frontend/src/components/*
- Üç sekme: "Eşyamı Kaybettim" (varsayılan), "Eşya Buldum", "Tüm İlanlar". Üst kısımda tek cümlelik açıklama ve gizlilik notu ("Yüzler otomatik bulanıklaştırılır, iletişim bilgisi istenmez").
- Eşyamı Kaybettim: metin kutusu (örnek yer tutucu: "lacivert termos, üzerinde çıkartma var"), opsiyonel fotoğraf, yer ve kategori filtreleri; sonuç kartları: görsel, başlık, yer, tarih, teslim noktası, eşleşme seviyesi rozeti ve benzerlik çubuğu. Sonuç yoksa yönlendirici boş durum mesajı.
- Eşya Buldum: form (fotoğraf önizlemesi, başlık, açıklama, yer, tarih [varsayılan bugün], teslim noktası). Gönderince sonuç kartı: otomatik kategori ve renk etiketi, "N yüz bulanıklaştırıldı" bilgisi.
- Tüm İlanlar: sayfalı liste ve durum filtresi.
- Her istekte yükleniyor göstergesi ve düğmenin devre dışı kalması; hata mesajları API'nin `detail` alanından gösterilir; ağ hatasında "Sunucuya ulaşılamadı" mesajı; 503'te "Model yükleniyor, birkaç saniye sonra tekrar deneyin". İstemci tarafında dosya türü ve boyut ön kontrolü.
- API adresi yalnızca `import.meta.env.VITE_API_URL` üzerinden alınır. Dockerfile'da ARG/ENV VITE_API_URL; çok aşamalı build (node:20-alpine → nginx:alpine); nginx.conf SPA fallback ve gzip içerir.
- Erişilebilirlik: label'lar, alt metinler, klavyeyle gezinme. Mobil uyumlu (tek sütun, 16 px kenar boşluğu). UI kütüphanesi YOK, düz CSS.
Kabul: `npm run build` hatasız; `tsc` hatasız; nginx imajı build olur; kullanıcıya görünen bütün metinler Türkçe.

## Faz 5: Compose entegrasyonu ve temiz klon testi (Sonnet, docker-tester agent'ı)
Dosyalar: docker-compose.yml, .env.example (son hali)
- services.backend: build ./backend (args TORCH_VERSION), ports "${BACKEND_PORT:-8000}:8000", env_file .env (required: false), environment varsayılanları, volume app_data:/data, healthcheck (interval 10s, start_period 120s), restart unless-stopped.
- services.frontend: build ./frontend (args VITE_API_URL: ${VITE_API_URL:-http://localhost:8000}), ports "${FRONTEND_PORT:-3000}:80", depends_on backend condition service_healthy, restart unless-stopped.
- volumes: app_data.
- Temiz klon testi: depoyu geçici bir klasöre `git clone` ile kopyala, `.env` OLMADAN `docker compose up --build -d`, health bekle, curl ile meta, yükleme ve arama dene, `docker compose down -v`. Build süresi ve imaj boyutlarını ILERLEME'ye yaz.
Kabul: temiz klonda tek komutla çalışıyor; http://localhost:3000 açılıyor ve uçtan uca yükleme+arama tarayıcıda çalışıyor (kullanıcı tarayıcıda doğrular).

## Faz 6: Demo verisi ve retrieval değerlendirmesi (Opus, ml-engineer agent'ı)
Dosyalar: demo_data/items.json, demo_data/queries.json, backend/scripts/seed_demo.py, backend/scripts/eval_retrieval.py, docs/EVAL.md
- Kullanıcı fotoğraflarını demo_data/raw/ altına koyar (git'e girmez). seed_demo.py fotoğrafları küçültür (≤ 1024 px), demo_data/images/ altına yazar (bu klasör commit'lenebilir; toplam < 15 MB) ve items.json'daki meta ile API'ye POST eder.
- queries.json: her eşya için kullanıcının yazdığı 1–2 doğal Türkçe sorgu ve beklenen item anahtarı; varsa ikinci açıdan çekilmiş fotoğrafla görsel sorgu.
- eval_retrieval.py (çalışan API üzerinden): Recall@1, Recall@5, MRR; metin ve görsel sorgu ayrı ayrı; Türkçe ve İngilizce çeviri sorgu karşılaştırması; skor dağılımına bakarak MATCH_HIGH ve MATCH_MEDIUM önerisi. Sonuçlar docs/EVAL.md'ye tablo olarak yazılır.
- Sonuçlar zayıfsa (Recall@5 < 0.7) sırasıyla dene ve her denemeyi EVAL.md'ye yaz: sorgu şablonu ("bir fotoğraf: {q}"), kategori filtresi önerisi, metin+görsel füzyon ağırlığı. Model DEĞİŞTİRME (kullanıcıya sorulmadan).
Kabul: EVAL.md'de gerçek sayılar var; eşikler .env.example'da güncel.

## Faz 7: (Ek, yalnızca Faz 1–6 tamamsa) Kayıp bildirimi ve otomatik eşleşme
- POST /api/lost-reports (query metni + opsiyonel görsel, yer, tarih) → {tracking_code} (8 karakter, tahmin edilemez). Rapor embedding'i saklanır; görsel saklanmaz.
- Yeni bulunan eşya eklenince açık raporlarla eşleşme hesaplanır ve skor ≥ MATCH_MEDIUM olanlar kaydedilir.
- GET /api/lost-reports/{code}/matches → eşleşen ilanlar. Frontend'de "Takip kodumla kontrol et" kutusu.
- İletişim bilgisi YOK; bildirim servisi YOK.
Kabul: testler + uçtan uca senaryo (önce rapor, sonra ilan, sonra kodla eşleşme görünür).

## Faz 8: Şartname denetimi ve inceleme (Opus)
- spec-guard agent'ı docs/SARTNAME_KONTROL.md'deki her maddeyi kanıtla (dosya:satır veya komut çıktısı) doğrular.
- `/code-review` ve `/security-review` çalıştırılır; bulunan sorunlar düzeltilir veya gerekçesiyle ILERLEME'ye yazılır.
- Hata senaryoları elle denenir: boş form, 30 MB dosya, .pdf yükleme, backend kapalıyken frontend, ilk açılışta model yüklenirken arama.
- `grep -rniE "ultralytics|yolo|openai|anthropic|generativeai" --exclude-dir={node_modules,.git,docs} --exclude=*.md .` boş çıkmalı.
Kabul: kontrol listesinin tamamı [x]; açık kritik bulgu yok.

## Faz 9: README, AI günlüğü, video, son test (Sonnet; docs-writer agent'ı)
- README.md: en üstte demo video bağlantısı (yer tutucu, kullanıcı dolduracak), problem, çözüm, ekran görüntüsü, mimari şeması (mermaid), yapay zekâ bileşenleri ve neden YOLO değil CLIP (kısa), gizlilik, çalıştırma (`docker compose up --build`, adresler 3000/8000, ilk build süresi ve indirme boyutu uyarısı), ortam değişkenleri tablosu, API özeti, değerlendirme sonuçları (EVAL.md'den), geliştiriciler (kullanıcı dolduracak), "Yapay zekâyı nasıl kullandık" (AI_KULLANIM_GUNLUGU.md'den özet: araçlar, hangi işte, gerçek örnek istemler, elle düzeltilenler, yapay zekânın yanıldığı yerler).
- docs/VIDEO_SENARYOSU.md: 3 dakikalık akış (aşağıdaki 9. bölüm).
- Son temiz klon testi (Faz 5 prosedürü).
Kabul: README şartnamedeki zorunlu bölümlerin hepsini içeriyor; temiz klon testi yeşil.
