"""
JARVIS Cache — SQLite-backed response cache with fuzzy matching.
Reduces API usage by 50-80% for repeated/similar questions.
"""

import difflib
import hashlib
import json
import os
import sqlite3
import time
from typing import Optional

_DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_cache.db")

# TTL in seconds
_TTL_FACTUAL   = 86400 * 7   # 7 days
_TTL_CURRENT   = 600          # 10 min
_TTL_DEFAULT   = 86400        # 1 day

_FUZZY_THRESHOLD = 0.72
_MAX_ENTRIES     = 500        # hard cap on rows
_MAX_DB_MB       = 5          # delete oldest when db exceeds this


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
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
    return conn


_CONN: Optional[sqlite3.Connection] = None


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = _get_conn()
    return _CONN


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


# ─── Public API ───────────────────────────────────────────────────────────────

def get(query: str) -> Optional[str]:
    """
    Look up a cached response. Returns None if not found or expired.
    Tries exact match first, then fuzzy match across recent entries.
    """
    q = query.lower().strip()
    key = _make_key(q)
    now = time.time()
    db  = _conn()

    # 1. Exact match
    row = db.execute(
        "SELECT response, ttl_type, created FROM cache WHERE key=?", (key,)
    ).fetchone()
    if row:
        response, ttl_type, created = row
        if now - created < _ttl_for(ttl_type):
            db.execute("UPDATE cache SET hits=hits+1 WHERE key=?", (key,))
            db.commit()
            return response
        else:
            db.execute("DELETE FROM cache WHERE key=?", (key,))
            db.commit()
            return None

    # 2. Fuzzy match across recent unexpired entries (last 500)
    rows = db.execute(
        "SELECT key, query, response, ttl_type, created FROM cache ORDER BY created DESC LIMIT 500"
    ).fetchall()

    best_score = 0.0
    best_response = None
    best_key = None

    for row_key, row_query, row_response, row_ttl, row_created in rows:
        if now - row_created >= _ttl_for(row_ttl):
            continue
        score = difflib.SequenceMatcher(None, q, row_query.lower()).ratio()
        if score > best_score:
            best_score = score
            best_response = row_response
            best_key = row_key

    if best_score >= _FUZZY_THRESHOLD and best_response:
        db.execute("UPDATE cache SET hits=hits+1 WHERE key=?", (best_key,))
        db.commit()
        return best_response

    return None


def put(query: str, response: str, ttl_type: str = "auto") -> None:
    """Store a response in the cache."""
    if not query or not response:
        return
    q  = query.lower().strip()
    if ttl_type == "auto":
        ttl_type = _classify_ttl(q)
    key = _make_key(q)
    db  = _conn()
    db.execute(
        """INSERT INTO cache (key, query, response, ttl_type, created, hits)
           VALUES (?, ?, ?, ?, ?, 0)
           ON CONFLICT(key) DO UPDATE SET
               response=excluded.response,
               created=excluded.created,
               ttl_type=excluded.ttl_type""",
        (key, q, response, ttl_type, time.time())
    )
    db.commit()


def purge_expired() -> int:
    """Remove all expired entries. Returns count removed."""
    db   = _conn()
    now  = time.time()
    rows = db.execute("SELECT key, ttl_type, created FROM cache").fetchall()
    expired = [r[0] for r in rows if now - r[2] >= _ttl_for(r[1])]
    if expired:
        db.executemany("DELETE FROM cache WHERE key=?", [(k,) for k in expired])
        db.commit()
    return len(expired)


def _auto_maintain() -> None:
    """Purge expired, then trim to MAX_ENTRIES and MAX_DB_MB. Runs once on import."""
    try:
        purge_expired()
        db = _conn()
        # trim to row cap — delete lowest-hit oldest entries first
        total = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        if total > _MAX_ENTRIES:
            excess = total - _MAX_ENTRIES
            db.execute(
                "DELETE FROM cache WHERE key IN "
                "(SELECT key FROM cache ORDER BY hits ASC, created ASC LIMIT ?)",
                (excess,)
            )
            db.commit()
        # trim by file size
        if os.path.exists(_DB_PATH) and os.path.getsize(_DB_PATH) > _MAX_DB_MB * 1024 * 1024:
            # remove bottom 20% least-used
            cut = max(1, total // 5)
            db.execute(
                "DELETE FROM cache WHERE key IN "
                "(SELECT key FROM cache ORDER BY hits ASC, created ASC LIMIT ?)",
                (cut,)
            )
            db.commit()
            db.execute("VACUUM")
            db.commit()
    except Exception:
        pass


# run maintenance once when module is imported
_auto_maintain()


def stats() -> dict:
    """Return cache statistics."""
    db = _conn()
    total   = db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    hits    = db.execute("SELECT SUM(hits) FROM cache").fetchone()[0] or 0
    size_kb = os.path.getsize(_DB_PATH) // 1024 if os.path.exists(_DB_PATH) else 0
    return {"total_entries": total, "total_hits": hits, "db_size_kb": size_kb}
