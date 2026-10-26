# Video Senaryosu (3 dakika)

- Video bağlantısı: TODO(kullanıcı) (README'nin en üstüne eklenecek)
- Geliştirici(ler): TODO(kullanıcı)
- Durum: taslak. Çekimden önce "Çekim öncesi kontrol listesi" ve "Doğrulanacaklar" bölümlerini tamamlayın.

## 1. Kapsam

- Ekran kaydı; uygulama çalışırken ve Docker ile ayağa kalkış gösterilir. Ses anlaşılır Türkçe olmalı.
- Yalnızca depoda var olan özellikler anlatılır: metin ve görselle arama, eşya kaydı (yüz bulanıklaştırma, OCR ile kişisel veri kapatma, otomatik kategori ve renk), kayıp bildirimi ve takip kodu, yönetici paneli.
- Kayıp bildiriminin bildirim göndermediği söylenir. Bildirim ya da e-posta servisi yoktur; kullanıcı takip koduyla kendisi kontrol eder.
- Arayüzdeki sekme ve düğme metinleri birebir kullanılır.

## 2. Senaryo tablosu

| Zaman | Ekranda ne var | Söylenecek metin |
|---|---|---|
| 0:00–0:10 | Tarayıcı, http://localhost:3000. Başlık "Kampüs Kayıp Eşya" ve tanıtım cümlesi. | "Kampüste eşyasını kaybeden biriyle eşyayı bulan biri arasında köprü kuruyoruz." |
| 0:10–0:20 | Sekmeler: "Eşyamı Kaybettim", "Eşya Buldum", "Tüm İlanlar", "Yönetici". Gizlilik notu: "Yüzler otomatik bulanıklaştırılır, iletişim bilgisi istenmez." | "Eşyayı bulan fotoğrafını yükler, kaybeden Türkçe olarak tarif eder. Yüzler otomatik bulanıklaştırılır, iletişim bilgisi istenmez." |
| 0:20–0:30 | Terminal, proje klasörü. Komut: `docker compose up --build` | "Tek komutla ayağa kaldırıyoruz. Başka bir kurulum adımı yok; modeller imaj derlenirken iner." |
| 0:30–0:40 | Terminal logları, backend açılıyor. | "Backend modelleri açılışta yüklüyor. Bu sırada sağlık ucu 'loading' döner; yüklenince 200 verir." |
| 0:40–0:50 | Tarayıcı, http://localhost:8000/health. JSON: models_loaded, face_blur, ocr. | "Sağlık ucu modellerin yüklü olduğunu, yüz bulanıklaştırmanın ve yerel OCR'ın açık olduğunu gösteriyor." |
| 0:50–1:00 | "Eşya Buldum" sekmesi. "Bulunan eşyanın fotoğrafı" alanına `demo_data/images/keys_blue_fob.jpg` sürüklenir. | "Bir eşya buldum. Fotoğrafı sürükleyip bırakıyorum." |
| 1:00–1:10 | Form: Başlık "Mavi kartlı anahtarlık, üç anahtar"; açıklama; "Bulunduğu yer" Temel Bilimler Fakültesi; "Bulunma tarihi"; "Teslim noktası" Güvenlik Birimi (Ana Kapı). | "Başlığı, yeri ve tarihi yazıyorum, teslim noktasını seçiyorum. Telefon ya da e-posta alanı yok; eşya bir teslim noktasına bırakılıyor." |
| 1:10–1:20 | "İlanı Kaydet" → "Fotoğraf işleniyor, lütfen bekleyin…" → "İlan kaydedildi", "Otomatik etiketler: kategori …, renk …", yüz durumu, etiket çipleri. | "Kaydedince sistem kategoriyi ve rengi kendisi belirliyor, yüzleri bulanıklaştırıyor. Yazılı kişisel veriler de siyah kutuyla kapatılıyor. Orijinal fotoğraf diske yazılmıyor, konum bilgisi (EXIF) siliniyor." |
| 1:20–1:30 | "Eşyamı Kaybettim" sekmesi. Metin kutusu boş (yer tutucu: "lacivert termos, üzerinde çıkartma var"); kutuya "mavi kartlı ev anahtarım düştü" yazılır. | "Şimdi kaybeden tarafı. Türkçe, serbest bir cümle yazıyorum. Marka ya da kategori seçmek zorunda değilim." |
| 1:30–1:40 | "Ara" → "Sonuçlar (N)" başlığı, ilan kartları, "Yüksek/Orta/Düşük eşleşme" rozeti, benzerlik çubuğu. | "Ara. Sonuçlarda fotoğraf, yer, tarih, teslim noktası ve eşleşme düzeyi var." |
| 1:40–1:50 | Metin temizlenir. "Benzer bir fotoğraf (isteğe bağlı)" alanına `demo_data/images/queries/094016_1.jpg` konur, "Ara". | "Şimdi aynı anahtarlığın başka bir açıdan çekilmiş fotoğrafıyla arıyorum. Görselle arama da aynı ilanı öne çıkarıyor." |
| 1:50–2:00 | Yer veya kategori filtresi ("Tümü" seçenekleri). | "Yer ve kategoriyle daraltabiliyorum. Ölçümlerimizde metin araması yaklaşık 30 milisaniye, görselle arama yaklaşık 75 milisaniye sürdü." |
| 2:00–2:10 | "Eşyamı Kaybettim", metin: "beyaz kablosuz kulaklıklarım kayboldu kutusuz". Düğme: "Bulunursa haber almak için bildirim bırak" → "Kaydediliyor…". | "Eşyam bulunmazsa diye bildirim bırakıyorum. Benden telefon ya da e-posta istenmiyor." |
| 2:10–2:18 | "Takip kodunuz:" altında 8 karakterlik kod; "Bu kodu not alın; bir daha gösterilmez" uyarısı. | "Bana 8 karakterlik bir takip kodu verildi. Bu kodu not alıyorum; sistem kodu bir daha göstermiyor. Bildirim bana haber vermez, kodla kendim kontrol ederim." |
| 2:18–2:25 | "Takip kodumla kontrol et" alanına kod yazılır, "Kontrol et". Sonuç: "Eşleşen ilanlar (N)" ya da "Henüz eşleşen bir ilan yok". | "Kodu yazıp kontrol ediyorum. Eşleşen ilan varsa burada listeleniyor; yoksa daha sonra tekrar bakarım." |
| 2:25–2:32 | "Yönetici" sekmesi. "Yönetici girişi", "Yönetici anahtarı" (maskeli alan), "Giriş". | "Her teslim noktasının kendi yönetici anahtarı var. Anahtar yalnızca tarayıcının belleğinde tutuluyor; hesap, kullanıcı kaydı ya da oturum yok." |
| 2:32–2:40 | Başlık "Güvenlik Birimi (Ana Kapı) yönetimi"; anahtarlık kartı; "Teslim edildi olarak işaretle". | "Sahibi eşyasını aldığında ilanı 'Teslim edildi olarak işaretle' ile kapatıyorum." |
| 2:40–2:45 | Kart "Teslim edildi" rozetiyle. Ardından "Tüm İlanlar" sekmesi. | "Teslim edilen ilan kayıp aramalarında çıkmıyor; Tüm İlanlar'da 'Teslim edildi' olarak kalıyor." |
| 2:45–2:52 | Terminal, proje kökünde: `grep -rniE "ultralytics\|yolo\|openai\|anthropic\|generativeai" --exclude-dir={node_modules,.git,docs,.claude,.venv} --exclude=*.md .` Çıktı boş olmalı. | "Projede YOLO ya da bulut yapay zekâ servisi yok. Sınıflandırma CLIP ile, yüz tespiti OpenCV YuNet ile, OCR Tesseract ile; hepsi konteynerin içinde, CPU üzerinde çalışıyor." |
| 2:52–3:00 | Tarayıcı, http://localhost:3000 ya da kapanış ekranı. | "Yapay zekâ modelleri imajın içinde; çalışırken dış bir servis çağrılmıyor. Eşya teslim noktasına bırakılıyor ve iletişim bilgisi toplanmıyor. Dinlediğiniz için teşekkürler." |

Notlar:
- 1:30–1:50 satırlarında "keys" sorgusunun ilk sırada çıkacağı ve görsel sorgunun aynı ilanı öne çıkaracağı varsayılmıştır. Çekimden önce bir deneme yapın; sonuç farklıysa anlatım o sonuca göre değiştirilir.
- 2:45 satırındaki grep çıktısı boş değilse bu sahne çekilmez.

## 3. Hazırlık (çekimden önce)

- Önbellekli build: `docker compose up --build` en az bir kez kayda alınmadan çalıştırılmalı. İlk build uzundur (ILERLEME ölçümleri: temiz klonda 336 sn ile 8 dk 41 sn arası). Kayda girmemesi için önceden derlenmiş olmalı; kesit (hızlandırılmış) olarak da alınabilir.
- Veri: Anahtarlık ilanı (`keys_blue_fob`) yükleme sahnesinde canlı eklenecek. `backend/scripts/seed_demo.py` 21 ilanın tamamını yükler ve ilan hariç tutma seçeneği yoktur (yalnızca `--api-url` var). Çözüm: önce `docker compose down -v`, sonra seed çalıştırıp çekimden önce yönetici panelinden anahtarlık ilanını silin (ya da yüklemeyi başka bir demo fotoğrafıyla gösterip o ilanı silin); arama sahnesi anahtarlığı bulacağı için ilan yükleme sahnesinden sonra veritabanında olmalıdır.
- Yönetici: Anahtarlık ilanı "Güvenlik Birimi (Ana Kapı)" noktasına bırakıldığı için bu noktanın yönetici anahtarı gerekir. Anahtar `.env` içinde `ADMIN_POINT_TOKENS` ile tanımlanmalı: TODO(kullanıcı). Zayıf veya örnek anahtarlar (change-me, ornek-*) `ADMIN_REJECT_WEAK_TOKENS=true` iken reddedilir (403). Çekim sırasında yalnızca maskeli alana yazılır, panoya kopyalanmaz.
- Eşikler: ILERLEME'ye göre yerel `.env` dosyasında eski metin eşikleri (0.315 / 0.255) kalmış olabilir. Yeni varsayılanlar 0.37 / 0.31. Eski değerler varsa sonuç sıraları ve rozetler farklı çıkar. Kontrol: TODO(kullanıcı).
- Adres: Tarayıcıda `http://localhost:3000` kullanılır. Backend 8000 ve frontend 3000 portları başka bir şey tarafından kullanılmamalı.
- Bulunma tarihi: Varsayılan bugündür; anahtarlık için ilanda 2026-10-16 yazılabilir (son 60 gün içinde olmalı).

## 4. Doğrulanacaklar (çekimden önce, TODO(kullanıcı))

- "mavi kartlı ev anahtarım düştü" sorgusu anahtarlık ilanını ilk sırada mı çıkarıyor?
- 094016_1.jpg görsel sorgusu aynı ilanı öne çıkarıyor mu?
- "beyaz kablosuz kulaklıklarım kayboldu kutusuz" bildirimi, kulaklık ilanıyla eşleşiyor mu; takip kodu kontrolünde ne çıkıyor?
- Kaydedilen anahtarlık kartında kategori ve renk ne yazıyor (anlatımda yer tutucu bırakıldı)? Görselde OCR'ın okuduğu bir kod (demo setinde anahtar kodu olduğu bilinir) kapatılmış mı, "N bölge gizlendi" çipi çıkıyor mu? Ne gösteriyorsa anlatımı ona göre söyleyin; kapatıldığını varsaymayın.
- Yönetici girişi ve "Teslim edildi" akışı kayıt öncesi bir kez denenmiş mi?

## 5. Çekim öncesi kontrol listesi

- [ ] Ekranda yalnızca kendi çektiğiniz, yüz içermeyen demo fotoğrafları kullanılıyor (`demo_data/images/`). Eski internet kaynaklı dosyalar (`demo_data/raw/`) dosya gezgininde ya da sekmede görünmüyor. Bu klasörün silinmesi ILERLEME'de kullanıcıya bırakıldı.
- [ ] Ekranda gerçek kişi verisi yok: kişi adı, telefon, e-posta, TC kimlik no yazılmıyor, kullanıcı bildirimlerinde de yok.
- [ ] `.env` dosyası açılmıyor, `cat .env` ve `docker compose config` çalıştırılmıyor (ikincisi ortam değişkenlerini, dolayısıyla tokenları yazdırır).
- [ ] Yönetici anahtarı ekranda görünmüyor; maskeli alana yazılıyor, terminal geçmişinde yok.
- [ ] Terminal geçmişi ve komut satırı temizlendi; kullanıcı adı ve yerel yol gibi kişisel bilgi görünmüyor (gerekiyorsa prompt sadeleştirilir).
- [ ] Tarayıcıda e-posta, yer imi çubuğu ve kişisel sekmeler gizli; tek sekme.
- [ ] Yalnızca gösterilen adresler: http://localhost:3000 ve http://localhost:8000/health.
- [ ] Ses: mikrofon testi yapıldı, ortam sessiz, konuşma Türkçe ve anlaşılır.
- [ ] Süre 3:00 civarında; sahneler sırayla çekildi.
- [ ] Dosya boyutu 50 MB'ın altında. Depoya konacaksa yalnızca bu koşulda eklenir; aksi halde video dış bir bağlantıya konur (TODO(kullanıcı)).
- [ ] Bağlantı README'ye yazıldı (TODO(kullanıcı)).

## 6. Bilinen sınırlar (anlatımda söylenmemeli)

- Yüz bulanıklaştırma: Demo setinde yüz yok (kendi çekimleriniz, yüzsüz). Bu nedenle yüz bulanıklaştırma sahnesi gösterilmiyor; "Fotoğrafta yüz bulunmadı" yazısı görünür. Kendi yüzünüzü içeren bir çekim eklemek isterseniz rızanız olmalı: TODO(kullanıcı).
- Saat ilanı ("Yeşil kadranlı metal kol saati") bu videoda kullanılmıyor. Kadranı yüz sayıyor ve belge benzeri sayılıp 12 bölge kapatılıyor (ILERLEME: bilinen yanlış pozitif).
- Eşleşme sıralamaları ve rozetler çekim öncesi denenmelidir. ILERLEME'deki Recall ve MRR değerleri Faz 6 (SEARCH_TEXT_WEIGHT=0.0) ölçümüdür; güncel ayar 0.1. Güncel ölçüm docs/EVAL.md'nin Faz 8 bölümünde ve farklı bir ilan sayısıyla (24) yapıldı. Videoda bu sayılar kullanılmıyor.
- Arama süresi ekranda gösterilmiyor; söylenen süreler ILERLEME'deki ölçümlerdir (metin ~27–33 ms, görsel ~72–77 ms; yükleme ile OCR dahil 1,06–1,56 sn).
- Bildirim e-posta ya da mesaj göndermez; bildirim servisi kapsam dışıdır.
- Teslim edilen ilanlar yalnızca Tüm İlanlar'da görünür (arama bunları göstermez).
