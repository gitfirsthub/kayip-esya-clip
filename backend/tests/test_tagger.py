import json
from pathlib import Path

import numpy as np
import pytest

from app.ml.encoder import FakeEncoder
from app.ml.tagger import Tagger

CAMPUS = json.loads((Path(__file__).resolve().parents[1] / "app" / "data" / "campus.json").read_text("utf-8"))
# "diğer" istem olarak kodlanmaz; yalnızca düşük güvende dönen yedek etikettir.
CATEGORY_NAMES = [c["tr"] for c in CAMPUS["categories"] if c["tr"] != "diğer"]
COLOR_NAMES = [c["tr"] for c in CAMPUS["colors"]]


class RecordingEncoder(FakeEncoder):
    def __init__(self):
        super().__init__()
        self.calls = []

    def encode_texts(self, texts):
        self.calls.append(list(texts))
        return super().encode_texts(texts)


def tagger(template="avg") -> Tagger:
    return Tagger(FakeEncoder(), CAMPUS["categories"], CAMPUS["colors"], template=template)


@pytest.mark.parametrize("template", ["avg", "en", "tr"])
def test_prompt_embeddings_are_normalized(template):
    t = tagger(template)
    for matrix, n in ((t.category_embeddings, len(CATEGORY_NAMES)), (t.color_embeddings, len(COLOR_NAMES))):
        assert matrix.shape == (n, 512)
        assert np.allclose(np.linalg.norm(matrix, axis=1), 1.0, atol=1e-5)


def test_prompts_use_both_languages_for_avg():
    enc = RecordingEncoder()
    Tagger(enc, CAMPUS["categories"], CAMPUS["colors"], template="avg")
    texts = [t for call in enc.calls for t in call]
    assert "a photo of a backpack" in texts
    assert "bir sırt çantası fotoğrafı" in texts


def test_other_is_not_a_prompt():
    enc = RecordingEncoder()
    Tagger(enc, CAMPUS["categories"], CAMPUS["colors"], template="avg")
    texts = [t for call in enc.calls for t in call]
    assert not any("other" in t or "diğer" in t for t in texts)


def test_prompt_vector_maps_to_its_category():
    t = tagger()
    idx = CATEGORY_NAMES.index("sırt çantası")
    category, score, color = t.tag(t.category_embeddings[idx])
    assert category == "sırt çantası"
    assert 0.35 <= score <= 1.0
    assert color in COLOR_NAMES


def test_color_vector_maps_to_its_color():
    t = tagger()
    idx = COLOR_NAMES.index("lacivert")
    assert t.tag(t.color_embeddings[idx])[2] == "lacivert"


def test_low_confidence_falls_back_to_other():
    t = tagger()
    # Bütün kategori istemlerine dik bir vektör: kosinüsler 0, softmax düz, güven ~1/18.
    basis = t.category_embeddings.T
    vec = np.random.default_rng(0).standard_normal(basis.shape[0])
    vec -= basis @ np.linalg.lstsq(basis, vec, rcond=None)[0]
    vec /= np.linalg.norm(vec)
    category, score, color = t.tag(vec.astype(np.float32))
    assert category == "diğer"
    assert score < 0.35
    assert color in COLOR_NAMES
