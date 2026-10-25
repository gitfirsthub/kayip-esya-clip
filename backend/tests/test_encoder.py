import numpy as np
from PIL import Image

from app.ml.encoder import FakeEncoder


def test_fake_encoder_shapes_and_norms():
    enc = FakeEncoder()
    t = enc.encode_texts(["siyah sırt çantası", "mavi termos"])
    i = enc.encode_images([Image.new("RGB", (32, 32), "red")])
    assert t.shape == (2, 512) and t.dtype == np.float32
    assert i.shape == (1, 512) and i.dtype == np.float32
    assert np.allclose(np.linalg.norm(t, axis=1), 1.0, atol=1e-5)
    assert np.allclose(np.linalg.norm(i, axis=1), 1.0, atol=1e-5)
    assert enc.dim == 512


def test_fake_encoder_is_deterministic_and_discriminative():
    a, b = FakeEncoder(), FakeEncoder()
    assert np.array_equal(a.encode_texts(["anahtar"]), b.encode_texts(["anahtar"]))
    red = Image.new("RGB", (32, 32), "red")
    assert np.array_equal(a.encode_images([red]), b.encode_images([red.copy()]))

    t = a.encode_texts(["anahtar", "cüzdan"])
    assert not np.allclose(t[0], t[1])
    imgs = a.encode_images([red, Image.new("RGB", (32, 32), "blue")])
    assert not np.allclose(imgs[0], imgs[1])


def test_fake_encoder_empty_lists():
    enc = FakeEncoder()
    assert enc.encode_texts([]).shape == (0, 512)
    assert enc.encode_images([]).shape == (0, 512)
