# İlerleme

| Faz | Durum | Tarih | Not |
|---|---|---|---|
| 0 Kurulum | ✅ | 2026-10-25 | Kurallar, plan, hook'lar, agent'lar ve komutlar eklendi; venv: `.venv` (Python 3.12.10); hook ve commit-msg testleri geçti |
| 1 Backend iskeleti | ✅ | 2026-10-26 | /health, hata yakalayıcılar, model indirme betiği ve Dockerfile eklendi; 6 test geçti; imaj internetsiz ayağa kalktı |
| 2 ML çekirdeği | ✅ | 2026-10-26 | image_io, ClipEncoder/FakeEncoder, YuNet yüz bulanıklaştırma (kapalı-güvenli), tagger, SQLite deposu + vektör arama, smoke ve try_blur betikleri; 44 test geçti; imaj internetsiz açılıyor (face_blur=true). "siyah sırt çantası top-3" kontrolü Faz 6'ya ertelendi (demo_data yok) |
| 3 API | ⬜ | | |
| 4 Frontend | ⬜ | | |
| 5 Compose | ⬜ | | |
| 6 Eval | ⬜ | | |
| 7 Ek: kayıp bildirimi | ⬜ | | |
| 8 Denetim | ⬜ | | |
| 9 Dokümantasyon | ⬜ | | |

## Açık sorular (kullanıcıya)
- Faz 3: yüz modeli yokken (`blurrer.available == False`, örn. FACE_BLUR_ENABLED=false) yükleme kabul edilsin mi, reddedilsin mi? (spec-guard uyarısı; CLAUDE.md madde 6)
- Faz 2: try_blur.py ile selfie üzerinde elle yüz bulanıklaştırma doğrulaması bekleniyor; sonuç buraya yazılacak.
- Commit'lerin 5 farklı güne yayılma şartı: organizatör teyidi bekleniyor.
- campus.json'daki yer isimleri GTÜ'ye uygun mu?

## Notlar
- Faz 2 kararları (kullanıcı onaylı): aynı-uzay doğrulaması dokulu sentetik nesnelerle yapıldı (düz beyaz kare CLIP'in kendi İngilizce kodlayıcısında da başarısız; görsel kodlayıcı sınırlaması). "diğer" kategorisi istem matrisinden çıkarıldı, yalnızca güven < 0.35'te dönen yedek etiket. `backend/scripts/try_blur.py` kullanıcının isteğiyle eklendi (PLAN dosya listesi dışında). `.gitignore`'da `data/` → `/data/` (campus.json takip edilsin diye).
- Faz 2: model yüklüyken yüz tespiti hata verirse `FaceBlurError` fırlatılır (görsel bulanıklaştırılmadan geçmez).
- Faz 2 commit'leri kod paralel yazıldıktan sonra adım adım (her biri kendi testiyle) ama kısa aralıkla atıldı; spec-guard bunu "toplu commit" gibi görünebilir diye uyardı. Sonraki fazlarda her adım bitince hemen commit atılacak.
- Faz 8'deki yasaklı kelime grep'i `.claude/hooks/spec_guard.py` dosyasını da yakalar (yasak listesi o dosyada). Faz 8'de `--exclude-dir=.claude` eklenmesi kullanıcıya sorulacak.

## Fikir Havuzu (kapsam dışı, onay bekleyen)
- Faz 5: BACKEND_PORT backend'de okunmuyor (CMD 8000 sabit); compose'da portu eşle veya .env.example'dan çıkar (spec-guard notu).

## Ölçümler (build süresi, imaj boyutu, gecikmeler)
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
