"""SQLite tabanlı ilan deposu ve bellek içi vektör arama."""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

import numpy as np

STATUS_WAITING = "bekliyor"
STATUS_RETURNED = "teslim_edildi"
STATUSES = (STATUS_WAITING, STATUS_RETURNED)

FIELDS = (
    "id",
    "title",
    "description",
    "location",
    "found_date",
    "dropoff_point",
    "image_path",
    "category",
    "category_score",
    "color",
    "faces_blurred",
    "tags",
    "redacted_regions",
    "document_like",
    "status",
    "created_at",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL,
    found_date TEXT NOT NULL,
    dropoff_point TEXT NOT NULL,
    image_path TEXT NOT NULL,
    category TEXT NOT NULL,
    category_score REAL NOT NULL,
    color TEXT NOT NULL,
    faces_blurred INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'bekliyor',
    created_at TEXT NOT NULL,
    embedding BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at);
CREATE TABLE IF NOT EXISTS lost_reports (
    id TEXT PRIMARY KEY,
    code_hash TEXT NOT NULL UNIQUE,
    query_text TEXT NOT NULL DEFAULT '',
    location TEXT,
    created_at TEXT NOT NULL,
    text_embedding BLOB,
    image_embedding BLOB
);
CREATE TABLE IF NOT EXISTS report_matches (
    report_id TEXT NOT NULL REFERENCES lost_reports(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    score REAL NOT NULL,
    match_level TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (report_id, item_id)
);
"""

# Faz 7A: eski veritabanlarına idempotent olarak eklenen sütunlar.
MIGRATIONS = (
    ("tags", "TEXT NOT NULL DEFAULT '[]'"),
    ("redacted_regions", "INTEGER NOT NULL DEFAULT 0"),
    ("document_like", "INTEGER NOT NULL DEFAULT 0"),
    ("text_embedding", "BLOB"),
)

_COLUMNS = ", ".join(FIELDS)


def _row_to_item(row: sqlite3.Row) -> dict:
    item = {key: row[key] for key in FIELDS}
    item["faces_blurred"] = int(item["faces_blurred"])
    item["tags"] = json.loads(item["tags"])
    item["redacted_regions"] = int(item["redacted_regions"])
    item["document_like"] = bool(item["document_like"])
    return item


def _to_db(key: str, value):
    if key == "tags":
        return json.dumps(value, ensure_ascii=False)
    if key == "document_like":
        return int(value)
    return value


class Store:
    """İlanları SQLite'ta, embedding'leri ayrıca bellekte (N×dim) matris olarak tutar.

    Tek bağlantı ve tek kilit kullanılır; yazma ile bellek güncellemesi atomiktir.
    """

    def __init__(self, data_dir: str, dim: int = 512):
        os.makedirs(data_dir, exist_ok=True)
        self.dim = dim
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(os.path.join(data_dir, "app.db"), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._load_matrix()

    def _migrate(self) -> None:
        existing = {r["name"] for r in self._conn.execute("PRAGMA table_info(items)")}
        with self._conn:
            for column, ddl in MIGRATIONS:
                if column not in existing:
                    self._conn.execute(f"ALTER TABLE items ADD COLUMN {column} {ddl}")

    def _load_matrix(self) -> None:
        rows = self._conn.execute(
            "SELECT id, location, category, status, tags, embedding, text_embedding FROM items ORDER BY rowid"
        ).fetchall()
        self._ids: list[str] = [r["id"] for r in rows]
        self._locations = np.array([r["location"] for r in rows], dtype=object)
        self._categories = np.array([r["category"] for r in rows], dtype=object)
        self._statuses = np.array([r["status"] for r in rows], dtype=object)
        self._tags: list[frozenset[str]] = [frozenset(json.loads(r["tags"])) for r in rows]
        if rows:
            self._matrix = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
            # Metin embedding'i olmayan (Faz 7A öncesi) ilanlarda görsel embedding yedek olarak kullanılır;
            # böylece metin indeksi o ilanın skorunu değiştirmez. Açılışta backfill ile doldurulur.
            self._text_matrix = np.stack([
                np.frombuffer(r["text_embedding"] or r["embedding"], dtype=np.float32) for r in rows
            ])
        else:
            self._matrix = np.empty((0, self.dim), dtype=np.float32)
            self._text_matrix = np.empty((0, self.dim), dtype=np.float32)

    def _check_vec(self, vec: np.ndarray) -> np.ndarray:
        vec = np.asarray(vec, dtype=np.float32).reshape(-1)
        if vec.shape[0] != self.dim:
            raise ValueError(f"Embedding boyutu {self.dim} olmalı, {vec.shape[0]} geldi.")
        return vec

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def count(self) -> int:
        with self._lock:
            return len(self._ids)

    def add(self, fields: dict, embedding: np.ndarray, text_embedding: np.ndarray | None = None) -> dict:
        vec = self._check_vec(embedding)
        text_vec = self._check_vec(text_embedding) if text_embedding is not None else None
        item = {
            "id": uuid.uuid4().hex,
            "title": fields["title"],
            "description": fields.get("description", ""),
            "location": fields["location"],
            "found_date": fields["found_date"],
            "dropoff_point": fields["dropoff_point"],
            "image_path": fields["image_path"],
            "category": fields["category"],
            "category_score": float(fields["category_score"]),
            "color": fields["color"],
            "faces_blurred": int(fields.get("faces_blurred", 0)),
            "tags": list(fields.get("tags", [])),
            "redacted_regions": int(fields.get("redacted_regions", 0)),
            "document_like": bool(fields.get("document_like", False)),
            "status": STATUS_WAITING,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            with self._conn:
                self._conn.execute(
                    f"INSERT INTO items ({_COLUMNS}, embedding, text_embedding) "
                    f"VALUES ({', '.join('?' * (len(FIELDS) + 2))})",
                    [_to_db(k, item[k]) for k in FIELDS]
                    + [vec.tobytes(), text_vec.tobytes() if text_vec is not None else None],
                )
            self._ids.append(item["id"])
            self._locations = np.append(self._locations, np.array([item["location"]], dtype=object))
            self._categories = np.append(self._categories, np.array([item["category"]], dtype=object))
            self._statuses = np.append(self._statuses, np.array([item["status"]], dtype=object))
            self._tags.append(frozenset(item["tags"]))
            self._matrix = np.vstack([self._matrix, vec[None, :]])
            self._text_matrix = np.vstack([self._text_matrix, (text_vec if text_vec is not None else vec)[None, :]])
        return item

    def items_missing_text_embedding(self) -> list[dict]:
        """Metin embedding'i olmayan ilanların metin indeksine girecek alanları."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, title, description, tags FROM items WHERE text_embedding IS NULL ORDER BY rowid"
            ).fetchall()
        return [{"id": r["id"], "title": r["title"], "description": r["description"],
                 "tags": json.loads(r["tags"])} for r in rows]

    def set_text_embeddings(self, vectors: dict[str, np.ndarray]) -> None:
        checked = {item_id: self._check_vec(v) for item_id, v in vectors.items()}
        with self._lock:
            with self._conn:
                for item_id, vec in checked.items():
                    self._conn.execute("UPDATE items SET text_embedding = ? WHERE id = ?", (vec.tobytes(), item_id))
            for item_id, vec in checked.items():
                if item_id in self._ids:
                    self._text_matrix[self._ids.index(item_id)] = vec

    def get(self, item_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(f"SELECT {_COLUMNS} FROM items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(row) if row else None

    def list_items(
        self,
        status: str | None = None,
        location: str | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        clauses, params = [], []
        for column, value in (("status", status), ("location", location), ("category", category)):
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            total = self._conn.execute(f"SELECT COUNT(*) FROM items {where}", params).fetchone()[0]
            rows = self._conn.execute(
                f"SELECT {_COLUMNS} FROM items {where} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        return [_row_to_item(r) for r in rows], total

    def update_status(self, item_id: str, status: str) -> dict | None:
        if status not in STATUSES:
            raise ValueError(f"Geçersiz durum: {status}")
        with self._lock:
            with self._conn:
                cur = self._conn.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))
            if cur.rowcount == 0:
                return None
            self._statuses[self._ids.index(item_id)] = status
            return self.get(item_id)

    def delete(self, item_id: str) -> bool:
        with self._lock:
            with self._conn:
                cur = self._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            if cur.rowcount == 0:
                return False
            idx = self._ids.index(item_id)
            del self._ids[idx]
            self._locations = np.delete(self._locations, idx)
            self._categories = np.delete(self._categories, idx)
            self._statuses = np.delete(self._statuses, idx)
            del self._tags[idx]
            self._matrix = np.delete(self._matrix, idx, axis=0)
            self._text_matrix = np.delete(self._text_matrix, idx, axis=0)
            return True

    def search(
        self,
        vec: np.ndarray,
        *,
        location: str | None = None,
        category: str | None = None,
        include_returned: bool = False,
        top_k: int = 12,
        text_vec: np.ndarray | None = None,
        text_weight: float = 0.0,
        text_share: float = 1.0,
        query_terms: set[str] | frozenset[str] = frozenset(),
        tag_bonus: float = 0.0,
        tag_bonus_max: float = 0.0,
    ) -> list[tuple[dict, float]]:
        """Kosinüs benzerliğine (normalize vektörlerde nokta çarpım) göre en iyi top_k ilanı döndürür.

        Temel skor `görsel_matris @ vec`. Metin sorgusu varsa (text_vec) metin kısmı
        s_text = (1-w)*cos(q, ilan_görsel) + w*cos(q, ilan_metin) + etiket bonusu olur ve
        toplam skora text_share oranında girer (yalnızca metin: 1.0, metin+görsel: 0.5).
        """
        vec = self._check_vec(vec)
        text_vec = self._check_vec(text_vec) if text_vec is not None else None
        with self._lock:
            if not self._ids or top_k <= 0:
                return []
            mask = np.ones(len(self._ids), dtype=bool)
            if location:
                mask &= self._locations == location
            if category:
                mask &= self._categories == category
            if not include_returned:
                mask &= self._statuses != STATUS_RETURNED
            candidates = np.flatnonzero(mask)
            if candidates.size == 0:
                return []
            scores = self._matrix[candidates] @ vec
            if text_vec is not None and text_weight:
                text_part = self._text_matrix[candidates] @ text_vec - self._matrix[candidates] @ text_vec
                scores = scores + text_share * text_weight * text_part
            if query_terms and tag_bonus:
                bonus = np.array(
                    [min(tag_bonus * len(self._tags[i] & query_terms), tag_bonus_max) for i in candidates],
                    dtype=np.float32,
                )
                scores = scores + text_share * bonus
            k = min(top_k, candidates.size)
            if k < candidates.size:
                top = np.argpartition(-scores, k - 1)[:k]
            else:
                top = np.arange(candidates.size)
            top = top[np.argsort(-scores[top], kind="stable")]
            ids = [self._ids[candidates[i]] for i in top]
            top_scores = [float(scores[i]) for i in top]
            placeholders = ", ".join("?" * len(ids))
            rows = self._conn.execute(f"SELECT {_COLUMNS} FROM items WHERE id IN ({placeholders})", ids).fetchall()
        by_id = {r["id"]: _row_to_item(r) for r in rows}
        return [(by_id[i], s) for i, s in zip(ids, top_scores)]

    # --- Kayıp bildirimleri ---

    def add_report(
        self,
        code_hash: str,
        query_text: str,
        location: str | None,
        text_embedding: np.ndarray | None,
        image_embedding: np.ndarray | None,
    ) -> dict:
        text_vec = self._check_vec(text_embedding) if text_embedding is not None else None
        image_vec = self._check_vec(image_embedding) if image_embedding is not None else None
        report = {
            "id": uuid.uuid4().hex,
            "query_text": query_text,
            "location": location,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO lost_reports (id, code_hash, query_text, location, created_at, "
                    "text_embedding, image_embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        report["id"],
                        code_hash,
                        query_text,
                        location,
                        report["created_at"],
                        text_vec.tobytes() if text_vec is not None else None,
                        image_vec.tobytes() if image_vec is not None else None,
                    ),
                )
        return report

    def get_report_by_code_hash(self, code_hash: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, query_text, location, created_at FROM lost_reports WHERE code_hash = ?",
                (code_hash,),
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _best_score(
        item_vec: np.ndarray,
        text_blob: bytes | None,
        image_blob: bytes | None,
        medium: float,
        image_medium: float,
    ) -> float | None:
        """Metin ya da görsel eşiğini geçen skorların en yükseğini döndürür; geçmezse None."""
        passed = []
        if text_blob is not None:
            score = float(np.frombuffer(text_blob, dtype=np.float32) @ item_vec)
            if score >= medium:
                passed.append(score)
        if image_blob is not None:
            score = float(np.frombuffer(image_blob, dtype=np.float32) @ item_vec)
            if score >= image_medium:
                passed.append(score)
        return max(passed) if passed else None

    def _save_match(self, report_id: str, item_id: str, score: float, high: float, medium: float) -> None:
        level = "yüksek" if score >= high else "orta"
        self._conn.execute(
            "INSERT OR REPLACE INTO report_matches (report_id, item_id, score, match_level, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (report_id, item_id, round(score, 4), level, datetime.now(timezone.utc).isoformat()),
        )

    def match_item_to_reports(
        self, item_id: str, location: str, embedding: np.ndarray, *, high: float, medium: float, image_medium: float
    ) -> int:
        """Yeni ilanı tüm açık bildirimlerle karşılaştırır; eşleşenleri kaydeder, sayısını döndürür."""
        vec = self._check_vec(embedding)
        saved = 0
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, location, text_embedding, image_embedding FROM lost_reports"
            ).fetchall()
            with self._conn:
                for r in rows:
                    if r["location"] and r["location"] != location:
                        continue
                    score = self._best_score(vec, r["text_embedding"], r["image_embedding"], medium, image_medium)
                    if score is not None:
                        self._save_match(r["id"], item_id, score, high, medium)
                        saved += 1
        return saved

    def match_report_to_items(self, report_id: str, *, high: float, medium: float, image_medium: float) -> int:
        """Yeni bildirimi bekleyen mevcut ilanlarla karşılaştırır; eşleşenleri kaydeder."""
        saved = 0
        with self._lock:
            r = self._conn.execute(
                "SELECT id, location, text_embedding, image_embedding FROM lost_reports WHERE id = ?",
                (report_id,),
            ).fetchone()
            if r is None or not self._ids:
                return 0
            with self._conn:
                for i, item_id in enumerate(self._ids):
                    if self._statuses[i] == STATUS_RETURNED:
                        continue
                    if r["location"] and self._locations[i] != r["location"]:
                        continue
                    score = self._best_score(self._matrix[i], r["text_embedding"], r["image_embedding"], medium, image_medium)
                    if score is not None:
                        self._save_match(r["id"], item_id, score, high, medium)
                        saved += 1
        return saved

    def list_matches(self, report_id: str) -> list[tuple[dict, float, str]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT item_id, score, match_level FROM report_matches WHERE report_id = ? "
                "ORDER BY score DESC",
                (report_id,),
            ).fetchall()
            out = []
            for r in rows:
                item = self.get(r["item_id"])
                if item is not None:
                    out.append((item, float(r["score"]), r["match_level"]))
        return out
