"""
JARVIS Rate Guard — Tracks daily & per-minute API usage.
Prevents hitting free-tier limits. Triggers strict mode near limits.
Persists usage in SQLite across sessions.
"""

import os
import sqlite3
import time
from typing import Tuple

_DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_usage.db")

# ─── Hard limits (free tier) ──────────────────────────────────────────────────
LIMITS = {
    "groq": {
        "rpm": 30,           # requests per minute
        "rpd": 14_400,       # requests per day
        "warn_pct": 0.75,    # warn at 75%
        "strict_pct": 0.90,  # strict mode at 90%
    },
    "gemini": {
        "rpm": 15,
        "rpd": 1_500,
        "warn_pct": 0.75,
        "strict_pct": 0.90,
    },
}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
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


_CONN: sqlite3.Connection | None = None


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
    db  = _conn()
    day = _today()
    now = time.time()
    db.execute(
        """INSERT INTO usage (provider, date, calls) VALUES (?, ?, 1)
           ON CONFLICT(provider, date) DO UPDATE SET calls=calls+1""",
        (provider, day)
    )
    db.execute("INSERT INTO rpm_log (provider, timestamp) VALUES (?, ?)", (provider, now))
    # Clean old rpm log entries (keep last 2 minutes)
    db.execute("DELETE FROM rpm_log WHERE provider=? AND timestamp < ?", (provider, now - 120))
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


def can_call(provider: str) -> Tuple[bool, str]:
    """
    Returns (allowed, reason).
    reason: 'ok' | 'rpm_limit' | 'rpd_limit' | 'strict_mode'
    """
    limits = LIMITS.get(provider, {})
    if not limits:
        return True, "ok"

    rpm_used = get_rpm(provider)
    rpd_used = get_daily_calls(provider)
    rpm_cap  = limits["rpm"]
    rpd_cap  = limits["rpd"]

    if rpm_used >= rpm_cap:
        return False, f"rpm_limit ({rpm_used}/{rpm_cap} this minute)"
    if rpd_used >= rpd_cap:
        return False, f"rpd_limit ({rpd_used}/{rpd_cap} today)"
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
        report[p] = {
            "daily_calls":   used,
            "daily_cap":     rpd_cap,
            "daily_pct":     round(used / rpd_cap * 100, 1),
            "rpm_calls":     rpm,
            "rpm_cap":       rpm_cap,
            "mode":          get_mode(p),
        }
    return report
