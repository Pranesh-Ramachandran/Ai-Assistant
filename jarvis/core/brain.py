"""
JARVIS Core Brain — intent detection, response routing, alarm management.
Single authoritative brain module. All other brain variants are removed.
"""

import json
import logging
import os
import random
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.core.nlp import process_natural_language
from jarvis.services.data_collector import get_information, get_weather, get_news_headlines

logger = logging.getLogger(__name__)

# ── Optional document intelligence ──────────────────────────────────────────
try:
    from jarvis.services.document_intelligence import process_document_command
    _DOC_INTEL_AVAILABLE = True
except ImportError as e:
    _DOC_INTEL_AVAILABLE = False
    logger.warning("Document intelligence not loaded: %s", e)
    def process_document_command(text): return "Document intelligence not available."

# ── Optional vision ─────────────────────────────────────────────────────────
try:
    from jarvis.services.vision import handle_vision_command, get_vision_capabilities
    _VISION_AVAILABLE = True
except ImportError as e:
    _VISION_AVAILABLE = False
    logger.warning("Vision not loaded: %s", e)
    def handle_vision_command(text): return "Vision not available."
    def get_vision_capabilities(): return "Vision features require additional packages."

logger = logging.getLogger(__name__)

# ── AI Brain (Groq + Gemini hybrid) ──────────────────────────────────────────
try:
    from jarvis.core.ai_brain import ask as ai_ask, clear_memory as ai_clear, get_status as ai_status
    _AI_BRAIN_AVAILABLE = True
except ImportError as e:
    _AI_BRAIN_AVAILABLE = False
    logger.warning("AI brain not loaded: %s", e)
    def ai_ask(text, **kw): return None
    def ai_clear(): pass
    def ai_status(): return {}

# ── Optional modules ──────────────────────────────────────────────────────────
try:
    from jarvis.services.iot import IoTAssistant
except ImportError:
    IoTAssistant = None

try:
    from jarvis.services.tts import speak as default_speak
except ImportError:
    def default_speak(text): print(f"TTS: {text}")

try:
    from jarvis.services.stt import listen as default_listen
except ImportError:
    def default_listen(): return input("Voice: ").lower().strip()


class _SimpleTTS:
    def speak(self, text: str) -> None:
        default_speak(text)


class JarvisBrain:
    MEMORY_FILE = str(Path(__file__).resolve().parent.parent.parent / "data" / "assistant_memory.json")

    def __init__(self, tts_engine=None, voice_listener=None):
        self.context = {
            "last_intent": None,
            "conversation": [],
            "last_response": None,
            "last_command": None,
            "last_command_time": 0.0,
        }
        os.makedirs(os.path.dirname(self.MEMORY_FILE), exist_ok=True)
        self.memory = self._load_memory()
        self._memory_dirty = False
        self.last_nlp_result = None
        self.iot = IoTAssistant() if IoTAssistant else None
        self.tts = self._init_tts(tts_engine)
        self.listen = voice_listener if voice_listener else default_listen
        self._alarm_thread_running = False
        self.start_alarm_thread()

    def _init_tts(self, tts_engine):
        if tts_engine is None:
            return _SimpleTTS()
        if hasattr(tts_engine, "speak"):
            return tts_engine
        if callable(tts_engine):
            class _FuncTTS:
                def speak(self, text): tts_engine(text)
            return _FuncTTS()
        return _SimpleTTS()

    # ── Text normalization ────────────────────────────────────────────────────

    def _normalize_command(self, command: str) -> str:
        if not command:
            return ""
        normalized = command.lower().strip()
        normalized = re.sub(r"[^\w\s:\+\-\*/\(\)%\=\.]", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    # ── Intent mapping ────────────────────────────────────────────────────────

    _NLP_INTENT_MAP = {
        "greeting": "greeting",
        "thanks": "thanks",
        "time_query": "time_date",
        "weather_query": "weather",
        "light_control": "iot_control",
        "music": "music",
        "alarm_reminder": "alarm_reminder",
        "booking": "booking",
        "capability_query": "capabilities",
        "farewell": "exit",
        "info_request": "info_request",
        "calculation": "info_request",
        "definition": "info_request",
        "news_query": "news",
        "joke": "joke",
    }

    def _map_nlp_intent(self, nlp_intent: str) -> str:
        return self._NLP_INTENT_MAP.get(nlp_intent or "", "unknown")

    # ── Duplicate detection ───────────────────────────────────────────────────

    def _track_recent_command(self, command: str) -> bool:
        now = time.time()
        previous = self.context.get("last_command")
        previous_ts = self.context.get("last_command_time", 0.0)
        is_duplicate = bool(command and command == previous and (now - previous_ts) < 2.5)
        self.context["last_command"] = command
        self.context["last_command_time"] = now
        return is_duplicate

    def _remember_turn(self, intent: str, command: str, duplicate: bool) -> None:
        self.context["last_intent"] = intent
        self.context["conversation"].append({
            "command": command,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "duplicate": duplicate,
        })
        if len(self.context["conversation"]) > 12:
            self.context["conversation"].pop(0)

    # ── Intent analysis ───────────────────────────────────────────────────────

    def analyze_intent(self, command: str) -> str:
        cleaned = self._normalize_command(command)
        if not cleaned:
            self.last_nlp_result = None
            return "unknown"

        self.last_nlp_result = process_natural_language(cleaned)
        nlp_intent = self._map_nlp_intent(self.last_nlp_result.get("intent"))
        nlp_confidence = float(self.last_nlp_result.get("confidence", 0.0))

        if nlp_intent != "unknown" and nlp_confidence >= 0.45:
            return nlp_intent

        def has_any(words):
            return any(w in cleaned for w in words)

        if has_any(["bulb", "light", "lamp", "brightness", "dim", "bright", "%", "switch", "turn on", "turn off", "color"]):
            return "iot_control"
        if has_any(["time", "date", "day", "today", "now"]):
            return "time_date"
        if has_any(["weather", "temperature", "forecast", "rain", "sunny", "cloud"]):
            return "weather"
        if has_any(["music", "song", "play", "audio", "track", "volume", "playlist"]):
            return "music"
        # Check more specific alarm sub-intents before the generic one
        if "cancel" in cleaned and ("alarm" in cleaned or "reminder" in cleaned):
            return "cancel_alarm"
        if any(w in cleaned for w in ("list", "show")) and ("alarm" in cleaned or "reminder" in cleaned):
            return "list_alarms"
        if has_any(["scan qr", "qr code", "what do you see", "read screen", "vision", "camera", "look", "describe image"]):
            return "vision"
        if has_any(["alarm", "remind", "reminder", "wake", "schedule"]):
            return "alarm_reminder"
        if has_any(["book", "ticket", "reserve", "reservation", "hotel", "flight", "train"]):
            return "booking"
        if has_any(["bye", "goodbye", "exit", "quit", "shutdown", "close"]):
            return "exit"
        if has_any(["hello", "hi", "hey", "greetings", "vanakkam"]):
            return "greeting"
        if has_any(["thank", "thanks", "nandri"]):
            return "thanks"
        if has_any(["what can you do", "your features", "capabilities"]):
            return "capabilities"
        if has_any(["forget everything", "clear memory", "clear history", "reset conversation"]):
            return "clear_memory"
        if has_any(["news", "headline", "latest update"]):
            return "news"
        if has_any(["document", "pdf", "analyze", "summarize", "extract", "image text"]):
            return "document_intelligence"
        if has_any(["vision", "camera", "see", "look", "what do you see", "read screen", "qr code", "describe image", "scan qr", "ocr"]):
            return "vision"
        if has_any(["who", "what", "why", "how", "tell me", "explain", "info", "information",
                    "define", "meaning of", "what does"]):
            return "info_request"

        if nlp_intent != "unknown" and nlp_confidence >= 0.30:
            return nlp_intent

        return "unknown"

    # ── Response generation ───────────────────────────────────────────────────

    def generate_response(self, intent: str, command: str = None) -> str:
        intent = intent or "unknown"
        cleaned = self._normalize_command(command or "")
        duplicate = self._track_recent_command(cleaned)
        self._remember_turn(intent, cleaned, duplicate)

        if duplicate and self.context.get("last_response"):
            return "I heard that already. If you want, I can keep going with the same request."

        nlp_result = self.last_nlp_result if cleaned else None
        nlp_response = nlp_result.get("response") if nlp_result else None

        handlers = {
            "greeting": lambda: nlp_response or random.choice([
                "Hi. What can I do for you?", "Hello. What do you need?", "Ready when you are.",
            ]),
            "thanks": lambda: nlp_response or random.choice([
                "You are welcome.", "Any time.", "Glad to help.",
            ]),
            "time_date": lambda: self.get_current_time_date(),
            "weather": lambda: self._weather_response(command, nlp_response),
            "music": lambda: nlp_response or random.choice([
                "Sure. Tell me which song, artist, or playlist you want.",
                "Ready for music. Say what you want to play.",
            ]),
            "iot_control": lambda: (
                self.iot.handle_iot_command(command) if self.iot
                else nlp_response or "I can handle device commands once the IoT module is connected."
            ),
            "alarm_reminder": lambda: self.handle_alarm_reminder(command),
            "list_alarms": lambda: self._list_alarms(),
            "cancel_alarm": lambda: self._cancel_alarms(),
            "capabilities": lambda: self._capabilities_response(),
            "clear_memory": lambda: self._clear_memory_response(),
            "news": lambda: get_news_headlines(),
            "document_intelligence": lambda: (
                process_document_command(command) if _DOC_INTEL_AVAILABLE
                else "Document intelligence requires additional packages. Install with: pip install PyPDF2 pytesseract pillow"
            ),
            "vision": lambda: (
                handle_vision_command(command) if _VISION_AVAILABLE
                else "Vision requires additional packages. Install with: pip install opencv-python pillow pytesseract pyzbar"
            ),
            "booking": lambda: nlp_response or "Tell me what you want to book and I will guide you through it.",
            "info_request": lambda: (
                (ai_ask(command or "") if _AI_BRAIN_AVAILABLE else None)
                or self._information_response(command, nlp_response)
            ),
            "joke": lambda: (
                (ai_ask(command or "tell me a joke") if _AI_BRAIN_AVAILABLE else None)
                or self._joke_response()
            ),
            "exit": lambda: nlp_response or random.choice([
                "All right. See you later.", "Closing out for now.", "Talk soon.",
            ]),
        }

        handler = handlers.get(intent)
        if handler:
            response = handler()
        else:
            response = (
                (ai_ask(command or intent) if _AI_BRAIN_AVAILABLE else None)
                or nlp_response
                or "I need a bit more detail before I can act on that."
            )

        self.context["last_response"] = response
        return response

    # ── Response helpers ──────────────────────────────────────────────────────

    def _joke_response(self) -> str:
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
            "Why was the computer cold? It left its Windows open.",
            "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
            "Why do Java developers wear glasses? Because they don't C sharp.",
            "A SQL query walks into a bar, walks up to two tables and asks... Can I join you?",
        ]
        return random.choice(jokes)

    def _weather_response(self, command: str, fallback: str = None) -> str:
        try:
            response = get_weather(command)
            if response:
                return response
        except Exception:
            logger.exception("Weather fetch failed")
        return fallback or "I can help with the weather. Tell me the city if you want a specific forecast."

    def _information_response(self, command: str, fallback: str = None) -> str:
        try:
            response = get_information(command)
            if response:
                return response
        except Exception:
            logger.exception("Information fetch failed")
        return fallback or "Tell me exactly what you want to know, and I will narrow it down."

    def get_current_time_date(self) -> str:
        now = datetime.now()
        return f"It is {now.strftime('%I:%M %p').lstrip('0')} on {now.strftime('%A, %B %d, %Y')}."

    def _capabilities_response(self) -> str:
        return (
            "Here is what I can do:\n"
            "\u2022 \U0001f551 Time & Date \u2014 'what time is it', 'what day is it'\n"
            "\u2022 \U0001f326\ufe0f Weather \u2014 'weather in London', 'temperature in Chennai'\n"
            "\u2022 \u23f0 Reminders \u2014 'remind me in 5 minutes', 'alarm at 7:30 am'\n"
            "\u2022 \U0001f4a1 IoT Control \u2014 'turn on the light', 'dim the lamp'\n"
            "\u2022 \U0001f4ac AI Questions \u2014 'explain quantum computing', 'who is Elon Musk'\n"
            "\u2022 \U0001f3b5 Music \u2014 'play some jazz', 'pause music'\n"
            "\u2022 \U0001f602 Jokes \u2014 'tell me a joke'\n"
            "\u2022 \U0001f4dd Alarms \u2014 'list my alarms', 'cancel all alarms'\n"
            "\u2022 \U0001f4c4 Documents \u2014 'analyze document file.pdf', 'extract text from image.jpg'\n"
            "\u2022 \U0001f441\ufe0f Vision \u2014 'what do you see', 'read screen', 'scan QR code'\n"
            "\u2022 \U0001f9f9 Memory \u2014 'clear conversation history'"
        )

    def _clear_memory_response(self) -> str:
        try:
            ai_clear()
        except Exception:
            pass
        self.context["conversation"] = []
        self.context["last_response"] = None
        self.context["last_command"] = None
        return "Done. I have cleared our conversation history and started fresh."

    def _list_alarms(self) -> str:
        alarms = [a for a in self.memory.get("alarms", []) if a.get("active")]
        if not alarms:
            return "You have no active reminders."
        lines = []
        for a in alarms:
            try:
                dt = datetime.fromisoformat(a["datetime"])
                lines.append(f"  \u2022 {dt.strftime('%I:%M %p').lstrip('0')}: {a.get('message', 'Reminder')}")
            except (ValueError, KeyError):
                pass
        return "Active reminders:\n" + "\n".join(lines) if lines else "No active reminders."

    def _cancel_alarms(self) -> str:
        alarms = self.memory.get("alarms", [])
        active = [a for a in alarms if a.get("active")]
        if not active:
            return "No active alarms to cancel."
        for a in active:
            a["active"] = False
        self._memory_dirty = True
        self._save_memory()
        return f"Cancelled {len(active)} reminder(s)."

    # ── Alarm / reminder ──────────────────────────────────────────────────────

    def handle_alarm_reminder(self, command: str) -> str:
        cleaned = self._normalize_command(command or "")
        words = cleaned.split()

        # ── Relative time: "in N minutes" / "in N hours" ──────────────────────
        rel_m = re.search(r"in\s+(\d+)\s+minute", cleaned)
        rel_h = re.search(r"in\s+(\d+)\s+hour", cleaned)
        rel_s = re.search(r"in\s+(\d+)\s+second", cleaned)
        if rel_m or rel_h or rel_s:
            delta_seconds = 0
            if rel_m:
                delta_seconds += int(rel_m.group(1)) * 60
            if rel_h:
                delta_seconds += int(rel_h.group(1)) * 3600
            if rel_s:
                delta_seconds += int(rel_s.group(1))
            alarm_time = datetime.now() + timedelta(seconds=delta_seconds)
            # Extract message: everything after "remind me (to)?"
            msg_match = re.search(r"remind(?:\s+me)?(?:\s+to)?\s+(.+?)(?:\s+in\s+\d+|$)", cleaned)
            message = msg_match.group(1).strip() if msg_match else "Reminder"
            if not message or message in ("me", "to", ""):
                message = "Reminder"
            return self.set_alarm_reminder_abs(alarm_time, message)

        # ── Absolute time: "at 7:30", "for 7:30 pm" ──────────────────────────
        time_found = None
        for i, word in enumerate(words):
            if ":" in word and len(word) <= 8:
                time_found = word
                break
            if word in ("at", "for") and i + 1 < len(words):
                nw = words[i + 1]
                if ":" in nw or nw.isdigit():
                    time_found = nw
                    break

        if not time_found:
            return "Tell me when \u2014 for example: 'remind me in 5 minutes' or 'alarm at 7:30 pm'."

        message = "Reminder"
        if time_found in words:
            idx = words.index(time_found)
            tail = " ".join(words[idx + 1:]).strip()
            if tail:
                message = tail

        return self.set_alarm_reminder(time_found, message)

    def set_alarm_reminder(self, time_str: str, message: str = "Alarm") -> str:
        try:
            time_str = time_str.lower().replace(".", "")
            if time_str.endswith(("am", "pm")) and ":" not in time_str:
                time_str = time_str[:-2] + ":00" + time_str[-2:]

            if time_str.endswith(("am", "pm")):
                alarm_time = datetime.strptime(time_str, "%I:%M%p")
                hour, minute = alarm_time.hour, alarm_time.minute
            else:
                hour, minute = map(int, time_str.split(":"))

            alarm_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            if alarm_time < datetime.now():
                alarm_time += timedelta(days=1)

            return self.set_alarm_reminder_abs(alarm_time, message)
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to set alarm: %s", e)
            return "I could not set that reminder. Use a time like 07:30 or 7:30 pm."

    def set_alarm_reminder_abs(self, alarm_time: datetime, message: str = "Alarm") -> str:
        """Save an alarm given an absolute datetime object."""
        self.memory.setdefault("alarms", []).append({
            "time": alarm_time.strftime("%I:%M %p"),
            "message": message,
            "datetime": alarm_time.isoformat(),
            "active": True,
        })
        self._memory_dirty = True
        self._save_memory()
        return f"Reminder set for {alarm_time.strftime('%I:%M %p').lstrip('0')}: {message}"

    # ── Memory persistence ────────────────────────────────────────────────────

    def _load_memory(self) -> dict:
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load memory file: %s", e)
        return {}

    def _save_memory(self) -> None:
        if not self._memory_dirty:
            return
        try:
            with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2)
            self._memory_dirty = False
        except OSError as e:
            logger.error("Could not save memory file: %s", e)

    # ── Alarm background thread ───────────────────────────────────────────────

    def start_alarm_thread(self) -> None:
        if self._alarm_thread_running:
            return
        self._alarm_thread_running = True
        threading.Thread(target=self._alarm_loop, daemon=True).start()

    def stop_alarm_thread(self) -> None:
        self._alarm_thread_running = False

    def _alarm_loop(self) -> None:
        while self._alarm_thread_running:
            try:
                self._check_due_alarms()
            except Exception:
                logger.exception("Alarm loop error")
            time.sleep(10)

    def _check_due_alarms(self) -> None:
        alarms = self.memory.get("alarms", [])
        if not alarms:
            return
        now = datetime.now()
        fired = False
        for alarm in alarms:
            if not alarm.get("active", False):
                continue
            try:
                alarm_dt = datetime.fromisoformat(alarm["datetime"])
                if now >= alarm_dt:
                    msg = alarm.get("message", "Reminder")
                    logger.info("ALARM: %s", msg)
                    self.tts.speak(f"Reminder: {msg}")
                    alarm["active"] = False
                    fired = True
            except (ValueError, KeyError) as e:
                logger.warning("Bad alarm entry: %s", e)
                alarm["active"] = False
        if fired:
            self._memory_dirty = True
            self._save_memory()
