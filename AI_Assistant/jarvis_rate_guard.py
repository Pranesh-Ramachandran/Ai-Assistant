"""
JARVIS Rate Guard — Tracks daily & per-minute API usage.
Prevents hitting free-tier limits. Triggers strict mode near limits.
Persists usage in SQLite across sessions.
"""

import os
import sqlite3
import threading
import time
from typing import Tuple

_DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_usage.db")

# ─── Hard limits (free tier) ──────────────────────────────────────────────────
LIMITS = {
    "groq": {
        "rpm": 30,           # requests per minute
        "rpd": 14_400,       # requests per day
        "rph": int(os.getenv("JARVIS_GROQ_HOURLY_LIMIT", "3")),
        "warn_pct": 0.75,    # warn at 75%
        "strict_pct": 0.90,  # strict mode at 90%
    },
    "gemini": {
        "rpm": 15,
        "rpd": 1_500,
        "rph": int(os.getenv("JARVIS_GEMINI_HOURLY_LIMIT", "1")),
        "warn_pct": 0.75,
        "strict_pct": 0.90,
    },
}


def _get_conn() -> sqlite3.Connection:
    def open_and_initialize() -> sqlite3.Connection:
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        integrity = conn.execute("PRAGMA quick_check").fetchone()
        if not integrity or integrity[0] != "ok":
            conn.close()
            raise sqlite3.DatabaseError("quota usage database failed integrity check")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                provider TEXT NOT NULL,
                date     TEXT NOT NULL,
                calls    INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (provider, date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rpm_log (
                provider  TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rpm ON rpm_log(provider, timestamp)")
        conn.commit()
        return conn

    try:
        return open_and_initialize()
    except sqlite3.DatabaseError:
        # This database contains counters only. Preserve the broken copy for
        # diagnosis and rebuild so quota protection cannot crash JARVIS.
        if os.path.exists(_DB_PATH):
            backup = f"{_DB_PATH}.corrupt-{int(time.time())}"
            os.replace(_DB_PATH, backup)
            print(f"[Rate Guard] Archived corrupt usage database: {backup}")
        return open_and_initialize()


_CONN: sqlite3.Connection | None = None
_LOCK = threading.RLock()


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = _get_conn()
    return _CONN


def _today() -> str:
    from datetime import datetime, timezone
    # Groq resets at midnight UTC; Gemini at midnight Pacific — use UTC for safety
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_call(provider: str) -> None:
    """Record one API call for a provider."""
    with _LOCK:
        db  = _conn()
        day = _today()
        now = time.time()
        db.execute(
            """INSERT INTO usage (provider, date, calls) VALUES (?, ?, 1)
               ON CONFLICT(provider, date) DO UPDATE SET calls=calls+1""",
            (provider, day)
        )
        db.execute("INSERT INTO rpm_log (provider, timestamp) VALUES (?, ?)", (provider, now))
        # Keep an hour of attempt history for the conservative hourly budget.
        db.execute("DELETE FROM rpm_log WHERE timestamp < ?", (now - 3600,))
        db.commit()


def get_daily_calls(provider: str) -> int:
    row = _conn().execute(
        "SELECT calls FROM usage WHERE provider=? AND date=?", (provider, _today())
    ).fetchone()
    return row[0] if row else 0


def get_rpm(provider: str) -> int:
    now = time.time()
    row = _conn().execute(
        "SELECT COUNT(*) FROM rpm_log WHERE provider=? AND timestamp > ?",
        (provider, now - 60)
    ).fetchone()
    return row[0] if row else 0


def get_hourly_calls(provider: str) -> int:
    """Return actual network attempts in the rolling last hour."""
    row = _conn().execute(
        "SELECT COUNT(*) FROM rpm_log WHERE provider=? AND timestamp > ?",
        (provider, time.time() - 3600)
    ).fetchone()
    return row[0] if row else 0


def can_call(provider: str) -> Tuple[bool, str]:
    """
    Returns (allowed, reason).
    reason: 'ok' | 'rpm_limit' | 'rpd_limit' | 'strict_mode'
    """
    limits = LIMITS.get(provider, {})
    if not limits:
        return True, "ok"

    rpm_used = get_rpm(provider)
    rph_used = get_hourly_calls(provider)
    rpd_used = get_daily_calls(provider)
    rpm_cap  = limits["rpm"]
    rph_cap  = limits.get("rph", 0)
    rpd_cap  = limits["rpd"]

    if rpm_used >= rpm_cap:
        return False, f"rpm_limit ({rpm_used}/{rpm_cap} this minute)"
    if rph_cap and rph_used >= rph_cap:
        return False, f"hourly_budget ({rph_used}/{rph_cap} this hour)"
    if rpd_used >= rpd_cap:
        return False, f"rpd_limit ({rpd_used}/{rpd_cap} today)"
    return True, "ok"


def acquire_call(provider: str) -> Tuple[bool, str]:
    """Atomically reserve and count one API attempt before network I/O.

    Counting attempts rather than only successful responses prevents retries,
    timeouts, and tool-synthesis requests from silently exhausting quota.
    """
    with _LOCK:
        allowed, reason = can_call(provider)
        if not allowed:
            return False, reason
        record_call(provider)
        return True, "ok"


def get_mode(provider: str) -> str:
    """
    Returns 'normal' | 'strict' | 'blocked'.
    strict  = approaching limit, shorten responses
    blocked = at limit
    """
    limits  = LIMITS.get(provider, {})
    rpd_cap = limits.get("rpd", 9999)
    used    = get_daily_calls(provider)
    ratio   = used / rpd_cap

    if ratio >= 1.0:
        return "blocked"
    if ratio >= limits.get("strict_pct", 0.90):
        return "strict"
    if ratio >= limits.get("warn_pct", 0.75):
        return "warn"
    return "normal"


def status_report() -> dict:
    """Full usage report for both providers."""
    report = {}
    for p in ("groq", "gemini"):
        limits  = LIMITS[p]
        rpd_cap = limits["rpd"]
        rpm_cap = limits["rpm"]
        used    = get_daily_calls(p)
        rpm     = get_rpm(p)
        hourly  = get_hourly_calls(p)
        report[p] = {
            "daily_calls":   used,
            "daily_cap":     rpd_cap,
            "daily_pct":     round(used / rpd_cap * 100, 1),
            "rpm_calls":     rpm,
            "rpm_cap":       rpm_cap,
            "hourly_calls":  hourly,
            "hourly_cap":    limits.get("rph", 0),
            "mode":          get_mode(p),
        }
    return report
