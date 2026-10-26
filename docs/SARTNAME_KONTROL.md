# Şartname Kontrol Listesi (Teknik Şartlar ve Uygulama Rehberi'nden)

## 1. Production'a hazır
- [ ] backend/ ve frontend/ ayrı klasörlerde, her birinde kendi Dockerfile'ı var
- [ ] Kökte docker-compose.yml var; `docker compose up --build` başka hiçbir adım olmadan her şeyi ayağa kaldırıyor
- [ ] Backend'de durumunu bildiren `/health` ucu var
- [ ] Frontend backend'e yalnızca API üzerinden bağlanıyor
- [ ] Yalnızca CPU ile çalışıyor
- [ ] Frontend ve API adresleri README'de yazıyor (http://localhost:3000, http://localhost:8000)
- [ ] Model ağırlıkları build sırasında otomatik iniyor; elle dosya kopyalama yok
- [ ] Port, adres ve model yolu ortam değişkenlerinden okunuyor
- [ ] Hatalı veya eksik girdi uygulamayı çökertmiyor; anlaşılır Türkçe hata mesajı gösteriliyor
- [ ] Debug kapalı; frontend derlenmiş haliyle (nginx) sunuluyor
- [ ] Uzun işlemlerde yükleniyor göstergesi var
- [ ] Backend 0.0.0.0'ı dinliyor; CORS frontend kaynağına izin veriyor
- [ ] opencv-python-headless kullanılıyor
## 2. YOLO yok
- [ ] Depoda ultralytics, yolo veya YOLO ağırlığı geçmiyor
## 3. En az bir yapay zekâ bileşeni
- [ ] Görüntü işleme (CLIP embedding, zero-shot etiketleme, YuNet yüz tespiti)
## 4. Harici yapay zekâ API'si yok
- [ ] Kodda bulut AI SDK'sı veya çağrısı yok; çalışma zamanında HF_HUB_OFFLINE=1
## 5. Yapay zekâ asistanı kullanımı
- [ ] README'de "Yapay zekâyı nasıl kullandık" bölümü: araç, iş, örnek istemler, elle düzeltilenler
## 6. Güvenlik ve veri
- [ ] Gizli bilgi depoda yok; .env git'te yok; .env.example var
- [ ] Yüzler bulanıklaştırılıyor, orijinal saklanmıyor, EXIF siliniyor
- [ ] Demo görselleri kendi çekimimiz, yüz içermiyor
- [ ] OCR tamamen yerel, harici servis yok; sistem bağımlılıkları Dockerfile'da
- [ ] Metin tabanlı kişisel veriler (TC, telefon, e-posta, IBAN, öğrenci no) görselden kalıcı olarak silinir
- [ ] OCR ham metni loglanmaz, saklanmaz, API'den dönmez
- [ ] Yönetici tokenları (ADMIN_TOKEN, ADMIN_POINT_TOKENS) yalnızca ortam değişkeninden gelir; depoda gerçek değer yok, loglanmaz, API yanıtında dönmez
## 7. Git
- [ ] Küçük, sık, anlamlı commit'ler; mesajlar açıklayıcı
- [ ] En az 5 farklı güne yayılma (organizatörle teyit edilecek)
- [ ] İki kişilik ekipse iki üyenin de kendi hesabından commit'i var
- [ ] Hiç force push yok
## 8. Depo ve medya
- [ ] Public GitHub deposu
- [ ] README: problem, çözüm, çalıştırma adımları, geliştiriciler, AI kullanımı; en üstte demo video bağlantısı
- [ ] Video: uygulama çalışırken + Docker ile ayağa kalkış; bilgisayar ekran kaydı; anlaşılır ses; depoya konacaksa < 50 MB
