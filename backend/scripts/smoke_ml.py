"""Gerçek modellerle hızlı ML kontrolü (CPU, çevrimdışı).

Kullanım (backend/ dizininden):  python scripts/smoke_ml.py
Modeller MODEL_CACHE_DIR / FACE_MODEL_PATH ortam değişkenlerinden, yoksa backend/data/models'tan okunur.
Sentetik görseller: gri zeminde gürültülü renkli nesne (düz renk kareler CLIP için yanıltıcıdır).
"""
import json
import os
import platform
import resource
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.ml.encoder import ClipEncoder  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.ml.image_io import load_and_sanitize  # noqa: E402
from app.ml.tagger import Tagger  # noqa: E402

LOCAL_MODELS = BACKEND_DIR / "data" / "models"
CACHE = os.environ.get("MODEL_CACHE_DIR") or str(LOCAL_MODELS)
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "clip-ViT-B-32")
TEXT_MODEL = os.environ.get("TEXT_MODEL", "sentence-transformers/clip-ViT-B-32-multilingual-v1")
THREADS = int(os.environ.get("TORCH_NUM_THREADS", "4"))
CAMPUS = json.loads((BACKEND_DIR / "app" / "data" / "campus.json").read_text("utf-8"))

COLOR_RGB = {
    "siyah": (15, 15, 15), "beyaz": (245, 245, 245), "gri": (175, 175, 175), "kırmızı": (210, 30, 35),
    "mavi": (40, 110, 230), "lacivert": (20, 30, 90), "yeşil": (35, 160, 60), "sarı": (240, 215, 40),
    "turuncu": (245, 130, 20), "mor": (120, 50, 160), "pembe": (240, 140, 180), "kahverengi": (110, 65, 30),
    "bej": (220, 200, 160),
}


def rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024  # macOS bayt, Linux KB


def object_image(rgb, size=(224, 224), seed=0) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, (128, 128, 128))
    ImageDraw.Draw(img).rounded_rectangle((int(w * .18), int(h * .13), int(w * .82), int(h * .87)), radius=min(w, h) // 7, fill=rgb)
    noise = np.random.default_rng(seed).integers(-12, 13, (h, w, 3))
    return Image.fromarray((np.asarray(img, dtype=np.int16) + noise).clip(0, 255).astype(np.uint8))


def timed(fn, reps=10):
    ts = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1000)
    return float(np.mean(ts)), float(np.max(ts))


def section(title):
    print(f"\n=== {title} ===")


def main() -> int:
    section("Ortam")
    print(f"{platform.platform()} | {platform.processor() or platform.machine()} | çekirdek={os.cpu_count()}")
    print(f"torch={torch.__version__} threads={THREADS} | model önbelleği={CACHE}")

    section("Model yükleme")
    t = time.perf_counter()
    enc = ClipEncoder(IMAGE_MODEL, TEXT_MODEL, cache_folder=CACHE, threads=THREADS)
    print(f"ClipEncoder (iki model + ısınma): {(time.perf_counter() - t) * 1000:.0f} ms | dim={enc.dim} | tepe RSS={rss_mb():.0f} MB")

    section("Gecikme (ısınma sonrası, 10 tekrar)")
    big = object_image(COLOR_RGB["mavi"], size=(1024, 768))
    m, x = timed(lambda: enc.encode_images([big]))
    print(f"tek görsel kodlama (1024x768): ort {m:.1f} ms, maks {x:.1f} ms")
    raw = np.asarray(object_image(COLOR_RGB["mavi"], size=(4000, 3000)))
    import io
    buf = io.BytesIO()
    Image.fromarray(raw).save(buf, "JPEG", quality=90)
    data = buf.getvalue()
    m, x = timed(lambda: load_and_sanitize(data, 1024, get_settings().max_image_pixels))
    print(f"load_and_sanitize (4000x3000 JPEG -> 1024): ort {m:.1f} ms, maks {x:.1f} ms")
    m, x = timed(lambda: enc.encode_texts(["siyah sırt çantası, üzerinde anahtarlık var"]))
    print(f"tek metin kodlama: ort {m:.1f} ms, maks {x:.1f} ms")

    section("Benzerlik matrisi (satır=Türkçe sorgu, sütun=görsel)")
    names = ["kırmızı", "mavi", "yeşil"]
    I = enc.encode_images([object_image(COLOR_RGB[n], seed=i) for i, n in enumerate(names)])
    queries = ["kırmızı bir eşya", "mavi bir eşya", "yeşil bir eşya"]
    T = enc.encode_texts(queries)
    S = T @ I.T
    print(" " * 20 + "".join(f"{n:>10s}" for n in names))
    for i, q in enumerate(queries):
        margin = S[i, i] - np.delete(S[i], i).max()
        print(f"{q:20s}" + "".join(f"{v:10.3f}" for v in S[i]) + f"   marj {margin:+.3f} {'OK' if np.argmax(S[i]) == i else 'HATA'}")

    section("Etiketleyici şablon karşılaştırması (13 sentetik renkli nesne)")
    color_names = [c["tr"] for c in CAMPUS["colors"]]
    imgs = [object_image(COLOR_RGB[n], seed=i) for i, n in enumerate(color_names)]
    E = enc.encode_images(imgs)
    taggers = {}
    for tpl in ("tr", "en", "avg"):
        t = time.perf_counter()
        taggers[tpl] = Tagger(enc, CAMPUS["categories"], CAMPUS["colors"], template=tpl)
        build_ms = (time.perf_counter() - t) * 1000
        tg = taggers[tpl]
        preds, probs, other = [], [], 0
        for e in E:
            cp = tg.color_probs(e)
            preds.append(tg.color_names[int(np.argmax(cp))])
            probs.append(float(cp.max()))
            other += tg.tag(e)[0] == "diğer"
        acc = np.mean([p == g for p, g in zip(preds, color_names)])
        wrong = ", ".join(f"{g}->{p}" for p, g in zip(preds, color_names) if p != g) or "-"
        print(f"[{tpl:3s}] renk doğruluğu {acc * 100:.0f}% ({int(acc * 13)}/13) | ort renk güveni {np.mean(probs):.3f} "
              f"| kategori='diğer' {other}/13 | istem hazırlama {build_ms:.0f} ms | hatalar: {wrong}")

    raw_dir = REPO_DIR / "demo_data" / "raw"
    photos = sorted(p for p in raw_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}) if raw_dir.is_dir() else []
    if photos:
        section(f"demo_data/raw kategori çıktıları ({len(photos)} fotoğraf)")
        for p in photos:
            e = enc.encode_images([load_and_sanitize(p.read_bytes(), 1024, get_settings().max_image_pixels)])[0]
            cells = []
            for tpl, tg in taggers.items():
                c, s, col = tg.tag(e)
                cells.append(f"{tpl}: {c} ({s:.2f}), {col}")
            print(f"{p.name}: " + " | ".join(cells))
    else:
        print("demo_data/raw yok; gerçek fotoğraflarda kategori karşılaştırması Faz 6'ya kaldı.")

    section("Arama gecikmesi (1000 rastgele öğe, Store)")
    try:
        from app.store import Store
    except ImportError as exc:
        print(f"app.store yüklenemedi: {exc}")
        return 0
    rng = np.random.default_rng(42)
    locs, cats = CAMPUS["locations"], [c["tr"] for c in CAMPUS["categories"]]
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(tmp, dim=enc.dim)
        t = time.perf_counter()
        for i in range(1000):
            v = rng.standard_normal(enc.dim).astype(np.float32)
            store.add({
                "title": f"Eşya {i}", "description": "", "location": locs[i % len(locs)],
                "found_date": "2026-10-26", "dropoff_point": CAMPUS["dropoff_points"][0],
                "image_path": f"{i}.jpg", "category": cats[i % len(cats)], "category_score": 0.5,
                "color": color_names[i % len(color_names)], "faces_blurred": 0,
            }, v / np.linalg.norm(v))
        print(f"1000 ekleme: {(time.perf_counter() - t) * 1000:.0f} ms")
        q = enc.encode_texts(["siyah sırt çantası"])[0]
        m, x = timed(lambda: store.search(q, top_k=12), reps=100)
        print(f"arama (filtresiz, top_k=12, 100 tekrar): ort {m:.2f} ms, maks {x:.2f} ms")
        m, x = timed(lambda: store.search(q, location=locs[0], category=cats[3], top_k=12), reps=100)
        print(f"arama (yer+kategori filtreli): ort {m:.2f} ms, maks {x:.2f} ms")
        m, x = timed(lambda: store.search(enc.encode_texts(["siyah sırt çantası"])[0], top_k=12), reps=20)
        print(f"uçtan uca metin kodlama + arama (20 tekrar): ort {m:.1f} ms, maks {x:.1f} ms")
        store.close()
    print(f"\ntepe RSS: {rss_mb():.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
