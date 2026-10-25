import os

from app.config import Settings, get_settings
from tests.conftest import ADMIN_TOKEN
from tests.test_api_items import post_item
from tests.test_api_search import search

HEADERS = {"X-Admin-Token": ADMIN_TOKEN}
FORBIDDEN = {"detail": "Bu işlem için yetkiniz yok."}


def test_patch_requires_valid_token(api):
    item = post_item(api).json()
    url = f"/api/items/{item['id']}/status"
    body = {"status": "teslim_edildi"}
    for headers in ({}, {"X-Admin-Token": "yanlis"}, {"X-Admin-Token": ""}):
        r = api.patch(url, json=body, headers=headers)
        assert r.status_code == 403 and r.json() == FORBIDDEN
    assert api.get(f"/api/items/{item['id']}").json()["status"] == "bekliyor"


def test_admin_disabled_when_token_empty(api):
    api.app.dependency_overrides[get_settings] = lambda: Settings(data_dir=api.settings.data_dir, admin_token="")
    item = post_item(api).json()
    r = api.patch(f"/api/items/{item['id']}/status", json={"status": "teslim_edildi"}, headers={"X-Admin-Token": ""})
    assert r.status_code == 403 and r.json() == FORBIDDEN
    r = api.delete(f"/api/items/{item['id']}", headers={"X-Admin-Token": "change-me"})
    assert r.status_code == 403


def test_patch_updates_status_both_ways(api):
    item = post_item(api).json()
    url = f"/api/items/{item['id']}/status"
    r = api.patch(url, json={"status": "teslim_edildi"}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["status"] == "teslim_edildi"
    assert api.get("/api/items?status=teslim_edildi").json()["total"] == 1
    r = api.patch(url, json={"status": "bekliyor"}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["status"] == "bekliyor"


def test_patch_invalid_status_and_404(api):
    item = post_item(api).json()
    r = api.patch(f"/api/items/{item['id']}/status", json={"status": "kayip"}, headers=HEADERS)
    assert r.status_code == 422 and r.json() == {"detail": "Geçersiz durum."}
    r = api.patch("/api/items/yok/status", json={"status": "bekliyor"}, headers=HEADERS)
    assert r.status_code == 404 and r.json() == {"detail": "İlan bulunamadı."}


def test_delete_removes_item_and_file(api):
    item = post_item(api).json()
    path = os.path.join(api.settings.data_dir, "uploads", os.path.basename(item["image_url"]))
    assert os.path.exists(path)
    assert api.delete(f"/api/items/{item['id']}").status_code == 403
    r = api.delete(f"/api/items/{item['id']}", headers=HEADERS)
    assert r.status_code == 204 and r.content == b""
    assert not os.path.exists(path)
    assert api.get(f"/api/items/{item['id']}").status_code == 404
    assert search(api, query="x").json()["results"] == []
    assert api.delete(f"/api/items/{item['id']}", headers=HEADERS).status_code == 404


def test_include_returned_in_search(api):
    item = post_item(api).json()
    api.patch(f"/api/items/{item['id']}/status", json={"status": "teslim_edildi"}, headers=HEADERS)
    assert search(api, query="x").json()["results"] == []
    assert len(search(api, query="x", include_returned="true").json()["results"]) == 1
    assert search(api, query="x", include_returned="maybe").status_code == 422
