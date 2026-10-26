"""POST /api/items içindeki OCR adımı: fail-closed davranış, sansür alanları ve log gizliliği."""
import logging
import os
import re

from PIL import Image

from app.ml.ocr import OcrError, Word
from tests.conftest import make_image_bytes
from tests.test_api_items import post_item, uploaded_files

MSG_OCR = {"detail": "Görsel gizlilik kontrolünden geçirilemedi, lütfen tekrar deneyin."}


def word(text, x0, y0, x1, y1, line=1):
    return Word(text=text, conf=90.0, box=(x0, y0, x1, y1), line_id=(1, 1, 1, line))


def test_ocr_error_returns_503_and_nothing_saved(api, ocr):
    ocr.error = OcrError()
    r = post_item(api)
    assert r.status_code == 503
    assert r.json() == MSG_OCR
    assert uploaded_files(api) == []
    assert api.get("/health").json()["item_count"] == 0


def test_ocr_unavailable_returns_503_and_nothing_saved(api, ocr):
    ocr.available = False
    r = post_item(api)
    assert r.status_code == 503
    assert r.json() == MSG_OCR
    assert ocr.calls == 0
    assert uploaded_files(api) == []


def test_ocr_disabled_skips_ocr(api, ocr):
    api.settings.ocr_enabled = False
    ocr.available = False
    r = post_item(api)
    assert r.status_code == 201
    assert ocr.calls == 0
    assert r.json()["redacted_regions"] == 0


def test_phone_is_blacked_out_and_brand_tagged(api, ocr, caplog):
    caplog.set_level(logging.DEBUG)
    ocr.words = [
        word("CASIO", 10, 10, 90, 30, line=1),
        word("05321234567", 10, 60, 150, 80, line=2),
        word("ornek@example.com", 10, 100, 190, 120, line=3),
    ]
    r = post_item(api, image=make_image_bytes(color=(250, 250, 250), size=(320, 240)))
    assert r.status_code == 201
    body = r.json()
    assert body["redacted_regions"] >= 1
    assert body["document_like"] is False
    assert "casio" in body["tags"]
    # Ham OCR metni yanıtta yok.
    assert "05321234567" not in r.text and "example.com" not in r.text

    path = os.path.join(api.settings.data_dir, "uploads", os.path.basename(body["image_url"]))
    with Image.open(path) as saved:
        rgb = saved.convert("RGB")
        assert max(rgb.getpixel((80, 70))) < 40  # telefon kutusunun içi siyah
        assert min(rgb.getpixel((300, 200))) > 200  # metin dışı alan değişmedi

    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert not re.search(r"\d{6,}", logged)
    assert "@" not in logged and "casio" not in logged.lower()


def test_document_like_image_has_no_tags(api, ocr):
    ocr.words = [
        word("T.C.", 10, 10, 50, 25, line=1),
        word("KİMLİK", 60, 10, 130, 25, line=1),
        word("SOYADI", 10, 40, 80, 55, line=2),
        word("CASIO", 10, 70, 80, 85, line=3),
    ]
    r = post_item(api, image=make_image_bytes(size=(320, 240)))
    assert r.status_code == 201
    body = r.json()
    assert body["document_like"] is True
    assert body["tags"] == []
    assert body["redacted_regions"] >= 1


def test_new_fields_persist(api, ocr):
    ocr.words = [word("CASIO", 10, 10, 90, 30)]
    created = post_item(api, image=make_image_bytes(size=(320, 240))).json()
    fetched = api.get(f"/api/items/{created['id']}").json()
    assert fetched["tags"] == created["tags"] == ["casio"]
    assert fetched["redacted_regions"] == 0
    assert fetched["document_like"] is False
