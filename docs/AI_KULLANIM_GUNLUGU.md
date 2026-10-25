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
