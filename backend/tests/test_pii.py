"""pii.py birim testleri. Tesseract gerekmez; Word nesneleri elle kurulur.
Bütün numaralar UYDURMADIR (ör. 12345678901, 05321234567)."""
import numpy as np
import pytest
from PIL import Image

from app.ml.ocr import Word
from app.ml.pii import (
    classify_digits,
    detect_pii,
    expand_and_clip,
    find_redactions,
    group_lines,
    merge_boxes,
    redact,
    tckn_checksum_ok,
)

FAKE_TCKN = "12345678901"
FAKE_PHONE = "05321234567"
FAKE_EMAIL = "ornek@example.com"
FAKE_IBAN = "TR330006100519786457841326"


def line(*texts, line_no=1, y=100, h=30, x=10, gap=12, char_w=15):
    """Aynı satırda soldan sağa dizilmiş kelimeler."""
    words = []
    for t in texts:
        w = max(1, len(t)) * char_w
        words.append(Word(t, 90.0, (x, y, x + w, y + h), (1, 1, 1, line_no)))
        x += w + gap
    return words


def redacted_texts(words):
    idx = {i for m in detect_pii(words) for i in m.words}
    return [words[i].text for i in sorted(idx)]


def kinds(words):
    return [m.kind for m in detect_pii(words)]


# --- TCKN ---

@pytest.mark.parametrize("texts", [
    [FAKE_TCKN],
    ["123", "456", "789", "01"],
    ["123.456.789.01"],
    ["123", "456", "78901"],
    ["123-456-789-01"],
])
def test_tckn_variants(texts):
    words = line("T.C.", "Kimlik", "No", *texts)
    assert redacted_texts(words) == texts
    assert "tckn" in kinds(words)


def test_tckn_with_letter_o_instead_of_zero():
    words = line("1234567890l")  # OCR: son iki hane "0l"
    assert redacted_texts(words) == ["1234567890l"]
    words = line("1O3", "456", "7B9", "01")
    assert redacted_texts(words) == ["1O3", "456", "7B9", "01"]
    assert kinds(words) == ["tckn"]


def test_tckn_after_colon_in_same_word():
    words = line("TC:" + FAKE_TCKN)
    assert redacted_texts(words) == ["TC:" + FAKE_TCKN]


def test_tckn_checksum_is_informative_only():
    assert tckn_checksum_ok("10000000146")
    assert not tckn_checksum_ok(FAKE_TCKN)
    # Sağlama tutmasa da sansürlenir.
    assert classify_digits(FAKE_TCKN) == "tckn"
    assert redacted_texts(line(FAKE_TCKN)) == [FAKE_TCKN]


def test_letter_fix_requires_mostly_digits():
    # "SOLO" rakam değil: düzeltme uygulanmaz.
    assert redacted_texts(line("SOLO", "BOSS", "1234")) == []


# --- Telefon ---

@pytest.mark.parametrize("texts", [
    [FAKE_PHONE],
    ["0532", "123", "45", "67"],
    ["0", "532", "123", "45", "67"],
    ["+90", "532", "123", "45", "67"],
    ["+905321234567"],
    ["(0532)", "123-45-67"],
    ["532", "123", "4567"],
    ["O532", "l23", "45", "67"],
])
def test_phone_variants(texts):
    words = line("Tel", *texts, "ara")
    assert redacted_texts(words) == texts
    assert "phone" in kinds(words)


def test_phone_split_into_different_blocks_on_same_row():
    # psm 11 parçaları farklı bloklara koyabilir; geometrik satır birleştirme yakalar.
    words = [
        Word("0532", 90.0, (10, 100, 70, 130), (1, 1, 1, 1)),
        Word("123", 90.0, (82, 101, 127, 131), (1, 2, 1, 1)),
        Word("45", 90.0, (139, 99, 169, 129), (1, 3, 1, 1)),
        Word("67", 90.0, (181, 100, 211, 130), (1, 4, 1, 1)),
    ]
    assert len(group_lines(words)) == 1
    assert redacted_texts(words) == ["0532", "123", "45", "67"]


def test_far_apart_short_numbers_on_different_rows_not_joined():
    words = [
        Word("123", 90.0, (10, 100, 55, 130), (1, 1, 1, 1)),
        Word("456", 90.0, (10, 300, 55, 330), (1, 2, 1, 1)),
    ]
    assert len(group_lines(words)) == 2
    assert redacted_texts(words) == []


# --- E-posta ---

@pytest.mark.parametrize("texts", [
    [FAKE_EMAIL],
    ["ornek©example.com"],
    ["ornek(at)example.com"],
    ["ornek", "@", "example.com"],
    ["ornek@", "example.com"],
    ["ornek@example", ".com"],
    ["ornek®example.com"],
])
def test_email_variants(texts):
    words = line("mail", *texts, "yaz")
    assert redacted_texts(words) == texts
    assert "email" in kinds(words)


def test_email_without_at_on_known_provider():
    words = line("ornekgmail.com")
    assert redacted_texts(words) == ["ornekgmail.com"]


def test_bare_at_fragment_is_redacted():
    # Satır kırılmış e-postanın yarısı da kişisel veridir.
    assert redacted_texts(line("ornek@")) == ["ornek@"]


def test_website_and_copyright_are_not_email():
    assert redacted_texts(line("www.casio.com", "©2023", "CASIO")) == []


# --- IBAN ---

@pytest.mark.parametrize("texts", [
    [FAKE_IBAN],
    ["TR33", "0006", "1005", "1978", "6457", "8413", "26"],
    ["TR", "33", "0006", "1005", "1978", "6457", "8413", "26"],
    ["TR33", "O006", "1O05", "1978", "6457", "8413", "26"],
])
def test_iban_variants(texts):
    words = line("IBAN", *texts)
    assert redacted_texts(words) == texts
    assert "iban" in kinds(words)


# --- Kart ---

def test_card_with_luhn():
    words = line("4111", "1111", "1111", "1111")
    assert redacted_texts(words) == ["4111", "1111", "1111", "1111"]
    assert "card" in kinds(words)


def test_card_like_number_without_luhn_still_redacted_as_number():
    words = line("4111", "1111", "1111", "1112")
    assert redacted_texts(words) == ["4111", "1111", "1111", "1112"]
    assert kinds(words) == ["number"]


# --- Genel kural ---

def test_six_digits_redacted_five_not():
    assert redacted_texts(line("No", "123456")) == ["123456"]
    assert redacted_texts(line("No", "12345")) == []
    assert redacted_texts(line("123", "456")) == ["123", "456"]


def test_gtu_student_number_twelve_digits_covered_by_generic_rule():
    student_no = "200104004001"  # uydurma, 12 hane
    words = line("Öğrenci", "No:", student_no)
    assert redacted_texts(words) == [student_no]
    assert classify_digits(student_no) == "number"
    assert redacted_texts(line("2001", "0400", "4001")) == ["2001", "0400", "4001"]


@pytest.mark.parametrize("code", ["WH-1000XM4", "fx-991ES", "fx-991", "TI-84", "MX3", "ABC123456", "S23"])
def test_model_codes_are_kept(code):
    assert redacted_texts(line("SONY", code, "Plus")) == []


def test_digits_glued_to_letters_long_enough_are_redacted():
    assert redacted_texts(line("T" + FAKE_TCKN)) == ["T" + FAKE_TCKN]


def test_letters_break_numeric_runs():
    assert redacted_texts(line("123", "adet", "456")) == []


def test_multiple_patterns_on_one_line():
    words = line(FAKE_PHONE, FAKE_TCKN)
    assert redacted_texts(words) == [FAKE_PHONE, FAKE_TCKN]
    assert kinds(words) == ["phone", "tckn"]


def test_empty_input():
    assert detect_pii([]) == []


def test_ampersand_between_words_is_not_email():
    assert redacted_texts(line("Ben", "&", "Jerry")) == []


# --- Kutu genişletme, birleştirme, siyah bant ---

def test_expand_and_clip():
    assert expand_and_clip((10, 10, 20, 20), (100, 100)) == (6, 6, 24, 24)
    assert expand_and_clip((1, 2, 98, 99), (100, 100)) == (0, 0, 100, 100)


def test_merge_touching_and_overlapping_boxes():
    boxes = [(0, 0, 10, 10), (10, 0, 20, 10), (50, 50, 60, 60), (55, 55, 70, 70), (100, 100, 110, 110)]
    assert merge_boxes(boxes) == [(0, 0, 20, 10), (50, 50, 70, 70), (100, 100, 110, 110)]


def test_merge_is_transitive():
    # c ancak a+b birleşince ona değer.
    boxes = [(0, 0, 10, 10), (30, 0, 40, 10), (5, 5, 35, 8)]
    assert merge_boxes(boxes) == [(0, 0, 40, 10)]


def test_merge_keeps_separate_boxes_and_drops_empty():
    assert merge_boxes([(0, 0, 10, 10), (11, 0, 20, 10), (5, 5, 5, 9)]) == [(0, 0, 10, 10), (11, 0, 20, 10)]


def test_find_redactions_covers_every_word_of_split_phone_and_merges():
    words = line("CASIO", "fx-991", "0532", "123", "45", "67", gap=12)
    result = find_redactions(words, faces=0, img_size=(1000, 500))
    assert result.document_like is False
    # Dört parça + 4 px genişletme: 12 px aralık 8 px'e iner, değmez; dört ayrı kutu kalır.
    assert len(result.boxes) == 4
    for w in words[2:]:
        x0, y0, x1, y1 = w.box
        assert any(b[0] <= x0 - 4 and b[1] <= y0 - 4 and b[2] >= x1 + 4 and b[3] >= y1 + 4 for b in result.boxes)
    for w in words[:2]:
        assert not any(_overlaps(b, w.box) for b in result.boxes)
    close = line("0532", "123", "45", "67", gap=6)
    assert len(find_redactions(close, 0, (1000, 500)).boxes) == 1


def test_find_redactions_clips_to_image():
    words = [Word(FAKE_PHONE, 90.0, (0, 0, 165, 30), (1, 1, 1, 1))]
    assert find_redactions(words, 0, (160, 32)).boxes == [(0, 0, 160, 32)]


def test_find_redactions_nothing_to_hide():
    assert find_redactions(line("CASIO", "fx-991ES", "PLUS"), 0, (1000, 500)).boxes == []


def _overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_redact_blacks_inside_and_keeps_outside():
    img = Image.new("RGB", (100, 80), (200, 150, 50))
    img.putpixel((5, 5), (1, 2, 3))
    out = redact(img, [(10, 20, 30, 40), (60, 0, 100, 80)])
    assert out is not img
    arr, orig = np.asarray(out), np.asarray(img)
    assert (arr[20:40, 10:30] == 0).all()
    assert (arr[:, 60:100] == 0).all()
    mask = np.ones(arr.shape[:2], dtype=bool)
    mask[20:40, 10:30] = False
    mask[:, 60:100] = False
    assert np.array_equal(arr[mask], orig[mask])
    # Dışlayıcı sınır: x1=30 sütunu ve y1=40 satırı değişmez.
    assert tuple(arr[39, 30]) == (200, 150, 50) and tuple(arr[40, 29]) == (200, 150, 50)
    # Girdi değişmedi.
    assert tuple(np.asarray(img)[25, 15]) == (200, 150, 50)


def test_redact_grayscale_and_empty_boxes():
    img = Image.new("L", (20, 20), 255)
    out = redact(img, [(0, 0, 5, 5), (7, 7, 7, 9)])
    arr = np.asarray(out)
    assert (arr[0:5, 0:5] == 0).all() and arr[5:, 5:].min() == 255
