"""
JARVIS Cache — SQLite-backed response cache with fuzzy matching.
"""

import difflib
import hashlib
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "data" / "jarvis_cache.db")

_TTL_FACTUAL = 86400 * 7
_TTL_CURRENT = 600
_TTL_DEFAULT = 86400
_FUZZY_THRESHOLD = 0.72

# Per-thread connections — safe under concurrent Flask requests
_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(_DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key      TEXT PRIMARY KEY,
                query    TEXT NOT NULL,
                response TEXT NOT NULL,
                ttl_type TEXT NOT NULL DEFAULT 'default',
                created  REAL NOT NULL,
                hits     INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON cache(created)")
        conn.commit()
        _local.conn = conn
    return _local.conn


def _make_key(query: str) -> str:
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def _ttl_for(ttl_type: str) -> float:
    return {"factual": _TTL_FACTUAL, "current": _TTL_CURRENT}.get(ttl_type, _TTL_DEFAULT)


def _classify_ttl(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ("weather", "news", "today", "now", "current", "latest", "time")):
        return "current"
    if any(w in q for w in ("who is", "what is", "define", "explain", "how does", "history of")):
        return "factual"
    return "default"


def get(query: str) -> Optional[str]:
    q = query.lower().strip()
    key = _make_key(q)
    now = time.time()
    db = _conn()

    try:
        row = db.execute("SELECT response, ttl_type, created FROM cache WHERE key=?", (key,)).fetchone()
        if row:
            response, ttl_type, created = row
            if now - created < _ttl_for(ttl_type):
                db.execute("UPDATE cache SET hits=hits+1 WHERE key=?", (key,))
                db.commit()
                return response
            db.execute("DELETE FROM cache WHERE key=?", (key,))
            db.commit()
            return None

        rows = db.execute(
            "SELECT key, query, response, ttl_type, created FROM cache ORDER BY created DESC LIMIT 500"
        ).fetchall()
        best_score, best_response, best_key = 0.0, None, None
        for row_key, row_query, row_response, row_ttl, row_created in rows:
            if now - row_created >= _ttl_for(row_ttl):
                continue
            score = difflib.SequenceMatcher(None, q, row_query.lower()).ratio()
            if score > best_score:
                best_score, best_response, best_key = score, row_response, row_key

        if best_score >= _FUZZY_THRESHOLD and best_response:
            db.execute("UPDATE cache SET hits=hits+1 WHERE key=?", (best_key,))
            db.commit()
            return best_response
    except sqlite3.Error as e:
        logger.error("Cache read error: %s", e)

    return None


def put(query: str, response: str, ttl_type: str = "auto") -> None:
    if not query or not response:
        return
    q = query.lower().strip()
    if ttl_type == "auto":
        ttl_type = _classify_ttl(q)
    key = _make_key(q)
    try:
        db = _conn()
        db.execute(
            """INSERT INTO cache (key, query, response, ttl_type, created, hits)
               VALUES (?, ?, ?, ?, ?, 0)
               ON CONFLICT(key) DO UPDATE SET
                   response=excluded.response,
                   created=excluded.created,
                   ttl_type=excluded.ttl_type""",
            (key, q, response, ttl_type, time.time()),
        )
        db.commit()
    except sqlite3.Error as e:
        logger.error("Cache write error: %s", e)


def stats() -> dict:
    try:
        db = _conn()
        total = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        hits = db.execute("SELECT SUM(hits) FROM cache").fetchone()[0] or 0
        try:
            size_kb = os.path.getsize(_DB_PATH) // 1024
        except OSError:
            size_kb = 0
        return {"total_entries": total, "total_hits": hits, "db_size_kb": size_kb}
    except sqlite3.Error as e:
        logger.error("Cache stats error: %s", e)
        return {}
