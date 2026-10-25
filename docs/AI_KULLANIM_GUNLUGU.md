# Yapay Zekâ Kullanım Günlüğü
README'deki "Yapay zekâyı nasıl kullandık" bölümünün kaynağıdır. Her faz sonunda bir kayıt eklenir. Dürüst ol: yapay zekânın yanıldığı ve insanın düzelttiği yerleri mutlaka yaz.

Kayıt şablonu:
## Faz N: <başlık> (<tarih>)
- Araç ve model: Claude Code (Opus 5.5 / Sonnet 5.5 / Haiku 5.5 alt agent'ı)
- Kullanılan özellikler: plan modu, alt agent'lar, hook'lar, vb.
- Örnek istem: "<kısaltılmış gerçek istem>"
- Yapay zekânın ürettiği:
- Yanlış veya eksik çıkan ve nasıl düzeltildiği:
- İnsanın (geliştiricinin) elle yaptığı veya karar verdiği:

## Faz 0: Kurulum (2026-10-25)
- Araç ve model: Claude Code (Opus 5.5)
- Kullanılan özellikler: plan modu, PreToolUse hook'u, izin kuralları (allow/ask/deny), alt agent tanımları, özel slash komutları, git commit-msg hook'u
- Örnek istem: "Bu ilk oturumda YALNIZCA Faz 0'ı yapacaksın: uygulama kodu YAZMAYACAKSIN. Görevin, bu mesajdaki kuralları, mimariyi ve planı depoya kalıcı dosyalar olarak yazmak ve Claude Code korumalarını kurmak."
- Yapay zekânın ürettiği: Depo incelemesi (mevcut venv `.venv` olarak tespit edildi), `git init`, `.gitignore`, geliştiricinin verdiği metinlerden CLAUDE.md, docs/*, .claude/* ve .githooks/commit-msg dosyalarının birebir yazılması; hook testleri (yasaklı içerik exit=2, zararsız içerik exit=0, "update" commit mesajı reddedildi).
- Yanlış veya eksik çıkan ve nasıl düzeltildiği: Hata çıkmadı. Tespit edilen not: Faz 8'deki yasaklı kelime grep'i, yasak listesini içeren `.claude/hooks/spec_guard.py` dosyasını da bulacak; içerik değiştirilmedi, ILERLEME'ye not düşüldü.
- İnsanın (geliştiricinin) elle yaptığı veya karar verdiği: Bütün kurallar, mimari, faz planı ve koruma dosyalarının içeriği geliştirici tarafından yazıldı; plan onaylandı; F adımının (ILERLEME ve günlük güncellemesi) tek commit'e dahil edilmesi onaylandı.

## Faz 1: Backend iskeleti, /health, Dockerfile (2026-10-26)
- Araç ve model: Claude Code (Sonnet 5.5); denetimde spec-guard alt agent'ı
- Kullanılan özellikler: plan modu, /faz komutu, arka plan docker build, spec-guard agent'ı
- Örnek istem: "requirements.txt'i yazmadan önce izinli paketleri kökteki mevcut venv'e kur ve çalışan sürümleri == ile sabitle. torch sürümünü Dockerfile'daki ARG TORCH_VERSION'a yaz."
- Yapay zekânın ürettiği: config/schemas/errors/main, /health testleri, download_models.py, Dockerfile, .dockerignore, .env.example; docker build ve internetsiz çalıştırma doğrulaması.
- Yanlış veya eksik çıkan ve nasıl düzeltildiği: (1) 404 yanıtı İngilizce "Not Found" döndü; işleyici FastAPI yerine Starlette HTTPException'a bağlanarak düzeltildi. (2) İlk docker build komutuna `; true` eklenip çıktı gizlenmişti; Docker daemon kapalı olduğu için build aslında hiç çalışmamıştı, fark edilince daemon açılıp build gerçek log ile yeniden çalıştırıldı. (3) `chown -R /models` imajı 1,15 GB şişirdi (6,16 GB); chown kaldırıldı (4,11 GB). (4) `--network none -p 8000:8000` ile host'tan erişim mümkün değil; doğrulama `docker exec` ile yapıldı.
- İnsanın (geliştiricinin) elle yaptığı veya karar verdiği: Faz isteminin içeriği, plan onayı, pip kurulum onayı.

## Faz 2: ML çekirdeği (2026-10-26)
- Araç ve model: Claude Code (Opus 5.5); ML modülleri ml-engineer alt agent'ı (Opus), denetim spec-guard alt agent'ı
- Kullanılan özellikler: plan modu, /faz komutu, arka planda paralel alt agent (ML modülleri) ve ana oturum (store.py + testler), agent'a SendMessage ile ek talimat, AskUserQuestion ile karar sorma
- Örnek istem: "Bu fazın ML işlerini ml-engineer alt agent'ına devret; veri katmanını (store.py) ve testleri sen yaz. Önce venv'de küçük bir doğrulama betiğiyle iki şeyi kanıtla: (a) clip-ViT-B-32 görsel embedding'i ile clip-ViT-B-32-multilingual-v1 Türkçe metin embedding'i aynı uzayda ... (b) YuNet modeli cv2.FaceDetectorYN ile yükleniyor. Testte yüz görseli KULLANMA."
- Yapay zekânın ürettiği: image_io (EXIF silme, yön düzeltme, küçültme), ClipEncoder (batch, inference_mode, TORCH_NUM_THREADS) ve FakeEncoder, FaceBlurrer (YuNet, %20 genişletme, pikselleştirme + Gaussian), Tagger (TR/EN/ortalama şablon), Store (SQLite WAL + numpy matris + argpartition), smoke_ml.py, try_blur.py, 38 yeni test; gecikme ölçümleri.
- Şablon seçimi: 13 renkli dokulu sentetik nesnede renk doğruluğu TR 9/13, EN 10/13, ortalama 11/13. TR ve EN farklı renklerde hata yaptığı için ortalama hataları kısmen telafi ediyor → "avg" seçildi. Kategori karşılaştırması kullanıcı fotoğrafı olmadığı için anlamlı değil; Faz 6'da tekrar bakılacak.
- Yanlış veya eksik çıkan ve nasıl düzeltildiği: (1) Plandaki "düz renk kareler" doğrulaması 6 satırın 5'inde geçti: "beyaz" metni en çok siyah kareye benzedi. Agent planın gereği durdu ve tanı koydu: CLIP'in kendi İngilizce kodlayıcısı aynı karede daha kötü sonuç verdi, yani sorun Türkçe hizalaması değil, test düzeni. Dokulu nesnelerle 6/6 geçti; kullanıcı bu ölçütü onayladı. (2) `Store.list` adlı metot, sınıf gövdesinde `list[...]` tip ipucunu gölgeledi (TypeError); `list_items` olarak yeniden adlandırıldı. (3) `.gitignore`'daki `data/` deseni `backend/app/data/campus.json`'ı da yutuyordu; `/data/` yapıldı. (4) Agent'ın ilk FaceBlurrer'ı tespit sırasında hata olursa görseli bulanıklaştırmadan döndürüyordu (agent bunu kendisi raporladı); kapalı-güvenli hale getirildi (FaceBlurError). (5) sentence-transformers `encode([])` (0,512) yerine (0,) döndürüyor; venv'de denenerek fark edildi ve ayrıca ele alındı. (6) Pillow `verify()` kesik JPEG'i yakalamıyor; yeniden açınca `load()` eklendi. (7) Commit'ler kod paralel yazıldıktan sonra kısa aralıkla atıldı; spec-guard "toplu commit" görünümüne karşı uyardı.
- İnsanın (geliştiricinin) elle yaptığı veya karar verdiği: Faz istemi ve iş bölümü, plan onayı, doğrulama ölçütünün dokulu nesnelerle kabulü, "diğer" kategorisinin istemden çıkarılması; try_blur.py ile selfie üzerinde gerçek yüz doğrulaması (bekliyor).

