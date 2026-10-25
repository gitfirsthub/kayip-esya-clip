import threading

import numpy as np
import pytest

from app.store import STATUS_RETURNED, STATUS_WAITING, Store

DIM = 8


def unit(i: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    v[i % DIM] = 1.0
    return v


def fields(**overrides) -> dict:
    base = {
        "title": "Siyah sırt çantası",
        "description": "",
        "location": "Merkez Kütüphane",
        "found_date": "2026-10-25",
        "dropoff_point": "Kütüphane Danışma",
        "image_path": "x.jpg",
        "category": "sırt çantası",
        "category_score": 0.8,
        "color": "siyah",
        "faces_blurred": 0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path), dim=DIM)
    yield s
    s.close()


def test_add_and_get(store):
    item = store.add(fields(faces_blurred=2), unit(0))
    assert item["status"] == STATUS_WAITING
    assert store.get(item["id"]) == item
    assert store.get("yok") is None
    assert store.count() == 1


def test_add_rejects_wrong_dim(store):
    with pytest.raises(ValueError):
        store.add(fields(), np.ones(DIM + 1, dtype=np.float32))


def test_list_order_filters_and_paging(store):
    a = store.add(fields(title="a", location="Yemekhane"), unit(0))
    b = store.add(fields(title="b", category="telefon"), unit(1))
    c = store.add(fields(title="c"), unit(2))

    items, total = store.list_items()
    assert total == 3
    assert [i["id"] for i in items] == [c["id"], b["id"], a["id"]]

    items, total = store.list_items(location="Yemekhane")
    assert (total, [i["id"] for i in items]) == (1, [a["id"]])

    items, total = store.list_items(category="telefon")
    assert [i["id"] for i in items] == [b["id"]]

    items, total = store.list_items(limit=1, offset=1)
    assert total == 3 and [i["id"] for i in items] == [b["id"]]


def test_update_status(store):
    item = store.add(fields(), unit(0))
    updated = store.update_status(item["id"], STATUS_RETURNED)
    assert updated["status"] == STATUS_RETURNED
    assert store.list_items(status=STATUS_RETURNED)[1] == 1
    assert store.update_status("yok", STATUS_RETURNED) is None
    with pytest.raises(ValueError):
        store.update_status(item["id"], "kayıp")


def test_delete_removes_from_search(store):
    a = store.add(fields(), unit(0))
    b = store.add(fields(), unit(1))
    assert store.delete(a["id"]) is True
    assert store.delete(a["id"]) is False
    assert store.get(a["id"]) is None
    results = store.search(unit(0), top_k=5)
    assert [r[0]["id"] for r in results] == [b["id"]]


def test_reopen_reloads_matrix(tmp_path):
    s = Store(str(tmp_path), dim=DIM)
    ids = [s.add(fields(), unit(i))["id"] for i in range(3)]
    s.close()

    s2 = Store(str(tmp_path), dim=DIM)
    assert s2.count() == 3
    item, score = s2.search(unit(1), top_k=1)[0]
    assert item["id"] == ids[1]
    assert score == pytest.approx(1.0)
    s2.close()


def test_search_ranks_by_cosine(store):
    ids = [store.add(fields(), unit(i))["id"] for i in range(4)]
    query = unit(2) * 0.8 + unit(3) * 0.6
    results = store.search(query, top_k=3)
    assert [r[0]["id"] for r in results] == [ids[2], ids[3], ids[0]]
    assert results[0][1] == pytest.approx(0.8)
    assert results[1][1] == pytest.approx(0.6)


def test_search_filters_and_returned(store):
    a = store.add(fields(location="Yemekhane"), unit(0))
    b = store.add(fields(category="telefon"), unit(0))
    c = store.add(fields(), unit(0))
    store.update_status(c["id"], STATUS_RETURNED)

    ids = lambda res: {r[0]["id"] for r in res}
    assert ids(store.search(unit(0))) == {a["id"], b["id"]}
    assert ids(store.search(unit(0), include_returned=True)) == {a["id"], b["id"], c["id"]}
    assert ids(store.search(unit(0), location="Yemekhane")) == {a["id"]}
    assert ids(store.search(unit(0), category="telefon")) == {b["id"]}
    assert store.search(unit(0), location="Yurtlar") == []


def test_search_top_k_larger_than_n_and_empty(store):
    assert store.search(unit(0)) == []
    store.add(fields(), unit(0))
    store.add(fields(), unit(1))
    assert len(store.search(unit(0), top_k=50)) == 2


def test_concurrent_adds(store):
    def worker(n):
        for i in range(10):
            store.add(fields(title=f"{n}-{i}"), unit(i))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert store.count() == 80
    assert store.list_items(limit=100)[1] == 80
    assert len(store.search(unit(0), top_k=100)) == 80
