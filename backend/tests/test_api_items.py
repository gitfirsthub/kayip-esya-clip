import os
from datetime import datetime, timedelta

from PIL import Image

from app.api.items import TURKEY_TZ
from tests.conftest import make_image_bytes


def today(delta_days: int = 0) -> str:
    return (datetime.now(TURKEY_TZ).date() + timedelta(days=delta_days)).isoformat()


def valid_form(**over):
    form = {
        "title": "Mavi şemsiye",
        "description": "Sapı kırık",
        "location": "Yemekhane",
        "found_date": today(),
        "dropoff_point": "Öğrenci İşleri",
    }
    form.update(over)
    return form


def post_item(client, image=None, content_type="image/jpeg", filename="a.jpg", **over):
    files = {"image": (filename, image if image is not None else make_image_bytes(), content_type)}
    return client.post("/api/items", data=valid_form(**over), files=files)


def uploaded_files(client):
    directory = os.path.join(client.settings.data_dir, "uploads")
    return os.listdir(directory) if os.path.isdir(directory) else []


def test_create_item_success(api, blurrer):
    blurrer.faces = 2
    r = post_item(api)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {
        "id", "title", "description", "location", "found_date", "dropoff_point", "image_url",
        "category", "category_score", "color", "faces_blurred", "status", "created_at",
    }
    assert body["title"] == "Mavi şemsiye"
    assert body["status"] == "bekliyor"
    assert body["faces_blurred"] == 2
    assert body["image_url"].startswith("/uploads/") and body["image_url"].endswith(".jpg")
    assert len(uploaded_files(api)) == 1
    assert api.get("/health").json()["item_count"] == 1


def test_uploaded_image_is_served_and_exif_free(api):
    r = post_item(api, image=make_image_bytes(exif=True))
    url = r.json()["image_url"]
    served = api.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"
    path = os.path.join(api.settings.data_dir, "uploads", os.path.basename(url))
    with Image.open(path) as saved:
        assert saved.format == "JPEG"
        assert len(saved.getexif()) == 0


def test_large_image_is_downscaled(api):
    big = make_image_bytes(size=(3000, 1500))
    r = post_item(api, image=big)
    # max_upload_mb=1: düz renkli JPEG küçük kalır, 201 beklenir
    assert r.status_code == 201
    path = os.path.join(api.settings.data_dir, "uploads", os.path.basename(r.json()["image_url"]))
    with Image.open(path) as saved:
        assert max(saved.size) == 1024


def test_missing_image_422(api):
    r = api.post("/api/items", data=valid_form())
    assert r.status_code == 422
    assert r.json() == {"detail": "Lütfen bir fotoğraf yükleyin."}


def test_text_file_415(api):
    r = post_item(api, image=b"merhaba", content_type="text/plain", filename="a.txt")
    assert r.status_code == 415
    assert r.json() == {"detail": "Desteklenmeyen dosya türü. JPEG, PNG veya WEBP yükleyin."}


def test_gif_with_image_header_is_415_by_pillow_format(api):
    gif = make_image_bytes(fmt="GIF")
    r = post_item(api, image=gif, content_type="image/jpeg")
    assert r.status_code == 415


def test_corrupt_jpeg_400(api):
    r = post_item(api, image=b"\xff\xd8\xff\xe0 bozuk veri")
    assert r.status_code == 400
    assert r.json() == {"detail": "Görsel açılamadı. Lütfen geçerli bir JPEG, PNG veya WEBP dosyası yükleyin."}
    assert uploaded_files(api) == []


def test_too_large_413(api):
    r = post_item(api, image=b"\xff\xd8" + b"0" * (1024 * 1024 + 10))
    assert r.status_code == 413
    assert r.json() == {"detail": "Dosya çok büyük. En fazla 1 MB yükleyebilirsiniz."}


def test_field_validation_messages(api):
    cases = [
        ({"title": "ab"}, "Başlık 3 ile 80 karakter arasında olmalıdır."),
        ({"title": "x" * 81}, "Başlık 3 ile 80 karakter arasında olmalıdır."),
        ({"description": "x" * 501}, "Açıklama en fazla 500 karakter olabilir."),
        ({"location": "Ay"}, "Geçersiz yer."),
        ({"dropoff_point": "Ay"}, "Geçersiz teslim noktası."),
        ({"found_date": "25.10.2026"}, "Geçersiz tarih biçimi (YYYY-AA-GG)."),
        ({"found_date": "2026-02-30"}, "Geçersiz tarih biçimi (YYYY-AA-GG)."),
        ({"found_date": today(1)}, "Bulunma tarihi gelecekte olamaz."),
        ({"found_date": today(-61)}, "Bulunma tarihi en fazla 60 gün öncesi olabilir."),
    ]
    for over, detail in cases:
        r = post_item(api, **over)
        assert r.status_code == 422, over
        assert r.json() == {"detail": detail}, over
    assert uploaded_files(api) == []


def test_date_boundaries_accepted(api):
    assert post_item(api, found_date=today()).status_code == 201
    assert post_item(api, found_date=today(-60)).status_code == 201


def test_missing_title_422(api):
    files = {"image": ("a.jpg", make_image_bytes(), "image/jpeg")}
    data = valid_form()
    del data["title"]
    r = api.post("/api/items", data=data, files=files)
    assert r.status_code == 422
    assert r.json() == {"detail": "Başlık 3 ile 80 karakter arasında olmalıdır."}


def test_blur_unavailable_503_and_nothing_saved(api, blurrer):
    blurrer.available = False
    r = post_item(api)
    assert r.status_code == 503
    assert r.json() == {"detail": "Yüz bulanıklaştırma şu an kullanılamıyor; ilan kaydedilemedi."}
    assert uploaded_files(api) == []
    assert api.get("/health").json()["item_count"] == 0


def test_list_items_newest_first_and_paging(api):
    ids = [post_item(api, title=f"Eşya {i}").json()["id"] for i in range(3)]
    r = api.get("/api/items")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert [i["id"] for i in body["items"]] == ids[::-1]
    page = api.get("/api/items?limit=2&offset=2").json()
    assert page["total"] == 3 and [i["id"] for i in page["items"]] == [ids[0]]


def test_list_items_filters(api):
    post_item(api, location="Yemekhane")
    post_item(api, location="Spor Salonu")
    assert api.get("/api/items?location=Yemekhane").json()["total"] == 1
    assert api.get("/api/items?status=teslim_edildi").json()["total"] == 0
    assert api.get("/api/items?status=bekliyor").json()["total"] == 2
    cat = api.get("/api/items").json()["items"][0]["category"]
    assert api.get(f"/api/items?category={cat}").json()["total"] >= 1


def test_list_items_invalid_params_422(api):
    for query, detail in [
        ("status=x", "Geçersiz durum."),
        ("location=Ay", "Geçersiz yer."),
        ("category=x", "Geçersiz kategori."),
        ("limit=0", "Geçersiz sayfalama değeri."),
        ("limit=101", "Geçersiz sayfalama değeri."),
        ("offset=-1", "Geçersiz sayfalama değeri."),
    ]:
        r = api.get(f"/api/items?{query}")
        assert r.status_code == 422, query
        assert r.json() == {"detail": detail}, query


def test_get_item_and_404(api):
    created = post_item(api).json()
    r = api.get(f"/api/items/{created['id']}")
    assert r.status_code == 200 and r.json() == created
    r = api.get("/api/items/yok")
    assert r.status_code == 404
    assert r.json() == {"detail": "İlan bulunamadı."}
