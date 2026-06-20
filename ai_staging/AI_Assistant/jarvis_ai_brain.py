"""
JARVIS AI Brain — Hybrid Groq + Gemini with tool calling.
Architecture:
  1. Rule-based fast path  (free, instant)
  2. Fuzzy cache           (free, instant)
  3. Groq LLM + tools      (primary,  ~500ms)
  4. Gemini LLM + tools    (fallback, ~800ms)
  5. Offline reply         (always works)

Tools exposed to LLM:
  get_weather, get_information, get_time, set_alarm, control_light
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from typing import Any, Optional

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

# ─── Load env ─────────────────────────────────────────────────────────────────
_ENV_FILE = os.path.join(os.path.dirname(__file__), "jarvis.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODE    = os.getenv("JARVIS_AI_MODE", "hybrid")

# ─── Optional imports ─────────────────────────────────────────────────────────
try:
    from groq import Groq as _Groq
    _GROQ_LIB = True
except ImportError:
    _Groq = None
    _GROQ_LIB = False

try:
    import google.genai as _genai
    _GEMINI_LIB = True
except ImportError:
    _genai = None
    _GEMINI_LIB = False

# ── NLP for offline intent handling ─────────────────────────────────────────
try:
    from jarvis_nlp import jarvis_nlp as _nlp
    _NLP_AVAILABLE = True
except Exception:
    _NLP_AVAILABLE = False


# ── Extended modules ──────────────────────────────────────────────────────────
try:
    from game_module import GameModule as _GameModule
    _game = _GameModule(tts=None, stt=None)
    _GAME_OK = True
except Exception:
    _GAME_OK = False

try:
    from ticket_booking_hybrid import ticket_booking as _ticket_booking
    _BOOKING_OK = True
except Exception:
    _BOOKING_OK = False

try:
    from offline_entertainment import offline_entertainment as _entertainment
    _ENTERTAIN_OK = True
except Exception:
    _ENTERTAIN_OK = False

try:
    from music_controller import JarvisMusicController as _MusicCtrl
    _music_ctrl = _MusicCtrl()
    _MUSIC_OK = True
except Exception:
    _MUSIC_OK = False

try:
    from data_collector import get_weather, get_information
    _DATA_OK = True
except Exception:
    _DATA_OK = False

try:
    from user_memory import (get_profile, set_preference, get_preference,
                              save_place, get_place, get_all_places,
                              remember_contact, get_contact, add_alarm,
                              get_active_alarms, get_summary, resolve_shortcut)
    _MEMORY_OK = True
except Exception as e:
    _MEMORY_OK = False
    print(f"[JARVIS] user_memory unavailable: {e}")

try:
    from calendar_integration import (get_events_today, get_events_week,
                                       get_next_event, add_event,
                                       find_free_slots, is_connected as cal_connected)
    _CALENDAR_OK = True
except Exception as e:
    _CALENDAR_OK = False
    print(f"[JARVIS] Calendar unavailable: {e}")

try:
    from maps_assistant import maps_assistant as _maps
    _MAPS_OK = True
except Exception as e:
    _MAPS_OK = False
    print(f"[JARVIS] Maps unavailable: {e}")

try:
    from smart_home import control as _smarthome_control, set_scene as _set_scene, get_status as _smarthome_status
    _SMARTHOME_OK = True
except Exception as e:
    _SMARTHOME_OK = False
    print(f"[JARVIS] Smart home unavailable: {e}")

try:
    from desktop_control import handle as _desktop_handle, open_app as _open_app, find_files as _find_files, clipboard_read, clipboard_write
    _DESKTOP_OK = True
except Exception as e:
    _DESKTOP_OK = False
    print(f"[JARVIS] Desktop control unavailable: {e}")

try:
    from web_automation import handle as _web_handle, search_product as _search_product, google_search as _google_search, fill_form_with_profile, get_pending as _get_web_pending, resolve as _web_resolve
    _WEB_OK = True
except Exception as e:
    _WEB_OK = False
    print(f"[JARVIS] Web automation unavailable: {e}")

try:
    from vision_module import handle as _vision_handle, capture_and_describe, read_screen_and_describe
    _VISION_OK = True
except Exception as e:
    _VISION_OK = False
    print(f"[JARVIS] Vision unavailable: {e}")

try:
    from call_sms import handle as _callsms_handle, announce_call, draft_reply
    _CALLSMS_OK = True
except Exception as e:
    _CALLSMS_OK = False
    print(f"[JARVIS] Call/SMS unavailable: {e}")

try:
    from emotion_adapter import adapt_jarvis_response as _adapt_response
    _EMOTION_OK = True
except Exception as e:
    _EMOTION_OK = False
    def _adapt_response(r, context="", command=""): return r

try:
    from tamil_ai import detect_language as _detect_lang, inject_tamil_context as _inject_tamil
    _TAMIL_OK = True
except Exception as e:
    _TAMIL_OK = False
    def _detect_lang(t): return 'en'
    def _inject_tamil(t): return t

from jarvis_cache      import get as cache_get, put as cache_put
from jarvis_rate_guard import can_call, record_call, get_mode, status_report
from data_collector    import get_weather, get_information, get_news

# ─── Tier 1: Extended Memory & Intent Classification ──────────────────────────
try:
    from extended_memory import EXTENDED_MEMORY
    _EXTENDED_MEMORY_OK = True
except Exception as e:
    _EXTENDED_MEMORY_OK = False
    print(f"[JARVIS] Extended memory unavailable: {e}")

try:
    from intent_classifier import classify_query
    _INTENT_CLASSIFIER_OK = True
except Exception as e:
    _INTENT_CLASSIFIER_OK = False
    print(f"[JARVIS] Intent classifier unavailable: {e}")
    def classify_query(text): return {"intent": "REQUEST", "confidence": 0.5, "entities": {}, "requires_clarification": False, "clarification_questions": []}

try:
    from error_recovery import ERROR_RECOVERY
    _ERROR_RECOVERY_OK = True
except Exception as e:
    _ERROR_RECOVERY_OK = False
    print(f"[JARVIS] Error recovery unavailable: {e}")

# ── Tier 2: Advanced conversational features ─────────────────────────────────
try:
    from natural_followup import handle_followup
    _FOLLOWUP_OK = True
except Exception as e:
    _FOLLOWUP_OK = False
    print(f"[JARVIS] Natural followup unavailable: {e}")
    def handle_followup(text, **kwargs): return {"is_followup": False, "rewritten_query": text}

try:
    from query_rephrasing import rephrase_query
    _REPHRASING_OK = True
except Exception as e:
    _REPHRASING_OK = False
    print(f"[JARVIS] Query rephrasing unavailable: {e}")
    def rephrase_query(text, **kwargs): return {"original": text, "rephrased": text, "needs_clarification": False}

try:
    from time_aware_execution import extract_scheduled_action
    _TIME_AWARE_OK = True
except Exception as e:
    _TIME_AWARE_OK = False
    print(f"[JARVIS] Time-aware execution unavailable: {e}")
    def extract_scheduled_action(text): return {"is_timed": False, "action": text, "target_time": None}

try:
    from personalization_engine import personalize, PERSONALIZATION_ENGINE
    _PERSONALIZATION_OK = True
except Exception as e:
    _PERSONALIZATION_OK = False
    print(f"[JARVIS] Personalization engine unavailable: {e}")
    def personalize(text, **kwargs): return {"extracted_preferences": {}, "should_adapt_response": False}

try:
    from confidence_scoring import score_response as score_ai_confidence
    _CONFIDENCE_SCORING_OK = True
except Exception as e:
    _CONFIDENCE_SCORING_OK = False
    print(f"[JARVIS] Confidence scoring unavailable: {e}")
    def score_ai_confidence(text, **kwargs): return {"confidence": 0.7, "should_clarify": False}

# Tier 3 Modules (Calendar Integration, Email, Web Search, Proactive, Notifications)
try:
    from calendar_integration import add_event as calendar_add_event
    _CALENDAR_OK = True
except Exception as e:
    _CALENDAR_OK = False
    print(f"[JARVIS] Calendar integration unavailable: {e}")
    def calendar_add_event(text, **kwargs): return {"success": False}

try:
    from email_manager import handle_email
    _EMAIL_OK = True
except Exception as e:
    _EMAIL_OK = False
    print(f"[JARVIS] Email manager unavailable: {e}")
    def handle_email(text): return {"success": False}

try:
    from web_search import handle_web_search
    _WEB_SEARCH_OK = True
except Exception as e:
    _WEB_SEARCH_OK = False
    print(f"[JARVIS] Web search unavailable: {e}")
    def handle_web_search(text, **kwargs): return {"success": False}

try:
    from proactive_assistance import detect_proactive_needs
    _PROACTIVE_OK = True
except Exception as e:
    _PROACTIVE_OK = False
    print(f"[JARVIS] Proactive assistance unavailable: {e}")
    def detect_proactive_needs(text, **kwargs): return {"has_suggestions": False}

try:
    from smart_notifications import create_and_send_notification, get_next_notification
    _NOTIFICATIONS_OK = True
except Exception as e:
    _NOTIFICATIONS_OK = False
    print(f"[JARVIS] Smart notifications unavailable: {e}")
    def create_and_send_notification(t, m, **kwargs): return {"success": False}
    def get_next_notification(): return None

try:
    from system_access import execute_tool as _sys_exec, TOOL_DEFINITIONS as _SYS_TOOLS
    _SYS_ACCESS = True
except Exception:
    _SYS_ACCESS = False
    _sys_exec = lambda n, a: "System access unavailable."
    _SYS_TOOLS = []


# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS system prompt
# ═══════════════════════════════════════════════════════════════════════════════


def _clean_response(text: str) -> str:
    """Strip leaked function call tags from LLM response."""
    if not text:
        return text
    text = str(text)
    
    # Remove <function=...></function> or <function=.../>
    text = re.sub(r'<function[^>]*>.*?</function>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<function=[^>]*/?>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</function>', '', text, flags=re.IGNORECASE)
    
    # Remove <function...> standalone tags
    text = re.sub(r'<function[^>]*>', '', text, flags=re.IGNORECASE)
    if '<function' in text.lower():
        match = re.search(r'<function', text, flags=re.IGNORECASE)
        if match:
            text = text[:match.start()]
    
    # Remove function_name>{"key":"value"} patterns (e.g., get_news>{"category":"world"})
    text = re.sub(r'(?:get_weather|get_information|get_news|get_time|set_alarm|control_light|call_sms|play_game)\s*>\s*\{[^}]*\}', '', 
                  text, flags=re.IGNORECASE)
    
    # Remove raw JSON tool calls with "parameters" or "arguments" wrappers
    text = re.sub(r'\{[\s\n]*"name"[\s\n]*:[\s\n]*"([^"]+)"[\s\n]*,[\s\n]*"(?:arguments?|parameters)"[\s\n]*:[\s\n]*\{[^}]*\}[\s\n]*\}', '', 
                  text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove shorthand JSON without wrapper: {"name":"get_news","category":"india"}
    text = re.sub(r'\{\s*"name"\s*:\s*"[^"]*"\s*,\s*"(?:category|query|location|room|action|type|time_str|message|command)"[^}]*\}', '', 
                  text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining orphaned tool call starts
    text = re.sub(r'\{\s*"name"\s*:', '', text, flags=re.IGNORECASE)
    
    # Remove any function_name> prefix when followed by space or nothing
    text = re.sub(r'(?:get_weather|get_information|get_news|get_time|set_alarm|control_light|call_sms|play_game)\s*>\s*', '', 
                  text, flags=re.IGNORECASE)
    
    # Remove bare `function=identifier` patterns (without angle brackets)
    text = re.sub(r'\bfunction\s*=\s*[a-zA-Z_][\w.]*', '', text, flags=re.IGNORECASE)

    # Remove orphaned JSON arg fragments like >{"query":"Taylor Swift"} or >{"location":"..."}
    text = re.sub(r'>\s*\{[^}]{0,200}\}', '', text)

    # Remove any remaining bare JSON objects at start of text (tool call leak)
    text = re.sub(r'^\s*\{[^}]{0,200}\}\s*', '', text)

    # Remove tool-result label prefixes that sometimes leak into synthesized response
    # e.g. "get_weather: Chennai: ..." or "get_news: Top world news:"
    text = re.sub(r'^\s*(?:get_weather|get_news|get_information|get_time|set_alarm|control_light|play_game|book_ticket|play_music)\s*:\s*', '', text, flags=re.IGNORECASE)

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

_SYSTEM_PROMPT_BASE = """You are JARVIS, a smart, concise AI assistant. You speak like a confident, helpful assistant — not like a customer service bot.

Rules:
- Respond in ENGLISH by default unless the user asks in Tamil.
- Be direct. No filler like "Certainly!" or "Of course!" or "Great question!"
- Keep answers SHORT unless asked to elaborate. 1-3 sentences is ideal.
- Use tools when relevant: Always call weather tool for weather queries — MUST use get_weather for ANY question about weather, temperature, rain, forecast, conditions. Same for news, info, time.
- Only call ONE tool per response. Never call multiple tools at once.
- For any question NOT covered by tools (general knowledge, advice, explanations, opinions, creative questions): Answer directly and confidently. You are knowledgeable and helpful on ANY topic.
- Remember the conversation context.
- If user asks in Tamil script or Tanglish, respond in Tamil.
- You have a personality: calm, slightly witty, always helpful, confident.
- Never say you're an AI model or mention Groq/Gemini. You are JARVIS.
- NEVER output raw function call syntax like <function=...> in your replies. Use tools silently.
- Default location is Tamil Nadu, India unless the user specifies otherwise.
"""


def _build_system_prompt() -> str:
    """Inject dynamic context: user name, time, day."""
    now  = datetime.now()
    time_str = now.strftime("%I:%M %p").lstrip("0")
    day_str  = now.strftime("%A, %B %d")
    # Pull user name from voice ID profiles if available
    user_name = "User"
    try:
        from voice_id import get_profiles
        profiles = get_profiles()
        if profiles:
            user_name = profiles[0]  # primary enrolled user
    except Exception:
        pass
    # Pull saved preferences
    city = "Tamil Nadu"
    try:
        from user_memory import get_profile, get_active_alarms
        profile = get_profile()
        if profile.get("name"):     user_name = profile["name"]
        if profile.get("city"):     city      = profile["city"]
    except Exception:
        pass
    alarms = []
    try:
        alarms = get_active_alarms()
    except Exception:
        pass
    alarm_note = f" You have {len(alarms)} active reminder(s)." if alarms else ""
    context = f"\nCurrent context: It is {time_str} on {day_str}. You are speaking with {user_name}. Default city: {city}.{alarm_note}"
    return _SYSTEM_PROMPT_BASE + context

_STRICT_ADDENDUM = " Answer in 1-2 sentences maximum. Be extremely concise."


# ═══════════════════════════════════════════════════════════════════════════════
# Tool definitions
# ═══════════════════════════════════════════════════════════════════════════════

_TOOLS_GROQ = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city or location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location"}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_information",
            "description": "Get factual information, definitions, or Wikipedia summaries",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look up"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get latest news headlines. Categories: world, india, technology, business, science",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "News category: world, india, technology, business, science"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current date and time",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": "Set an alarm or reminder",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_str": {"type": "string", "description": "Time like '7:30 AM' or '30 minutes'"},
                    "message":  {"type": "string", "description": "What to remind about"}
                },
                "required": ["time_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_light",
            "description": "Turn lights on or off, or change color/brightness",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["on", "off", "dim", "bright"]},
                    "room":   {"type": "string", "description": "Room name (optional)"}
                },
                "required": ["action"]
            }
        }
    }
] + (_SYS_TOOLS if _SYS_ACCESS else []) + [
    {
        "type": "function",
        "function": {
            "name": "play_game",
            "description": "Play a fun game: riddle, number guessing, math quiz, joke, or motivational quote",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string",
                             "description": "Type of game or entertainment (riddle, number_guess, math, joke, quote)"}
                },
                "required": ["type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_ticket",
            "description": "Search or book movie tickets, get showtimes and theater info",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie": {"type": "string", "description": "Movie name to book (optional)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Play music or songs on YouTube Music",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song, artist, or playlist to play"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar",
            "description": "Get calendar events: today, week, or next event",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["today", "week", "next"],
                               "description": "Which events to fetch"}
                },
                "required": ["period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_calendar_event",
            "description": "Add an event to Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "when":    {"type": "string", "description": "When: 'tomorrow 3pm', 'Monday 10am', 'in 2 hours'"},
                    "duration_min": {"type": "integer", "description": "Duration in minutes (default 60)"}
                },
                "required": ["summary", "when"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby",
            "description": "Find nearest place of a category: hospital, atm, restaurant, petrol, pharmacy, bank",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Place category"},
                    "city":     {"type": "string", "description": "City to search in (optional)"}
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "where_is",
            "description": "Find where a place is located and how far it is",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {"type": "string", "description": "Place name to look up"}
                },
                "required": ["place"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Remember a user preference, contact, or saved place",
            "parameters": {
                "type": "object",
                "properties": {
                    "type":  {"type": "string", "enum": ["preference", "place", "contact"],
                              "description": "What to remember"},
                    "key":   {"type": "string", "description": "Name or label"},
                    "value": {"type": "string", "description": "Value to remember"}
                },
                "required": ["type", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Recall a saved preference, place, or contact",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "What to recall"}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "smart_home",
            "description": "Control smart home devices: lights, fans, AC, TV. Set scenes like movie, sleep, work, morning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Full voice command e.g. 'turn on bedroom light', 'set movie scene', 'dim living room to 30%'"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop",
            "description": "Control the desktop: open apps, manage windows, search files, read/write clipboard",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "e.g. 'open VS Code', 'find file report', 'read clipboard', 'switch to Chrome'"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web",
            "description": "Web automation: search products on Flipkart/Amazon, Google search, fill forms",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "e.g. 'search iPhone 15 on flipkart under 60000', 'google latest news', 'fill form'"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vision",
            "description": "Use camera or screen vision: describe what camera sees, read screen text, scan QR codes, describe images",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "e.g. 'what do you see', 'read screen', 'scan QR', 'describe image.jpg'"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "call_sms",
            "description": "Handle calls and messages: reply to contacts, open WhatsApp, announce calls",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "e.g. 'reply to Rahul saying I am on my way', 'open whatsapp', 'open messages'"}
                },
                "required": ["command"]
            }
        }
    },
]


# ─── Tool executor ────────────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict) -> str:
    """Run a tool and return its result as a string."""
    try:
        if name == "get_weather":
            loc = args.get("location", "") or "Tamil Nadu, India"
            return get_weather(f"weather in {loc}")

        elif name == "get_information":
            return get_information(args.get("query", ""))

        elif name == "get_news":
            return get_news(args.get("category", "world"))

        elif name == "get_time":
            now = datetime.now()
            return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."

        elif name == "set_alarm":
            time_str = args.get("time_str", "")
            message  = args.get("message", "Reminder")
            try:
                mem_file = os.path.join(os.path.dirname(__file__), ".jarvis_memory.json")
                mem = {}
                if os.path.exists(mem_file):
                    with open(mem_file, encoding="utf-8") as f:
                        mem = json.load(f)
                mem.setdefault("alarms", []).append({"time": time_str, "message": message, "active": True})
                with open(mem_file, "w", encoding="utf-8") as f:
                    json.dump(mem, f)
                return f"Reminder set for {time_str}: {message}."
            except Exception:
                return f"Reminder noted: {message} at {time_str}."

        elif name == "control_light":
            action = args.get("action", "on")
            room   = args.get("room", "")
            where  = f"in the {room}" if room else ""
            return f"Lights turned {action} {where}.".strip()

        elif name == "play_game":
            game_type = args.get("type", "riddle")
            if _ENTERTAIN_OK:
                if "riddle" in game_type:
                    return _entertainment.get_random_riddle()
                elif "number" in game_type or "guess" in game_type:
                    return _entertainment.start_number_guessing_game()
                elif "math" in game_type:
                    return _entertainment.start_math_quiz()
                elif "joke" in game_type:
                    return _entertainment.get_random_joke()
                elif "quote" in game_type:
                    return _entertainment.get_motivational_quote()
            return "Game module not available."

        elif name == "book_ticket":
            if _BOOKING_OK:
                movie = args.get("movie", "")
                if movie:
                    showtimes = _ticket_booking.get_showtimes(movie)
                    theaters = _ticket_booking.get_theaters()
                    return f"Available showtimes for '{movie}': {', '.join(showtimes[:3])}. Theaters: {', '.join(theaters[:2])}."
                else:
                    movies = _ticket_booking.search_movies()
                    return f"Available movies: {', '.join(movies)}. Which one would you like to book?"
            return "Ticket booking not available."

        elif name == "play_music":
            query = args.get("query", "")
            if query:
                import webbrowser
                url = f"https://music.youtube.com/search?q={query.replace(' ', '+')}"
                webbrowser.open(url)
                return f"Opening YouTube Music for '{query}'."
            return "What would you like to listen to?"

        elif name == "get_calendar":
            if not _CALENDAR_OK:
                return "Calendar not set up. Add calendar_credentials.json to enable it."
            period = args.get("period", "today")
            if period == "week":   return get_events_week()
            if period == "next":   return get_next_event()
            return get_events_today()

        elif name == "add_calendar_event":
            if not _CALENDAR_OK:
                return "Calendar not set up."
            return add_event(args.get("summary","Meeting"),
                             args.get("when","tomorrow 10am"),
                             int(args.get("duration_min", 60)))

        elif name == "find_nearby":
            if not _MAPS_OK:
                return "Maps module unavailable."
            cat  = args.get("category", "")
            city = args.get("city", "")
            query = f"nearest {cat}" + (f" in {city}" if city else "")
            return _maps.handle_location_query(query)

        elif name == "where_is":
            if not _MAPS_OK:
                return "Maps module unavailable."
            return _maps.handle_location_query(f"where is {args.get('place','')}")

        elif name == "remember":
            if not _MEMORY_OK:
                return "Memory module unavailable."
            t, k, v = args.get("type",""), args.get("key",""), args.get("value","")
            if t == "preference": set_preference(k, v); return f"Got it — I'll remember {k} is {v}."
            if t == "place":      save_place(k, v);     return f"Saved '{k}' as {v}."
            if t == "contact":    remember_contact(k, v); return f"Remembered {k}: {v}."
            return "Remembered."

        elif name == "recall":
            if not _MEMORY_OK:
                return "Memory module unavailable."
            k = args.get("key", "").lower()
            p = get_place(k)
            if p: return f"{k.title()} is saved as {p['name']}."
            c = get_contact(k)
            if c: return f"{k.title()}: {c}"
            v = get_preference(k)
            if v: return f"{k}: {v}"
            return f"I don't have anything saved for '{k}'."

        elif name == "smart_home":
            if not _SMARTHOME_OK:
                return "Smart home module unavailable."
            return _smarthome_control(args.get("command", ""))

        elif name == "desktop":
            if not _DESKTOP_OK:
                return "Desktop control unavailable."
            return _desktop_handle(args.get("command", ""))

        elif name == "web":
            if not _WEB_OK:
                return "Web automation unavailable."
            return _web_handle(args.get("command", ""))

        elif name == "vision":
            if not _VISION_OK:
                return "Vision module unavailable. Install: pip install opencv-python pytesseract pillow"
            return _vision_handle(args.get("command", ""))

        elif name == "call_sms":
            if not _CALLSMS_OK:
                return "Call/SMS module unavailable."
            return _callsms_handle(args.get("command", ""))

        elif _SYS_ACCESS:
            return _sys_exec(name, args)

        else:
            return f"Tool '{name}' not implemented."

    except Exception as exc:
        return f"Tool error: {exc}"


# ═══════════════════════════════════════════════════════════════════════════════
# Conversation memory
# ═══════════════════════════════════════════════════════════════════════════════

class _ConversationMemory:
    """Rolling window of last N turns, persisted to disk across restarts."""
    MAX_TURNS = 8
    _FILE = os.path.join(os.path.dirname(__file__), ".jarvis_memory.json")
    _lock = threading.RLock()  # ← Thread-safe file access

    def __init__(self):
        self._history: list[dict] = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self._FILE):
                with self._lock:  # ← Acquire lock before reading
                    with open(self._FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._history = data.get("history", [])[-self.MAX_TURNS * 2:]
        except Exception:
            self._history = []

    def _save(self):
        try:
            # Write to temp file first for atomicity, then replace
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=os.path.dirname(self._FILE))
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump({"history": self._history}, f)
                # Atomic rename with lock
                with self._lock:
                    os.replace(temp_path, self._FILE)
            except Exception:
                try:
                    os.unlink(temp_path)  # Clean up temp file on error
                except:
                    pass
                raise
        except Exception as e:
            print(f"[Memory] Save failed: {e}")

    def add_user(self, text: str):
        with self._lock:
            self._history.append({"role": "user", "content": text})
            self._trim()
            self._save()

    def add_assistant(self, text: str):
        with self._lock:
            self._history.append({"role": "assistant", "content": text})
            self._trim()
            self._save()

    def _trim(self):
        max_msgs = self.MAX_TURNS * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

    def get_messages(self, system: str, filter_language: str = None) -> list[dict]:
        """
        Get messages with optional language filtering.
        filter_language: 'en' (English only), 'ta' (Tamil only), None (all)
        """
        with self._lock:
            result = [{"role": "system", "content": system}]
            
            if filter_language is None:
                result.extend(self._history)
            else:
                # Filter history to only include messages in the same language
                for msg in self._history:
                    content = msg.get("content", "")
                    has_tamil = any('\u0b80' <= char <= '\u0bff' for char in content)
                    
                    if filter_language == 'en':
                        # Only include English messages (no Tamil script)
                        if not has_tamil:
                            result.append(msg)
                    elif filter_language == 'ta':
                        # Only include messages with Tamil script  
                        if has_tamil or msg.get("role") == "user":
                            result.append(msg)
            
            return result

    def clear(self):
        with self._lock:
            self._history.clear()
            self._save()


_MEMORY = _ConversationMemory()

# Bug 3 fix: initialize _pending_schedule at module level to prevent NameError
_pending_schedule: dict = {}


# ═══════════════════════════════════════════════════════════════════════════════
# Fast rule-based path (no API needed)
# ═══════════════════════════════════════════════════════════════════════════════

_SIMPLE_RULES = {
    ("hello", "hi", "hey", "vanakkam", "good morning", "good evening"):
        lambda: f"Hello! It's {datetime.now().strftime('%I:%M %p')}. What do you need?",
    ("what time", "current time", "time now", "mani enna", "tell me the time"):
        lambda: f"It's {datetime.now().strftime('%I:%M %p')} on {datetime.now().strftime('%A')}.",
    ("what date", "today's date", "what day", "what is today",
     "what is the date", "current date", "tell me the date"):
        lambda: f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.",
    ("thank you", "thanks", "nandri", "thank u"):
        lambda: "You're welcome.",
    ("bye", "goodbye", "exit", "see you"):
        lambda: "Goodbye. I'll be here when you need me.",
    ("who are you", "what are you", "your name", "what's your name"):
        lambda: "I'm JARVIS \u2014 your AI assistant.",
    ("how are you", "how are you doing", "how's it going", "you okay"):
        lambda: "I'm doing great! Ready to help. What can I do for you?",
    ("what's up", "whats up", "what up", "yo"):
        lambda: "Not much! Just here and ready to assist.",
}


import ast as _ast

def _safe_math_eval(expr: str):
    """Safely evaluate a simple arithmetic expression. Returns str or None."""
    e = re.sub(r'(?:what\s+is|calculate|compute|equals?|please|\?)', '', expr, flags=re.I).strip()
    e = re.sub(r'\btimes\b', '*', e, flags=re.I)
    e = re.sub(r'\bdivided\s+by\b', '/', e, flags=re.I)
    e = re.sub(r'\bplus\b', '+', e, flags=re.I)
    e = re.sub(r'\bminus\b', '-', e, flags=re.I)
    e = re.sub(r'\bmod(?:ulo)?\b', '%', e, flags=re.I)
    e = e.strip()
    if not re.match(r'^[\d\s\+\-\*\/\%\(\)\.]+$', e):
        return None
    try:
        tree = _ast.parse(e, mode='eval')
        for node in _ast.walk(tree):
            if not isinstance(node, (_ast.Expression, _ast.BinOp, _ast.UnaryOp,
                                     _ast.Num, _ast.Constant, _ast.Add, _ast.Sub,
                                     _ast.Mult, _ast.Div, _ast.FloorDiv, _ast.Mod,
                                     _ast.Pow, _ast.USub, _ast.UAdd)):
                return None
        result = eval(compile(tree, '<string>', 'eval'))  # noqa: S307
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 6))
    except Exception:
        return None


def _try_rule(text: str) -> Optional[str]:
    t = text.lower().strip()
    for triggers, handler in _SIMPLE_RULES.items():
        for kw in triggers:
            # Match whole words at start of sentence OR as complete words, not substrings
            if t.startswith(kw + " ") or t == kw:
                print(f"[Rule] Matched '{kw}' in '{t}'")
                return handler()
            # Also match if keyword is followed by punctuation (e.g., "hello,", "hey!")
            if t.startswith(kw) and len(t) > len(kw) and not t[len(kw)].isalnum():
                print(f"[Rule] Matched '{kw}' (with punctuation) in '{t}'")
                return handler()

    # Math fast path — handle before hitting LLM
    if any(op in t for op in ['+', '-', '*', '/', 'times', 'divided', 'plus', 'minus', 'mod']):
        result = _safe_math_eval(t)
        if result is not None:
            print(f"[Math] '{t}' = {result}")
            return f"The answer is {result}."

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Groq client
# ═══════════════════════════════════════════════════════════════════════════════

_groq_client = None

def _get_groq():
    global _groq_client
    # During unit tests or CI we avoid creating a real Groq client to
    # prevent network calls and incompatibilities with the installed
    # groq/httpx versions. Detect pytest by environment or loaded modules
    # and skip client creation in that case.
    running_under_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST") or any('pytest' in k for k in sys.modules.keys()))
    if running_under_pytest:
        return None

    if _groq_client is None and _GROQ_LIB and GROQ_KEY:
        _groq_client = _Groq(api_key=GROQ_KEY)
    return _groq_client


def _call_groq(messages: list[dict], strict: bool = False) -> Optional[str]:
    client = _get_groq()
    if not client:
        return None

    system_prompt = _build_system_prompt() + (_STRICT_ADDENDUM if strict else "")
    msgs = [m if m["role"] != "system" else {"role": "system", "content": system_prompt}
            for m in messages]

    max_tokens = 120 if strict else 400

    try:
        # First call — may include tool use (wrapped with error recovery)
        def _groq_call_1():
            return client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=msgs,
                tools=_TOOLS_GROQ,
                tool_choice="auto",
                max_tokens=max_tokens,
                temperature=0.7,
                parallel_tool_calls=False,
                timeout=10,
            )
        
        response = ERROR_RECOVERY.retry_with_backoff(_groq_call_1, "groq", args=())
        if response is None:
            return None
        record_call("groq")

        msg = response.choices[0].message

        # Handle structured tool calls
        if msg.tool_calls:
            tool_results = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                result = _execute_tool(tc.function.name, args)
                tool_results.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })

            # Second call with tool results — no tools, just synthesise (wrapped)
            msgs2 = msgs + [msg] + tool_results  # type: ignore[list-item]
            
            def _groq_call_2():
                return client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=msgs2,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    timeout=10,
                )
            
            response2 = ERROR_RECOVERY.retry_with_backoff(_groq_call_2, "groq", args=())
            if response2 is None:
                return None
            record_call("groq")
            return _clean_response(response2.choices[0].message.content or "")

        # Fallback: check if response has raw JSON tool call text
        response_text = (msg.content or "").strip()
        
        # Pattern 1: {"name":"...", "parameters/arguments":{...}} or {"name":"...", "category":...}
        if response_text.startswith("{") and '"name"' in response_text:
            try:
                tool_call = json.loads(response_text)
                if "name" in tool_call:
                    result = _execute_tool(tool_call["name"], tool_call)
                    synthesis_msgs = msgs + [
                        {"role": "assistant", "content": response_text},
                        {"role": "tool", "tool_call_id": "fallback", "content": result}
                    ]
                    response3 = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=synthesis_msgs,
                        max_tokens=max_tokens,
                        temperature=0.7,
                        timeout=10,
                    )
                    record_call("groq")
                    return _clean_response(response3.choices[0].message.content or "")
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Pattern 2: function_name>{"key":"value"} (e.g., get_news>{"category":"world"})
        match = re.match(r'^(\S+?)\s*>\s*(\{.+\})$', response_text)
        if match:
            func_name = match.group(1)
            json_str = match.group(2)
            try:
                args = json.loads(json_str)
                if func_name in ("get_weather", "get_information", "get_news", "get_time", "set_alarm", "control_light", "call_sms", "play_game"):
                    result = _execute_tool(func_name, args)
                    synthesis_msgs = msgs + [
                        {"role": "assistant", "content": response_text},
                        {"role": "tool", "tool_call_id": "fallback", "content": result}
                    ]
                    response3 = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=synthesis_msgs,
                        max_tokens=max_tokens,
                        temperature=0.7,
                        timeout=10,
                    )
                    record_call("groq")
                    return _clean_response(response3.choices[0].message.content or "")
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        
        # Pattern 2b: function_name{"key":"value"} without > separator (e.g., get_weather{"location":"Kerala"})
        match = re.match(r'^([a-z_]+)\s*(\{.+\})$', response_text)
        if match:
            func_name = match.group(1)
            json_str = match.group(2)
            try:
                args = json.loads(json_str)
                if func_name in ("get_weather", "get_information", "get_news", "get_time", "set_alarm", "control_light", "call_sms", "play_game"):
                    result = _execute_tool(func_name, args)
                    synthesis_msgs = msgs + [
                        {"role": "assistant", "content": response_text},
                        {"role": "tool", "tool_call_id": "fallback", "content": result}
                    ]
                    response3 = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=synthesis_msgs,
                        max_tokens=max_tokens,
                        temperature=0.7,
                        timeout=10,
                    )
                    record_call("groq")
                    return _clean_response(response3.choices[0].message.content or "")
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass

        return _clean_response(response_text)

    except Exception as exc:
        err = str(exc)
        if "rate_limit" in err.lower() or "429" in err:
            return None
        # tool_use_failed: model tried to call multiple tools as raw text.
        # Retry once without tools so Groq answers directly.
        if "tool_use_failed" in err or "Failed to call a function" in err:
            try:
                r2 = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=msgs,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                record_call("groq")
                return _clean_response(r2.choices[0].message.content or "")
            except Exception as exc2:
                print(f"[Groq retry error] {exc2}")
                return None
        print(f"[Groq error] {exc}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Gemini client
# ═══════════════════════════════════════════════════════════════════════════════

_gemini_model = None

def _get_gemini():
    global _gemini_model
    if _gemini_model is None and _GEMINI_LIB and GEMINI_KEY:
        _gemini_model = _genai.Client(api_key=GEMINI_KEY)
    return _gemini_model


def _call_gemini(history: list[dict], user_text: str, strict: bool = False) -> Optional[str]:
    client = _get_gemini()
    if not client:
        return None

    # Build contents from history (skip system message)
    contents = []
    for m in history:
        if m["role"] == "system":
            continue
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    prompt = user_text + (" Answer in 1-2 sentences only." if strict else "")
    if not contents or contents[-1]["role"] != "user":
        contents.append({"role": "user", "parts": [{"text": prompt}]})
    else:
        contents[-1]["parts"][0]["text"] = prompt

    try:
        def _gemini_call():
            return client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config=_genai.types.GenerateContentConfig(
                    system_instruction=_build_system_prompt(),
                    max_output_tokens=120 if strict else 400,
                    temperature=0.7,
                )
            )
        
        response = ERROR_RECOVERY.retry_with_backoff(_gemini_call, "gemini", args=())
        if response is None:
            return None
        record_call("gemini")
        return _clean_response(response.text or "")

    except Exception as exc:
        err = str(exc)
        if "429" in err or "quota" in err.lower():
            return None
        print(f"[Gemini error] {exc}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Offline fallback
# ═══════════════════════════════════════════════════════════════════════════════

def _offline_reply(query: str) -> str:
    """Use NLP intent classification to give a meaningful offline response."""
    # 1. Try local tools first (time, alarms)
    result = _execute_tool_locally(query)
    if result:
        return result

    # 2. Route through NLP for intent-based responses
    if _NLP_AVAILABLE:
        try:
            nlp_result = _nlp.process_text(query)
            intent     = nlp_result.get("intent", "unknown")
            response   = nlp_result.get("response", "")

            # Intents that work fully offline
            OFFLINE_OK = {
                "greeting", "thanks", "farewell", "joke",
                "capability_query", "time_query", "alarm_reminder",
                "light_control", "music", "calculation", "definition",
            }
            if intent in OFFLINE_OK and response:
                return response

            # Intents that need internet — say so clearly
            if intent == "weather_query":
                return "I need an internet connection to fetch weather. I'll check as soon as you're back online."
            if intent == "news_query":
                return "News requires internet. I'll get the latest headlines when you're connected."
            if intent == "joke" and _ENTERTAIN_OK:
                return _entertainment.get_random_joke()
            if intent in ("info_request", "definition"):
                # Try to answer general knowledge offline
                offline_answer = _attempt_offline_answer(query)
                if offline_answer:
                    return offline_answer
                return "I need internet for detailed info. Offline I can help with time, alarms, games, and device control."
            if intent == "calculation":
                # try to evaluate simple math offline
                import re as _re
                expr = _re.search(r"[\d\s\+\-\*\/\(\)\.]+", query)
                if expr:
                    try:
                        result = eval(expr.group().strip())
                        return f"That's {result}."
                    except Exception:
                        pass
                return "I need internet for complex calculations."
        except Exception:
            pass

    # 3. For unknown intents, still try a general answer
    offline_answer = _attempt_offline_answer(query)
    if offline_answer:
        return offline_answer
    
    return "I'm offline right now. I can help with time, alarms, device control, and general questions. What do you need?"


def _attempt_offline_answer(query: str) -> Optional[str]:
    """Try to answer general knowledge questions offline using simple patterns."""
    q_lower = query.lower()
    
    # Simple pattern-based answers for common questions
    patterns = {
        r"(what|who) (is|are|was) (an|a|the)?.+(python|java|javascript|coding|programming)": 
            "A programming language — used to write software. Python is beginner-friendly, Java is powerful, JavaScript runs in browsers.",
        r"(why|how) (does|do|can|is).+work": 
            "That's a detailed question. I'd need internet to give you the full technical explanation.",
        r"(what|how) (is|are).+(sum|total|average) (of|for).+(\d+)":
            "I can help with math. Give me the numbers and I'll calculate.",
        r"(tell|give).+(joke|funny|laugh)":
            "Why did the AI go to school? To improve its neural network! 😄",
        r"(how|what).+(python|code|program)":
            "Python is great for beginners and experts. Want to learn? I can guide you when I'm back online.",
        r"(who|what) (are|is) you":
            "I'm JARVIS, your AI assistant. I'm here to help with whatever you need.",
    }
    
    for pattern, answer in patterns.items():
        if re.match(pattern, q_lower, re.IGNORECASE):
            return answer
    
    # If it's a simple question, try a generic helpful response
    if any(q_lower.startswith(w) for w in ("what ", "how ", "why ", "when ", "where ", "who ")):
        return "That's a great question. I'd give you a better answer with internet access. For now, ask me about time, alarms, or device control."
    
    return None


def _execute_tool_locally(query: str) -> Optional[str]:
    q = query.lower()
    if re.search(r"\b(what time is it|current time|time now|clock)\b", q) or q.strip() in {"time", "what time", "time?"}:
        return _execute_tool("get_time", {})
    if re.search(r"\b(what(?:'s| is) the date|current date|today's date|what day is it|what day|date today)\b", q) or q.strip() in {"date", "today", "what date"}:
        now = datetime.now()
        return f"Today is {now.strftime('%A, %B %d, %Y')}."
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Main router — public API
# ═══════════════════════════════════════════════════════════════════════════════

def ask(user_input: str, personality: str = "default") -> str:
    """
    Main entry point. Routes through:
    rule → cache → Groq → Gemini → offline

    Args:
        user_input:  Raw user text.
        personality: 'default' | 'strict' | 'funny'

    Returns:
        Response string.
    """
    text = (user_input or "").strip()
    if not text:
        return "I didn't catch that."

    # ── 0b. Tier 2: Extract personalization data ────────────────────────────
    # Learn from user input about their preferences
    user_intent = "REQUEST"  # Will be updated later by intent classifier
    if _PERSONALIZATION_OK:
        try:
            pref_result = personalize(text, intent=user_intent, extract_prefs=True)
            if pref_result.get("extracted_preferences"):
                print(f"[Personalization] Learned: {pref_result['extracted_preferences']}")
            # Show greeting if we just learned the user's name
            if pref_result.get("greeting"):
                greeting = pref_result["greeting"]
                print(f"[Personalization] {greeting}")
        except Exception as e:
            print(f"[Personalization error] {e}")

    # ── 0. Check pending confirmation (web automation) ─────────────────────
    if _WEB_OK:
        try:
            resolved = _web_resolve(text)
            if resolved is not None:
                _MEMORY.add_user(text)
                _MEMORY.add_assistant(resolved)
                return resolved
        except Exception:
            pass

    # ── 1. Fast rule-based ──────────────────────────────────────────────────
    rule_result = _try_rule(text)
    if rule_result:
        _MEMORY.add_user(text)
        _MEMORY.add_assistant(rule_result)
        # Store in extended memory with intent metadata
        if _EXTENDED_MEMORY_OK:
            try:
                EXTENDED_MEMORY.add_turn(text, rule_result, {"intent": "GREETING", "source": "rule"})
            except Exception:
                pass
        return rule_result

    # ── 1b. Intent Classification (Tier 1) ──────────────────────────────────
    intent_result = None
    if _INTENT_CLASSIFIER_OK:
        try:
            intent_result = classify_query(text)
            print(f"[Intent] {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})")
            
            # If query is ambiguous, ask for clarification
            if intent_result.get('requires_clarification', False):
                clarification_questions = intent_result.get('clarification_questions', [])
                if clarification_questions:
                    clarification_prompt = "Could you clarify? " + " ".join(clarification_questions)
                    _MEMORY.add_user(text)
                    _MEMORY.add_assistant(clarification_prompt)
                    if _EXTENDED_MEMORY_OK:
                        try:
                            EXTENDED_MEMORY.add_turn(text, clarification_prompt, {
                                "intent": intent_result['intent'],
                                "confidence": intent_result['confidence'],
                                "requires_clarification": True,
                            })
                        except Exception:
                            pass
                    return clarification_prompt
        except Exception as e:
            print(f"[Intent classifier error] {e}")

    # ── 2a. Tier 2: Query Enhancement ──────────────────────────────────────
    # Rephrase ambiguous queries
    if _REPHRASING_OK and intent_result:
        try:
            rephrased = rephrase_query(text, context={
                "intent": intent_result.get("intent", "REQUEST"),
                "entities": intent_result.get("entities", {}),
                "query": text
            })
            if rephrased.get("needs_clarification"):
                prompt = rephrased.get("clarification_prompt", "Could you clarify?")
                _MEMORY.add_user(text)
                _MEMORY.add_assistant(prompt)
                if _EXTENDED_MEMORY_OK:
                    try:
                        EXTENDED_MEMORY.add_turn(text, prompt, {
                            "intent": intent_result.get("intent"),
                            "source": "rephrasing_clarification"
                        })
                    except Exception:
                        pass
                return prompt
            # Use rephrased query if different
            if rephrased.get("rephrased") != text:
                text = rephrased["rephrased"]
                print(f"[Rephrased] {text}")
        except Exception as e:
            print(f"[Query rephrasing error] {e}")
    
    # Time-aware execution
    if _TIME_AWARE_OK:
        try:
            time_info = extract_scheduled_action(text)
            if time_info.get("is_timed"):
                # Store scheduling metadata (module-level so it persists across calls)
                global _pending_schedule
                _pending_schedule = {
                    "action": time_info["action"],
                    "target_time": time_info["target_time"],
                    "time_string": time_info["time_string"]
                }
                print(f"[Scheduled] {time_info['action']} at {time_info['time_string']}")
                # Continue processing with cleaned action text
                text = time_info["action"]
        except Exception as e:
            print(f"[Time-aware execution error] {e}")
    
    # Natural follow-up handling
    if _FOLLOWUP_OK and intent_result and EXTENDED_MEMORY.get_context():
        try:
            # get_context() returns [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}...]
            memory_context = EXTENDED_MEMORY.get_context(window_size=2)
            # Extract last user/assistant pair from the flat role-content list
            prev_user = ""
            prev_assistant = ""
            for msg in reversed(memory_context):
                if msg.get("role") == "assistant" and not prev_assistant:
                    prev_assistant = msg.get("content", "")
                elif msg.get("role") == "user" and not prev_user:
                    prev_user = msg.get("content", "")
                if prev_user and prev_assistant:
                    break
            if prev_user:
                followup = handle_followup(
                    text,
                    previous_query=prev_user,
                    previous_response=prev_assistant,
                    previous_intent=intent_result.get("intent", "REQUEST"),
                    entities=intent_result.get("entities", {})
                )
                if followup.get("is_followup"):
                    text = followup.get("rewritten_query", text)
                    print(f"[Follow-up] {followup['followup_type']}: {text}")
        except Exception as e:
            print(f"[Follow-up handling error] {e}")

    # ── 2. Fast lang detection + Cache (OPTIMIZED for speed) ─────────────────────────────────
    # Check for obvious tamil script ONLY - skip full language detection for speed
    detected_lang = 'ta' if any('\u0b80' <= c <= '\u0bff' for c in text) else 'en'
    if detected_lang == 'ta' and _TAMIL_OK:
        try:
            text = _inject_tamil(text)  # Inject Tamil context
        except Exception:
            detected_lang = 'en'
    os.environ['JARVIS_STT_LANG'] = detected_lang
    
    clean_text = _nlp.preprocess_text(text) if _NLP_AVAILABLE else text
    # CACHING DISABLED - to prevent stale "Getting late, sir." responses from emotion adapter
    # cached = cache_get(clean_text)
    # if cached:
    #     _MEMORY.add_user(text)
    #     _MEMORY.add_assistant(cached)
    #     return cached

    # ── 3. Build message history ─────────────────────────────────────────────
    _MEMORY.add_user(text)
    # Filter memory to only include messages in the same language as current query
    filter_lang = 'ta' if detected_lang in ('ta', 'mixed') else 'en'
    messages = _MEMORY.get_messages(_build_system_prompt(), filter_language=filter_lang)

    # ── 4. Determine strict mode ─────────────────────────────────────────────
    groq_mode   = get_mode("groq")
    gemini_mode = get_mode("gemini")
    strict = personality == "strict" or groq_mode in ("strict", "warn")

    # ── 5. Try Groq ──────────────────────────────────────────────────────────
    response: Optional[str] = None

    if AI_MODE in ("hybrid", "groq") and GROQ_KEY and _GROQ_LIB:
        if groq_mode != "blocked":
            allowed, reason = can_call("groq")
            if allowed:
                response = _call_groq(messages, strict=strict)
            else:
                print(f"[Rate Guard] Groq skipped: {reason}")

    # ── 6. Try Gemini (fallback) ─────────────────────────────────────────────
    if response is None and AI_MODE in ("hybrid", "gemini") and GEMINI_KEY and _GEMINI_LIB:
        if gemini_mode != "blocked":
            allowed, reason = can_call("gemini")
            if allowed:
                response = _call_gemini(messages, text, strict=gemini_mode in ("strict", "warn"))
            else:
                print(f"[Rate Guard] Gemini skipped: {reason}")

    # ── 7. Validate weather responses — if query was about weather but response looks generic, fetch weather ──
    text_lower = text.lower()
    is_weather_query = any(w in text_lower for w in ("weather", "temperature", "rain", "storm", "cloudy", "sunny", "forecast", "conditions"))
    response_lower = (response or "").lower()
    has_weather_info = any(w in response_lower for w in ("temperature", "rain", "cloud", "wind", "sunny", "clear", "°", "partly", "weather"))
    
    if is_weather_query and response and len(response) < 5:
        # Response is too short/vague for a weather query — force fetch
        print(f"[Weather fallback] Response too vague for weather query, fetching...")
        location = text.split("in ")[-1] if " in " in text_lower else ""
        try:
            response = _clean_response(get_weather(f"weather in {location or 'Tamil Nadu'}"))
        except Exception as e:
            print(f"[Weather fallback error] {e}")

    # ── 7b. Validate novel/general queries — if LLM response is empty or too vague, retry ──
    is_tool_query = any(w in text_lower for w in ("weather", "news", "time", "alarm", "light", "reminder", "temperature", "forecast", "headlines"))
    if not is_tool_query and response and len(response.strip()) < 4:
        # Novel query got a very vague response — likely LLM didn't understand
        print(f"[Novel query fallback] LLM response too vague ('{response}'), retrying without tools...")
        # Retry the call but ask Groq to answer directly without offering tools
        if _groq_client:
            try:
                msgs_retry = messages + [
                    {"role": "user", "content": f"Please answer directly and confidently: {text}"}
                ]
                response2 = _groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=msgs_retry,
                    tools=[],  # No tools — just answer
                    max_tokens=200,
                    temperature=0.7,
                    timeout=10,
                )
                record_call("groq")
                response = _clean_response(response2.choices[0].message.content or "")
                print(f"[Novel query retry] Got: {response[:50]}...")
            except Exception as e:
                print(f"[Novel query retry error] {e}")

    # ── 8. Offline fallback ──────────────────────────────────────────────────
    # Check for None OR empty string (Groq/Gemini may return "" instead of raising exception)
    if not response or (isinstance(response, str) and not response.strip()):
        response = _offline_reply(text)

    response = _clean_response((response or "").strip())
    if response:
        # EMOTION ADAPTER DISABLED TEMPORARILY
        # Causing unwanted "Getting late, sir." on conversational queries
        _MEMORY.add_assistant(response)
        
        # ── Tier 2: Personalize response ────────────────────────────────────
        if _PERSONALIZATION_OK:
            try:
                profile = PERSONALIZATION_ENGINE.get_profile_summary()
                if profile.get("user_name"):
                    # Adapt response based on user preferences
                    response = PERSONALIZATION_ENGINE.adapt_response(response, user_intent)
            except Exception as e:
                print(f"[Response personalization error] {e}")
        
        # Bug 4 fix: initialize confidence before the scoring block so it's always defined
        confidence = 0.0
        # ── Tier 2: Score confidence in response ────────────────────────────
        if _CONFIDENCE_SCORING_OK:
            try:
                source = "llm_groq" if response else "offline"
                conf_result = score_ai_confidence(response, source=source, intent=user_intent)
                confidence = conf_result.get("confidence", 0.7)
                # Log only — do NOT append clarification text to response.
                # Appending "I'm not entirely sure..." degrades factual answers.
                print(f"[Confidence] {conf_result['level']} ({confidence:.2f})")
            except Exception as e:
                print(f"[Confidence scoring error] {e}")
        
        # Store in extended memory with intent metadata (Tier 1)
        if _EXTENDED_MEMORY_OK:
            try:
                metadata = {}
                if intent_result:
                    metadata = {
                        "intent": intent_result.get("intent", "REQUEST"),
                        "confidence": intent_result.get("confidence", 0),
                        "topic": intent_result.get("intent", "general"),
                    }
                EXTENDED_MEMORY.add_turn(text, response, metadata)
            except Exception as e:
                print(f"[Extended memory error] {e}")
        
        # ── Tier 3: Email/Communication Handling ────────────────────────────
        if _EMAIL_OK and any(w in text_lower for w in ["email", "send message", "compose"]):
            try:
                email_result = handle_email(text)
                if email_result.get("success"):
                    response = email_result.get("message", response)
                    print(f"[Email] {email_result.get('message', 'Email handled')}")
            except Exception as e:
                print(f"[Email handling error] {e}")
        
        # ── Tier 3: Web Search Fallback (for low confidence factual queries) ─
        # NOTE: web_search.py currently returns MOCK results — disable fallback
        # until a real search API (DuckDuckGo / SerpAPI) is integrated.
        # Re-enable by removing the `False and` guard below.
        if False and _WEB_SEARCH_OK and confidence and confidence < 0.6:
            # If LLM confidence is low and query looks factual, use web search
            if any(w in text_lower for w in ["what is", "who is", "how to", "latest", "news", "information"]):
                try:
                    search_result = handle_web_search(text, fallback=True)
                    if search_result.get("success"):
                        # Supplement response with search results
                        search_summary = search_result.get("summary", "")
                        if search_summary and "Mock result" not in search_summary:
                            response = response + "\n\n" + search_summary
                            print(f"[Web Search Fallback] Added search results (confidence was {confidence:.2f})")
                except Exception as e:
                    print(f"[Web search fallback error] {e}")
        
        # ── Tier 3: Proactive Assistance Suggestions ────────────────────────
        if _PROACTIVE_OK and EXTENDED_MEMORY.get_context():
            try:
                # Get conversation history for context
                history = EXTENDED_MEMORY.get_context(window_size=3)
                history_text = [t.get("user_text", "") for t in history]
                
                proactive_result = detect_proactive_needs(text, conversation_history=history_text)
                if proactive_result.get("has_suggestions"):
                    suggestion_msg = proactive_result.get("message", "")
                    if suggestion_msg:
                        response = response + "\n\n" + suggestion_msg
                        print(f"[Proactive] Suggested {proactive_result.get('suggestion_type')}")
            except Exception as e:
                print(f"[Proactive assistance error] {e}")
        
        # ── Tier 3: Smart Notifications ─────────────────────────────────────
        if _NOTIFICATIONS_OK:
            try:
                # Detect if this response warrants a notification
                should_notify = False
                notif_type = "general"
                notif_channel = "general"
                
                # Calendar events
                if any(w in text_lower for w in ["meeting", "appointment", "schedule", "event"]):
                    should_notify = True
                    notif_type = "calendar"
                    notif_channel = "calendar"
                
                # Weather alerts
                elif any(w in text_lower for w in ["rain", "storm", "alert", "warning"]):
                    should_notify = True
                    notif_type = "weather"
                    notif_channel = "weather"
                
                # Urgent/important
                elif any(w in text_lower for w in ["urgent", "important", "critical", "asap"]):
                    should_notify = True
                    notif_type = "alert"
                    notif_channel = "general"
                
                # Create notification if needed
                if should_notify:
                    notif_result = create_and_send_notification(
                        notif_type,
                        response[:100] + "..." if len(response) > 100 else response,
                        context={"channel": notif_channel},
                        actions=["Details", "Dismiss"]
                    )
                    print(f"[Notification] Created: {notif_result.get('message', 'notification')}")
            except Exception as e:
                print(f"[Smart notifications error] {e}")
        
        # ── Tier 3: Calendar Integration (for scheduling) ────────────────────
        if _CALENDAR_OK and any(w in text_lower for w in ["schedule", "meeting", "event", "book"]):
            try:
                # Extract time from response if mentioned
                if any(w in response.lower() for w in ["tomorrow", "next", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "pm", "am"]):
                    # Offer to add to calendar
                    print(f"[Calendar] Scheduling capability available")
                    # Note: Actual addition requires user confirmation
            except Exception as e:
                print(f"[Calendar integration error] {e}")
        
        # CACHING DISABLED - to prevent stale "Getting late, sir." responses
        # if len(response) > 20:
        #     cache_put(clean_text, response)

    return response


def clear_memory():
    """Clear conversation history."""
    _MEMORY.clear()


def get_status() -> dict:
    """Return usage stats and system status."""
    return {
        "ai_mode":        AI_MODE,
        "groq_available": bool(_GROQ_LIB and GROQ_KEY),
        "gemini_available": bool(_GEMINI_LIB and GEMINI_KEY),
        "cache_stats":    __import__("jarvis_cache").stats(),
        "api_usage":      status_report(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("JARVIS AI Brain — Interactive Test")
    print("Status:", json.dumps(get_status(), indent=2))
    print("\nType 'quit' to exit, 'status' for usage stats\n")

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user:
            continue
        if user.lower() == "quit":
            break
        if user.lower() == "status":
            print(json.dumps(get_status(), indent=2))
            continue
        if user.lower() == "clear":
            clear_memory()
            print("Memory cleared.")
            continue

        t0       = time.perf_counter()
        response = ask(user)
        elapsed  = time.perf_counter() - t0
        print(f"JARVIS ({elapsed:.2f}s): {response}\n")
