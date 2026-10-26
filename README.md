TODO(kullanıcı): video bağlantısı

# Kampüs Kayıp Eşya

GTÜ kampüsünde bulunan eşyaları, kaybeden kişiyle anlamsal arama ile buluşturan web uygulaması. Yüzleri otomatik bulanıklaştırır ve tamamen yerelde, CPU üzerinde çalışır.

## Problem

Kampüste bulunan eşyalar çoğu zaman bulunduğu yerde kalır. Eşyayı bulan kişi ile kaybeden kişinin buluşması için genellikle ortak ve aranabilir bir kayıt yoktur.

## Çözüm

- Bulan kişi eşyanın fotoğrafını, yerini, tarihini ve teslim noktasını girer. Eşyanın kategorisi ve rengi otomatik etiketlenir; yüzler bulanıklaştırılır.
- Kaybeden kişi Türkçe bir açıklama ya da fotoğrafla arama yapar. Sonuçlar eşleşme düzeyiyle (yüksek, orta, düşük) listelenir.
- Kaybeden kişi kayıp bildirimi bırakır ve bir takip kodu alır. Yeni eklenen eşyalar bu bildirimle eşleşirse kodla kontrol edilebilir.
- İletişim bilgisi istenmez; eşya bir teslim noktasına bırakılır.

## Ekran görüntüsü

TODO(kullanıcı): docs/screenshot.png

## Mimari

```mermaid
flowchart LR
    B["Tarayıcı"]

    subgraph FE["frontend konteyneri (nginx:alpine, 3000 → 80)"]
        N["nginx: React + Vite derlenmiş statik dosyalar<br/>/api proxy'si yok"]
    end

    subgraph BE["backend konteyneri (FastAPI + uvicorn, 8000)"]
        API["main.py, api/*.py<br/>items, search, lost_reports, admin, meta, uploads"]
        subgraph ML["ml/"]
            ENC["encoder.py<br/>CLIP görsel + çok dilli metin encoder"]
            BLUR["face_blur.py<br/>YuNet yüz bulanıklaştırma"]
            OCR["ocr.py + pii.py<br/>Tesseract OCR, PII sansürü"]
            TAG["tagger.py + tags.py<br/>zero-shot kategori/renk, marka/model etiketi"]
        end
        DB[("SQLite app.db<br/>embedding BLOB")]
        UP["uploads/uuid.jpg<br/>yalnızca bulanıklaştırılmış JPEG"]
    end

    B -->|"sayfa (localhost:3000)"| N
    B -->|"API çağrıları (VITE_API_URL, 8000)"| API
    API --> BLUR
    API --> OCR
    API --> ENC
    OCR -.->|"OCR kelimeleri"| TAG
    API --> TAG
    API --> DB
    API --> UP
```

- Tarayıcı sayfayı nginx'ten (3000), API çağrılarını doğrudan FastAPI'ye (8000) yapar. nginx'te `/api` proxy'si yoktur; API adresi `VITE_API_URL` ile derleme zamanında gömülür.
- Yükleme hattı: EXIF temizliği, OCR, YuNet bulanıklaştırma, PII sansürü, JPEG kaydı, CLIP embedding, zero-shot etiketleme, SQLite. OCR hata verirse yükleme kaydedilmez.
- Orijinal görsel hiçbir aşamada diske yazılmaz. Aramada ve kayıp bildiriminde görsel kaydedilmez; embedding'ler başlangıçta bellekte matrise yüklenir.
- Model ağırlıkları build sırasında iner; çalışma zamanında `HF_HUB_OFFLINE=1` tanımlıdır ve bulut servisi çağrılmaz.

## Yapay zekâ bileşenleri ve neden YOLO değil CLIP

- **Görsel embedding:** `clip-ViT-B-32` (512 boyut). İlan ve arama görsellerini vektöre çevirir.
- **Çok dilli metin embedding:** `sentence-transformers/clip-ViT-B-32-multilingual-v1` (Türkçe dahil). Görsel encoder ile aynı vektör uzayında çalışır.
- **Zero-shot kategori ve renk etiketi:** Görsel vektörü ile metin istemleri arasındaki benzerlikten kategori ve renk seçilir. Kategori güveni `TAG_MIN_CONFIDENCE` altındaysa "diğer" olur.
- **Yüz tespiti:** OpenCV YuNet (`face_detection_yunet_2023mar.onnx`). Tespit edilen yüzler bulanıklaştırılır.
- **OCR:** Tesseract (`tur+eng`). Metin tabanlı kişisel verileri kapatır ve izin listesindeki marka/model sözcüklerinden etiket çıkarır.

Hepsi yerelde ve CPU üzerinde çalışır. Bulut yapay zekâ servisi çağrılmaz; çalışma zamanında `HF_HUB_OFFLINE=1` tanımlıdır.

Neden YOLO değil CLIP: YOLO, eğitildiği sabit nesne sınıflarını tanıyan bir dedektördür. Listede olmayan bir eşyayı tanımaz ve serbest metinle sorgulanamaz. CLIP ise metni ve görseli aynı uzayda karşılaştırır; bu sayede "lacivert termos, üzerinde çıkartma var" gibi serbest ve Türkçe sorgularla arama yapılabilir. Projede YOLO ailesinden hiçbir model ya da paket yoktur.

## Gizlilik

- Yüklenen görsellerden EXIF verisi (GPS dahil) silinir.
- Yüzler YuNet ile tespit edilir ve bulanıklaştırılır.
- Orijinal görsel diske yazılmaz; saklanan yalnızca bulanıklaştırılmış ve küçültülmüş kopyadır.
- OCR ile bulunan TC kimlik, telefon, e-posta, IBAN, kart numarası ve 6 ve üzeri ardışık rakamlar görselde siyah dolu dikdörtgenle kalıcı olarak kapatılır. Belge benzeri görsellerde okunan tüm metin kapatılır.
- Ham OCR metni loglanmaz, diske yazılmaz ve API yanıtında dönmez. OCR hata verirse ya da zaman aşımına uğrarsa yükleme kaydedilmez (503).
- Arama görseli ve kayıp bildirimi görseli diske kaydedilmez.
- Telefon, e-posta veya isim gibi iletişim bilgisi toplanmaz.
- Kayıp bildirimi metnine kişisel veri yazılmamalıdır. Bu metin olduğu gibi saklanır ve maskelenmez.
- Bildirimler ve embedding'ler süresiz saklanır. Silme veya süre aşımı (TTL) yoktur.
- Bilinen sınırlar:
  - OCR'ın okuyamadığı yazı sansürlenmez.
  - `OCR_ENABLED=false` yalnızca geliştirme içindir; bu durumda metin tabanlı kişisel veri sansürlenmez.
  - Yüz tespiti yanlış pozitif verebilir (demo verisinde bir saat kadranı yüz sayılmış ve bulanıklaştırılmıştır).
  - Compose dışında, örneğin `docker run` ile çalıştırıldığında geçici dosyalar konteyner katmanına yazılabilir. Compose'ta `/tmp` bellekte (tmpfs) tutulur.

## Çalıştırma

```
docker compose up --build
```

- Arayüz: http://localhost:3000
- API: http://localhost:8000 (durum: http://localhost:8000/health)
- `.env` dosyası gerekmez; tüm değişkenlerin compose varsayılanları vardır. Değer değiştirmek için `.env.example` dosyasını kopyalayın.
- İlk build uzun sürer ve büyük bir indirme yapar. Ölçülen süreler (Apple M4 Pro, Docker): `--no-cache` ile temiz klonda 8 dk 41 sn (Faz 7A); daha önceki ölçümler 216 sn ve 336 sn. Backend imajı 4.26 GB, frontend imajı 93.6 MB (Faz 7A). Torch CPU paketi ve modeller build sırasında iner. Faz 5'te 4.11 GB'lık backend imajının sıkıştırılmış boyutu yaklaşık 1.34 GB ölçüldü.
- Yönetici işlemleri (ilan durumunu değiştirme, silme) için:
  - `ADMIN_TOKEN` tüm teslim noktalarını yönetir. `ADMIN_POINT_TOKENS` ise her teslim noktası için ayrı token tanımlar (tek satır JSON).
  - Tokenlar yalnızca `.env` dosyasında tutulur, depoya yazılmaz.
  - `ADMIN_REJECT_WEAK_TOKENS=true` iken `change-me`, `ornek-*` ve `ADMIN_TOKEN_MIN_LEN` değerinden kısa tokenlar yok sayılır. Güçlü bir token için `openssl rand -hex 16` kullanın.
  - Token tanımlı değilse yönetici uçları 403 döner.
  - Yönetici paneli kullanıcı hesabı değildir; token yalnızca tarayıcı belleğinde tutulur.
- `VITE_API_URL` frontend'e derleme zamanında gömülür; değiştirirseniz frontend'i yeniden build edin.
- `.env` içinde `CORS_ORIGINS` tanımlıysa ve 127.0.0.1 üzerinden açacaksanız `http://127.0.0.1:3000` değerini de ekleyin.

## Ortam değişkenleri

Değerler `.env.example` dosyasındaki varsayılanlardır.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `BACKEND_PORT` | 8000 | Ana makinedeki backend portu. Konteyner içinde backend 8000'i dinler. |
| `FRONTEND_PORT` | 3000 | Ana makinedeki frontend portu. Konteynerde 80'i dinlenir. |
| `CORS_ORIGINS` | http://localhost:3000,http://127.0.0.1:3000 | Backend'e izin verilen tarayıcı kaynakları (virgülle ayrılmış). |
| `VITE_API_URL` | http://localhost:8000 | Frontend'in kullandığı API adresi. Derleme zamanında gömülür. |
| `DATA_DIR` | /data | SQLite veritabanının (`app.db`) ve yüklenen görsellerin klasörü. |
| `MODEL_CACHE_DIR` | /models | Model önbellek klasörü. |
| `IMAGE_MODEL` | clip-ViT-B-32 | Görsel embedding modeli. |
| `TEXT_MODEL` | sentence-transformers/clip-ViT-B-32-multilingual-v1 | Metin embedding modeli. |
| `FACE_MODEL_PATH` | /models/face_detection_yunet_2023mar.onnx | YuNet yüz tespit modelinin yolu. |
| `FACE_BLUR_ENABLED` | true | Yüz bulanıklaştırmayı açar ya da kapatır. |
| `FACE_SCORE_THRESHOLD` | 0.6 | YuNet yüz tespit güven eşiği. |
| `MAX_UPLOAD_MB` | 8 | En büyük yükleme boyutu (MB). Aşılırsa 413 döner. |
| `FOUND_DATE_MAX_DAYS` | 60 | Bulunma tarihi en fazla kaç gün önce olabilir. `/api/meta` ile arayüze de iletilir. |
| `MAX_IMAGE_SIDE` | 1024 | Saklanan görselin en uzun kenarı (piksel). |
| `MAX_IMAGE_PIXELS` | 50000000 | Görsel açılmadan önce reddedilen piksel sayısı sınırı. |
| `UPLOAD_FORM_OVERHEAD_MB` | 1 | İstek gövdesi sınırı = `MAX_UPLOAD_MB` + bu pay (MB). |
| `TMP_SIZE` | 128m | Compose'ta konteyner `/tmp` alanının (bellek) boyutu. `MAX_UPLOAD_MB` artırılırsa bunu da artırın. |
| `TORCH_NUM_THREADS` | 4 | Torch'un kullanacağı iş parçacığı sayısı. |
| `MATCH_HIGH` | 0.37 | Metin skoruyla "yüksek" eşleşme eşiği. Metin ve görselin birlikte kullanıldığı aramada yarı yarıya harmanlanır. |
| `MATCH_MEDIUM` | 0.31 | Metin skoruyla "orta" eşleşme eşiği. Kayıp bildirimi eşleşmesi için de kullanılır. |
| `MATCH_IMAGE_HIGH` | 0.87 | Yalnızca görselle aramada "yüksek" eşiği. |
| `MATCH_IMAGE_MEDIUM` | 0.80 | Yalnızca görselle aramada "orta" eşiği ve görselli kayıp bildirimi eşleşme eşiği. |
| `TAG_MIN_CONFIDENCE` | 0.35 | Kategori güveni bunun altındaysa ilan "diğer" kategorisine düşer. |
| `ADMIN_TOKEN` | change-me | Tüm teslim noktalarını yöneten token. Boşsa yönetici uçları kapalıdır (403). Örnek değerdir; değiştirin. |
| `ADMIN_POINT_TOKENS` | `{"<teslim noktası>":"<token>"}` biçiminde JSON | Teslim noktası başına token. Her token yalnızca o noktanın ilanlarını yönetir. |
| `ADMIN_REJECT_WEAK_TOKENS` | true | `true` iken `change-me`, `ornek-*` ve kısa tokenlar yok sayılır. `false` yalnızca yerel prototip içindir. |
| `ADMIN_TOKEN_MIN_LEN` | 12 | Zayıf token kontrolünde kabul edilen en kısa token uzunluğu. |
| `LOG_LEVEL` | INFO | Log seviyesi. |
| `OCR_ENABLED` | true | Yerel OCR ile kişisel veri sansürünü açar. `false` yalnızca geliştirme içindir. |
| `OCR_LANGS` | tur+eng | Tesseract dilleri. |
| `OCR_MAX_SIDE` | 1600 | OCR çalışma kopyasının en uzun kenarı (piksel). |
| `OCR_TIMEOUT_S` | 8 | OCR zaman aşımı (saniye). Aşılırsa yükleme 503 ile reddedilir. |
| `OCR_MIN_CONF` | 30 | Yalnızca marka/model etiketi çıkarmada kullanılan OCR güven eşiği. Sansür bu eşiğe bakmaz. |
| `OMP_THREAD_LIMIT` | 1 | Tesseract ile torch iş parçacıklarının çakışmasını önler. |
| `SEARCH_TEXT_WEIGHT` | 0.1 | İlan metni indeksinin (başlık, açıklama, etiketler) arama skorundaki ağırlığı. 0 ise yalnızca ilan görseli kullanılır. |
| `TAG_BONUS` | 0.05 | Sorgudaki marka/model sözcüğü ilanın etiketiyle eşleşirse eşleşme başına eklenen puan. |
| `TAG_BONUS_MAX` | 0.10 | Etiket bonusunun en yüksek toplamı. |

## API özeti

Hata yanıtları Türkçe `{"detail": "..."}` biçimindedir. Yönetici uçları `X-Admin-Token` başlığı ister.

| Yöntem ve uç | Açıklama |
|---|---|
| `GET /health` | Durum ve model yükleme bilgisi. Modeller yüklenirken 503 döner. |
| `GET /api/meta` | Yerler, teslim noktaları, kategoriler, renkler ve yükleme sınırı. |
| `POST /api/items` | Bulunan eşya kaydı (multipart). Başarılıysa 201 ve ilan döner. |
| `GET /api/items` | İlan listesi (`status`, `location`, `category`, `limit`, `offset`). |
| `GET /api/items/{id}` | Tek ilan. Yoksa 404. |
| `POST /api/search` | Metin, görsel ya da ikisiyle arama. Sonuçlar `match_level` ile döner. |
| `PATCH /api/items/{id}/status` | İlan durumunu değiştirir (`teslim_edildi` / `bekliyor`). Yönetici token'ı gerekir. |
| `DELETE /api/items/{id}` | İlanı ve görselini siler. Yönetici token'ı gerekir. |
| `GET /api/admin/me` | Token kapsamını döner (teslim noktası ya da tüm noktalar). |
| `GET /api/admin/items` | Token kapsamındaki ilanları listeler. |
| `POST /api/lost-reports` | Kayıp bildirimi oluşturur ve 8 karakterlik takip kodu döner (201). |
| `GET /api/lost-reports/{code}/matches` | Takip koduyla bildirime eşleşen ilanları listeler. |
| `GET /uploads/<dosya>.jpg` | Bulanıklaştırılmış görsel kopyaları (statik). |

## Değerlendirme sonuçları

Kaynak: [docs/EVAL.md](docs/EVAL.md) (Faz 8 bölümündeki "Sonuç tablosu" ve Faz 6 "Ana sonuç" tablosu).

Mevcut yapılandırma (`SEARCH_TEXT_WEIGHT=0.1`, 24 ilan: 21 demo ilanı + ölçüm sırasında veritabanında kalmış 3 eski test ilanı; fazlalar yanlış aday sayılır, 42 Türkçe ve 42 İngilizce metin sorgusu, 7 görsel sorgu):

| Sorgu türü | n | R@1 | R@5 | MRR |
|---|---|---|---|---|
| TR metin | 42 | 0.452 | 0.881 | 0.635 |
| EN metin | 42 | 0.619 | 0.881 | 0.737 |
| Görsel | 7 | 0.857 | 1.000 | 0.886 |

Önceki ölçüm (Faz 6, `SEARCH_TEXT_WEIGHT=0`, 21 ilan):

| Sorgu türü | n | R@1 | R@5 | MRR |
|---|---|---|---|---|
| TR metin | 42 | 0.524 | 0.857 | 0.657 |
| EN metin | 42 | 0.595 | 0.857 | 0.717 |
| Görsel | 7 | 0.857 | 1.000 | 0.886 |

Sınırlar:

- Veri küçük: 21–24 ilan ve 7 görsel sorgu. Tek bir sorgu sonucu belirgin biçimde değiştirebilir.
- Eşikler aynı veriyle ayarlanıp aynı veriyle raporlandı. Gerçek ilanlarla yeniden ölçülmedi.
- Sorgular yapay zekâ tarafından yazıldı; Türkçe sorgular kullanıcı tarafından tek tek gözden geçirilmedi. Veri seti kullanıcının kendi çektiği fotoğraflardan oluşur.
- R@1 düşüktür. Hatalar çoğunlukla benzer eşyalar arasında (üç kulaklık kutusu, kalemler, şarj aletleri) olur.

## Geliştiriciler

TODO(kullanıcı): geliştirici adları

## Yapay zekâyı nasıl kullandık

Kaynak: [docs/AI_KULLANIM_GUNLUGU.md](docs/AI_KULLANIM_GUNLUGU.md). Proje tek geliştiriciyle, Claude Code ile yürütüldü.

### Araç ve model

Günlük model seçiminin gerekçesini kaydetmez; tabloda yalnızca fazdaki iş yer alır.

| Faz | Model | İş |
|---|---|---|
| 0 | Opus 5.5 | Kurulum: CLAUDE.md, docs, `.claude/` ve commit-msg hook'u |
| 1 | Sonnet 5.5 | Backend iskeleti, `/health`, Dockerfile |
| 2 | Opus 5.5 (ML modülleri: ml-engineer, Opus) | ML çekirdeği: CLIP, YuNet, tagger, store |
| 3 | Sonnet 5.5 | API uçları |
| 4 | Sonnet 5.5 (frontend-dev) | Vite + React + TypeScript arayüzü |
| 5 | Sonnet 5.5 (docker-tester) | Compose ve temiz klon testi |
| 6 | Opus 5.5 (ml-engineer) | Demo verisi ve retrieval değerlendirmesi |
| 7 | Sonnet 5.5 | Kayıp bildirimi, takip kodu, otomatik eşleşme |
| 7A | Opus 5.5 | Yerel OCR, PII sansürü, marka/model etiketi |
| 7B | Sonnet 5.5 (frontend-dev) | Arayüz cilası, teslim noktası yönetici paneli |
| 8 | Opus 5.5 | Şartname, kod ve güvenlik incelemesi |

### Kullanılan özellikler

- **Plan modu:** Her faz önce planlanıp onaylandı; kabul kriterleri plandan geldi.
- **Slash komutlar** (`.claude/commands/`): `/faz <n>` (PLAN'daki fazı uygular), `/sartname-kontrol` (spec-guard ile tam denetim), `/temiz-klon-testi` (commit'lenmiş hali temiz klonda compose ile test eder), `/gunluk` (günlüğe kayıt ekler).
- **Alt agent'lar** (`.claude/agents/`):
  - `spec-guard` (sonnet): salt okunur şartname denetçisi; kod yazmaz.
  - `ml-engineer` (opus): CLIP, zero-shot etiketleme, YuNet, retrieval değerlendirmesi, eşik ayarı.
  - `frontend-dev` (sonnet): React arayüzü ve nginx Dockerfile'ı.
  - `docker-tester` (sonnet): compose build ve çalıştırma, temiz klon testi, ölçümler.
  - `docs-writer` (haiku): README ve günlük özeti için tanımlı; günlükte kullanım kaydı yok.
- **Şartname koruma hook'u** (`.claude/hooks/spec_guard.py`, `.claude/settings.json` içinde `PreToolUse`, eşleşme `Write|Edit|MultiEdit|Bash`): Gerçekte yaptığı:
  - Bash: force push, `--no-verify` ve `--date`, `GIT_*_DATE`, yasaklı paket kurulumu (pip/uv/npm) ve `git add .env` komutlarını engeller.
  - Dosya yazımı: `.env` dosyasına yazmayı engeller. `.md` ve `.claude/` dosyaları muaftır.
  - Kod ve yapılandırma dosyalarında YOLO/ultralytics, OpenAI, Anthropic, Gemini/Vertex, Groq/Cohere/Replicate, HF Inference API ve CUDA kullanımını arar; eşleşirse işlemi exit 2 ile durdurur.
  - `settings.json` ayrıca `git push --force`, `git reset --hard`, `git rebase` ve `Read(./.env)` gibi komutları `deny` listesine koyar.
- **Commit-msg hook'u** (`.githooks/commit-msg`, `git config core.hooksPath = .githooks`): Gerçekte yaptığı: ilk satırı `update`, `fix`, `wip`, `test`, `changes`, `commit` gibi genel bir mesajı veya boş mesajı reddeder; 15 karakterden kısa mesajı reddeder. Mesajın içeriğini denetlemez.

### Örnek istemler

- Faz 1: "requirements.txt'i yazmadan önce izinli paketleri kökteki mevcut venv'e kur ve çalışan sürümleri == ile sabitle. torch sürümünü Dockerfile'daki ARG TORCH_VERSION'a yaz."
- Faz 3: "docs/PLAN.md'deki API sözleşmesinden sapma: alan adları, durum kodları ve Türkçe hata metinleri birebir aynı olmalı. Sözleşmede bir boşluk görürsen tahmin etme, bana sor."
- Faz 7A: "FAIL-CLOSED: OCR hata verir, zaman aşımına uğrar veya tesseract binary'si yoksa yükleme KAYDEDİLMEZ."
- Faz 8: "Bulguları 'kritik / önemli / kozmetik' diye grupla. Kritik ve önemli olanları onayımla düzelt; her düzeltme ayrı commit olsun. Kozmetikleri yalnızca listele."

### Yapay zekânın yanıldığı ve düzeltilen yerler

1. **Faz 1, `; true` ile gizlenen build.** Docker build komutuna `; true` eklenip çıktı gizlenmişti; daemon kapalı olduğu için build hiç çalışmamıştı. Fark edilince daemon açıldı ve build gerçek logla yeniden çalıştırıldı.
2. **Faz 1, şişen imaj.** `chown -R /models` imajı 1,15 GB şişirdi (6,16 GB). İmaj boyutu ölçülünce chown kaldırıldı; imaj 4,11 GB oldu.
3. **Faz 5, sahte nginx `/api` başarısı.** docker-tester, nginx üzerinden `:3000/api/meta` için 200 bildirdi. `nginx.conf`'ta proxy olmadığı, 200'ün SPA fallback'inden geldiği ana oturumda görüldü ve bulgu geçersiz sayıldı.
4. **Faz 6, internetten alınmış demo görselleri (geliştirici hatası, yapay zekâ yakaladı).** Geliştirici veri setini hızlandırmak için önce internetten görsel indirdi ve "hepsi benim çektiğim" dedi. Ana oturum kimlik kartlarında yüz, isim ve TC no buldu; ml-engineer 5 görselde Reddit şeridini, bir sırt çantası kolisinde ABD adresini fark etti. Görseller ana oturumda açılıp doğrulandı ve seed durduruldu; geliştirici kendi fotoğraflarını çekti. Yani bu örnekte hata yapay zekânın değil insanın; yapay zekâ kuralı (md. 7) uygulayıp durdurdu.
5. **Faz 8, eşik değişince bildirim eşleşmesi.** Metin eşikleri (0,37 / 0,31) commit'lendikten sonra fark edildi ki kayıp bildirimi eşleşmesi metin skorunu aramadan farklı (metin indeksi olmadan) hesaplıyor; yeni eşik orada doğru eşleşmelerin çoğunu eleyecekti. Ayrı bir commit ile iki yol aynı formüle getirildi.

### Elle düzeltmelerim

TODO(kullanıcı): geliştirici kendi elle yaptığı düzeltmeleri yazacak
