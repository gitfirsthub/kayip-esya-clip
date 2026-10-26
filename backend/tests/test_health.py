from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app


def make_client(**state) -> TestClient:
    app = create_app()
    for key, value in state.items():
        setattr(app.state, key, value)
    return TestClient(app, raise_server_exceptions=False)


def test_health_ok_when_ready():
    client = make_client(ready=True, models_loaded=True, face_blur=True)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "models_loaded": True,
        "face_blur": True,
        "ocr": False,
        "item_count": 0,
        "version": "0.1.0",
    }


def test_health_loading_returns_503():
    r = make_client().get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "loading"}


def test_health_load_failed_returns_turkish_detail():
    r = make_client(load_failed=True).get("/health")
    assert r.status_code == 503
    assert r.json() == {"detail": "Modeller yüklenemedi."}


def test_unhandled_error_hides_traceback():
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("gizli iç ayrıntı")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert "gizli" not in r.text and "Traceback" not in r.text
    assert r.json()["detail"].startswith("Beklenmeyen bir hata")


def test_validation_error_is_turkish():
    app = create_app()

    @app.get("/num")
    async def num(n: int):
        return n

    r = TestClient(app).get("/num?n=abc")
    assert r.status_code == 422
    assert r.json() == {"detail": "Gönderilen bilgiler geçersiz. Lütfen alanları kontrol edin."}


def test_http_exception_and_404_are_turkish():
    client = make_client()
    r = client.get("/yok")
    assert r.status_code == 404
    assert r.json() == {"detail": "Kaynak bulunamadı."}

    app = create_app()

    @app.get("/gone")
    async def gone():
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")

    assert TestClient(app).get("/gone").json() == {"detail": "İlan bulunamadı."}


def test_health_item_count_comes_from_store(tmp_path):
    import numpy as np

    from app.store import Store

    store = Store(str(tmp_path), dim=4)
    store.add(
        {
            "title": "Termos",
            "location": "Yemekhane",
            "found_date": "2026-10-25",
            "dropoff_point": "Öğrenci İşleri",
            "image_path": "x.jpg",
            "category": "su şişesi-termos",
            "category_score": 0.7,
            "color": "mavi",
        },
        np.array([1, 0, 0, 0], dtype=np.float32),
    )
    r = make_client(ready=True, models_loaded=True, face_blur=False, store=store).get("/health")
    assert r.status_code == 200
    assert r.json()["item_count"] == 1
    store.close()
