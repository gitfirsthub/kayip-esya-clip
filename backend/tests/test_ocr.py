"""OcrEngine birim testleri. Tesseract binary'si GEREKMEZ; pytesseract çağrıları monkeypatch ile taklit edilir."""
import logging

import pytest
import pytesseract
from PIL import Image

from app.ml import ocr
from app.ml.ocr import OcrEngine, OcrError, Word

FAKE_PHONE = "05321234567"


def _no_binary(*args, **kwargs):
    raise pytesseract.TesseractNotFoundError()


def _installed(monkeypatch, langs=("tur", "eng", "osd")):
    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.0.0")
    monkeypatch.setattr(pytesseract, "get_languages", lambda *a, **k: list(langs))


def _fake_data(entries):
    keys = ["page_num", "block_num", "par_num", "line_num", "left", "top", "width", "height", "conf", "text"]
    data = {k: [] for k in keys}
    for e in entries:
        for k in keys:
            data[k].append(e[k])
    return data


def _entry(text, conf, left, top, width, height, line=1):
    return dict(page_num=1, block_num=1, par_num=1, line_num=line, left=left, top=top,
                width=width, height=height, conf=conf, text=text)


def test_unavailable_without_binary_and_run_raises(monkeypatch, caplog):
    monkeypatch.setattr(pytesseract, "get_tesseract_version", _no_binary)
    monkeypatch.setattr(pytesseract, "get_languages", _no_binary)
    with caplog.at_level(logging.WARNING):
        engine = OcrEngine("tur+eng", timeout_s=8, min_conf=30)
    assert engine.available is False
    with pytest.raises(OcrError):
        engine.run_ocr(Image.new("RGB", (100, 100), "white"))


def test_unavailable_when_language_missing(monkeypatch):
    _installed(monkeypatch, langs=("eng", "osd"))
    assert OcrEngine("tur+eng", 8, 30).available is False


def test_available_when_all_languages_present(monkeypatch):
    _installed(monkeypatch)
    assert OcrEngine("tur+eng", 8, 30).available is True


def test_timeout_raises_ocr_error_without_text_in_logs(monkeypatch, caplog):
    _installed(monkeypatch)

    def timeout(*args, **kwargs):
        raise RuntimeError(f"Tesseract process timeout {FAKE_PHONE}")

    monkeypatch.setattr(pytesseract, "image_to_data", timeout)
    engine = OcrEngine("tur+eng", 8, 30)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(OcrError) as info:
            engine.run_ocr(Image.new("RGB", (100, 100), "white"))
    assert FAKE_PHONE not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__
    assert FAKE_PHONE not in caplog.text


def test_tesseract_error_is_wrapped(monkeypatch):
    _installed(monkeypatch)

    def fail(*args, **kwargs):
        raise pytesseract.TesseractError(1, "bozuk")

    monkeypatch.setattr(pytesseract, "image_to_data", fail)
    with pytest.raises(OcrError):
        OcrEngine("tur+eng", 8, 30).run_ocr(Image.new("RGB", (100, 100), "white"))


def test_run_ocr_passes_settings_filters_and_rescales(monkeypatch):
    _installed(monkeypatch)
    seen = {}

    def fake_image_to_data(image, lang, config, timeout, output_type):
        seen.update(size=image.size, mode=image.mode, lang=lang, config=config, timeout=timeout, out=output_type)
        return _fake_data([
            _entry("", -1, 0, 0, 1200, 800),  # blok satırı
            _entry("CASIO", 91.5, 100, 40, 200, 60),
            _entry("   ", 95, 10, 10, 20, 20),
            _entry("gurultu", 12, 300, 300, 50, 20),
            _entry("fx-991", "88", 101, 41, 201, 61, line=2),
        ])

    monkeypatch.setattr(pytesseract, "image_to_data", fake_image_to_data)
    words = OcrEngine("tur+eng", 8, 30).run_ocr(Image.new("RGB", (600, 400), "white"))
    assert seen["size"] == (1200, 800)  # 2x büyütüldü
    assert seen["mode"] == "L"
    assert seen["lang"] == "tur+eng"
    assert seen["config"] == "--oem 1 --psm 11"
    assert seen["timeout"] == 8
    assert seen["out"] == pytesseract.Output.DICT
    assert [w.text for w in words] == ["CASIO", "fx-991"]
    assert words[0] == Word("CASIO", 91.5, (50, 20, 150, 50), (1, 1, 1, 1))
    # Tek koordinatlar dışa yuvarlanır: kutu küçülmez.
    assert words[1].box == (50, 20, 151, 51)
    assert words[1].line_id == (1, 1, 1, 2)


def test_large_image_is_not_upscaled(monkeypatch):
    _installed(monkeypatch)
    seen = {}

    def fake_image_to_data(image, **kwargs):
        seen["size"] = image.size
        return _fake_data([_entry("CASIO", 90, 100, 40, 200, 60)])

    monkeypatch.setattr(pytesseract, "image_to_data", fake_image_to_data)
    size = (ocr.UPSCALE_MAX_SIDE + 1, 500)
    words = OcrEngine("tur+eng", 8, 30).run_ocr(Image.new("RGB", size, "white"))
    assert seen["size"] == size
    assert words[0].box == (100, 40, 300, 100)
