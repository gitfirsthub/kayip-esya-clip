"""Demo ilanlarını çalışan API'ye yükler.

Kullanım (kök dizinden):  python backend/scripts/seed_demo.py [--api-url http://localhost:8000]
API adresi --api-url, yoksa API_URL ortam değişkeni, yoksa http://localhost:8000.

1. demo_data/raw/<dosya> varsa: EXIF yönü uygulanır, en uzun kenar <= 1024 px'e küçültülür,
   EXIF'siz JPEG olarak demo_data/images/<key>.jpg (ilanlar) ve
   demo_data/images/queries/<ad>.jpg (görsel sorgular) yazılır.
2. raw yoksa daha önce üretilmiş images/ kopyaları kullanılır (raw git'e girmez).
3. Her ilan images/ kopyasından POST /api/items ile gönderilir; aynı başlık zaten varsa atlanır.
Görsel sorgular POST edilmez; yalnızca eval için kopyalanır.
"""
import argparse
import io
import json
import os
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageOps

REPO_DIR = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_DIR / "demo_data"
RAW_DIR = DEMO_DIR / "raw"
IMAGES_DIR = DEMO_DIR / "images"
QUERY_IMAGES_DIR = IMAGES_DIR / "queries"
MAX_SIDE = 1024
JPEG_QUALITY = 85


def shrink_to_jpeg(src: Path, dst: Path) -> None:
    """EXIF yönünü uygular, küçültür ve meta verisiz JPEG yazar (orijinal raw'da kalır)."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        # Piksellerden yeni görsel: EXIF, GPS, ICC vb. hiçbir meta veri taşınmaz.
        clean = Image.new("RGB", im.size)
        clean.paste(im)
    dst.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    clean.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
    dst.write_bytes(buf.getvalue())


def query_image_name(raw_name: str) -> str:
    """'WhatsApp Image 2026-10-26 at 09.40.16 (1).jpeg' -> '094016_1.jpg'"""
    stem = Path(raw_name).stem.split(" at ")[-1]
    return stem.replace(".", "").replace(" (", "_").replace(")", "") + ".jpg"


def prepare(src_name: str, dst: Path) -> Path:
    raw = RAW_DIR / src_name
    if raw.is_file():
        shrink_to_jpeg(raw, dst)
    elif not dst.is_file():
        sys.exit(f"Görsel bulunamadı: ne {raw} ne {dst} var.")
    return dst


def prepare_query_images() -> None:
    path = DEMO_DIR / "queries.json"
    queries = json.loads(path.read_text("utf-8"))
    changed = False
    for q in queries["image"]:
        name = Path(q["file"]).name
        if q["file"].startswith("images/queries/"):
            src_name, dst_name = None, name
        else:
            src_name, dst_name = name, query_image_name(name)
        dst = QUERY_IMAGES_DIR / dst_name
        if src_name:
            prepare(src_name, dst)
            q["file"] = f"images/queries/{dst_name}"
            changed = True
        elif not dst.is_file():
            sys.exit(f"Sorgu görseli yok: {dst}")
    if changed:
        lines = [json.dumps(t, ensure_ascii=False) for t in queries["text"]]
        imgs = [json.dumps(i, ensure_ascii=False) for i in queries["image"]]
        body = '{\n  "text": [\n    ' + ",\n    ".join(lines) + '\n  ],\n  "image": [\n    ' + ",\n    ".join(imgs) + "\n  ]\n}\n"
        path.write_text(body, "utf-8")
    print(f"Sorgu görselleri hazır: {len(queries['image'])} dosya -> {QUERY_IMAGES_DIR.relative_to(REPO_DIR)}")


def existing_titles(client: httpx.Client) -> set[str]:
    titles, offset = set(), 0
    while True:
        r = client.get("/api/items", params={"limit": 100, "offset": offset})
        r.raise_for_status()
        data = r.json()
        titles.update(i["title"] for i in data["items"])
        offset += len(data["items"])
        if not data["items"] or offset >= data["total"]:
            return titles


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo ilanlarını API'ye yükler.")
    parser.add_argument("--api-url", default=os.environ.get("API_URL", "http://localhost:8000"))
    args = parser.parse_args()

    items = json.loads((DEMO_DIR / "items.json").read_text("utf-8"))
    for it in items:
        prepare(it["file"], IMAGES_DIR / f"{it['key']}.jpg")
    print(f"İlan görselleri hazır: {len(items)} dosya -> {IMAGES_DIR.relative_to(REPO_DIR)}")
    prepare_query_images()

    created = skipped = 0
    with httpx.Client(base_url=args.api_url, timeout=60) as client:
        health = client.get("/health").json()
        print(f"API: {args.api_url}  item_count (önce) = {health['item_count']}")
        titles = existing_titles(client)
        for it in items:
            if it["title"] in titles:
                print(f"  atlandı (zaten var): {it['key']}")
                skipped += 1
                continue
            img = IMAGES_DIR / f"{it['key']}.jpg"
            fields = {k: it[k] for k in ("title", "description", "location", "dropoff_point", "found_date")}
            r = client.post("/api/items", data=fields, files={"image": (img.name, img.read_bytes(), "image/jpeg")})
            if r.status_code != 201:
                sys.exit(f"Yükleme başarısız ({it['key']}): {r.status_code} {r.text}")
            body = r.json()
            print(f"  eklendi: {it['key']:<26} kategori={body['category']:<16} renk={body['color']:<10} yüz={body['faces_blurred']}")
            created += 1
        health = client.get("/health").json()
    print(f"Eklenen: {created}, atlanan: {skipped}, item_count (sonra) = {health['item_count']}")


if __name__ == "__main__":
    main()
