"""
JARVIS Calendar Integration — Google Calendar via OAuth2.

Setup (one-time):
  1. Go to https://console.cloud.google.com
  2. Create project → Enable Google Calendar API
  3. Create OAuth2 credentials (Desktop app)
  4. Download as calendar_credentials.json → place in d:/ai/AI_Assistant/
  5. First run opens browser for auth → saves calendar_token.json

Public API:
  get_events_today()           → str
  get_events_week()            → str
  get_next_event()             → str
  add_event(summary, when_str, duration_min) → str
  find_free_slots(duration_min)→ str
  process_command(text)        → str
"""

from __future__ import annotations
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

_BASE = os.path.dirname(os.path.abspath(__file__))
_TOKEN_PATH = os.path.join(_BASE, "calendar_token.json")
_CREDS_PATH = os.path.join(_BASE, "calendar_credentials.json")
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]
_TZ = "Asia/Kolkata"

# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_service():
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(_TOKEN_PATH, _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(_CREDS_PATH):
                    return None, "no_credentials"
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(_CREDS_PATH, _SCOPES)
                creds = flow.run_local_server(port=0)

            with open(_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        return build("calendar", "v3", credentials=creds), "ok"
    except ImportError:
        return None, "missing_deps"
    except Exception as e:
        return None, str(e)


_service = None
_service_status = None

def _svc():
    global _service, _service_status
    if _service is None:
        _service, _service_status = _get_service()
    return _service, _service_status


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ist_now() -> datetime:
    try:
        import zoneinfo
        return datetime.now(zoneinfo.ZoneInfo(_TZ))
    except Exception:
        return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def _fmt(dt_str: str) -> str:
    try:
        if "T" in dt_str:
            d = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            ist = d.astimezone(timezone(timedelta(hours=5, minutes=30)))
            return ist.strftime("%b %d at %I:%M %p")
        else:
            d = datetime.fromisoformat(dt_str)
            return d.strftime("%b %d")
    except Exception:
        return dt_str


def _parse_when(when_str: str) -> Optional[datetime]:
    """Parse natural language time like 'tomorrow 3pm', 'Monday 10am', 'in 2 hours'."""
    now = _ist_now()
    s = when_str.lower().strip()

    # "in X hours/minutes"
    m = re.search(r"in (\d+) (hour|minute|min)", s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(hours=n) if "hour" in unit else timedelta(minutes=n)
        return now + delta

    # "tomorrow at HH:MM" or "tomorrow 3pm"
    base = now
    if "tomorrow" in s:
        base = now + timedelta(days=1)
    elif "day after" in s:
        base = now + timedelta(days=2)

    # Extract time
    t = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if t:
        hour = int(t.group(1))
        minute = int(t.group(2)) if t.group(2) else 0
        ampm = t.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Default: 1 hour from now
    return now + timedelta(hours=1)


# ── Public API ────────────────────────────────────────────────────────────────

def get_events_today() -> str:
    svc, status = _svc()
    if not svc:
        return _no_calendar_msg(status)

    now = _ist_now()
    start = now.replace(hour=0, minute=0, second=0).isoformat()
    end   = now.replace(hour=23, minute=59, second=59).isoformat()

    try:
        result = svc.events().list(
            calendarId="primary", timeMin=start, timeMax=end,
            singleEvents=True, orderBy="startTime"
        ).execute()
        events = result.get("items", [])
        if not events:
            return "You have no events today."
        lines = [f"{_fmt(e['start'].get('dateTime', e['start'].get('date')))} — {e.get('summary','(no title)')}"
                 for e in events[:5]]
        return "Today: " + ". ".join(lines) + "."
    except Exception as e:
        return f"Calendar error: {e}"


def get_events_week() -> str:
    svc, status = _svc()
    if not svc:
        return _no_calendar_msg(status)

    now   = _ist_now()
    start = now.isoformat()
    end   = (now + timedelta(days=7)).isoformat()

    try:
        result = svc.events().list(
            calendarId="primary", timeMin=start, timeMax=end,
            singleEvents=True, orderBy="startTime"
        ).execute()
        events = result.get("items", [])
        if not events:
            return "No events this week."
        lines = [f"{_fmt(e['start'].get('dateTime', e['start'].get('date')))} — {e.get('summary','(no title)')}"
                 for e in events[:7]]
        return "This week: " + ". ".join(lines) + "."
    except Exception as e:
        return f"Calendar error: {e}"


def get_next_event() -> str:
    svc, status = _svc()
    if not svc:
        return _no_calendar_msg(status)

    try:
        result = svc.events().list(
            calendarId="primary", timeMin=_ist_now().isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=1
        ).execute()
        events = result.get("items", [])
        if not events:
            return "No upcoming events."
        e = events[0]
        return f"Next: {e.get('summary','(no title)')} at {_fmt(e['start'].get('dateTime', e['start'].get('date')))}."
    except Exception as e:
        return f"Calendar error: {e}"


def add_event(summary: str, when_str: str = "", duration_min: int = 60) -> str:
    svc, status = _svc()
    if not svc:
        return _no_calendar_msg(status)

    start_dt = _parse_when(when_str) if when_str else _ist_now() + timedelta(hours=1)
    end_dt   = start_dt + timedelta(minutes=duration_min)

    event = {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": _TZ},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": _TZ},
    }
    try:
        created = svc.events().insert(calendarId="primary", body=event).execute()
        return f"Added '{summary}' on {_fmt(start_dt.isoformat())}."
    except Exception as e:
        return f"Could not add event: {e}"


def find_free_slots(duration_min: int = 60) -> str:
    svc, status = _svc()
    if not svc:
        return _no_calendar_msg(status)

    now   = _ist_now()
    end   = now + timedelta(days=2)

    try:
        fb = svc.freebusy().query(body={
            "timeMin": now.isoformat(), "timeMax": end.isoformat(),
            "items": [{"id": "primary"}]
        }).execute()
        busy = fb["calendars"]["primary"]["busy"]

        slots, cur = [], now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        while cur < end and len(slots) < 3:
            slot_end = cur + timedelta(minutes=duration_min)
            if 9 <= cur.hour < 20:
                free = all(
                    not (cur < datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
                         and slot_end > datetime.fromisoformat(b["start"].replace("Z", "+00:00")))
                    for b in busy
                )
                if free:
                    slots.append(_fmt(cur.isoformat()))
            cur += timedelta(minutes=30)

        if not slots:
            return "No free slots found in the next 48 hours."
        return "Free slots: " + ", ".join(slots) + "."
    except Exception as e:
        return f"Calendar error: {e}"


def process_command(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("today", "what's on", "schedule today")):
        return get_events_today()
    if any(w in t for w in ("week", "this week", "upcoming")):
        return get_events_week()
    if any(w in t for w in ("next event", "what's next", "coming up")):
        return get_next_event()
    if any(w in t for w in ("free", "available", "when am i free")):
        return find_free_slots()
    if any(w in t for w in ("add", "create", "schedule", "set meeting", "book meeting")):
        # extract summary and time
        m = re.search(r"(?:add|create|schedule|set|book)\s+(?:a\s+)?(.+?)(?:\s+(?:at|on|for|tomorrow|today)\s+(.+))?$", t)
        if m:
            summary = m.group(1).strip().title()
            when    = m.group(2) or ""
            return add_event(summary, when)
        return add_event("Meeting", "tomorrow 10am")
    return get_events_today()


def is_connected() -> bool:
    svc, status = _svc()
    return svc is not None


def _no_calendar_msg(status: str) -> str:
    if status == "no_credentials":
        return ("Calendar not set up. Download credentials.json from Google Cloud Console "
                "and save it as calendar_credentials.json in the AI_Assistant folder.")
    if status == "missing_deps":
        return "Calendar requires: pip install google-api-python-client google-auth-oauthlib"
    return f"Calendar unavailable: {status}"


# Global instance shim for backward compat
class _CalendarShim:
    def process_command(self, cmd): return process_command(cmd)
    def get_events_today(self): return get_events_today()
    def get_events_week(self): return get_events_week()
    def add_event(self, s, t=None, d=60): return add_event(s, str(t) if t else "", d)

calendar_module = _CalendarShim()
