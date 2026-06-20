"""
Time-aware Execution - Tier 2 Feature
Extracts time expressions and schedules actions accordingly.

Examples:
  "Set a reminder to call mom tomorrow at 3 PM"
  -> Intent: REMINDER, time: tomorrow, action_time: 3 PM
  
  "Meet me in 5 minutes"
  -> Intent: REQUEST, time_delta: 5 minutes, timezone-aware
  
  "Book a slot for next Monday"
  -> Intent: BOOKING, scheduled_date: 2026-04-20
"""

import re
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Dict, Any, Tuple

try:
    import pytz
except ImportError:
    pytz = None
    from zoneinfo import ZoneInfo


def _build_timezone(timezone_name: str):
    """Return a usable timezone object without requiring tzdata."""
    if pytz is not None:
        return pytz.timezone(timezone_name)
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        if timezone_name in ("Asia/Kolkata", "Asia/Calcutta"):
            return dt_timezone(timedelta(hours=5, minutes=30), name=timezone_name)
        return dt_timezone.utc


class TimeAwareExecution:
    """
    Extracts temporal expressions from text and creates executable time-based actions.
    """
    
    # Relative time deltas
    RELATIVE_TIME = {
        "now": 0,
        "immediately": 0,
        "asap": 0,
        "soon": 300,  # 5 minutes
        "in a bit": 600,  # 10 minutes
        "shortly": 900,  # 15 minutes
    }
    
    # Absolute day references
    DAY_REFERENCES = {
        "today": 0,
        "tomorrow": 1,
        "day after tomorrow": 2,
        "next day": 1,
        "yesterday": -1,
        "day before yesterday": -2,
        "last day": -1,
    }
    
    # Weekday references
    WEEKDAYS = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1, "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "thurs": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }
    
    # Month references
    MONTHS = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    
    def __init__(self, timezone: str = "Asia/Kolkata"):
        """
        Initialize time-aware handler.
        
        Args:
            timezone: Default timezone (default: Asia/Kolkata)
        """
        self.timezone = _build_timezone(timezone)
        self.current_time = self._now()
    
    def _now(self) -> datetime:
        """Get current time in the configured timezone."""
        return datetime.now(self.timezone)
    
    def extract_time_expression(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract time expressions from text.
        
        Returns:
            {
                "has_time": bool,
                "time_type": str (relative/absolute/weekday/occurrence),
                "target_time": datetime,
                "time_delta": int (seconds),
                "time_string": str (human readable),
                "confidence": float,
                "recurring": bool (if repeating)
            }
        """
        text_lower = text.lower()
        
        # Try relative time (in X minutes/hours/days)
        result = self._extract_relative_time(text_lower)
        if result:
            return result
        
        # Try absolute day references (tomorrow, today, etc.)
        result = self._extract_day_reference(text_lower)
        if result:
            return result
        
        # Try weekday references (next Monday, last Friday)
        result = self._extract_weekday_reference(text_lower)
        if result:
            return result
        
        # Try clock time (3 PM, 15:30, etc.)
        result = self._extract_clock_time(text_lower)
        if result:
            return result
        
        # Try date patterns (April 15, 4/15/2026)
        result = self._extract_date_pattern(text_lower)
        if result:
            return result
        
        # No time expression found
        return None
    
    def _extract_relative_time(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract relative time expressions like 'in 5 minutes'."""
        # Pattern: "in X minutes/hours/days"
        match = re.search(
            r"in\s+(\d+)\s+(second|minute|hour|day|week|month)s?(?:\s|$)",
            text, re.IGNORECASE
        )
        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            multipliers = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400,
                "week": 604800,
                "month": 2592000,
            }
            
            time_delta = amount * multipliers.get(unit, 60)
            target_time = self._now() + timedelta(seconds=time_delta)
            
            return {
                "has_time": True,
                "time_type": "relative",
                "target_time": target_time,
                "time_delta": time_delta,
                "time_string": f"in {amount} {unit}{'s' if amount != 1 else ''}",
                "confidence": 0.95,
                "recurring": False
            }
        
        # Check for simple relative references (soon, asap, etc.)
        for ref, delta in self.RELATIVE_TIME.items():
            if ref in text:
                target_time = self._now() + timedelta(seconds=delta)
                return {
                    "has_time": True,
                    "time_type": "relative",
                    "target_time": target_time,
                    "time_delta": delta,
                    "time_string": ref,
                    "confidence": 0.85,
                    "recurring": False
                }
        
        return None
    
    def _extract_day_reference(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract day references like 'tomorrow', 'today', 'day after tomorrow'."""
        # Order matters - check longer phrases first
        for day_ref in sorted(self.DAY_REFERENCES.keys(), key=len, reverse=True):
            if day_ref in text:
                days_delta = self.DAY_REFERENCES[day_ref]
                target_date = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
                target_date += timedelta(days=days_delta)
                
                return {
                    "has_time": True,
                    "time_type": "absolute",
                    "target_time": target_date,
                    "time_delta": days_delta * 86400,
                    "time_string": day_ref,
                    "confidence": 0.9,
                    "recurring": False
                }
        
        return None
    
    def _extract_weekday_reference(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract weekday references like 'next Monday', 'last Friday'."""
        # Pattern: "next/last WEEKDAY"
        match = re.search(
            r"(next|last|this)\s+(" + "|".join(self.WEEKDAYS.keys()) + r")(?:\s|$)",
            text, re.IGNORECASE
        )
        if match:
            direction = match.group(1).lower()
            weekday_name = match.group(2).lower()
            target_weekday = self.WEEKDAYS[weekday_name]
            
            current = self._now()
            current_weekday = current.weekday()
            
            # Calculate days until target weekday
            if direction == "next":
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # If today is the same weekday, go to next week
            elif direction == "last":
                days_ahead = -((current_weekday - target_weekday) % 7)
                if days_ahead == 0:
                    days_ahead = -7
            else:  # "this"
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead < 0:
                    days_ahead += 7
            
            target_time = current + timedelta(days=days_ahead)
            target_time = target_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            return {
                "has_time": True,
                "time_type": "weekday",
                "target_time": target_time,
                "time_delta": abs(days_ahead) * 86400,
                "time_string": f"{direction} {weekday_name}",
                "confidence": 0.9,
                "recurring": "weekly"
            }
        
        return None
    
    def _extract_clock_time(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract clock times like '3 PM', '15:30', '3:45 in the afternoon'."""
        # Pattern: "HH:MM AM/PM" or "H AM/PM"
        match = re.search(
            r"(\d{1,2}):?(\d{0,2})\s*(am|pm|AM|PM|a\.m\.|p\.m\.)?(?:\s|$)",
            text
        )
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            period = match.group(3)
            
            # Convert to 24-hour format
            if period and period.lower().startswith("p"):
                if hour != 12:
                    hour += 12
            elif period and period.lower().startswith("a"):
                if hour == 12:
                    hour = 0
            
            if hour > 23 or minute > 59:
                return None  # Invalid time
            
            target_time = self._now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time is in the past, assume next day
            if target_time < self._now():
                target_time += timedelta(days=1)
            
            return {
                "has_time": True,
                "time_type": "clock",
                "target_time": target_time,
                "time_delta": (target_time - self._now()).total_seconds(),
                "time_string": f"{hour:02d}:{minute:02d}",
                "confidence": 0.85,
                "recurring": False
            }
        
        return None
    
    def _extract_date_pattern(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract date patterns like 'April 15', '4/15/2026'."""
        # Pattern: "Month DD" or "MM/DD" or "MM/DD/YYYY"
        match = re.search(
            r"(" + "|".join(self.MONTHS.keys()) + r")\s+(\d{1,2})",
            text, re.IGNORECASE
        )
        if match:
            month = self.MONTHS[match.group(1).lower()]
            day = int(match.group(2))
            year = self._now().year
            
            try:
                target_time = datetime(year, month, day, tzinfo=self.timezone)
                if target_time < self._now():
                    target_time = datetime(year + 1, month, day, tzinfo=self.timezone)
                
                return {
                    "has_time": True,
                    "time_type": "date",
                    "target_time": target_time,
                    "time_delta": (target_time - self._now()).total_seconds(),
                    "time_string": f"{match.group(1)} {day}",
                    "confidence": 0.9,
                    "recurring": False
                }
            except ValueError:
                return None
        
        # Pattern: MM/DD or MM/DD/YYYY
        match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", text)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else self._now().year
            
            try:
                target_time = datetime(year, month, day, tzinfo=self.timezone)
                if target_time < self._now():
                    target_time = datetime(year + 1, month, day, tzinfo=self.timezone)
                
                return {
                    "has_time": True,
                    "time_type": "date",
                    "target_time": target_time,
                    "time_delta": (target_time - self._now()).total_seconds(),
                    "time_string": f"{month:02d}/{day:02d}/{year}",
                    "confidence": 0.85,
                    "recurring": False
                }
            except ValueError:
                return None
        
        return None
    
    def extract_action_and_time(self, text: str) -> Dict[str, Any]:
        """
        Extract both the action and time from a command.
        
        Returns: {
            "action": str (what to do),
            "time_info": Dict or None (when to do it),
            "confidence": float,
            "is_scheduled": bool
        }
        """
        time_info = self.extract_time_expression(text)
        
        # Remove time expressions to get cleaner action
        action_text = text
        if time_info:
            # Remove common time patterns
            action_text = re.sub(r"in\s+\d+\s+\w+", "", action_text, flags=re.IGNORECASE)
            action_text = re.sub(r"\b(tomorrow|today|next|last|this)\s+\w+", "", action_text, flags=re.IGNORECASE)
            action_text = re.sub(r"\d{1,2}:?\d{0,2}\s*(am|pm)?", "", action_text, flags=re.IGNORECASE)
            action_text = action_text.strip()
        
        return {
            "action": action_text or text,
            "time_info": time_info,
            "confidence": (time_info["confidence"] if time_info else 0.7),
            "is_scheduled": time_info is not None
        }


# Singleton
TIME_HANDLER = TimeAwareExecution()


def extract_scheduled_action(text: str) -> Dict[str, Any]:
    """
    Public function to extract scheduled actions.
    
    Returns:
        {
            "is_timed": bool,
            "action": str,
            "target_time": datetime (if timed),
            "time_string": str,
            "timezone": str
        }
    """
    result = TIME_HANDLER.extract_action_and_time(text)
    
    if result["is_scheduled"]:
        return {
            "is_timed": True,
            "action": result["action"],
            "target_time": result["time_info"]["target_time"],
            "time_string": result["time_info"]["time_string"],
            "timezone": "Asia/Kolkata"
        }
    else:
        return {
            "is_timed": False,
            "action": text,
            "target_time": None,
            "time_string": None,
            "timezone": "Asia/Kolkata"
        }
