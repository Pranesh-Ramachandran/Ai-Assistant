"""
JARVIS User Memory — persistent user profile + preferences + saved places.

Stores in .jarvis_memory.json alongside conversation history.
Public API:
  get_profile()                    → dict
  set_preference(key, value)       → None
  get_preference(key, default)     → value
  save_place(label, name, lat, lon)→ None
  get_place(label)                 → dict | None
  get_all_places()                 → dict
  remember_contact(name, detail)   → None
  get_contact(name)                → str | None
  add_alarm(time_str, message)     → None
  get_active_alarms()              → list
  clear_alarms()                   → None
  get_summary()                    → str  (for morning briefing)
"""

from __future__ import annotations
import json
import os
import time
from datetime import datetime
from typing import Any, Optional

_FILE = os.path.join(os.path.dirname(__file__), ".jarvis_memory.json")


def _load() -> dict:
    try:
        if os.path.exists(_FILE):
            with open(_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save(data: dict) -> None:
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ── Profile ───────────────────────────────────────────────────────────────────

def get_profile() -> dict:
    return _load().get("profile", {})


def set_profile(name: str = "", city: str = "", language: str = "en") -> None:
    data = _load()
    data.setdefault("profile", {})
    if name:     data["profile"]["name"]     = name
    if city:     data["profile"]["city"]     = city
    if language: data["profile"]["language"] = language
    _save(data)


# ── Preferences ───────────────────────────────────────────────────────────────

def set_preference(key: str, value: Any) -> None:
    data = _load()
    data.setdefault("preferences", {})[key] = value
    _save(data)


def get_preference(key: str, default: Any = None) -> Any:
    return _load().get("preferences", {}).get(key, default)


# ── Saved places ──────────────────────────────────────────────────────────────

def save_place(label: str, name: str, lat: float = 0.0, lon: float = 0.0) -> None:
    """Save a named place. label = 'home', 'office', 'gym' etc."""
    data = _load()
    data.setdefault("places", {})[label.lower()] = {
        "name": name, "lat": lat, "lon": lon,
        "saved_at": datetime.now().isoformat()
    }
    _save(data)


def get_place(label: str) -> Optional[dict]:
    return _load().get("places", {}).get(label.lower())


def get_all_places() -> dict:
    return _load().get("places", {})


# ── Contacts ──────────────────────────────────────────────────────────────────

def remember_contact(name: str, detail: str) -> None:
    """Remember a contact detail. e.g. remember_contact('Rahul', 'brother, +91-9876543210')"""
    data = _load()
    data.setdefault("contacts", {})[name.lower()] = {
        "detail": detail, "saved_at": datetime.now().isoformat()
    }
    _save(data)


def get_contact(name: str) -> Optional[str]:
    c = _load().get("contacts", {}).get(name.lower())
    return c["detail"] if c else None


# ── Alarms ────────────────────────────────────────────────────────────────────

def add_alarm(time_str: str, message: str = "Reminder") -> None:
    data = _load()
    data.setdefault("alarms", []).append({
        "time": time_str, "message": message,
        "active": True, "created": datetime.now().isoformat()
    })
    _save(data)


def get_active_alarms() -> list:
    return [a for a in _load().get("alarms", []) if a.get("active")]


def clear_alarms() -> None:
    data = _load()
    data["alarms"] = []
    _save(data)


def dismiss_alarm(index: int) -> None:
    data = _load()
    alarms = data.get("alarms", [])
    active = [a for a in alarms if a.get("active")]
    if 0 <= index < len(active):
        active[index]["active"] = False
    data["alarms"] = alarms
    _save(data)


# ── Conversation history ──────────────────────────────────────────────────────

def get_history() -> list:
    return _load().get("history", [])


# ── Morning briefing summary ──────────────────────────────────────────────────

def get_summary() -> str:
    data   = _load()
    now    = datetime.now()
    name   = data.get("profile", {}).get("name", "")
    alarms = [a for a in data.get("alarms", []) if a.get("active")]
    places = data.get("places", {})

    parts = []
    greeting = f"Good {'morning' if now.hour < 12 else 'afternoon' if now.hour < 17 else 'evening'}"
    parts.append(f"{greeting}{', ' + name if name else ''}.")
    parts.append(f"It's {now.strftime('%A, %B %d')}.")

    if alarms:
        parts.append(f"You have {len(alarms)} active reminder{'s' if len(alarms) > 1 else ''}.")

    if places:
        labels = list(places.keys())[:3]
        parts.append(f"Saved places: {', '.join(labels)}.")

    return " ".join(parts)


# ── Shortcut resolver ─────────────────────────────────────────────────────────

def resolve_shortcut(text: str) -> Optional[str]:
    """
    Resolve shortcut phrases to real values.
    'the usual seats' → preference 'usual_seats'
    'my home' → saved place 'home'
    'my office' → saved place 'office'
    """
    t = text.lower().strip()
    prefs = _load().get("preferences", {})
    places = _load().get("places", {})

    # Check saved places
    for label, place in places.items():
        if f"my {label}" in t or f"the {label}" in t:
            return place["name"]

    # Check preferences
    for key, val in prefs.items():
        if key.replace("_", " ") in t:
            return str(val)

    return None
