# Kampüs Kayıp Eşya: Proje Anayasası

Bu dosya her oturumda geçerlidir. Burada yazmayan bir şeyi yapmadan önce kullanıcıya sor.

## Ürün (tek cümle)
GTÜ kampüsünde bulunan eşyaların fotoğrafını yükleyen kişi ile eşyasını kaybeden kişiyi, çok dilli CLIP embedding'leriyle (Türkçe metinden görsele ve görselden görsele) anlamsal arama yaparak buluşturan, yüzleri otomatik bulanıklaştıran ve tamamen yerelde/CPU'da çalışan web uygulaması.

## MUTLAK YASAKLAR (yarışma şartnamesi; ihlal = diskalifiye)
1. YOLO ailesinden hiçbir model ya da paket (ultralytics, yolov5/v8/11...) kullanılmaz, önerilmez, kurulmaz.
2. Ürün içinde bulut yapay zekâ servisi çağrılmaz: OpenAI, Anthropic/Claude API, Gemini, Groq, Cohere, Replicate, HF Inference API vb. Bütün modeller konteyner içinde yerelde çalışır. Çalışma zamanında HF_HUB_OFFLINE=1 olur.
3. GPU varsayılmaz; her şey CPU'da makul sürede çalışır (görsel kodlama < 1 sn, arama < 300 ms hedef).
4. Model eğitimi çalıştırma bilgisayarında yapılmaz. Ağırlıklar Docker build sırasında otomatik iner; elle dosya kopyalama adımı olmaz.
5. Şifre, token ve gizli bilgi depoya yazılmaz. `.env` git'e girmez; yalnızca `.env.example` örnek değerlerle bulunur. `.env` dosyasını OKUMA.
6. Kişisel veri: Kimsenin yüzü izinsiz gösterilmez; yüklenen her görselde yüz bulanıklaştırma çalışır ve orijinal görsel diske YAZILMAZ. EXIF (GPS dahil) silinir. Telefon, e-posta veya isim gibi iletişim bilgisi toplanmaz; eşya bir "teslim noktasına" bırakılır.
7. İnternetten demo görseli indirilmez. Demo görselleri kullanıcının kendi çektiği, yüz içermeyen fotoğraflardır.
8. Git: `push --force`, `reset --hard`, `rebase` ve geçmişi değiştiren hiçbir komut yok. Commit tarihleri değiştirilmez. Push için her seferinde kullanıcı onayı gerekir.
9. Debug modu kapalı; frontend dev sunucusuyla değil, derlenmiş haliyle nginx üzerinden sunulur.

## KAPSAM SINIRI
- Yalnızca docs/PLAN.md'deki fazlar ve oradaki kabul kriterleri uygulanır. Plan dışı özellik, kütüphane, servis veya sayfa EKLENMEZ. Fikir varsa docs/ILERLEME.md "Fikir Havuzu" bölümüne yazılır ve kullanıcıya sorulur.
- İzinli bağımlılıklar: Backend: fastapi, uvicorn[standard], python-multipart, pydantic, pydantic-settings, sentence-transformers, torch (CPU), numpy, pillow, opencv-python-headless, pytest, httpx. Frontend: react, react-dom, vite, @vitejs/plugin-react, typescript. Bu liste dışına çıkmak kullanıcı onayı ister.
- Yerel LLM, kimlik doğrulama sistemi, harici veritabanı sunucusu, bildirim/e-posta servisi ve mobil uygulama KAPSAM DIŞIDIR.

## Teknik kararlar (değiştirmeden önce sor)
- Görsel encoder: sentence-transformers `clip-ViT-B-32` (512 boyut). Metin encoder: `sentence-transformers/clip-ViT-B-32-multilingual-v1` (Türkçe dahil 50+ dil, aynı uzaya hizalı). Embedding'ler L2-normalize edilir; benzerlik = kosinüs (nokta çarpım).
- Yüz bulanıklaştırma: OpenCV YuNet (`cv2.FaceDetectorYN`, `face_detection_yunet_2023mar.onnx`), build sırasında indirilir.
- Saklama: SQLite (`$DATA_DIR/app.db`), embedding'ler float32 BLOB; başlangıçta numpy matrisine yüklenir. Görseller: `$DATA_DIR/uploads/<uuid>.jpg` (yalnızca bulanıklaştırılmış ve küçültülmüş kopya).
- Backend: Python 3.12, FastAPI, uvicorn, python:3.12-slim imajı, 0.0.0.0:8000. Frontend: React + Vite + TypeScript, düz CSS, nginx:alpine üzerinden sunulur, port 3000→80.
- Bütün ayarlar ortam değişkenlerinden okunur (pydantic-settings), koda gömülmez.
- Kod tanımlayıcıları İngilizce; kullanıcıya görünen metinler ve hata mesajları Türkçe.

## Klasör yapısı
backend/  (Dockerfile, requirements.txt, app/, scripts/, tests/)
frontend/ (Dockerfile, nginx.conf, package.json, src/)
docs/     (PLAN.md, ILERLEME.md, AI_KULLANIM_GUNLUGU.md, SARTNAME_KONTROL.md, EVAL.md, VIDEO_SENARYOSU.md)
demo_data/ (kullanıcının fotoğrafları + items.json + queries.json)
docker-compose.yml, .env.example, README.md

## Çalışma şekli
- Her oturumda önce docs/ILERLEME.md ve docs/PLAN.md'deki ilgili fazı oku.
- Her faza plan modunda başla: dosya listesi, adımlar, riskler, kabul kriterleri. Onay olmadan dosya yazma.
- Küçük adımlarla ilerle. Her anlamlı değişiklikten sonra testi çalıştır ve commit at. Commit mesajları Türkçe, geçmiş zaman, ne yapıldığını anlatır (örnek: "Görsel yükleme uç noktası eklendi"). Bir commit = bir anlamlı değişiklik.
- Yerel testler kökteki mevcut venv ile çalışır (yeni venv oluşturma). Backend bağımlılıkları bu venv'e kurulur.
- Sürümleri uydurma: Paketi venv'e kur, çalışan sürümü `pip show` ile öğren ve requirements.txt'e `==` ile sabitle.
- Faz sonunda: testler → spec-guard agent'ı → docs/ILERLEME.md güncelle → docs/AI_KULLANIM_GUNLUGU.md'ye kayıt → commit → push için kullanıcıya sor.
- Emin olmadığın bir API veya kütüphane davranışını tahmin etme; küçük bir betikle venv'de dene.
- Bir şey bozulursa kök nedeni bul. Testi silerek veya atlayarak "yeşil" yapma.
