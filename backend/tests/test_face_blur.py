"""Yüz bulanıklaştırma testleri. Yüz içeren görsel KULLANILMAZ; gerçek yüz doğrulaması
scripts/try_blur.py ile elle yapılır."""
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.ml.face_blur import FaceBlurError, FaceBlurrer, anonymize_region, expand_box

LOCAL_MODEL = Path(__file__).resolve().parents[1] / "data" / "models" / "face_detection_yunet_2023mar.onnx"
MODEL_PATH = os.environ.get("FACE_MODEL_PATH", str(LOCAL_MODEL))
needs_model = pytest.mark.skipif(not os.path.isfile(MODEL_PATH), reason="YuNet modeli indirilmemiş")


def faceless_image() -> Image.Image:
    img = Image.new("RGB", (640, 480), (40, 90, 160))
    draw = ImageDraw.Draw(img)
    draw.rectangle((100, 100, 300, 250), fill=(220, 200, 30))
    draw.ellipse((350, 150, 550, 400), fill=(20, 20, 20))
    return img


@needs_model
def test_real_model_finds_no_face_in_synthetic_image():
    blurrer = FaceBlurrer(MODEL_PATH, score_threshold=0.6)
    assert blurrer.available
    img = faceless_image()
    out, n = blurrer.blur(img)
    assert n == 0
    assert out.size == img.size
    assert np.array_equal(np.asarray(out), np.asarray(img))


@needs_model
def test_real_model_handles_varied_sizes():
    blurrer = FaceBlurrer(MODEL_PATH, score_threshold=0.6)
    for size in [(1024, 768), (300, 900), (17, 23)]:
        out, n = blurrer.blur(Image.new("RGB", size, "gray"))
        assert n == 0 and out.size == size


def test_detection_error_fails_closed():
    class BrokenDetector:
        def setInputSize(self, size):
            pass

        def detect(self, img):
            raise RuntimeError("bozuk")

    blurrer = FaceBlurrer("/yok.onnx", score_threshold=0.6)
    blurrer._detector = BrokenDetector()
    with pytest.raises(FaceBlurError):
        blurrer.blur(faceless_image())


def test_missing_model_does_not_crash(tmp_path):
    blurrer = FaceBlurrer(str(tmp_path / "yok.onnx"), score_threshold=0.6)
    assert blurrer.available is False
    img = faceless_image()
    out, n = blurrer.blur(img)
    assert n == 0
    assert np.array_equal(np.asarray(out), np.asarray(img))


def test_corrupt_model_does_not_crash(tmp_path):
    bad = tmp_path / "bozuk.onnx"
    bad.write_bytes(b"bu bir onnx degil")
    blurrer = FaceBlurrer(str(bad), score_threshold=0.6)
    assert blurrer.available is False
    assert blurrer.blur(faceless_image())[1] == 0


def test_disabled_does_not_load(tmp_path):
    blurrer = FaceBlurrer(MODEL_PATH, score_threshold=0.6, enabled=False)
    assert blurrer.available is False
    assert blurrer.blur(faceless_image())[1] == 0


def test_expand_box_grows_and_clips():
    x0, y0, x1, y1 = expand_box(100, 100, 50, 100, 640, 480, ratio=0.2)
    assert (x0, y0, x1, y1) == (90, 80, 160, 220)

    x0, y0, x1, y1 = expand_box(-5, 470, 50, 40, 640, 480, ratio=0.2)
    assert x0 == 0 and y0 >= 0 and x1 <= 640 and y1 == 480


def test_anonymize_region_changes_only_the_box():
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 256, size=(200, 300, 3), dtype=np.uint8)
    box = (50, 40, 150, 160)
    out = anonymize_region(arr.copy(), box)
    x0, y0, x1, y1 = box
    inside_before = arr[y0:y1, x0:x1].astype(float)
    inside_after = out[y0:y1, x0:x1].astype(float)
    assert inside_after.std() < inside_before.std() * 0.5
    outside = np.ones(arr.shape[:2], dtype=bool)
    outside[y0:y1, x0:x1] = False
    assert np.array_equal(out[outside], arr[outside])
