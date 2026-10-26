"""Bir görselde OCR + kişisel veri sansürü + yüz bulanıklaştırmayı elle denemek için.

Kullanım (kök dizinden):
    .venv/bin/python backend/scripts/try_redact.py <girdi> redact_out/<çıktı>.jpg
Konsola yalnızca SAYILAR ve izin listesinden gelen etiketler yazılır; ham OCR metni yazılmaz.
redact_out/ git tarafından yok sayılır.
"""
import argparse
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from PIL import Image  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.ml.face_blur import FaceBlurError, FaceBlurrer  # noqa: E402
from app.ml.image_io import InvalidImageError, load_and_sanitize  # noqa: E402
from app.ml.ocr import OcrEngine, OcrError, confident_words  # noqa: E402
from app.ml.pii import find_redactions, redact  # noqa: E402
from app.ml.tags import extract_tags, load_brands  # noqa: E402


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="OCR ile kişisel veri sansürü denemesi")
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    model_path = settings.face_model_path
    local = BACKEND_DIR / "data" / "models" / "face_detection_yunet_2023mar.onnx"
    if not os.path.isfile(model_path) and local.is_file():
        model_path = str(local)

    engine = OcrEngine(settings.ocr_langs, settings.ocr_timeout_s, settings.ocr_min_conf)
    if not engine.available:
        print("HATA: Tesseract ya da dil verisi (%s) bulunamadı." % settings.ocr_langs, file=sys.stderr)
        return 1
    blurrer = FaceBlurrer(model_path, settings.face_score_threshold, settings.face_blur_enabled)
    if not blurrer.available:
        print("UYARI: Yüz modeli yüklenemedi; yüz bulanıklaştırma atlanıyor.", file=sys.stderr)

    try:
        data = Path(args.input).read_bytes()
    except OSError:
        print("HATA: Girdi okunamadı.", file=sys.stderr)
        return 1

    t_total = time.perf_counter()
    try:
        t0 = time.perf_counter()
        work = load_and_sanitize(data, max(settings.ocr_max_side, settings.max_image_side))
        load_ms = _ms(t0)
        t0 = time.perf_counter()
        words = engine.run_ocr(work)
        ocr_ms = _ms(t0)
        t0 = time.perf_counter()
        blurred, faces = blurrer.blur(work)
        face_ms = _ms(t0)
    except InvalidImageError as exc:
        print(f"HATA: {exc.message}", file=sys.stderr)
        return 1
    except (OcrError, FaceBlurError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    result = find_redactions(words, faces, work.size)
    out = redact(blurred, result.boxes)
    tags = [] if result.document_like else extract_tags(confident_words(words, settings.ocr_min_conf), result.boxes, load_brands())
    pii_ms = _ms(t0)
    out.thumbnail((settings.max_image_side, settings.max_image_side), Image.Resampling.LANCZOS)
    total_ms = _ms(t_total)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, "JPEG", quality=85)

    print(f"çalışma kopyası: {work.size[0]}x{work.size[1]}, çıktı: {out.size[0]}x{out.size[1]}")
    print(f"kelime: {len(words)}, sansür kutusu: {len(result.boxes)}, belge benzeri: {result.document_like}, yüz: {faces}")
    print(f"etiketler: {', '.join(tags) if tags else '-'}")
    print(f"süre (ms): açma {load_ms}, ocr {ocr_ms}, yüz {face_ms}, pii+sansür {pii_ms}, toplam {total_ms}")
    print(f"Çıktı: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
