"""tags.py birim testleri. Tesseract gerekmez; Word nesneleri elle kurulur."""

from app.ml.ocr import Word
from app.ml.pii import find_redactions
from app.ml.tags import extract_tags, load_brands, model_code, query_terms

BRANDS = load_brands()


def line(*texts, line_no=1, y=100, h=30, x=10, gap=12, char_w=15):
    words = []
    for t in texts:
        w = max(1, len(t)) * char_w
        words.append(Word(t, 90.0, (x, y, x + w, y + h), (1, 1, 1, line_no)))
        x += w + gap
    return words


def tags_of(words, boxes=()):
    return extract_tags(words, list(boxes), BRANDS)


def test_brand_file_loads_and_has_required_brands():
    required = {"casio", "logitech", "apple", "samsung", "xiaomi", "huawei", "sony", "jbl", "anker", "nike",
                "adidas", "the north face", "eastpak", "stanley", "texas instruments", "lamy", "faber-castell",
                "hp", "lenovo", "asus"}
    assert required <= BRANDS
    assert 130 <= len(BRANDS) <= 170
    assert all(b == b.strip().lower() and not b.startswith("#") for b in BRANDS)


def test_load_brands_custom_path(tmp_path):
    p = tmp_path / "b.txt"
    p.write_text("# yorum\n\nCASIO\n  The  North Face \n", encoding="utf-8")
    assert load_brands(p) == frozenset({"casio", "the north face"})


def test_brand_and_model_code():
    assert tags_of(line("CASIO", "fx-991ES", "PLUS")) == ["casio", "fx991es"]


def test_multi_word_brands():
    assert tags_of(line("THE", "NORTH", "FACE")) == ["the north face"]
    assert tags_of(line("Texas", "Instruments", "TI-84")) == ["texas instruments", "ti84"]
    assert tags_of(line("FABER-CASTELL")) == ["faber-castell"]
    assert tags_of(line("Faber", "Castell")) == ["faber-castell"]


def test_ocr_typo_tolerance_returns_correct_spelling():
    assert tags_of(line("CASJO")) == ["casio"]  # değiştirme
    assert tags_of(line("Logitec")) == ["logitech"]  # silme
    assert tags_of(line("Samsungg")) == ["samsung"]  # ekleme
    assert tags_of(line("Lenov0")) == ["lenovo"]


def test_typo_tolerance_limits():
    assert tags_of(line("CASJQ")) == []  # 2 fark
    assert tags_of(line("SONI")) == []  # < 5 harf: yalnızca tam eşleşme
    assert tags_of(line("Sony")) == ["sony"]


def test_non_brand_words_never_become_tags():
    assert tags_of(line("Örnek", "Kişi", "kalem", "kutusu", "Bilgisayar")) == []


def test_model_code_pattern():
    assert model_code("WH-1000XM4") == "wh1000xm4"
    assert model_code("fx-991") == "fx991"
    assert model_code("S23") == "s23"
    for not_code in ["123456", "1234", "MX3", "ABCDE12", "AB123456", "A12345", "kalem", "fx-991-ABCDE"]:
        assert model_code(not_code) is None, not_code


def test_words_intersecting_redaction_are_not_tags():
    words = line("CASIO", "fx-991", "05321234567")
    boxes = [(0, 0, 90, 200)]  # CASIO kutusunu kapatır
    assert tags_of(words, boxes) == ["fx991"]


def test_redacted_word_breaks_multi_word_brand():
    words = line("THE", "NORTH", "FACE")
    assert tags_of(words, [words[1].box]) == []


def test_pii_tokens_never_become_tags_after_find_redactions():
    words = line("SONY", "TR33", "0006", "1005", "1978", "6457", "8413", "26")
    result = find_redactions(words, faces=0, img_size=(2000, 500))
    assert tags_of(words, result.boxes) == ["sony"]


def test_max_eight_unique_tags_lowercase_deterministic():
    texts = ["APPLE", "apple", "SONY", "JBL", "ANKER", "NIKE", "ADIDAS", "LAMY", "CASIO", "HP", "ASUS"]
    words = line(*texts[:6], line_no=1, y=10) + line(*texts[6:], line_no=2, y=80)
    tags = tags_of(words)
    assert tags == ["apple", "sony", "jbl", "anker", "nike", "adidas", "lamy", "casio"]
    assert tags == tags_of(list(words))


def test_line_order_is_left_to_right_regardless_of_input_order():
    words = line("CASIO", "LAMY")
    assert tags_of(list(reversed(words))) == ["casio", "lamy"]


def test_brand_with_trademark_symbol():
    assert tags_of(line("CASIO®", "Logitech™")) == ["casio", "logitech"]


def test_query_terms_matches_tag_normalization():
    terms = query_terms("Kırmızı CASIO fx-991ES hesap makinesi")
    assert {"casio", "fx991es", "kirmizi"} <= terms
    assert "casio" in query_terms("CASİO")  # Türkçe büyük İ
    assert "casio" in query_terms("casıo")  # noktasız ı
    assert "the north face" in query_terms("siyah the north face çanta")
    assert "faber-castell" in query_terms("Faber Castell kalem")
    assert "levi's" in query_terms("levis ceket")
    assert "fx991" in query_terms("fx 991 hesap makinesi")


def test_query_terms_tag_bonus_intersection():
    tags = tags_of(line("CASIO", "fx-991ES"))
    assert len(query_terms("casio fx991es") & set(tags)) == 2
    assert len(query_terms("siyah sırt çantası") & set(tags)) == 0


def test_query_terms_empty():
    assert query_terms("") == set()
    assert query_terms("   ") == set()
