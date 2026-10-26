"""OCR kelimelerinden kişisel veri (PII) tespiti ve görsel sansürü. Saf fonksiyonlar; tesseract gerektirmez.

Kural: Şüphede sansürle. Her 6+ haneli rakam dizisi (ayırıcılar yok sayılarak) zaten sansürlenir;
TCKN/telefon/IBAN/kart desenleri yalnızca türü adlandırır ve satır içinde dağılmış parçaları birleştirir.
"""
import re
from dataclasses import dataclass

from PIL import Image, ImageDraw

from app.ml.ocr import Word

Box = tuple[int, int, int, int]

BOX_PADDING = 4
GENERIC_MIN_DIGITS = 6
# Harf yapışık belirteçlerde bile bu kadar ardışık rakam varsa sansürlenir (model kodları ≤ 4-5 rakamlıdır;
# OCR'ın harfe yapıştırdığı TCKN/telefon kaçmasın).
GLUED_MIN_DIGITS = 9
MAX_WINDOW_TOKENS = 12

DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1", "S": "5", "B": "8"})
SEPARATORS = " .-/"
# Belirteçleri bölen noktalama; e-posta kontrolü bölmeden ÖNCE ham kelimede yapılır.
SPLIT_RE = re.compile(r"[:;,()\[\]{}#=\"'«»]+")
AT_VARIANTS = r"(?:@|＠|©|®|\(a\)|\(at\)|\[at\]|\{at\}|&)"
EMAIL_RE = re.compile(
    rf"[A-Za-z0-9._%+\-]+\s*{AT_VARIANTS}\s*[A-Za-z0-9\-]+(?:\s*[.,]\s*[A-Za-z0-9\-]+)*\s*[.,]\s*[A-Za-z]{{2,}}"
)
# "@" düşse bile kişisel e-posta sağlayıcısının alan adı bir e-postanın parçasıdır.
MAIL_DOMAIN_RE = re.compile(
    r"(gmail|hotmail|outlook|yahoo|yandex|icloud|windowslive|live|msn|protonmail|proton)\s*[.,]\s*(com|net|me)(\s*[.,]\s*tr)?$"
    r"|gtu\s*[.,]\s*edu\s*[.,]\s*tr$",
    re.IGNORECASE,
)
LITERAL_AT_RE = re.compile(r"\w[@＠]|[@＠]\w")

# Kimlik/öğrenci kartı/ehliyet/pasaport anahtar sözcükleri (Türkçe karakterler katlanmış, büyük harf).
DOCUMENT_KEYWORDS = frozenset({
    "TC", "KIMLIK", "SERI", "SOYADI", "ADI", "DOGUM", "GECERLILIK", "OGRENCI", "FAKULTE", "FAKULTESI",
    "IDENTITY", "STUDENT", "UNIVERSITY", "UNIVERSITESI", "CUMHURIYETI", "NUFUS", "CINSIYET", "CINSIYETI",
    "SURNAME", "NAME", "NAMES", "GIVEN", "BIRTH", "NATIONALITY", "UYRUGU", "PASAPORT", "PASSPORT",
    "EHLIYET", "SURUCU", "DRIVING", "LICENCE", "LICENSE", "BELGESI", "KARTI", "CARD", "EXPIRY", "VALID",
})
FUZZY_KEYWORD_MIN_LEN = 6
DOC_FACE_MIN_WORDS = 8
TR_FOLD = str.maketrans({"İ": "I", "ı": "I", "i": "I", "Ş": "S", "ş": "S", "Ğ": "G", "ğ": "G",
                         "Ü": "U", "ü": "U", "Ö": "O", "ö": "O", "Ç": "C", "ç": "C"})


@dataclass(frozen=True)
class PiiMatch:
    kind: str  # "email" | "iban" | "card" | "tckn" | "phone" | "number"
    words: tuple[int, ...]  # girdi listesindeki kelime indeksleri


@dataclass
class RedactionResult:
    boxes: list[Box]  # genişletilmiş, kırpılmış, birleştirilmiş; çalışma kopyası koordinatı
    document_like: bool


@dataclass
class _Token:
    word: int
    text: str
    digits: str | None  # yalnızca rakam belirteci ise (ayırıcı/+ dışında yalnız rakam)
    iban_start: bool = False


def _fix_digits(text: str) -> str:
    """%60+ rakamlı belirteçlerde rakama benzeyen harfleri rakama çevirir."""
    core = [c for c in text if c not in SEPARATORS + "+"]
    if not core:
        return text
    digits = sum(c.isdigit() for c in core)
    if digits / len(core) < 0.6:
        return text
    return text.translate(DIGIT_FIX)


def _as_number(text: str) -> str | None:
    """Belirteç yalnızca rakam (+ ayırıcı, baştaki +) içeriyorsa rakamlarını döndürür; aksi halde None."""
    fixed = _fix_digits(text)
    body = fixed[1:] if fixed.startswith("+") else fixed
    if body and all(c.isdigit() or c in SEPARATORS for c in body):
        return "".join(c for c in body if c.isdigit())
    return None


def _make_tokens(word_index: int, text: str) -> list[_Token]:
    tokens = []
    for part in SPLIT_RE.split(text):
        part = part.strip(SEPARATORS.strip() + " ")
        if not part:
            continue
        if part[:2].upper() == "TR" and len(part) > 2:
            rest = _as_number(part[2:])
            if rest is not None:
                tokens.append(_Token(word_index, part, rest, iban_start=True))
                continue
        if part.upper() == "TR":
            tokens.append(_Token(word_index, part, "", iban_start=True))
            continue
        tokens.append(_Token(word_index, part, _as_number(part)))
    return tokens


def group_lines(words: list[Word]) -> list[list[int]]:
    """Kelimeleri satırlara ayırır: aynı line_id ya da geometrik olarak aynı satırda ve yakın olanlar.

    psm 11 (seyrek metin) aynı satırdaki sayı gruplarını farklı bloklara bölebilir; geometrik birleştirme
    "0532 123 45 67" gibi parçaların tek pencerede değerlendirilmesini sağlar. Her satır x'e göre sıralıdır.
    """
    n = len(words)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(n):
        ax0, ay0, ax1, ay1 = words[i].box
        ah = ay1 - ay0
        for j in range(i + 1, n):
            if words[i].line_id == words[j].line_id:
                union(i, j)
                continue
            bx0, by0, bx1, by1 = words[j].box
            bh = by1 - by0
            overlap = min(ay1, by1) - max(ay0, by0)
            if overlap < 0.5 * min(ah, bh):
                continue
            gap = max(bx0 - ax1, ax0 - bx1)
            if gap <= 1.2 * max(ah, bh):
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [sorted(g, key=lambda k: (words[k].box[0], k)) for _, g in sorted(groups.items())]


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def tckn_checksum_ok(digits: str) -> bool:
    """TCKN sağlama toplamı. Yalnızca bilgi amaçlı: tutmasa da 11 hane sansürlenir (OCR hatası olabilir)."""
    if len(digits) != 11 or not digits.isdigit() or digits[0] == "0":
        return False
    d = [int(c) for c in digits]
    if ((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10) != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def classify_digits(digits: str, iban: bool = False, plus: bool = False) -> str | None:
    """Rakam dizisinin türü. Öncelik: IBAN > kart (Luhn) > TCKN > telefon > genel (6+ hane)."""
    n = len(digits)
    if iban and 20 <= n <= 26:
        return "iban"
    if 13 <= n <= 19 and _luhn_ok(digits):
        return "card"
    if n == 11 and digits[0] != "0" and not plus:
        return "tckn"
    if (n == 10 and digits[0] == "5") or (n == 11 and digits[0] == "0") or (n == 12 and digits.startswith("90")):
        return "phone"
    if n >= GENERIC_MIN_DIGITS:
        return "number"
    return None


def _numeric_runs(tokens: list[_Token]) -> list[list[_Token]]:
    runs: list[list[_Token]] = []
    current: list[_Token] = []
    for tok in tokens:
        if tok.digits is None:
            if current:
                runs.append(current)
            current = []
            continue
        if tok.iban_start and current:
            runs.append(current)
            current = []
        current.append(tok)
    if current:
        runs.append(current)
    return runs


def _run_matches(run: list[_Token]) -> list[PiiMatch]:
    """Bir rakam koşusunda özel desenleri kayan pencereyle arar; koşu toplamı 6+ ise tamamını sansürler."""
    matches: list[PiiMatch] = []
    covered: set[int] = set()
    i = 0
    while i < len(run):
        best = None
        digits = ""
        for j in range(i, min(len(run), i + MAX_WINDOW_TOKENS)):
            digits += run[j].digits
            kind = classify_digits(digits, iban=run[i].iban_start, plus=run[i].text.startswith("+"))
            if kind is not None and kind != "number":
                best = (j, kind)
        if best is None:
            i += 1
            continue
        j, kind = best
        idx = tuple(dict.fromkeys(t.word for t in run[i : j + 1]))
        matches.append(PiiMatch(kind, idx))
        covered.update(range(i, j + 1))
        i = j + 1
    total = sum(len(t.digits) for t in run)
    rest = [t for k, t in enumerate(run) if k not in covered and t.digits]
    if total >= GENERIC_MIN_DIGITS and rest:
        matches.append(PiiMatch("number", tuple(dict.fromkeys(t.word for t in run if t.digits or t.iban_start))))
    return matches


AT_START_RE = re.compile(rf"^{AT_VARIANTS}")
AT_END_RE = re.compile(rf"{AT_VARIANTS}$")


def _email_matches(words: list[Word], line: list[int]) -> list[PiiMatch]:
    """E-posta ve OCR'ın bozduğu biçimleri. Komşu kelimeler yalnızca sınırda "@" benzeri ya da nokta
    varsa birleştirilir ("ornek @ example.com", "ornek@ example .com")."""
    matches = []
    texts = [words[k].text for k in line]
    pos = 0
    while pos < len(texts):
        text = texts[pos]
        if not (re.search(AT_VARIANTS, text) or MAIL_DOMAIN_RE.search(text)):
            pos += 1
            continue
        a = b = pos
        while a > 0 and a > pos - 2 and (AT_START_RE.search(texts[a]) or AT_END_RE.search(texts[a - 1])
                                         or texts[a - 1].endswith(".")):
            a -= 1
        while b + 1 < len(texts) and b < pos + 2 and (
            AT_END_RE.search(texts[b]) or texts[b].endswith(".")
            or AT_START_RE.search(texts[b + 1]) or texts[b + 1].startswith(".")
        ):
            b += 1
        joined = "".join(texts[a : b + 1])
        if EMAIL_RE.search(joined) or LITERAL_AT_RE.search(joined) or MAIL_DOMAIN_RE.search(joined):
            matches.append(PiiMatch("email", tuple(line[a : b + 1])))
            pos = b + 1
        else:
            pos += 1
    return matches


def detect_pii(words: list[Word]) -> list[PiiMatch]:
    """Kişisel veri içeren kelime gruplarını bulur. Bir desen birden çok kelimeye yayılmışsa hepsi döner."""
    matches: list[PiiMatch] = []
    for line in group_lines(words):
        matches.extend(_email_matches(words, line))
        tokens = [tok for k in line for tok in _make_tokens(k, words[k].text)]
        for run in _numeric_runs(tokens):
            matches.extend(_run_matches(run))
        # Harfe yapışık uzun rakam dizileri (ör. OCR'ın "T12345678901" okuması). "WH-1000XM4" gibi
        # model kodları kısa rakam dizileri içerdiğinden korunur.
        for tok in tokens:
            if tok.digits is not None or tok.iban_start:
                continue
            longest = max((len(m) for m in re.findall(r"\d+", _fix_digits(tok.text))), default=0)
            if longest >= GLUED_MIN_DIGITS:
                matches.append(PiiMatch("number", (tok.word,)))
    return matches


def _within_one_edit(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:k] + long_[k + 1 :] == short for k in range(len(long_)))


def _keyword_of(part: str) -> str | None:
    key = re.sub(r"[^A-Z0-9]", "", part.translate(TR_FOLD).upper())
    if not key:
        return None
    if key in DOCUMENT_KEYWORDS:
        return key
    if len(key) >= FUZZY_KEYWORD_MIN_LEN - 1:
        for kw in sorted(DOCUMENT_KEYWORDS):
            if len(kw) >= FUZZY_KEYWORD_MIN_LEN and _within_one_edit(key, kw):
                return kw
    return None


def document_keywords(words: list[Word]) -> set[str]:
    found = set()
    for w in words:
        for part in re.split(r"[/|,;:]+", w.text):
            kw = _keyword_of(part)
            if kw:
                found.add(kw)
    return found


def is_document_like(words: list[Word], faces: int) -> bool:
    """≥2 farklı belge anahtar sözcüğü VEYA (yüz var VE ≥8 kelime okundu)."""
    if len(document_keywords(words)) >= 2:
        return True
    return faces > 0 and len(words) >= DOC_FACE_MIN_WORDS


def expand_and_clip(box: Box, img_size: tuple[int, int], pad: int = BOX_PADDING) -> Box:
    w, h = img_size
    x0, y0, x1, y1 = box
    return max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)


def _touch(a: Box, b: Box) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def merge_boxes(boxes: list[Box]) -> list[Box]:
    """Birbirine değen ya da çakışan kutuları, değişiklik kalmayana dek birleştirir. Çıktı sıralıdır."""
    merged = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
    changed = True
    while changed:
        changed = False
        out: list[Box] = []
        for box in merged:
            for k, other in enumerate(out):
                if _touch(box, other):
                    out[k] = (min(box[0], other[0]), min(box[1], other[1]), max(box[2], other[2]), max(box[3], other[3]))
                    changed = True
                    break
            else:
                out.append(box)
        merged = out
    return sorted(merged)


def find_redactions(words: list[Word], faces: int, img_size: tuple[int, int]) -> RedactionResult:
    """Sansürlenecek kutular. Bir desen birden çok kelimeye yayıldıysa her kelimenin kutusu girer."""
    document_like = is_document_like(words, faces)
    if document_like:
        # İsim/soyisim desenle yakalanamaz: belgedeki okunan bütün metin kapatılır.
        indices = list(range(len(words)))
    else:
        indices = sorted({i for m in detect_pii(words) for i in m.words})
    boxes = [expand_and_clip(words[i].box, img_size) for i in indices]
    return RedactionResult(boxes=merge_boxes(boxes), document_like=document_like)


def redact(img: Image.Image, boxes: list[Box]) -> Image.Image:
    """Kutuları siyah dolu dikdörtgenle kapatır (bulanıklaştırma değil). Yeni görüntü döndürür."""
    out = img.copy()
    draw = ImageDraw.Draw(out)
    for x0, y0, x1, y1 in boxes:
        if x1 > x0 and y1 > y0:
            draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill="black")
    return out
