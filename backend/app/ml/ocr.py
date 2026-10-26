"""Yerel Tesseract OCR (pytesseract). Ham OCR metni hiçbir koşulda loglanmaz."""
import logging
import math
from dataclasses import dataclass

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Uzun kenarı bu değere eşit ya da küçük görüntüler 2x büyütülür. Kısa kenar ölçütü 1600x900 gibi
# yaygın telefon oranlarını 3200x1800'e (4x piksel) çıkarıp OCR süresini katlardı; uzun kenar
# ölçütü büyütülmüş görüntüyü en fazla 2000 px ile sınırlar.
UPSCALE_MAX_SIDE = 1000
TESSERACT_CONFIG = "--oem 1 --psm 11"


def confident_words(words: list["Word"], min_conf: float) -> list["Word"]:
    """Etiket çıkarmada kullanılacak kelimeler. Sansür kararında KULLANILMAZ."""
    return [w for w in words if w.conf >= min_conf]


@dataclass(frozen=True)
class Word:
    text: str
    conf: float
    box: tuple[int, int, int, int]  # (x0, y0, x1, y1), x1/y1 hariç; çalışma kopyası koordinatı
    line_id: tuple[int, int, int, int]  # (page, block, par, line)


class OcrError(Exception):
    """OCR çalıştırılamadı; görsel gizlilik kontrolünden geçmemiş sayılır. Mesaj OCR metni içermez."""

    def __init__(self, message: str = "OCR çalıştırılamadı."):
        super().__init__(message)


class OcrEngine:
    """`available=False` ise ya da OCR herhangi bir nedenle başarısız olursa `run_ocr` OcrError fırlatır.

    `run_ocr` güveni ne olursa olsun bütün kelimeleri döndürür: düşük güvenle okunmuş bir numara da
    sansürlenmelidir. `min_conf` yalnızca etiket çıkarmada kullanılır (bkz. `confident_words`).
    """

    def __init__(self, langs: str, timeout_s: float, min_conf: float):
        self.langs = langs
        self.timeout_s = float(timeout_s)
        self.min_conf = float(min_conf)
        self._available = self._check()

    def _check(self) -> bool:
        wanted = [lang for lang in self.langs.split("+") if lang]
        try:
            pytesseract.get_tesseract_version()
            installed = set(pytesseract.get_languages())
        except Exception as exc:
            logger.warning("Tesseract bulunamadı veya çalıştırılamadı (%s). OCR devre dışı.", type(exc).__name__)
            return False
        missing = [lang for lang in wanted if lang not in installed]
        if not wanted or missing:
            logger.warning("Tesseract dil verisi eksik: %s. OCR devre dışı.", ",".join(missing) or "(boş)")
            return False
        return True

    @property
    def available(self) -> bool:
        return self._available

    def run_ocr(self, img: Image.Image) -> list[Word]:
        if not self._available:
            raise OcrError()
        try:
            return self._run(img)
        except Exception as exc:
            # Yalnızca istisna tipi loglanır; mesaj tesseract çıktısı içerebilir.
            logger.error("OCR başarısız oldu (%s).", type(exc).__name__)
            raise OcrError() from None

    def _run(self, img: Image.Image) -> list[Word]:
        w, h = img.size
        gray = img.convert("L")
        scale = 2 if max(w, h) <= UPSCALE_MAX_SIDE else 1
        if scale != 1:
            gray = gray.resize((w * scale, h * scale), Image.Resampling.BICUBIC)
        data = pytesseract.image_to_data(
            gray,
            lang=self.langs,
            config=TESSERACT_CONFIG,
            timeout=self.timeout_s,
            output_type=pytesseract.Output.DICT,
        )
        words: list[Word] = []
        for i, raw in enumerate(data["text"]):
            text = (raw or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                continue
            if conf < 0:  # tesseract'ın kelime olmayan yapı satırları
                continue
            left, top = int(data["left"][i]), int(data["top"][i])
            right, bottom = left + int(data["width"][i]), top + int(data["height"][i])
            box = (
                max(0, math.floor(left / scale)),
                max(0, math.floor(top / scale)),
                min(w, math.ceil(right / scale)),
                min(h, math.ceil(bottom / scale)),
            )
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            line_id = (
                int(data["page_num"][i]),
                int(data["block_num"][i]),
                int(data["par_num"][i]),
                int(data["line_num"][i]),
            )
            words.append(Word(text=text, conf=conf, box=box, line_id=line_id))
        return words
