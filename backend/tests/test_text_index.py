"""İlan metin indeksi (başlık + açıklama + etiketler), etiket bonusu ve eski veritabanı geçişi."""
import os
import sqlite3

import numpy as np
import pytest

from app.api.items import item_text
from app.main import backfill_text_index
from app.ml.encoder import FakeEncoder
from app.ml.ocr import Word
from app.store import Store
from tests.conftest import make_image_bytes
from tests.test_api_items import post_item
from tests.test_store import DIM, fields, unit

OLD_SCHEMA = """
CREATE TABLE items (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', location TEXT NOT NULL,
    found_date TEXT NOT NULL, dropoff_point TEXT NOT NULL, image_path TEXT NOT NULL, category TEXT NOT NULL,
    category_score REAL NOT NULL, color TEXT NOT NULL, faces_blurred INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'bekliyor', created_at TEXT NOT NULL, embedding BLOB NOT NULL
);
"""


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path), dim=DIM)
    yield s
    s.close()


def test_item_text_joins_title_description_tags():
    assert item_text("Hesap makinesi", "", ["casio", "fx991"]) == "Hesap makinesi casio fx991"
    assert item_text("Şemsiye", "mavi", []) == "Şemsiye mavi"


def test_old_database_is_migrated_idempotently(tmp_path):
    conn = sqlite3.connect(os.path.join(tmp_path, "app.db"))
    conn.executescript(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO items VALUES ('old', 'Eski', '', 'Yemekhane', '2026-10-20', 'Öğrenci İşleri', 'x.jpg',"
        " 'telefon', 0.9, 'siyah', 0, 'bekliyor', '2026-10-20T00:00:00+00:00', ?)",
        (unit(0).tobytes(),),
    )
    conn.commit()
    conn.close()
    for _ in range(2):  # ikinci açılış da hata vermemeli
        s = Store(str(tmp_path), dim=DIM)
        item = s.get("old")
        assert item["tags"] == [] and item["redacted_regions"] == 0 and item["document_like"] is False
        assert [r["id"] for r in s.items_missing_text_embedding()] == ["old"]
        # Metin embedding'i yokken metin ağırlığı skoru değiştirmez.
        (_, score), = s.search(unit(0), text_vec=unit(0), text_weight=0.5)
        assert score == pytest.approx(1.0)
        s.close()


def test_backfill_fills_missing_text_embeddings(tmp_path):
    encoder = FakeEncoder(dim=DIM)
    s = Store(str(tmp_path), dim=DIM)
    s.add(fields(title="Mavi şemsiye"), unit(0))
    backfill_text_index(s, encoder)
    assert s.items_missing_text_embedding() == []
    q = encoder.encode_texts(["Mavi şemsiye"])[0]
    (_, score), = s.search(q, text_vec=q, text_weight=1.0)
    assert score == pytest.approx(1.0, abs=1e-5)
    s.close()
    reopened = Store(str(tmp_path), dim=DIM)
    assert reopened.items_missing_text_embedding() == []
    reopened.close()


def test_text_weight_mixes_image_and_text_scores(store):
    a = store.add(fields(title="a"), unit(0), text_embedding=unit(1))
    b = store.add(fields(title="b"), unit(1), text_embedding=unit(2))
    q = unit(1)
    # w=0: yalnızca görsel embedding -> b önde
    assert [r["id"] for r, _ in store.search(q, text_vec=q, text_weight=0.0)][0] == b["id"]
    # w=1: yalnızca ilan metni -> a önde
    results = store.search(q, text_vec=q, text_weight=1.0)
    assert results[0][0]["id"] == a["id"] and results[0][1] == pytest.approx(1.0)
    # w=0.3: s = 0.7*img + 0.3*text
    scores = {r["id"]: s for r, s in store.search(q, text_vec=q, text_weight=0.3)}
    assert scores[a["id"]] == pytest.approx(0.3) and scores[b["id"]] == pytest.approx(0.7)


def test_text_share_halves_text_part(store):
    a = store.add(fields(), unit(0), text_embedding=unit(1))
    q_text, q_img = unit(1), unit(0)
    vec = 0.5 * q_text + 0.5 * q_img
    (_, score), = store.search(vec, text_vec=q_text, text_weight=1.0, text_share=0.5)
    # 0.5 * s_text (=1.0) + 0.5 * cos(q_img, img) (=1.0)
    assert score == pytest.approx(1.0)


def test_tag_bonus_per_match_and_capped(store):
    a = store.add(fields(tags=["casio", "fx991", "texas instruments"]), unit(0))
    b = store.add(fields(), unit(0))
    kw = dict(tag_bonus=0.05, tag_bonus_max=0.10)
    scores = {r["id"]: s for r, s in store.search(unit(0), query_terms={"casio"}, **kw)}
    assert scores[a["id"]] == pytest.approx(1.05) and scores[b["id"]] == pytest.approx(1.0)
    scores = {r["id"]: s for r, s in store.search(unit(0), query_terms={"casio", "fx991", "texas instruments"}, **kw)}
    assert scores[a["id"]] == pytest.approx(1.10)
    scores = {r["id"]: s for r, s in store.search(unit(0), query_terms={"casio"}, text_share=0.5, **kw)}
    assert scores[a["id"]] == pytest.approx(1.025)


def test_delete_keeps_text_index_aligned(store):
    a = store.add(fields(tags=["casio"]), unit(0), text_embedding=unit(3))
    b = store.add(fields(), unit(1), text_embedding=unit(4))
    store.delete(a["id"])
    (item, score), = store.search(unit(4), text_vec=unit(4), text_weight=1.0, query_terms={"casio"}, tag_bonus=0.05,
                                  tag_bonus_max=0.1)
    assert item["id"] == b["id"] and score == pytest.approx(1.0)


def test_api_search_uses_tags(api, ocr):
    api.settings.search_text_weight = 0.0
    ocr.words = [Word(text="CASIO", conf=90.0, box=(10, 10, 90, 30), line_id=(1, 1, 1, 1))]
    tagged = post_item(api, title="Hesap makinesi", image=make_image_bytes(color=(10, 10, 10), size=(320, 240))).json()
    ocr.words = []
    post_item(api, title="Hesap makinesi", image=make_image_bytes(color=(200, 10, 10), size=(320, 240)))
    assert tagged["tags"] == ["casio"]

    def scores():
        results = api.post("/api/search", data={"query": "Casio hesap makinem"}).json()["results"]
        return {r["item"]["id"]: r["score"] for r in results}

    with_bonus = scores()
    api.settings.tag_bonus = 0.0
    without_bonus = scores()
    assert len(with_bonus) == 2
    assert with_bonus[tagged["id"]] == pytest.approx(without_bonus[tagged["id"]] + 0.05, abs=1e-3)
    other = next(i for i in with_bonus if i != tagged["id"])
    assert with_bonus[other] == pytest.approx(without_bonus[other], abs=1e-4)
