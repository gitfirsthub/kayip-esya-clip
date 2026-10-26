# Faz Planı

Zaman çizelgesi: 25 Ekim Paz (Faz 0–3), 26 Ekim Pzt (Faz 4–7), 27 Ekim Salı 15:00'e kadar (Faz 8–9). 17:30 sunum.
Her fazın "Kabul" maddeleri sağlanmadan sonraki faza geçilmez.

## Ortam değişkenleri (tek kaynak; .env.example bununla aynı olur)
BACKEND_PORT=8000
FRONTEND_PORT=3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
VITE_API_URL=http://localhost:8000          # frontend build arg (derleme zamanında gömülür)
DATA_DIR=/data
MODEL_CACHE_DIR=/models
IMAGE_MODEL=clip-ViT-B-32
TEXT_MODEL=sentence-transformers/clip-ViT-B-32-multilingual-v1
FACE_MODEL_PATH=/models/face_detection_yunet_2023mar.onnx
FACE_BLUR_ENABLED=true
FACE_SCORE_THRESHOLD=0.6
MAX_UPLOAD_MB=8
FOUND_DATE_MAX_DAYS=60                       # Faz 8; /api/meta'da da döner
MAX_IMAGE_SIDE=1024
MAX_IMAGE_PIXELS=50000000                    # açılmadan önce reddedilir (Faz 8)
UPLOAD_FORM_OVERHEAD_MB=1                    # gövde sınırı = MAX_UPLOAD_MB + bu pay (Faz 8)
TMP_SIZE=128m                                # compose tmpfs /tmp boyutu (Faz 8)
TORCH_NUM_THREADS=4
MATCH_HIGH=0.37                              # Faz 8 eval ile SEARCH_TEXT_WEIGHT=0.1 için yeniden ayarlandı (docs/EVAL.md; Faz 6: 0.315)
MATCH_MEDIUM=0.31                             # Faz 6: 0.255
MATCH_IMAGE_HIGH=0.87                        # görsel-görsel eşikleri (Faz 8, kullanıcı kararı; docs/EVAL.md)
MATCH_IMAGE_MEDIUM=0.80                      # Faz 7'de bildirim eşleşmesi için eklendi
TAG_MIN_CONFIDENCE=0.35                      # kategori güveni bunun altındaysa "diğer" (Faz 8)
ADMIN_TOKEN=change-me                        # boşsa yönetici uçları kapalı (403); ADMIN_REJECT_WEAK_TOKENS=true iken change-me, ornek-* ve ADMIN_TOKEN_MIN_LEN'den kısa tokenlar yok sayılır (Faz 8)
ADMIN_POINT_TOKENS={}                        # JSON {"<teslim noktası>":"<token>"}; nokta tokenı yalnızca o noktanın ilanlarını yönetir (Faz 7B)
ADMIN_REJECT_WEAK_TOKENS=true                # false yalnızca yerel prototip (Faz 8, kullanıcı kararı)
ADMIN_TOKEN_MIN_LEN=12
OCR_ENABLED=true                             # Faz 7A; false yalnızca geliştirme amaçlı
OCR_LANGS=tur+eng
OCR_MAX_SIDE=1600
OCR_TIMEOUT_S=8
OCR_MIN_CONF=30                              # yalnızca etiket çıkarma; sansür tüm kelimelere bakar (Faz 8)
OMP_THREAD_LIMIT=1                           # tesseract ile torch iş parçacığı çakışmasın
SEARCH_TEXT_WEIGHT=0.1                       # kullanıcı elle denedi ve seçti (Faz 7A eval: 0.0 en güvenli Recall@1, 0.2 Recall@5 yüksek; bkz. docs/EVAL.md)
TAG_BONUS=0.05
TAG_BONUS_MAX=0.10
LOG_LEVEL=INFO

## API sözleşmesi
- GET /health → 200 {"status":"ok","models_loaded":true,"face_blur":true,"ocr":true,"item_count":N,"version":"x.y.z"}; modeller yüklenirken 503 {"status":"loading"}.
- GET /api/meta → {"locations":[...], "dropoff_points":[...], "categories":[...], "colors":[...], "max_upload_mb":8, "found_date_max_days":60}
- POST /api/items (multipart; bulunan eşya kaydı):
  image (zorunlu; jpeg/png/webp; ≤ MAX_UPLOAD_MB), title (3–80 karakter), description (0–500), location (meta.locations'tan), found_date (YYYY-MM-DD, gelecek olamaz, en fazla FOUND_DATE_MAX_DAYS (60) gün geçmiş), dropoff_point (meta.dropoff_points'ten).
  İşlem sırası (Faz 7A ile güncellendi): tür ve boyut doğrulama → Pillow açma ve verify → EXIF transpose → EXIF silme → en uzun kenarı OCR_MAX_SIDE'a küçültülmüş çalışma kopyası → yerel OCR (orijinal pikseller, sansürden önce) → PII tespiti → YuNet yüz bulanıklaştırma + PII kutularını siyah dolu dikdörtgenle kapatma → MAX_IMAGE_SIDE'a küçültme → JPEG (q=85) kaydetme → görsel embedding'i (sansürlü görselden) → zero-shot kategori ve renk etiketi → güvenli marka/model etiketleri → metin embedding'i (başlık + açıklama + etiketler) → SQLite. Yanıt: 201 + Item.
  OCR hata verir, zaman aşımına uğrar veya tesseract yoksa: 503 {"detail":"Görsel gizlilik kontrolünden geçirilemedi, lütfen tekrar deneyin."}, dosya kaydedilmez.
  Item: {id, title, description, location, found_date, dropoff_point, image_url, category, category_score, color, faces_blurred, tags:[str], redacted_regions:int, document_like:bool, status:"bekliyor"|"teslim_edildi", created_at}
- GET /api/items?status=&location=&category=&limit=20&offset=0 → {items:[...], total}; yeniden eskiye.
- GET /api/items/{id} → Item | 404 {"detail":"İlan bulunamadı."}
- POST /api/search (multipart): query (0–200), image (opsiyonel), location (opsiyonel filtre), category (opsiyonel filtre), include_returned (bool, varsayılan false), top_k (1–50, varsayılan 12).
  query ve image'den en az biri zorunlu, yoksa 422 {"detail":"Aramak için bir açıklama yazın veya fotoğraf yükleyin."}.
  İkisi birden varsa: s = 0.5*s_text + 0.5*cos(q_img, item). Faz 7A: s_text = (1-w)*cos(q_text, item_img) + w*cos(q_text, item_text) + etiket bonusu (w = SEARCH_TEXT_WEIGHT; sorgudaki marka/model sözcüğü ilanın etiketiyle eşleşirse eşleşme başına TAG_BONUS, en çok TAG_BONUS_MAX). Yanıt: {results:[{item, score, match_level:"yüksek"|"orta"|"düşük"}], took_ms}. match_level eşikleri (Faz 8): yalnızca metin → MATCH_HIGH/MATCH_MEDIUM; yalnızca görsel → MATCH_IMAGE_HIGH/MATCH_IMAGE_MEDIUM; ikisi birlikte → iki çiftin 0.5/0.5 ortalaması. Görselli bildirim eşleşmelerinin düzeyi de görsel eşikleriyle belirlenir. Arama görseli diske KAYDEDİLMEZ.
- PATCH /api/items/{id}/status  header X-Admin-Token, body {"status":"teslim_edildi"|"bekliyor"} → Item | 403 | 404 (Faz 7B: nokta tokenıyla başka noktanın ilanı da 404)
- DELETE /api/items/{id}  header X-Admin-Token → 204 | 403 | 404 (aynı kapsam kuralı; görsel dosyası da silinir)
- GET /api/admin/me  header X-Admin-Token → {"scope": "<teslim noktası>"|null} | 403 (null = ADMIN_TOKEN, tüm noktalar)
- GET /api/admin/items?status=&limit=20&offset=0  header X-Admin-Token → {items,total}, yalnızca kapsamdaki noktanın ilanları | 403
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
- tagger.py: kategori ve renk istem embedding'leri başlangıçta bir kez hesaplanır ("a photo of a {en}" ve "bir {tr} fotoğrafı" şablonlarının ortalaması, normalize). `tag(img_emb) -> (category, score, color)`; softmax(100*cos) ile güven puanı; kategori güveni < TAG_MIN_CONFIDENCE (0.35) ise "diğer".
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
- Yeni bulunan eşya eklenince açık raporlarla eşleşme hesaplanır ve skor ≥ MATCH_MEDIUM olanlar kaydedilir. (Faz 8: metin skoru aramayla aynı formülle, SEARCH_TEXT_WEIGHT dahil, etiket bonusu hariç; görselli rapor MATCH_IMAGE_* eşikleriyle.)
- GET /api/lost-reports/{code}/matches → eşleşen ilanlar. Frontend'de "Takip kodumla kontrol et" kutusu.
- İletişim bilgisi YOK; bildirim servisi YOK.
Kabul: testler + uçtan uca senaryo (önce rapor, sonra ilan, sonra kodla eşleşme görünür).

## Faz 7A: Kişisel veri (PII) sansürü ve yerel OCR (Opus, ml-engineer agent'ı)
Karar: Tesseract (pytesseract), diller tur+eng. EasyOCR KULLANILMAZ (çalışma zamanı model indirmesi, CPU'da yavaş).
Yeni ortam değişkenleri (.env.example ve config.py): OCR_ENABLED=true, OCR_LANGS=tur+eng, OCR_MAX_SIDE=1600, OCR_TIMEOUT_S=8, OCR_MIN_CONF=30, OMP_THREAD_LIMIT=1 (torch ile iş parçacığı çakışmasın); arama için SEARCH_TEXT_WEIGHT, TAG_BONUS=0.05, TAG_BONUS_MAX=0.10.

Yükleme sırası (backend/app/api/items.py ve ml/):
doğrulama → Pillow açma + EXIF silme → OCR_MAX_SIDE'a küçültülmüş çalışma kopyası → OCR (ORİJİNAL pikseller üzerinde, sansürden ÖNCE) → PII tespiti → yüz bulanıklaştırma + PII kutularını SİYAH DOLU DİKDÖRTGENLE kapatma (Gaussian blur değil; okunabilir kalabilir) → MAX_IMAGE_SIDE'a küçültme → kaydet → embedding SANSÜRLÜ görselden → güvenli etiketler → SQLite.
Ham OCR metni asla loglanmaz, diske yazılmaz, API yanıtında dönmez, hata mesajına girmez.

ml/ocr.py: `run_ocr(img) -> list[Word(text, conf, box, line_id)]` (pytesseract.image_to_data, --oem 1 --psm 11, timeout=OCR_TIMEOUT_S). Gri tonlama + gerekirse 2x büyütme ön işleme. Kutular çalışma kopyası koordinatlarında.
FAIL-CLOSED: OCR hata verir, zaman aşımına uğrar veya tesseract binary'si yoksa yükleme KAYDEDİLMEZ; 503 {"detail":"Görsel gizlilik kontrolünden geçirilemedi, lütfen tekrar deneyin."}. /health'e "ocr": true/false eklenir. Yalnızca OCR_ENABLED=false ise atlanır (geliştirme amaçlı; README'de belirtilir).

ml/pii.py (saf fonksiyonlar, tesseract gerektirmeden test edilebilir):
- Satır içi kayan pencere: aynı line_id'deki ardışık kelimelerin rakamlarını (boşluk, nokta, tire, eğik çizgi ayırıcılarını yok sayarak) birleştir. Rakam benzeri karakter düzeltmesi yalnızca %60+ rakam içeren belirteçlerde: O/o→0, I/l/|→1, S→5, B→8.
- Desenler: TCKN (11 rakam, ilk hane 0 değil; sağlama toplamı yalnızca güven artırır, tutmasa da SANSÜRLE: OCR hatası olabilir), telefon (+90/0/5xx ile başlayan 10–11 hane), e-posta (OCR'ın "@" bozmalarına tolerans), IBAN (TR + 24 hane), kart no (13–19 hane, Luhn), ve GENEL KURAL: 6 ve üzeri ardışık rakam (öğrenci numarası vb.), harf yapışık model kodları hariç (örn. "WH-1000XM4" korunur).
- Öğrenci numarası formatı: GTÜ öğrenci numaraları 12 haneli sayıdır. Genel kuralın bunu kapsadığı testle doğrulanır.
- Belge algılama (`is_document_like`): metinde ≥2 farklı anahtar sözcük (T.C., KİMLİK, SERİ, SOYADI, ADI, DOĞUM, GEÇERLİLİK, ÖĞRENCİ, FAKÜLTE, IDENTITY, STUDENT, UNIVERSITY...) VEYA (yüz bulundu VE ≥8 kelime okundu). Belge benzeriyse görseldeki OKUNAN TÜM METİN KUTULARI sansürlenir (isim ve soyisim regex ile yakalanamaz) ve etiket çıkarılmaz.
- Sansür kutuları 4 px genişletilir; birbirine değen kutular birleştirilir.

Güvenli etiketler (ml/tags.py + backend/app/data/brands.txt):
- Yalnızca İZİN LİSTESİNDEKİ marka/model sözcükleri etiket olur (brands.txt: yaygın ~150 marka; Claude üretir, kullanıcı gözden geçirir) + model kodu deseni (1–4 harf + 2–4 rakam + opsiyonel ek, tamamen rakam olanlar HARİÇ).
- OCR hatasına tolerans: uzunluğu ≥5 olan sözcüklerde difflib ile en fazla 1 karakter fark (yeni bağımlılık YOK).
- Sansürlenen kutularla kesişen kelimeler etiket olamaz. En fazla 8 etiket, küçük harf, tekrarsız.

Şema: Item'a `tags: list[str]`, `redacted_regions: int`, `document_like: bool` (API sözleşmesi yukarıda güncellendi). SQLite'a idempotent `ALTER TABLE ADD COLUMN` (tags JSON metin). POST /api/items yanıtında bunlar döner.
Arama (kullanıcı kararı: yeni metin indeksi + bonus): Mevcut formülde ilanın metni aramada kullanılmıyordu (sorgu metni yalnızca ilan görseliyle karşılaştırılıyordu). İlan için başlık + açıklama + etiketlerden metin embedding'i üretilir ve ayrı matris olarak saklanır (eski ilanlar açılışta doldurulur). s_text = (1-w)*cos(q, ilan_görsel) + w*cos(q, ilan_metin) + bonus; sorgudaki marka/model sözcüğü ilanın etiketleriyle eşleşirse eşleşme başına +0.05, en çok +0.10. w ve eşikler Faz 6 eval'iyle ÖNCE/SONRA ölçülür ve docs/EVAL.md'ye tablo olarak yazılır; Recall@5 düşüyorsa ağırlık değiştirilir veya geri alınır. Kayıp bildirimi eşleşmesi bu fazda değişmez.

Dockerfile (backend): `apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*`, TORCH katmanından ÖNCE ayrı katman; `ENV OMP_THREAD_LIMIT=1`. İmaj internetsiz çalışmalı (--network none testi tekrar edilir). Yerelde tesseract kullanıcı tarafından `brew install tesseract tesseract-lang` ile kurulur.

Testler:
- GERÇEK KİMLİK VERİSİ KULLANILMAZ. Pillow ile sentetik görseller (uydurma numaralar: "12345678901", "05321234567", "ornek@example.com", "TR330006100519786457841326") ve TTF yazı tipi (bulunamazsa ilgili test skip).
- pii.py birim testleri (tesseract gerekmez): boşluklu/noktalı TC, O↔0 karışması, telefon biçimleri, e-posta, IBAN, 6+ rakam, 12 haneli öğrenci no, "WH-1000XM4" korunur, belge algılama.
- Entegrasyon (tesseract yoksa skip): sentetik "CASIO fx-991 + 05321234567" görseli → çıktıda telefon kutusu siyah, etiketlerde "casio", item.redacted_regions ≥ 1; sentetik kimlik benzeri görsel → document_like=true, etiket yok.
- Fail-closed testi: OCR monkeypatch ile hataya düşürülür → 503 ve diske dosya yazılmadı.
- Log testi: caplog içinde rakam dizisi veya e-posta geçmiyor.
- Mevcut tüm testler önce yeşil, sonra yenileriyle birlikte yeşil kalır.

Performans: OCR'lı toplam yükleme süresi ölçülür (hedef: CPU'da tipik fotoğraf ≤ 6 sn, OCR kısmı ≤ 3 sn) ve ILERLEME "Ölçümler"e yazılır. Aşılırsa önce OCR_MAX_SIDE 1280'e indirilir, olmazsa kullanıcıya seçenek sunulur. Frontend zaman aşımı 60 sn kalır.

Elle doğrulama (kullanıcı yapar): backend/scripts/try_redact.py <girdi> <çıktı>; çıktı klasörü (redact_out/) .gitignore'da.
Kabul: testler yeşil; docker build OK; --network none ile çalışıyor; sentetik görsellerde PII kapanıyor; EVAL.md önce/sonra tablosu var; temiz klon testi (/temiz-klon-testi) yeşil; spec-guard raporunda kritik ihlal yok.

## Faz 7B: Frontend görsel cilası
Cilalama fazı (CSS + TSX yapısı; yeni npm paketi yok; sistem yazı tipi; metinler Türkçe).
- Tasarım belirteçleri (renk, 4/8 px boşluk, 5 kademe tipografi, 2 kademe köşe, 2 kademe gölge), başlık çubuğu, segmented sekmeler, kart ızgarası + iskelet yükleme, sürükle-bırak fotoğraf alanı, boş/hata/başarı durumları, mobil (360 px'te yatay kaydırma yok) ve WCAG AA erişilebilirlik.
- Faz 7A alanları (tags, redacted_regions, document_like) arayüzde gösterilir.
- Kullanıcı kararı ile eklendi: **Yönetici sekmesi**. Her teslim noktası kendi tokenıyla (ADMIN_POINT_TOKENS) o noktaya teslim edilen ilanların durumunu değiştirir ("teslim edildi"/"bekliyor") ve sahibine teslim edilen ilanı kaldırır. Token yalnızca tarayıcı belleğinde tutulur. Kimlik doğrulama sistemi DEĞİLDİR (kullanıcı hesabı yok).
- Doğrulama: `npm run build` + `npx tsc --noEmit`; 1440/768/375 px görünümlerini kullanıcı kontrol eder; bir tur geri bildirim.

## Faz 8: Şartname denetimi ve inceleme (Opus)
- spec-guard agent'ı docs/SARTNAME_KONTROL.md'deki her maddeyi kanıtla (dosya:satır veya komut çıktısı) doğrular.
- `/code-review` ve `/security-review` çalıştırılır; bulunan sorunlar düzeltilir veya gerekçesiyle ILERLEME'ye yazılır.
- Hata senaryoları elle denenir: boş form, 30 MB dosya, .pdf yükleme, backend kapalıyken frontend, ilk açılışta model yüklenirken arama.
- `grep -rniE "ultralytics|yolo|openai|anthropic|generativeai" --exclude-dir={node_modules,.git,docs,.claude} --exclude=*.md .` boş çıkmalı.
Kabul: kontrol listesinin tamamı [x]; açık kritik bulgu yok.

## Faz 9: README, AI günlüğü, video, son test (Sonnet; docs-writer agent'ı)
- README.md: en üstte demo video bağlantısı (yer tutucu, kullanıcı dolduracak), problem, çözüm, ekran görüntüsü, mimari şeması (mermaid), yapay zekâ bileşenleri ve neden YOLO değil CLIP (kısa), gizlilik, çalıştırma (`docker compose up --build`, adresler 3000/8000, ilk build süresi ve indirme boyutu uyarısı), ortam değişkenleri tablosu, API özeti, değerlendirme sonuçları (EVAL.md'den), geliştiriciler (kullanıcı dolduracak), "Yapay zekâyı nasıl kullandık" (AI_KULLANIM_GUNLUGU.md'den özet: araçlar, hangi işte, gerçek örnek istemler, elle düzeltilenler, yapay zekânın yanıldığı yerler).
- docs/VIDEO_SENARYOSU.md: 3 dakikalık akış (aşağıdaki 9. bölüm).
- Son temiz klon testi (Faz 5 prosedürü).
Kabul: README şartnamedeki zorunlu bölümlerin hepsini içeriyor; temiz klon testi yeşil.
