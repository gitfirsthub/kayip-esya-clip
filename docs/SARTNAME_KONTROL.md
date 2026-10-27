# Şartname Kontrol Listesi (Teknik Şartlar ve Uygulama Rehberi'nden)

## 1. Production'a hazır
- [x] backend/ ve frontend/ ayrı klasörlerde, her birinde kendi Dockerfile'ı var
- [x] Kökte docker-compose.yml var; `docker compose up --build` başka hiçbir adım olmadan her şeyi ayağa kaldırıyor
- [x] Backend'de durumunu bildiren `/health` ucu var
- [x] Frontend backend'e yalnızca API üzerinden bağlanıyor
- [x] Yalnızca CPU ile çalışıyor
- [x] Frontend ve API adresleri README'de yazıyor (http://127.0.0.1:3000, http://127.0.0.1:8000)
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
- [x] README'de "Yapay zekâyı nasıl kullandık" bölümü: araç, iş, örnek istemler, elle düzeltilenler
## 6. Güvenlik ve veri
- [x] Gizli bilgi depoda yok; .env git'te yok; .env.example var
- [x] Yüzler bulanıklaştırılıyor, orijinal saklanmıyor, EXIF siliniyor
- [x] Demo görselleri kendi çekimimiz, yüz içermiyor
- [x] OCR tamamen yerel, harici servis yok; sistem bağımlılıkları Dockerfile'da
- [x] Metin tabanlı kişisel veriler (TC, telefon, e-posta, IBAN, öğrenci no) görselden kalıcı olarak silinir
- [x] OCR ham metni loglanmaz, saklanmaz, API'den dönmez
- [x] Yönetici tokenları (ADMIN_TOKEN, ADMIN_POINT_TOKENS) yalnızca ortam değişkeninden gelir; depoda gerçek değer yok, loglanmaz, API yanıtında dönmez
## 7. Git
- [x] Küçük, sık, anlamlı commit'ler; mesajlar açıklayıcı
- [x] En az 5 farklı güne yayılma: organizatör teyidiyle muaf (kullanıcı bildirdi; gerçek durum 3 gün: 2026-10-25, 26, 27)
- [x] İki kişilik ekipse iki üyenin de kendi hesabından commit'i var: geçerli değil, ekip tek kişi (Efe Şenel)
- [x] Hiç force push yok
## 8. Depo ve medya
- [x] Public GitHub deposu (github.com/gitfirsthub/kayip-esya-clip; kimlik doğrulamasız API isteği 200 döndü, 2026-10-27)
- [x] README: problem, çözüm, çalıştırma adımları, geliştiriciler, AI kullanımı; en üstte demo video bağlantısı
- [x] Video: uygulama çalışırken + Docker ile ayağa kalkış; bilgisayar ekran kaydı; anlaşılır ses; depoya konacaksa < 50 MB (video kullanıcı tarafından çekildi, depoda değil; bağlantı README'nin ilk satırında; içeriği yapay zekâ tarafından izlenmedi)

## Faz 8 denetim notu (2026-10-26)
[x] maddeler spec-guard tarafından kanıtla (dosya:satır veya komut çıktısı) doğrulandı; ayrıntı docs/ILERLEME.md "Faz 8 denetimi".
Açık kalanlar: README, AI kullanımı bölümü ve adresler (Faz 9); video ve public depo (kullanıcı); 5 gün kuralı (kullanıcı kararıyla dikkate alınmıyor; gerçek durum 2 gün); ekip maddesi (tek yazar, ekip büyüklüğü kullanıcıya soruldu); demo görselleri: yüz yok; 2 karedeki el, anahtar kodu ve kalem baskısı kullanıcı tarafından sorun sayılmadı (madde [x]). Ekip tek kişi; commit gün dağılımı için kullanıcı organizatörle sorun olmadığını bildirdi.

## Teslim öncesi güncelleme (2026-10-27)
Bütün maddeler [x]. README'deki TODO'lar dolduruldu (geliştirici: Efe Şenel; "Elle düzeltmelerim" günlükteki insan kararlarından derlendi); ekran görüntüsü bölümü kullanıcı kararıyla kaldırıldı (video var). Adresler 127.0.0.1 olarak güncellendi.
