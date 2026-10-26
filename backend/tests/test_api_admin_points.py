"""Teslim noktası bazlı yönetici tokenları: kapsam, liste ve yetkisiz erişim."""
import json
import logging
import os

import pytest

from app.config import Settings, get_settings
from tests.conftest import ADMIN_TOKEN
from tests.test_api_items import post_item

OFIS = "Öğrenci İşleri"
KUTUPHANE = "Kütüphane Danışma"
T_OFIS = "ofis-test-token"
T_KUT = "kut-test-token"
FORBIDDEN = {"detail": "Bu işlem için yetkiniz yok."}


def hdr(token):
    return {"X-Admin-Token": token}


@pytest.fixture
def points(api):
    api.app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=api.settings.data_dir,
        admin_token=ADMIN_TOKEN,
        admin_point_tokens=json.dumps({OFIS: T_OFIS, KUTUPHANE: T_KUT}),
    )
    return api


def test_me_reports_scope(points):
    assert points.get("/api/admin/me", headers=hdr(T_OFIS)).json() == {"scope": OFIS}
    assert points.get("/api/admin/me", headers=hdr(T_KUT)).json() == {"scope": KUTUPHANE}
    assert points.get("/api/admin/me", headers=hdr(ADMIN_TOKEN)).json() == {"scope": None}


@pytest.mark.parametrize("headers", [{}, hdr(""), hdr("yanlis")])
def test_me_and_list_reject_bad_tokens(points, headers):
    for url in ("/api/admin/me", "/api/admin/items"):
        r = points.get(url, headers=headers)
        assert r.status_code == 403 and r.json() == FORBIDDEN


def test_list_is_scoped_to_point(points):
    a = post_item(points, dropoff_point=OFIS).json()
    b = post_item(points, dropoff_point=KUTUPHANE).json()
    ids = lambda token: {i["id"] for i in points.get("/api/admin/items", headers=hdr(token)).json()["items"]}
    assert ids(T_OFIS) == {a["id"]}
    assert ids(T_KUT) == {b["id"]}
    assert ids(ADMIN_TOKEN) == {a["id"], b["id"]}
    r = points.get("/api/admin/items?status=teslim_edildi", headers=hdr(T_OFIS)).json()
    assert r["total"] == 0


def test_patch_and_delete_only_in_scope(points):
    own = post_item(points, dropoff_point=OFIS).json()
    other = post_item(points, dropoff_point=KUTUPHANE).json()
    r = points.patch(f"/api/items/{other['id']}/status", json={"status": "teslim_edildi"}, headers=hdr(T_OFIS))
    assert r.status_code == 404 and r.json() == {"detail": "İlan bulunamadı."}
    assert points.delete(f"/api/items/{other['id']}", headers=hdr(T_OFIS)).status_code == 404
    assert points.get(f"/api/items/{other['id']}").json()["status"] == "bekliyor"

    r = points.patch(f"/api/items/{own['id']}/status", json={"status": "teslim_edildi"}, headers=hdr(T_OFIS))
    assert r.status_code == 200 and r.json()["status"] == "teslim_edildi"
    path = os.path.join(points.settings.data_dir, "uploads", os.path.basename(own["image_url"]))
    assert os.path.exists(path)
    assert points.delete(f"/api/items/{own['id']}", headers=hdr(T_OFIS)).status_code == 204
    assert not os.path.exists(path)
    # Genel token her noktada çalışır.
    assert points.delete(f"/api/items/{other['id']}", headers=hdr(ADMIN_TOKEN)).status_code == 204


def test_bad_point_tokens_json_disables_point_tokens(api):
    api.app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=api.settings.data_dir, admin_token="", admin_point_tokens="{bozuk"
    )
    assert api.get("/api/admin/me", headers=hdr(T_OFIS)).status_code == 403


def test_tokens_not_in_logs_or_responses(points, caplog):
    caplog.set_level(logging.DEBUG)
    r = points.get("/api/admin/items", headers=hdr(T_OFIS))
    points.get("/api/admin/me", headers=hdr("yanlis-deneme"))
    assert T_OFIS not in r.text
    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert T_OFIS not in logged and "yanlis-deneme" not in logged


@pytest.mark.parametrize("token", ["change-me", "ornek-token-kutuphane", "kisa-token"])
def test_placeholder_and_short_tokens_are_ignored(api, token):
    api.app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=api.settings.data_dir, admin_token=token, admin_point_tokens=json.dumps({OFIS: token})
    )
    assert api.get("/api/admin/me", headers=hdr(token)).status_code == 403
    assert api.delete("/api/items/1", headers=hdr(token)).status_code == 403


def test_ignored_tokens_are_counted_without_values():
    s = Settings(admin_token="change-me", admin_point_tokens=json.dumps({OFIS: "ornek-token-x", KUTUPHANE: T_KUT}))
    assert not s.admin_token_usable
    assert s.point_tokens == {KUTUPHANE: T_KUT}
    assert s.ignored_admin_tokens == 2
