import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from tests.conftest import ADMIN_TOKEN, make_image_bytes
from tests.test_api_items import valid_form

LOADING = {"detail": "Model yükleniyor, birkaç saniye sonra tekrar deneyin."}


def test_all_api_routes_503_while_loading():
    client = TestClient(create_app(), raise_server_exceptions=False)
    img = ("a.jpg", make_image_bytes(), "image/jpeg")
    calls = [
        client.get("/api/meta"),
        client.post("/api/items", data=valid_form(), files={"image": img}),
        client.get("/api/items"),
        client.get("/api/items/abc"),
        client.post("/api/search", data={"query": "x"}),
        client.patch("/api/items/abc/status", json={"status": "bekliyor"}, headers={"X-Admin-Token": ADMIN_TOKEN}),
        client.delete("/api/items/abc", headers={"X-Admin-Token": ADMIN_TOKEN}),
    ]
    for r in calls:
        assert r.status_code == 503, r.request.url
        assert r.json() == LOADING


def test_unknown_route_and_method_are_turkish(api):
    assert api.get("/api/yok").json() == {"detail": "Kaynak bulunamadı."}
    r = api.put("/api/meta")
    assert r.status_code == 405 and r.json() == {"detail": "Bu yönteme izin verilmiyor."}


def test_unhandled_error_in_endpoint_hides_internals(api):
    class Boom:
        def search(self, *a, **k):
            raise RuntimeError("gizli iç ayrıntı")

    from app import deps

    api.app.dependency_overrides[deps.get_store] = lambda: Boom()
    r = api.post("/api/search", data={"query": "x"})
    assert r.status_code == 500
    assert "gizli" not in r.text and "Traceback" not in r.text
    assert r.json()["detail"].startswith("Beklenmeyen bir hata")


def test_store_failure_on_upload_removes_saved_file(api):
    import os

    from app import deps

    class Failing:
        def add(self, *a, **k):
            raise RuntimeError("disk dolu")

    api.app.dependency_overrides[deps.get_store] = lambda: Failing()
    r = api.post(
        "/api/items", data=valid_form(), files={"image": ("a.jpg", make_image_bytes(), "image/jpeg")}
    )
    assert r.status_code == 500
    directory = os.path.join(api.settings.data_dir, "uploads")
    assert os.listdir(directory) == []


def test_missing_upload_on_fresh_install_is_404(api):
    # Henüz hiç ilan yüklenmemiş yeni kurulum: dizin açılışta oluşur, istek 500 değil 404 olur.
    r = api.get("/uploads/olmayan.jpg")
    assert r.status_code == 404
    assert r.json() == {"detail": "Kaynak bulunamadı."}


BAD_REQUEST = {"detail": "İstek okunamadı. Lütfen formu yeniden gönderin."}


def test_malformed_multipart_is_turkish(api):
    # Starlette'in İngilizce mesajları ("Invalid multipart data.", "Missing boundary in multipart.") sızmamalı.
    for ctype, body in (("multipart/form-data; boundary=b", b"rastgele"), ("multipart/form-data", b"x")):
        r = api.post("/api/search", content=body, headers={"Content-Type": ctype})
        assert r.status_code == 400
        assert r.json() == BAD_REQUEST


def test_uploads_path_traversal_blocked(api):
    r = api.get("/uploads/../app.db")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


def test_all_errors_use_detail_key(api):
    img = ("a.png", make_image_bytes(fmt="PNG"), "image/png")
    for r in (
        api.post("/api/items", data=valid_form(title="a"), files={"image": img}),
        api.get("/api/items/yok"),
        api.post("/api/search", data={}),
        api.delete("/api/items/yok"),
    ):
        assert r.status_code >= 400
        assert list(r.json()) == ["detail"] and isinstance(r.json()["detail"], str)


def test_png_and_webp_accepted(api):
    for fmt, ctype in (("PNG", "image/png"), ("WEBP", "image/webp")):
        r = api.post(
            "/api/items",
            data=valid_form(),
            files={"image": (f"a.{fmt.lower()}", make_image_bytes(fmt=fmt), ctype)},
        )
        assert r.status_code == 201, fmt


def test_phone_mpo_jpeg_accepted(api):
    # Telefonların çok kareli JPEG'i (MPO) image/jpeg olarak gelir; 415 almamalı.
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), "red").save(buf, "MPO", save_all=True, append_images=[Image.new("RGB", (64, 48), "blue")])
    r = api.post("/api/items", data=valid_form(), files={"image": ("tel.jpg", buf.getvalue(), "image/jpeg")})
    assert r.status_code == 201
