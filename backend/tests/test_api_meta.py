from fastapi.testclient import TestClient

from app.main import create_app


def test_meta_returns_campus_lists(api):
    r = api.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"locations", "dropoff_points", "categories", "colors", "max_upload_mb", "found_date_max_days"}
    assert "Yemekhane" in body["locations"]
    assert "Öğrenci İşleri" in body["dropoff_points"]
    assert "şemsiye" in body["categories"] and "diğer" in body["categories"]
    assert "lacivert" in body["colors"]
    assert body["max_upload_mb"] == 1
    assert body["found_date_max_days"] == 60


def test_meta_503_when_not_ready():
    r = TestClient(create_app()).get("/api/meta")
    assert r.status_code == 503
    assert r.json() == {"detail": "Model yükleniyor, birkaç saniye sonra tekrar deneyin."}


def test_default_cors_allows_localhost_and_loopback_ip(api, monkeypatch):
    from app.config import Settings
    from app.main import create_app
    from fastapi.testclient import TestClient

    # Kod varsayılanı sınanır: yerel .env ve ortam değişkeni okunmaz.
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    defaults = Settings(_env_file=None, data_dir=api.settings.data_dir)
    monkeypatch.setattr("app.main.get_settings", lambda: defaults)
    client = TestClient(create_app())
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        r = client.options("/api/meta", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
        assert r.headers.get("access-control-allow-origin") == origin
    r = client.options("/api/meta", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers
