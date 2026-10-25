import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import deps
from app.config import Settings, get_settings
from app.main import create_app, load_campus
from app.ml.encoder import FakeEncoder
from app.ml.tagger import Tagger
from app.store import Store

ADMIN_TOKEN = "test-admin-token"


class FakeBlurrer:
    """FaceBlurrer arayüzü; görseli değiştirmeden sabit sayıda yüz bulmuş gibi döner."""

    def __init__(self, available: bool = True, faces: int = 0):
        self.available = available
        self.faces = faces
        self.calls = 0

    def blur(self, img):
        self.calls += 1
        return img, self.faces


def make_image_bytes(color=(30, 90, 200), size=(64, 48), fmt="JPEG", exif: bool = False) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    kwargs = {}
    if exif and fmt == "JPEG":
        exif_data = Image.Exif()
        exif_data[0x010F] = "TestMarka"  # Make
        kwargs["exif"] = exif_data
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=str(tmp_path), admin_token=ADMIN_TOKEN, max_upload_mb=1)


@pytest.fixture
def blurrer():
    return FakeBlurrer()


@pytest.fixture
def api(settings, blurrer):
    app = create_app()
    encoder = FakeEncoder()
    campus = load_campus()
    store = Store(settings.data_dir, dim=encoder.dim)
    app.state.campus = campus
    app.state.store = store
    app.state.ready = True
    app.state.models_loaded = True
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[deps.get_encoder] = lambda: encoder
    app.dependency_overrides[deps.get_tagger] = lambda: Tagger(encoder, campus["categories"], campus["colors"])
    app.dependency_overrides[deps.get_blurrer] = lambda: blurrer
    app.dependency_overrides[deps.get_store] = lambda: store
    app.dependency_overrides[deps.get_campus] = lambda: campus
    client = TestClient(app, raise_server_exceptions=False)
    client.settings = settings
    yield client
    store.close()
