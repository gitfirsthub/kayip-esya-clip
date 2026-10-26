"""OCR kelimelerinden güvenli etiketler: yalnızca izin listesindeki markalar ve model kodu deseni.

Etikete OCR'ın okuduğu ham sözcük değil, izin listesindeki DOĞRU yazım girer; böylece etiketler
kişisel veri taşıyamaz. Model kodları tiresiz küçük harfle saklanır ("fx-991ES" -> "fx991es").
"""
import difflib
import re
from functools import lru_cache
from pathlib import Path

from app.ml.ocr import Word
from app.ml.pii import group_lines

DEFAULT_BRANDS_PATH = Path(__file__).resolve().parents[1] / "data" / "brands.txt"
MAX_TAGS = 8
FUZZY_MIN_LEN = 5
MAX_NGRAM = 3

_LOWER_FOLD = str.maketrans({"İ": "i", "I": "i", "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
                             "Ş": "s", "Ğ": "g", "Ü": "u", "Ö": "o", "Ç": "c"})
_EDGE_PUNCT = ".,;:!?()[]{}\"'`«»“”‘’®™©*•"
MODEL_CODE_RE = re.compile(r"[a-z]{1,4}-?\d{2,4}(?:-?[a-z0-9]{1,4})?")


def normalize(text: str) -> str:
    """Küçük harf; Türkçe karakterler ASCII'ye katlanır (İ/I/ı -> i)."""
    return text.translate(_LOWER_FOLD).lower()


def brand_key(text: str) -> str:
    """Eşleşme anahtarı: tire boşluk olur, kesme işareti düşer."""
    key = normalize(text).replace("-", " ").replace("'", "").replace("’", "")
    return " ".join(key.split())


def load_brands(path: str | Path | None = None) -> frozenset[str]:
    p = Path(path) if path is not None else DEFAULT_BRANDS_PATH
    brands = set()
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            brands.add(" ".join(normalize(line).split()))
    return frozenset(brands)


@lru_cache(maxsize=1)
def _default_brands() -> frozenset[str]:
    return load_brands()


def _clean(token: str) -> str:
    return normalize(token).strip(_EDGE_PUNCT)


def model_code(token: str) -> str | None:
    """1–4 harf + 2–4 rakam + opsiyonel ek. 5+ ardışık rakam (kişisel numara olabilir) reddedilir."""
    t = _clean(token)
    if not MODEL_CODE_RE.fullmatch(t) or re.search(r"\d{5,}", t.replace("-", "")):
        return None
    return t.replace("-", "")


def _fuzzy_brand(key: str, single_brands: dict[str, str]) -> str | None:
    """≥5 harfli sözcükte en fazla 1 karakter fark (ekleme/silme/değiştirme)."""
    if len(key) < FUZZY_MIN_LEN or " " in key:
        return None
    best = None
    for bkey in sorted(single_brands):
        if len(bkey) < FUZZY_MIN_LEN or abs(len(bkey) - len(key)) > 1:
            continue
        matcher = difflib.SequenceMatcher(None, key, bkey, autojunk=False)
        matched = sum(block.size for block in matcher.get_matching_blocks())
        if max(len(key), len(bkey)) - matched <= 1:
            best = bkey
            break
    return single_brands[best] if best else None


def _intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _brand_index(brands: frozenset[str]) -> dict[str, str]:
    return {brand_key(b): b for b in brands}


def extract_tags(words: list[Word], redacted_boxes, brands: frozenset[str]) -> list[str]:
    """Satır sırasıyla (sonra soldan sağa) ilk görülme sırasında en çok 8 tekrarsız etiket."""
    index = _brand_index(brands)
    single = {k: v for k, v in index.items() if " " not in k}
    boxes = list(redacted_boxes or [])
    tags: list[str] = []

    def add(tag: str) -> None:
        if tag and tag not in tags and len(tags) < MAX_TAGS:
            tags.append(tag)

    for line in group_lines(words):
        # Sansürlü kelime ardışıklığı böler: çok sözcüklü marka sansür bandının üstünden birleşmez.
        segments: list[list[str]] = [[]]
        for k in line:
            if any(_intersects(words[k].box, b) for b in boxes):
                segments.append([])
                continue
            segments[-1].extend(p for p in re.split(r"[\s/]+", words[k].text) if _clean(p))
        for seg in segments:
            i = 0
            while i < len(seg):
                matched = False
                for n in range(min(MAX_NGRAM, len(seg) - i), 0, -1):
                    key = brand_key(" ".join(_clean(t) for t in seg[i : i + n]))
                    if key in index:
                        add(index[key])
                        i += n
                        matched = True
                        break
                if matched:
                    continue
                token = seg[i]
                code = model_code(token)
                if code:
                    add(code)
                else:
                    fuzzy = _fuzzy_brand(brand_key(_clean(token)), single)
                    if fuzzy:
                        add(fuzzy)
                i += 1
    return tags


def query_terms(text: str, brands: frozenset[str] | None = None) -> set[str]:
    """Arama sorgusundan etiketlerle karşılaştırılabilir terimler (etiketlerle aynı normalizasyon).

    Tek sözcükler, izin listesindeki çok sözcüklü markaların doğru yazımı ve tiresiz model kodları
    ("fx-991", "fx 991" -> "fx991") üretilir. Bulanık eşleşme yapılmaz: kullanıcı yazımı esas alınır.
    """
    index = _brand_index(brands if brands is not None else _default_brands())
    tokens = [t for t in (_clean(p) for p in re.split(r"[\s/,;]+", text)) if t]
    terms: set[str] = set()
    for i, tok in enumerate(tokens):
        terms.add(tok)
        code = model_code(tok)
        if code:
            terms.add(code)
        for n in range(1, MAX_NGRAM + 1):
            if i + n > len(tokens):
                break
            key = brand_key(" ".join(tokens[i : i + n]))
            if key in index:
                terms.add(index[key])
        if i + 1 < len(tokens):
            pair = model_code(tok + tokens[i + 1])
            if pair and not tokens[i + 1].isalpha():
                terms.add(pair)
    return terms
