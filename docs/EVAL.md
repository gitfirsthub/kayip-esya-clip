# Arama Başarımı Değerlendirmesi (Faz 6)

## Ortam
- Tarih: 2026-10-26
- Donanım: Apple M4 Pro (12 çekirdek, 24 GB). Backend, Docker Desktop'ta (linux/aarch64; Docker VM'e 12 CPU, ~7.7 GB bellek ayrılmış) `docker compose` ile çalışıyor. CPU kullanılıyor, GPU yok.
- Modeller: görseller için `clip-ViT-B-32`, metinler için `sentence-transformers/clip-ViT-B-32-multilingual-v1`. Model değiştirilmedi.
- Ölçüm: `backend/scripts/eval_retrieval.py` çalışan API'nin `POST /api/search` ucunu `top_k=50` ile çağırır. Ölçümler 21 ilan yüklü (item_count = 21) ve iade edilmiş ilan olmayan API üzerinde alındı.
- Yeniden üretmek için: `python backend/scripts/seed_demo.py`, ardından `python backend/scripts/eval_retrieval.py --json sonuc.json`

## Veri seti
- 21 ilan (`demo_data/items.json`). Fotoğrafların hepsini kullanıcı kendi telefonuyla çekti; en uzun kenar 1024 px'e küçültüldü ve EXIF silindi (`demo_data/images/`).
- 42 Türkçe metin sorgusu (ilan başına 2). Her birinin İngilizce karşılığı (`q_en`) da var, bu da 42 İngilizce sorgu eder.
- 7 görsel sorgu: aynı eşyanın ilandaki fotoğraftan farklı bir açıdan çekilmiş fotoğrafı (`demo_data/images/queries/`).
- Kullanılmayan dosyalar:
  - İnternetten alınmış ilk setin tamamı (Reddit ekran görüntüleri, katalog görselleri, yüz ya da kimlik içeren kartlar). Bu set şartnameye aykırı olduğu için silindi. Klasörde kalan 4 dosyası (`09.00.23 (1)`, `09.00.23`, `09.00.24`, `09.00.24 (4)`) açılmadı ve kullanılmadı.
  - Yeni setten 1 fotoğraf: üzerinde okunabilir kişi ismi var.
- Sorgular günlük dilde ve küçük harfle yazıldı. Marka ya da logo bilgisi içermiyor. Bazıları bilerek belirsiz bırakıldı ("kulaklığımı kaybettim", "anahtarlarımı kaybettim").
- Sette benzer eşyalar yoğun: 3 siyah kulaklık parçası (kare kutu, oval kutu, tek kulaklık), 2 beyaz kulaklık parçası, 2 siyah çerçeveli gözlük, 3 kalem (tükenmez, versatil, ekran kalemi), 2 beyaz şarj eşyası (adaptör, powerbank), 3 çanta.

## Sonuçlar
### Ana sonuç

| Sorgu türü | n | R@1 | R@5 | MRR |
|---|---|---|---|---|
| TR metin | 42 | 0.524 | 0.857 | 0.657 |
| EN metin | 42 | 0.595 | 0.857 | 0.717 |
| Görsel | 7 | 0.857 | 1.000 | 0.886 |

### Skor dağılımı

| Küme | n | min | p10 | medyan | p90 | maks |
|---|---|---|---|---|---|---|
| Metin (TR+EN) doğru | 84 | 0.220 | 0.238 | 0.278 | 0.320 | 0.359 |
| Metin (TR+EN) en iyi yanlış | 84 | 0.234 | 0.250 | 0.280 | 0.311 | 0.331 |
| Metin (TR+EN) tüm yanlışlar | 1680 | 0.138 | 0.209 | 0.234 | 0.263 | 0.331 |
| TR doğru | 42 | 0.220 | 0.237 | 0.270 | 0.312 | 0.323 |
| TR en iyi yanlış | 42 | 0.234 | 0.247 | 0.271 | 0.303 | 0.313 |
| Görsel doğru | 7 | 0.759 | 0.815 | 0.946 | 0.952 | 0.953 |
| Görsel en iyi yanlış | 7 | 0.726 | 0.751 | 0.792 | 0.855 | 0.866 |
| Görsel tüm yanlışlar | 140 | 0.506 | 0.608 | 0.698 | 0.786 | 0.866 |

### Denemeler

| Deneme | TR R@1 | TR R@5 | TR MRR | EN R@1 | EN R@5 | EN MRR |
|---|---|---|---|---|---|---|
| Temel (şablonsuz, filtresiz) | 0.524 | 0.857 | 0.657 | 0.595 | 0.857 | 0.717 |
| Şablon: "bir fotoğraf: {q}" / "a photo of {q}" | 0.500 | 0.810 | 0.658 | 0.619 | 0.881 | 0.734 |
| Kategori filtresi (insan etiketi) | 0.571 | 0.667 | 0.615 | 0.595 | 0.667 | 0.627 |

### Başarısız sorgular

| Tür | Sorgu | Beklenen | Sıra | 1. sıradaki | Doğru skor | En iyi yanlış |
|---|---|---|---|---|---|---|
| TR metin | omuzdan takılan küçük siyah çantamı kafede unuttum | crossbody_bag_black | 2 | backpack_gray | 0.294 | 0.296 |
| TR metin | siyah bez çanta kayboldu askılı | crossbody_bag_black | 2 | backpack_gray | 0.281 | 0.286 |
| TR metin | kulaklığımın siyah kutusunu amfide bıraktım | earbud_case_square_black | 6 | single_earbud_black | 0.253 | 0.270 |
| TR metin | siyah bluetooth kulaklık kutusu arıyorum | earbud_case_square_black | 5 | single_earbud_black | 0.238 | 0.256 |
| TR metin | telefon şarj başlığımı prizde unuttum | charger_adapter_white | 7 | cigarette_pack_lighter | 0.233 | 0.245 |
| TR metin | beyaz şarj aleti kayıp | charger_adapter_white | 5 | powerbank_white | 0.250 | 0.262 |
| TR metin | yemekhanede powerbankimi unuttum | powerbank_white | 5 | charger_adapter_white | 0.238 | 0.249 |
| TR metin | kulaklık kutumu kütüphanede unuttum beyaz | earbud_case_white_open | 13 | earbuds_white_pair | 0.239 | 0.280 |
| TR metin | içi boş beyaz şarj kutusu | earbud_case_white_open | 4 | powerbank_white | 0.245 | 0.274 |
| TR metin | askeri desenli çantam spor salonunda kaldı | camo_bag_keychain | 3 | backpack_gray | 0.270 | 0.306 |
| TR metin | sınavda silgimi unuttum mavi | eraser_blue | 2 | ballpoint_pen_white | 0.258 | 0.263 |
| TR metin | kılıflı silgi | eraser_blue | 12 | stylus_white | 0.231 | 0.242 |
| TR metin | puantiyeli kalemimi kaybettim | mechanical_pencil_dotted | 3 | ballpoint_pen_white | 0.272 | 0.309 |
| TR metin | siyah beyaz benekli uçlu kalem | mechanical_pencil_dotted | 5 | ballpoint_pen_white | 0.265 | 0.303 |
| TR metin | siyah kulaklık kutum kayboldu çizik çizik | earbud_case_oval_black | 4 | single_earbud_black | 0.237 | 0.247 |
| TR metin | kafeteryada kulaklık şarj kutusu unuttum | earbud_case_oval_black | 12 | single_earbud_black | 0.235 | 0.272 |
| TR metin | tabletimi kütüphanede unuttum | tablet_navy_case | 18 | eraser_blue | 0.220 | 0.259 |
| TR metin | ekran kalemi düşürdüm amfide | stylus_white | 2 | ballpoint_pen_white | 0.292 | 0.297 |
| TR metin | yuvarlak gözlüğümü kaybettim | glasses_round_metal | 2 | glasses_browline | 0.266 | 0.301 |
| TR metin | ince telli siyah gözlük | glasses_round_metal | 2 | glasses_browline | 0.270 | 0.287 |
| EN metin | i forgot my small black shoulder bag at the cafe | crossbody_bag_black | 2 | backpack_gray | 0.279 | 0.282 |
| EN metin | lost a black fabric bag with a strap | crossbody_bag_black | 2 | backpack_gray | 0.303 | 0.323 |
| EN metin | i left the black case of my earphones in the lecture hall | earbud_case_square_black | 5 | single_earbud_black | 0.274 | 0.324 |
| EN metin | looking for a black bluetooth earbuds case | earbud_case_square_black | 13 | single_earbud_black | 0.231 | 0.273 |
| EN metin | i forgot my power bank in the dining hall | powerbank_white | 5 | charger_adapter_white | 0.246 | 0.271 |
| EN metin | white portable charger with a display | powerbank_white | 2 | charger_adapter_white | 0.286 | 0.298 |
| EN metin | i forgot my earbuds case in the library, it's white | earbud_case_white_open | 9 | earbuds_white_pair | 0.242 | 0.302 |
| EN metin | empty white charging case | earbud_case_white_open | 9 | powerbank_white | 0.257 | 0.312 |
| EN metin | my camouflage pattern bag was left at the gym | camo_bag_keychain | 3 | backpack_gray | 0.274 | 0.331 |
| EN metin | i lost my black wallet at the bus stop | wallet_black_fabric | 2 | crossbody_bag_black | 0.284 | 0.284 |
| EN metin | i lost my polka dot pencil | mechanical_pencil_dotted | 4 | ballpoint_pen_white | 0.252 | 0.286 |
| EN metin | black and white spotted mechanical pencil | mechanical_pencil_dotted | 2 | ballpoint_pen_white | 0.282 | 0.302 |
| EN metin | my black earbuds case is lost, it's all scratched | earbud_case_oval_black | 7 | single_earbud_black | 0.254 | 0.293 |
| EN metin | i forgot an earbuds charging case in the cafeteria | earbud_case_oval_black | 13 | single_earbud_black | 0.236 | 0.300 |
| EN metin | i forgot my tablet in the library | tablet_navy_case | 10 | crossbody_bag_black | 0.242 | 0.263 |
| EN metin | i lost my round glasses | glasses_round_metal | 2 | glasses_browline | 0.258 | 0.301 |
| EN metin | thin black wire frame glasses | glasses_round_metal | 2 | glasses_browline | 0.328 | 0.329 |
| Görsel | 094141.jpg | glasses_round_metal | 5 | glasses_browline | 0.759 | 0.866 |

Gecikme (API'nin `took_ms` değeri, 21 ilanla): metin sorgularında medyan yaklaşık 29 ms (en fazla 38 ms), görsel sorgularda medyan 73 ms (en fazla 79 ms). Görsel sorgu süresine görselin kodlanması da dahil. İki değer de hedefin (arama < 300 ms, görsel kodlama < 1 sn) altında.

## Yorum
- **Recall@5:** TR ve EN metin için 0.857, görsel için 1.0. PLAN'daki 0.7 sınırı aşıldı, bu nedenle iyileştirme denemeleri zorunlu değildi. Aşağıdaki denemeler bilgi amacıyla yapıldı.
- **Recall@1 düşük:** TR metinde 0.524, EN metinde 0.595. Hataların neredeyse hepsi benzer eşyalar arasında karışmadan geliyor. Kulaklık kutuları "tek siyah kulaklık" ilanına, kalemler birbirine, şarj adaptörü ve powerbank birbirine, iki gözlük birbirine gidiyor. Kamuflaj çanta ve çapraz çanta ise gri sırt çantasına kayıyor.
- **TR ile EN farkı küçük:** R@1'de 0.524'e karşı 0.595, R@5'te ikisi de 0.857. Çok dilli metin modeli Türkçe sorgularda İngilizce karşılıklarına göre biraz geride, ama sıralama kalitesi (R@5) aynı.
- **"tabletimi kütüphanede unuttum" sorgusu 18. sırada kaldı.** İlan fotoğrafı tableti kapalı kılıfıyla gösteriyor, bu yüzden görselde "tablet" değil lacivert bir kapak görünüyor. Aynı tabletin ekran tarafından çekilmiş görsel sorgusu ise ilanı 1. sırada buldu.
- **Görsel sorguda tek hata:** yuvarlak gözlüğün ikinci açısı 5. sırada kaldı; 1. sırada diğer siyah gözlük çıktı (skor 0.866'ya karşı 0.759).
- **Metin skoru doğruyu en benzer yanlıştan ayıramıyor:** doğru ilanın skoru (medyan 0.278) ile en iyi yanlış ilanın skoru (medyan 0.280) neredeyse aynı dağılımda. Doğru ilan ile en iyi yanlış arasında en iyi tek eşik 0.305, Youden J yalnızca 0.107. Doğru ilanı öne çıkaran şey mutlak skor değil, sıralama. Buna karşılık doğru ilan, ilgisiz ilanların büyük kısmından (tüm yanlışlar, medyan 0.234) belirgin biçimde ayrışıyor (J = 0.605).

## Eşik önerisi ve gerekçe
API, metin ve görsel aramada tek ve ortak bir eşik çifti kullanıyor (`MATCH_HIGH`, `MATCH_MEDIUM`). Görsel-görsel skorları metin-görsel skorlarından çok daha yüksek: görselde yanlış ilanların bile medyanı 0.698, en düşüğü 0.506. Bu nedenle eşik metin skorlarına göre ayarlandı.

- **MATCH_MEDIUM = 0.255** (eski 0.24): doğru ilan ile bütün yanlış ilanları en iyi ayıran eşik (Youden J = 0.605). Doğru eşleşmelerin %77'si bu eşiği geçiyor, ilgisiz ilanların %17'si geçiyor. Benzer bir eşyanın (en iyi yanlış) bu eşiği geçme oranı ise %86. Yani "orta" düzeyi "ilgili olabilir" anlamına geliyor, "kesin bu" anlamına gelmiyor.
- **MATCH_HIGH = 0.315** (eski 0.30): sorgu başına en iyi yanlış skorların 90. yüzdeliği, 0.005'e yukarı yuvarlandı. En benzer yanlış ilanın bu eşiği geçme oranı %7, bütün yanlışlarınki %0.4. Bunun bedeli, doğru eşleşmelerin yalnızca %14'ünün "yüksek" etiketi alması. Bu bilinçli olarak temkinli bir seçim: "yüksek" etiketi az verilsin ama verildiğinde güvenilir olsun.
- Yeni eşiklerle metin sorgularında doğru ilanın düzeyi: 12 yüksek, 53 orta, 19 düşük (toplam 84). En iyi yanlış ilanın düzeyi: 6 yüksek, 66 orta, 12 düşük.
- **Görsel aramada etiket ayırt edici değil:** ortak eşik nedeniyle 7 görsel sorgunun hepsinde hem doğru hem en iyi yanlış ilan "yüksek" görünüyor. Görsel arama için ayrı bir eşik gerekir. Bu bir API değişikliği olduğu için yapılmadı; kullanıcı onayına bağlı.
- Eşikler `backend/app/config.py`, `.env.example`, `docker-compose.yml` ve `docs/PLAN.md` dosyalarında güncellendi. Çalışan konteyner yeniden başlatılana kadar eski değerleri kullanmaya devam eder.

## Denemeler (yalnızca betik içinde; API davranışı değiştirilmedi)
1. **Şablon** ("bir fotoğraf: {q}" / "a photo of {q}"): TR R@5 0.857'den 0.810'a düştü, R@1 0.524'ten 0.500'e indi, MRR neredeyse aynı kaldı (0.657'den 0.658'e). EN'de küçük bir artış oldu (R@1 0.595'ten 0.619'a, R@5 0.857'den 0.881'e). Türkçe sorgularda fayda görülmediği için uygulanmadı.
2. **Kategori filtresi** (kullanıcının seçeceği kategori elle verildi): R@5 TR ve EN'de 0.857'den 0.667'ye düştü. Nedeni şu: filtre ilanın otomatik etiketine göre çalışıyor ve otomatik kategori etiketleyici 21 ilandan yalnızca 14'ünde insan etiketiyle aynı kategoriyi verdi. Örnekler: powerbank "cüzdan", silgi "cüzdan", versatil kalem "şarj aleti", beyaz kulaklık kutusu "gözlük", çapraz çanta "sırt çantası" olarak etiketlendi. Etiket yanlışsa filtre doğru ilanı tamamen dışarıda bırakıyor. Bu yüzden önerilmez.
3. **Füzyon ağırlığı:** uygulanmadı. R@5 sınırı zaten aşılmıştı; ayrıca sorgu setinde metin ve görselin birlikte gönderildiği sorgu yok ve ağırlık API'de 0.5 olarak sabit.

## "siyah sırt çantası" kontrolü (Faz 2'den ertelenen)
Uygulanamadı. Yeni sette siyah sırt çantası yok: çantalar gri melanj, gri-lacivert kamuflaj ve siyah küçük çapraz çanta. Yine de "siyah sırt çantası" sorgusu bilgi amacıyla çalıştırıldı. İlk 3 sonuç: gri sırt çantası (0.306), siyah küçük çapraz çanta (0.299), siyah cüzdan (0.275). Kontrolün asıl amacına uygun yapılabilmesi için sete siyah bir sırt çantası fotoğrafı eklenmesi gerekir.

## Bilinen sorunlar
- **Saatte yanlış yüz algılandı:** "Yeşil kadranlı metal kol saati" ilanında YuNet saatin kadranını yüz sandı (`faces_blurred = 1`, eşik 0.6). Bu yüzden saklanan görselde kadran bulanık. Bu ilanın metin sorguları yine de 1. sırada çıktı. Gizlilik açısından güvenli yönde bir hata, ama ilan görselini bozuyor. Ayar değişikliği kullanıcı kararına bırakıldı.

## Sınırlamalar
- **n küçük:** 21 ilan, 42 TR ve 42 EN metin sorgusu, 7 görsel sorgu. Tek bir sorgu TR'de R@1'i yaklaşık 0.024, görselde 0.143 değiştiriyor. Görsel sonuçlar (R@1 0.857) özellikle kırılgan.
- **Eşikler aynı veriyle ayarlandı ve aynı veriyle raporlandı.** Ayrı bir doğrulama kümesi yok, bu yüzden eşikler bu sete aşırı uyumlu (overfit) olabilir. Gerçek kullanımda gelen ilanlarla yeniden ölçülmeli.
- **Siyah ve benzer eşyalar yoğun:** R@1 bu yüzden düşük. Bu demo setinin bir özelliği; kampüs genelindeki eşya dağılımını temsil ettiği varsayılamaz.
- **İngilizce sorgular** Türkçe sorguların elle yapılmış çevirisi; bağımsız yazılmış İngilizce sorgular değil.
- **Sorguları ilanları hazırlayan kişi yazdı.** Marka ve görselden okunan ayrıntılar kullanılmadı, yine de gerçek kullanıcı sorgularından daha "isabetli" olabilirler.
