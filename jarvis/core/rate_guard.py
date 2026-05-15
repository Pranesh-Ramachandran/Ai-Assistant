"""
JARVIS Rate Guard — Tracks daily & per-minute API usage.
Prevents hitting free-tier limits.
"""

import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "data" / "jarvis_usage.db")

LIMITS = {
    "groq":   {"rpm": 30,  "rpd": 14_400, "warn_pct": 0.75, "strict_pct": 0.90},
    "gemini": {"rpm": 15,  "rpd": 1_500,  "warn_pct": 0.75, "strict_pct": 0.90},
}

_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(_DB_PATH)
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
        _local.conn = conn
    return _local.conn


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_call(provider: str) -> None:
    try:
        db = _conn()
        now = time.time()
        db.execute(
            "INSERT INTO usage (provider, date, calls) VALUES (?, ?, 1) "
            "ON CONFLICT(provider, date) DO UPDATE SET calls=calls+1",
            (provider, _today()),
        )
        db.execute("INSERT INTO rpm_log (provider, timestamp) VALUES (?, ?)", (provider, now))
        db.execute("DELETE FROM rpm_log WHERE provider=? AND timestamp < ?", (provider, now - 120))
        db.commit()
    except sqlite3.Error as e:
        logger.error("Rate guard record error: %s", e)


def get_daily_calls(provider: str) -> int:
    try:
        row = _conn().execute(
            "SELECT calls FROM usage WHERE provider=? AND date=?", (provider, _today())
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.Error:
        return 0


def get_rpm(provider: str) -> int:
    try:
        now = time.time()
        row = _conn().execute(
            "SELECT COUNT(*) FROM rpm_log WHERE provider=? AND timestamp > ?",
            (provider, now - 60),
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.Error:
        return 0


def can_call(provider: str) -> Tuple[bool, str]:
    limits = LIMITS.get(provider, {})
    if not limits:
        return True, "ok"
    rpm_used, rpd_used = get_rpm(provider), get_daily_calls(provider)
    rpm_cap, rpd_cap = limits["rpm"], limits["rpd"]
    if rpm_used >= rpm_cap:
        return False, f"rpm_limit ({rpm_used}/{rpm_cap} this minute)"
    if rpd_used >= rpd_cap:
        return False, f"rpd_limit ({rpd_used}/{rpd_cap} today)"
    return True, "ok"


def get_mode(provider: str) -> str:
    limits = LIMITS.get(provider, {})
    rpd_cap = limits.get("rpd", 9999)
    ratio = get_daily_calls(provider) / rpd_cap
    if ratio >= 1.0:
        return "blocked"
    if ratio >= limits.get("strict_pct", 0.90):
        return "strict"
    if ratio >= limits.get("warn_pct", 0.75):
        return "warn"
    return "normal"


def status_report() -> dict:
    report = {}
    for p in ("groq", "gemini"):
        limits = LIMITS[p]
        used, rpm = get_daily_calls(p), get_rpm(p)
        report[p] = {
            "daily_calls": used,
            "daily_cap": limits["rpd"],
            "daily_pct": round(used / limits["rpd"] * 100, 1),
            "rpm_calls": rpm,
            "rpm_cap": limits["rpm"],
            "mode": get_mode(p),
        }
    return report
