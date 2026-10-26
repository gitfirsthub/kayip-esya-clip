# Şartname Kontrol Listesi (Teknik Şartlar ve Uygulama Rehberi'nden)

## 1. Production'a hazır
- [x] backend/ ve frontend/ ayrı klasörlerde, her birinde kendi Dockerfile'ı var
- [x] Kökte docker-compose.yml var; `docker compose up --build` başka hiçbir adım olmadan her şeyi ayağa kaldırıyor
- [x] Backend'de durumunu bildiren `/health` ucu var
- [x] Frontend backend'e yalnızca API üzerinden bağlanıyor
- [x] Yalnızca CPU ile çalışıyor
- [ ] Frontend ve API adresleri README'de yazıyor (http://localhost:3000, http://localhost:8000)
- [x] Model ağırlıkları build sırasında otomatik iniyor; elle dosya kopyalama yok
- [x] Port, adres ve model yolu ortam değişkenlerinden okunuyor
- [x] Hatalı veya eksik girdi uygulamayı çökertmiyor; anlaşılır Türkçe hata mesajı gösteriliyor
- [x] Debug kapalı; frontend derlenmiş haliyle (nginx) sunuluyor
- [x] Uzun işlemlerde yükleniyor göstergesi var
- [x] Backend 0.0.0.0'ı dinliyor; CORS frontend kaynağına izin veriyor
- [x] opencv-python-headless kullanılıyor
## 2. YOLO yok
- [x] Depoda ultralytics, yolo veya YOLO ağırlığı geçmiyor
## 3. En az bir yapay zekâ bileşeni
- [x] Görüntü işleme (CLIP embedding, zero-shot etiketleme, YuNet yüz tespiti)
## 4. Harici yapay zekâ API'si yok
- [x] Kodda bulut AI SDK'sı veya çağrısı yok; çalışma zamanında HF_HUB_OFFLINE=1
## 5. Yapay zekâ asistanı kullanımı
- [ ] README'de "Yapay zekâyı nasıl kullandık" bölümü: araç, iş, örnek istemler, elle düzeltilenler
## 6. Güvenlik ve veri
- [x] Gizli bilgi depoda yok; .env git'te yok; .env.example var
- [x] Yüzler bulanıklaştırılıyor, orijinal saklanmıyor, EXIF siliniyor
- [ ] Demo görselleri kendi çekimimiz, yüz içermiyor
- [x] OCR tamamen yerel, harici servis yok; sistem bağımlılıkları Dockerfile'da
- [x] Metin tabanlı kişisel veriler (TC, telefon, e-posta, IBAN, öğrenci no) görselden kalıcı olarak silinir
- [x] OCR ham metni loglanmaz, saklanmaz, API'den dönmez
- [x] Yönetici tokenları (ADMIN_TOKEN, ADMIN_POINT_TOKENS) yalnızca ortam değişkeninden gelir; depoda gerçek değer yok, loglanmaz, API yanıtında dönmez
## 7. Git
- [x] Küçük, sık, anlamlı commit'ler; mesajlar açıklayıcı
- [ ] En az 5 farklı güne yayılma (organizatörle teyit edilecek)
- [ ] İki kişilik ekipse iki üyenin de kendi hesabından commit'i var
- [x] Hiç force push yok
## 8. Depo ve medya
- [ ] Public GitHub deposu
- [ ] README: problem, çözüm, çalıştırma adımları, geliştiriciler, AI kullanımı; en üstte demo video bağlantısı
- [ ] Video: uygulama çalışırken + Docker ile ayağa kalkış; bilgisayar ekran kaydı; anlaşılır ses; depoya konacaksa < 50 MB

## Faz 8 denetim notu (2026-10-26)
[x] maddeler spec-guard tarafından kanıtla (dosya:satır veya komut çıktısı) doğrulandı; ayrıntı docs/ILERLEME.md "Faz 8 denetimi".
Açık kalanlar: README, AI kullanımı bölümü ve adresler (Faz 9); video ve public depo (kullanıcı); 5 gün kuralı (kullanıcı kararıyla dikkate alınmıyor; gerçek durum 2 gün); ekip maddesi (tek yazar, ekip büyüklüğü kullanıcıya soruldu); demo görselleri (yüz yok, ama 2 karede el, anahtar kodu ve kalem baskısı kullanıcı kararını bekliyor).
