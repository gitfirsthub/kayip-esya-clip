from fastapi.testclient import TestClient

from app.main import create_app


def test_meta_returns_campus_lists(api):
    r = api.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"locations", "dropoff_points", "categories", "colors", "max_upload_mb"}
    assert "Yemekhane" in body["locations"]
    assert "Öğrenci İşleri" in body["dropoff_points"]
    assert "şemsiye" in body["categories"] and "diğer" in body["categories"]
    assert "lacivert" in body["colors"]
    assert body["max_upload_mb"] == 1


def test_meta_503_when_not_ready():
    r = TestClient(create_app()).get("/api/meta")
    assert r.status_code == 503
    assert r.json() == {"detail": "Model yükleniyor, birkaç saniye sonra tekrar deneyin."}
