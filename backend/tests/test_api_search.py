import os

from app.config import Settings
from tests.conftest import make_image_bytes
from tests.test_api_items import post_item


def search(client, image=None, **data):
    files = {"image": ("q.jpg", image, "image/jpeg")} if image is not None else None
    return client.post("/api/search", data=data, files=files)


def uploads(client):
    d = os.path.join(client.settings.data_dir, "uploads")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def test_empty_search_422(api):
    for r in (search(api), search(api, query="   ")):
        assert r.status_code == 422
        assert r.json() == {"detail": "Aramak için bir açıklama yazın veya fotoğraf yükleyin."}


def test_text_search_returns_results(api):
    post_item(api, title="Mavi şemsiye")
    post_item(api, title="Kırmızı kalem")
    r = search(api, query="mavi şemsiye")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"results", "took_ms"}
    assert len(body["results"]) == 2
    first = body["results"][0]
    assert set(first) == {"item", "score", "match_level"}
    assert first["match_level"] in {"yüksek", "orta", "düşük"}
    assert body["results"][0]["score"] >= body["results"][1]["score"]


def test_image_search_finds_identical_image_first_without_saving(api):
    img_a = make_image_bytes(color=(10, 200, 30))
    img_b = make_image_bytes(color=(200, 10, 30))
    a = post_item(api, image=img_a, title="Yeşil nesne").json()
    post_item(api, image=img_b, title="Kırmızı nesne")
    before = uploads(api)
    r = search(api, image=img_a)
    assert r.status_code == 200
    top = r.json()["results"][0]
    assert top["item"]["id"] == a["id"]
    assert top["score"] > 0.99 and top["match_level"] == "yüksek"
    assert uploads(api) == before


def test_text_and_image_fusion(api):
    img = make_image_bytes(color=(10, 200, 30))
    created = post_item(api, image=img).json()
    r = search(api, image=img, query="yeşil nesne")
    assert r.status_code == 200
    assert r.json()["results"][0]["item"]["id"] == created["id"]
    # 0.5*cos_text + 0.5*cos_img: görsel eşleşirse skor ~0.5 + 0.5*cos_text
    assert 0.3 < r.json()["results"][0]["score"] < 1.0


def test_filters_and_top_k(api):
    for i in range(3):
        post_item(api, title=f"Eşya {i}", location="Yemekhane", image=make_image_bytes(color=(i * 50, 10, 10)))
    post_item(api, location="Spor Salonu")
    assert len(search(api, query="x", location="Spor Salonu").json()["results"]) == 1
    assert len(search(api, query="x", top_k="2").json()["results"]) == 2
    cat = api.get("/api/items").json()["items"][0]["category"]
    for res in search(api, query="x", category=cat).json()["results"]:
        assert res["item"]["category"] == cat


def test_invalid_params_422(api):
    cases = [
        ({"query": "x", "location": "Ay"}, "Geçersiz yer."),
        ({"query": "x", "category": "uzay"}, "Geçersiz kategori."),
        ({"query": "x", "top_k": "0"}, "Sonuç sayısı 1 ile 50 arasında olmalıdır."),
        ({"query": "x", "top_k": "51"}, "Sonuç sayısı 1 ile 50 arasında olmalıdır."),
        ({"query": "x", "top_k": "abc"}, "Sonuç sayısı 1 ile 50 arasında olmalıdır."),
        ({"query": "x" * 201}, "Açıklama en fazla 200 karakter olabilir."),
    ]
    for data, detail in cases:
        r = search(api, **data)
        assert r.status_code == 422, data
        assert r.json() == {"detail": detail}, data


def test_search_image_errors(api):
    r = api.post("/api/search", files={"image": ("q.txt", b"abc", "text/plain")})
    assert r.status_code == 415
    r = search(api, image=b"\xff\xd8\xff bozuk")
    assert r.status_code == 400


def test_match_level_thresholds():
    from app.api.search import match_level

    assert match_level(0.30, 0.30, 0.24) == "yüksek"
    assert match_level(0.2999, 0.30, 0.24) == "orta"
    assert match_level(0.24, 0.30, 0.24) == "orta"
    assert match_level(0.2399, 0.30, 0.24) == "düşük"


def test_level_thresholds_depend_on_query_type():
    from app.api.search import level_thresholds

    s = Settings(match_high=0.30, match_medium=0.24, match_image_high=0.90, match_image_medium=0.80)
    assert level_thresholds(s, has_text=True, has_image=False) == (0.30, 0.24)
    assert level_thresholds(s, has_text=False, has_image=True) == (0.90, 0.80)
    high, medium = level_thresholds(s, has_text=True, has_image=True)
    assert abs(high - 0.60) < 1e-9 and abs(medium - 0.52) < 1e-9


def test_image_search_uses_image_thresholds(api):
    # Metin eşikleri her sonucu "yüksek" yapacak kadar düşük; görsel aramada yine de görsel eşikleri geçerli.
    api.settings.match_high = api.settings.match_medium = -1.0
    api.settings.match_image_high = api.settings.match_image_medium = 2.0
    post_item(api)
    files = {"image": ("a.jpg", make_image_bytes(), "image/jpeg")}
    levels = {r["match_level"] for r in api.post("/api/search", files=files).json()["results"]}
    assert levels == {"düşük"}
    levels = {r["match_level"] for r in api.post("/api/search", data={"query": "mavi"}).json()["results"]}
    assert levels == {"yüksek"}
