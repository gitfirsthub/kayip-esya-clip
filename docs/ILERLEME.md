# İlerleme

| Faz | Durum | Tarih | Not |
|---|---|---|---|
| 0 Kurulum | ✅ | 2026-10-25 | Kurallar, plan, hook'lar, agent'lar ve komutlar eklendi; venv: `.venv` (Python 3.12.10); hook ve commit-msg testleri geçti |
| 1 Backend iskeleti | ✅ | 2026-10-26 | /health, hata yakalayıcılar, model indirme betiği ve Dockerfile eklendi; 6 test geçti; imaj internetsiz ayağa kalktı |
| 2 ML çekirdeği | ⬜ | | |
| 3 API | ⬜ | | |
| 4 Frontend | ⬜ | | |
| 5 Compose | ⬜ | | |
| 6 Eval | ⬜ | | |
| 7 Ek: kayıp bildirimi | ⬜ | | |
| 8 Denetim | ⬜ | | |
| 9 Dokümantasyon | ⬜ | | |

## Açık sorular (kullanıcıya)
- Commit'lerin 5 farklı güne yayılma şartı: organizatör teyidi bekleniyor.
- campus.json'daki yer isimleri GTÜ'ye uygun mu?

## Notlar
- Faz 8'deki yasaklı kelime grep'i `.claude/hooks/spec_guard.py` dosyasını da yakalar (yasak listesi o dosyada). Faz 8'de `--exclude-dir=.claude` eklenmesi kullanıcıya sorulacak.

## Fikir Havuzu (kapsam dışı, onay bekleyen)
- Faz 5: BACKEND_PORT backend'de okunmuyor (CMD 8000 sabit); compose'da portu eşle veya .env.example'dan çıkar (spec-guard notu).

## Ölçümler (build süresi, imaj boyutu, gecikmeler)
- Faz 1: ilk backend build'i 223 sn (torch CPU + 2 model + YuNet indirme); imaj 4.11 GB (chown katmanı kaldırıldıktan sonra; öncesi 6.16 GB). Kod değişikliğiyle yeniden build 1 sn, model katmanı CACHED.
- Faz 1: `docker run --network none` ile /health 200 (`docker exec` ile doğrulandı; `--network none` ile host portu yayınlanamaz); ağlı çalıştırmada localhost:8000/health 200, models_loaded=true, face_blur=true.
- Faz 1 notu: `check_models` açılışta modelleri yükleyip atıyor (yavaş açılış); Faz 2'de encoder yüklemesine taşınacak. item_count şimdilik sabit 0.
