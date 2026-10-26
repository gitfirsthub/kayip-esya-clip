import os

from app.tracking import ALPHABET, CODE_LENGTH, generate_code
from tests.conftest import ADMIN_TOKEN, make_image_bytes
from tests.test_api_items import post_item, uploaded_files


def open_matching(api):
    """FakeEncoder rastgele vektör ürettiğinden eşikleri düşürüp her çifti eşleştirir."""
    api.settings.match_medium = -1.0
    api.settings.match_image_medium = -1.0


def post_report(client, **data):
    return client.post("/api/lost-reports", data=data)


def test_code_format_and_uniqueness():
    codes = {generate_code() for _ in range(1000)}
    assert len(codes) == 1000
    for code in codes:
        assert len(code) == CODE_LENGTH
        assert set(code) <= set(ALPHABET)
    assert not set("0O1lIi-_") & set(ALPHABET)


def test_report_requires_query_or_image(api):
    r = post_report(api)
    assert r.status_code == 422
    assert "açıklama" in r.json()["detail"]


def test_report_rejects_bad_location_and_long_query(api):
    assert post_report(api, query="termos", location="Mars").status_code == 422
    assert post_report(api, query="x" * 201).status_code == 422


def test_report_returns_code_and_matches_empty(api):
    r = post_report(api, query="lacivert termos")
    assert r.status_code == 201
    code = r.json()["tracking_code"]
    assert len(code) == CODE_LENGTH
    m = api.get(f"/api/lost-reports/{code}/matches")
    assert m.status_code == 200
    assert m.json()["matches"] == []
    assert m.json()["query_text"] == "lacivert termos"
    assert api.get(f"/api/lost-reports/{code.lower()}/matches").status_code == 200


def test_bad_and_unknown_code(api):
    assert api.get("/api/lost-reports/abc/matches").status_code == 422
    assert api.get("/api/lost-reports/0O1lI-_x/matches").status_code == 422
    r = api.get("/api/lost-reports/AAAAAAAA/matches")
    assert r.status_code == 404
    assert "bulunamadı" in r.json()["detail"]


def test_report_image_not_written_to_disk(api):
    r = api.post(
        "/api/lost-reports",
        data={"query": "termos"},
        files={"image": ("a.jpg", make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 201
    assert uploaded_files(api) == []
    assert not any(f.endswith(".jpg") for _, _, fs in os.walk(api.settings.data_dir) for f in fs)


def test_report_scans_existing_items(api):
    open_matching(api)
    item = post_item(api).json()
    code = post_report(api, query="mavi şemsiye").json()["tracking_code"]
    body = api.get(f"/api/lost-reports/{code}/matches").json()
    assert [m["item"]["id"] for m in body["matches"]] == [item["id"]]


def test_report_location_filter_and_threshold(api):
    open_matching(api)
    post_item(api, location="Yemekhane")
    other = post_report(api, query="şemsiye", location="Merkez Kütüphane").json()["tracking_code"]
    assert api.get(f"/api/lost-reports/{other}/matches").json()["matches"] == []
    api.settings.match_medium = 2.0  # hiçbir skor geçemez
    strict = post_report(api, query="şemsiye").json()["tracking_code"]
    assert api.get(f"/api/lost-reports/{strict}/matches").json()["matches"] == []


def test_report_skips_returned_items(api):
    open_matching(api)
    item = post_item(api).json()
    r = api.patch(
        f"/api/items/{item['id']}/status",
        json={"status": "teslim_edildi"},
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert r.status_code == 200
    code = post_report(api, query="şemsiye").json()["tracking_code"]
    assert api.get(f"/api/lost-reports/{code}/matches").json()["matches"] == []


def test_report_then_item_shows_match(api):
    open_matching(api)
    code = post_report(api, query="mavi şemsiye").json()["tracking_code"]
    assert api.get(f"/api/lost-reports/{code}/matches").json()["matches"] == []
    item = post_item(api).json()
    body = api.get(f"/api/lost-reports/{code}/matches").json()
    assert [m["item"]["id"] for m in body["matches"]] == [item["id"]]
    assert body["matches"][0]["match_level"] in ("yüksek", "orta")


def test_new_item_below_threshold_not_matched(api):
    code = post_report(api, query="mavi şemsiye").json()["tracking_code"]
    api.settings.match_medium = 2.0
    post_item(api)
    assert api.get(f"/api/lost-reports/{code}/matches").json()["matches"] == []


def test_new_item_respects_report_location(api):
    open_matching(api)
    code = post_report(api, query="şemsiye", location="Merkez Kütüphane").json()["tracking_code"]
    post_item(api, location="Yemekhane")
    assert api.get(f"/api/lost-reports/{code}/matches").json()["matches"] == []
    item = post_item(api, location="Merkez Kütüphane").json()
    ids = [m["item"]["id"] for m in api.get(f"/api/lost-reports/{code}/matches").json()["matches"]]
    assert ids == [item["id"]]


def test_deleted_item_disappears_from_matches(api):
    open_matching(api)
    code = post_report(api, query="şemsiye").json()["tracking_code"]
    item = post_item(api).json()
    r = api.delete(f"/api/items/{item['id']}", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert r.status_code == 204
    assert api.get(f"/api/lost-reports/{code}/matches").json()["matches"] == []


def test_matching_failure_does_not_break_item_creation(api, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("eşleştirme patladı")

    monkeypatch.setattr("app.store.Store.match_item_to_reports", boom)
    r = post_item(api)
    assert r.status_code == 201
    assert api.get("/health").json()["item_count"] == 1


def test_image_report_uses_image_threshold(api):
    api.settings.match_medium = 2.0  # metin yolu kapalı
    api.settings.match_image_medium = -1.0
    code = api.post(
        "/api/lost-reports",
        data={},
        files={"image": ("a.jpg", make_image_bytes(), "image/jpeg")},
    ).json()["tracking_code"]
    item = post_item(api).json()
    ids = [m["item"]["id"] for m in api.get(f"/api/lost-reports/{code}/matches").json()["matches"]]
    assert ids == [item["id"]]


def test_image_report_match_level_uses_image_high(api):
    api.settings.match_medium = 2.0  # metin yolu kapalı
    api.settings.match_high = -1.0  # metin eşiği görsel eşleşmeye uygulanmamalı
    api.settings.match_image_medium = -1.0
    api.settings.match_image_high = 2.0
    files = {"image": ("a.jpg", make_image_bytes(), "image/jpeg")}
    code = api.post("/api/lost-reports", data={}, files=files).json()["tracking_code"]
    post_item(api)
    levels = [m["match_level"] for m in api.get(f"/api/lost-reports/{code}/matches").json()["matches"]]
    assert levels == ["orta"]
