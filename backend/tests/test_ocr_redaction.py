"""OCR + PII sansürü uçtan uca testleri (sentetik görseller). Tesseract ya da TTF yazı tipi yoksa atlanır.
Bütün numaralar ve adlar UYDURMADIR."""
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.ml.ocr import OcrEngine, OcrError
from app.ml.pii import find_redactions, redact
from app.ml.tags import extract_tags, load_brands

FAKE_TCKN = "12345678901"
FAKE_PHONE = "05321234567"
LANGS = "tur+eng"
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font_path() -> str | None:
    return next((p for p in FONT_CANDIDATES if Path(p).is_file()), None)


def _engine(timeout_s: float = 30) -> OcrEngine:
    return OcrEngine(LANGS, timeout_s=timeout_s, min_conf=30)


TESSERACT_READY = shutil.which("tesseract") is not None and _engine().available
needs_tesseract = pytest.mark.skipif(not TESSERACT_READY, reason="tesseract ya da tur+eng dil verisi kurulu değil")
needs_font = pytest.mark.skipif(_font_path() is None, reason="TTF yazı tipi bulunamadı")


def _render(rows, size=(1400, 700), font_size=56, start_y=40, step=90):
    """Beyaz zemine siyah satırlar çizer; her satırın metin kutusunu döndürür."""
    font = ImageFont.truetype(_font_path(), font_size)
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    bboxes = []
    for n, text in enumerate(rows):
        xy = (60, start_y + n * step)
        draw.text(xy, text, fill="black", font=font)
        bboxes.append(draw.textbbox(xy, text, font=font))
    return img, bboxes


def _ink(img: Image.Image, bbox) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    return np.asarray(img.convert("L"))[y0:y1, x0:x1] < 128


def _black_ratio_of_ink(orig: Image.Image, out: Image.Image, bbox) -> float:
    x0, y0, x1, y1 = bbox
    ink = _ink(orig, bbox)
    region = np.asarray(out)[y0:y1, x0:x1]
    return float((region[ink] == 0).all(axis=-1).mean())


@pytest.mark.skipif(shutil.which("tesseract") is not None, reason="tesseract kurulu; bu test yalnızca kurulu değilken anlamlı")
def test_engine_unavailable_without_tesseract_binary():
    engine = _engine()
    assert engine.available is False
    with pytest.raises(OcrError):
        engine.run_ocr(Image.new("RGB", (200, 100), "white"))


@needs_tesseract
@needs_font
def test_phone_redacted_and_brand_tagged():
    img, (brand_bbox, phone_bbox) = _render(["CASIO fx-991", FAKE_PHONE], size=(1000, 300))
    words = _engine().run_ocr(img)
    result = find_redactions(words, faces=0, img_size=img.size)
    out = redact(img, result.boxes)

    assert result.document_like is False
    assert len(result.boxes) >= 1
    assert _black_ratio_of_ink(img, out, phone_bbox) == 1.0
    # Marka satırı kapatılmadı.
    assert _black_ratio_of_ink(img, out, brand_bbox) < 0.5
    assert "casio" in extract_tags(words, result.boxes, load_brands())


@needs_tesseract
@needs_font
def test_id_like_card_is_fully_redacted():
    rows = ["T.C. KİMLİK KARTI", "SOYADI / SURNAME", "ÖRNEKOĞLU", "ADI / NAME", "DENEME", "T.C. KİMLİK NO", FAKE_TCKN]
    img, bboxes = _render(rows, size=(1200, 720), font_size=48, start_y=30, step=95)
    words = _engine().run_ocr(img)
    result = find_redactions(words, faces=0, img_size=img.size)
    out = redact(img, result.boxes)

    assert result.document_like is True
    for w in words:
        x0, y0, x1, y1 = w.box
        assert (np.asarray(out)[y0:y1, x0:x1] == 0).all()
    assert _black_ratio_of_ink(img, out, bboxes[-1]) == 1.0
    total_ink = sum(int(_ink(img, b).sum()) for b in bboxes)
    black_ink = sum(_black_ratio_of_ink(img, out, b) * int(_ink(img, b).sum()) for b in bboxes)
    assert black_ink / total_ink >= 0.98


@needs_tesseract
def test_real_timeout_raises_ocr_error():
    img = Image.effect_noise((1600, 1200), 100).convert("RGB")
    with pytest.raises(OcrError):
        _engine(timeout_s=0.001).run_ocr(img)
