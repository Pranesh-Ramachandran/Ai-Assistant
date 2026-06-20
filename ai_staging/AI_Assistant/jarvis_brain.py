"""
Core JARVIS Brain
Intent detection and response routing for core modules.
"""

import json
import os
import random
import re
import threading
import time
from datetime import datetime, timedelta

from data_collector import get_information, get_weather

# ── AI Brain (Groq + Gemini hybrid) ──────────────────────────────────────────
try:
    from jarvis_ai_brain import ask as ai_ask, clear_memory as ai_clear, get_status as ai_status
    _AI_BRAIN_AVAILABLE = True
except Exception as _e:
    _AI_BRAIN_AVAILABLE = False
    print(f"[JARVIS] AI brain not loaded: {_e}")
    def ai_ask(text, **kw): return None
    def ai_clear(): pass
    def ai_status(): return {}
from jarvis_nlp import process_natural_language

try:
    from jarvis_neural import JarvisNeuralBrain
except Exception:
    JarvisNeuralBrain = None

try:
    from iot_assistant import IoTAssistant
except Exception:
    IoTAssistant = None

try:
    from game_module import GameModule
except Exception:
    GameModule = None

try:
    from enhanced_tts import speak as default_speak
except Exception:
    def default_speak(text):
        print(f"TTS: {text}")

try:
    from stt import listen as default_listen
except Exception:
    def default_listen():
        return input("Voice: ").lower().strip()


class _SimpleTTS:
    def speak(self, text):
        default_speak(text)


class JarvisBrain:
    def __init__(self, tts_engine=None, voice_listener=None):
        self.context = {
            "last_intent": None,
            "conversation": [],
            "last_response": None,
            "last_command": None,
            "last_command_time": 0.0,
        }
        self.memory_file = "assistant_memory.json"
        self.memory = self._load_memory()
        self.last_nlp_result = None

        self.neural = JarvisNeuralBrain() if JarvisNeuralBrain else None
        self.iot = IoTAssistant() if IoTAssistant else None

        if tts_engine is None:
            self.tts = _SimpleTTS()
        elif hasattr(tts_engine, "speak"):
            self.tts = tts_engine
        elif callable(tts_engine):
            class _FuncTTS:
                def speak(self, text):
                    tts_engine(text)
            self.tts = _FuncTTS()
        else:
            self.tts = _SimpleTTS()

        self.listen = voice_listener if voice_listener else default_listen

        self.game = None
        if GameModule:
            try:
                self.game = GameModule(self.tts, self.listen)
            except Exception:
                self.game = None

        # Start background alarm thread so set alarms actually fire
        self.start_alarm_thread()

    def _normalize_command(self, command: str) -> str:
        if not command:
            return ""
        normalized = command.lower().strip()
        normalized = re.sub(r"[^\w\s:]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _map_nlp_intent(self, nlp_intent: str) -> str:
        mapping = {
            "greeting": "greeting",
            "thanks": "thanks",
            "time_query": "time_date",
            "weather_query": "weather",
            "light_control": "iot_control",
            "music": "music",
            "alarm_reminder": "alarm_reminder",
            "booking": "booking",
            "capability_query": "info_request",
            "farewell": "exit",
            "info_request": "info_request",
            "calculation": "info_request",
            "definition": "info_request",
            "news_query": "info_request",
            "joke": "joke",
        }
        return mapping.get(nlp_intent or "", "unknown")

    def _track_recent_command(self, command: str) -> bool:
        now = time.time()
        previous = self.context.get("last_command")
        previous_ts = self.context.get("last_command_time", 0.0)
        is_duplicate = bool(command and command == previous and (now - previous_ts) < 2.5)
        self.context["last_command"] = command
        self.context["last_command_time"] = now
        return is_duplicate

    def _remember_turn(self, intent: str, command: str, duplicate: bool):
        self.context["last_intent"] = intent
        self.context["conversation"].append({
            "command": command,
            "intent": intent,
            "timestamp": str(datetime.now()),
            "duplicate": duplicate,
        })
        if len(self.context["conversation"]) > 12:
            self.context["conversation"].pop(0)

    def analyze_intent(self, command: str) -> str:
        cleaned = self._normalize_command(command)
        if not cleaned:
            self.last_nlp_result = None
            return "unknown"

        self.last_nlp_result = process_natural_language(cleaned)
        nlp_intent = self._map_nlp_intent(self.last_nlp_result.get("intent"))
        nlp_confidence = float(self.last_nlp_result.get("confidence", 0.0))

        # Lowered threshold: 0.45 catches more valid intents
        if nlp_intent != "unknown" and nlp_confidence >= 0.45:
            return nlp_intent

        def has_any(words):
            return any(word in cleaned for word in words)

        if has_any(["bulb", "light", "lamp", "brightness", "dim", "bright", "%", "switch", "turn on", "turn off", "color"]):
            return "iot_control"
        if has_any(["time", "date", "day", "today", "now"]):
            return "time_date"
        if has_any(["weather", "temperature", "forecast", "rain", "sunny", "cloud"]):
            return "weather"
        if has_any(["music", "song", "play", "audio", "track", "volume", "playlist"]):
            return "music"
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
        if has_any(["calculate", "compute", "what is", "how much is", "solve",
                    "+", "-", "*", "/", "percent", "percentage"]):
            # Only route to info if it looks mathy or explicit
            if any(c.isdigit() for c in cleaned):
                return "info_request"
        if has_any(["who", "what", "why", "how", "tell me", "explain", "info", "information", "help",
                    "define", "meaning of", "what does"]):
            return "info_request"

        if self.neural:
            intent, confidence = self.neural.predict_intent(cleaned)
            if confidence >= 0.25:
                return intent

        if nlp_intent != "unknown" and nlp_confidence >= 0.30:
            return nlp_intent

        return "unknown"

    def generate_response(self, intent: str, command: str = None) -> str:
        intent = intent or "unknown"
        cleaned = self._normalize_command(command or "")
        duplicate = self._track_recent_command(cleaned)
        self._remember_turn(intent, cleaned, duplicate)

        if duplicate and self.context.get("last_response"):
            return "I heard that already. If you want, I can keep going with the same request."

        nlp_result = self.last_nlp_result if cleaned else None
        nlp_response = nlp_result.get("response") if nlp_result else None

        if intent == "greeting":
            response = nlp_response or random.choice([
                "Hi. What can I do for you?",
                "Hello. What do you need?",
                "Ready when you are.",
            ])
        elif intent == "thanks":
            response = nlp_response or random.choice([
                "You are welcome.",
                "Any time.",
                "Glad to help.",
            ])
        elif intent == "time_date":
            response = self.get_current_time_date()
        elif intent == "weather":
            response = self._weather_response(command, nlp_response)
        elif intent == "music":
            response = nlp_response or random.choice([
                "Sure. Tell me which song, artist, or playlist you want.",
                "Ready for music. Say what you want to play.",
            ])
        elif intent == "iot_control":
            if self.iot:
                response = self.iot.handle_iot_command(command)
            else:
                response = nlp_response or "I can handle device commands once the IoT module is connected."
        elif intent == "alarm_reminder":
            response = self.handle_alarm_reminder(command)
        elif intent == "booking":
            response = nlp_response or "Tell me what you want to book and I will guide you through it."
        elif intent == "info_request":
            # Route through AI brain (Groq → Gemini → Wikipedia → offline)
            ai_response = ai_ask(command or "") if _AI_BRAIN_AVAILABLE else None
            response = ai_response or self._information_response(command, nlp_response)
        elif intent == "joke":
            # Let the AI tell a better joke if available
            ai_response = ai_ask(command or "tell me a joke") if _AI_BRAIN_AVAILABLE else None
            response = ai_response or self._joke_response()
        elif intent == "exit":
            response = nlp_response or random.choice([
                "All right. See you later.",
                "Closing out for now.",
                "Talk soon.",
            ])
        else:
            # ── All other intents → AI brain (Groq → Gemini → offline) ──
            ai_response = ai_ask(command or intent) if _AI_BRAIN_AVAILABLE else None
            response = ai_response or nlp_response or "I need a bit more detail before I can act on that."

        self.context["last_response"] = response
        return response

    def _joke_response(self) -> str:
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
            "Why was the computer cold? It left its Windows open.",
            "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
            "Why do Java developers wear glasses? Because they don't C sharp.",
            "A SQL query walks into a bar, walks up to two tables and asks... Can I join you?",
            "Why did the function break up with the loop? It kept going around in circles.",
        ]
        return random.choice(jokes)

    def _weather_response(self, command: str, fallback: str = None) -> str:
        try:
            response = get_weather(command)
            if response:
                return response
        except Exception:
            pass
        return fallback or "I can help with the weather. Tell me the city if you want a specific forecast."

    def _information_response(self, command: str, fallback: str = None) -> str:
        try:
            response = get_information(command)
            if response:
                return response
        except Exception:
            pass
        return fallback or "Tell me exactly what you want to know, and I will narrow it down."

    def get_current_time_date(self) -> str:
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        return f"It is {time_str} on {date_str}."

    def handle_alarm_reminder(self, command: str) -> str:
        cleaned = self._normalize_command(command or "")
        words = cleaned.split()
        time_found = None

        for i, word in enumerate(words):
            if ":" in word and len(word) <= 8:
                time_found = word
                break
            if word in ["at", "for"] and i + 1 < len(words):
                next_word = words[i + 1]
                if ":" in next_word or next_word.isdigit():
                    time_found = next_word
                    break

        if not time_found:
            return "Tell me the reminder time in HH:MM format so I can save it."

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
                hour = alarm_time.hour
                minute = alarm_time.minute
            else:
                hour, minute = map(int, time_str.split(":"))

            alarm_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            if alarm_time < datetime.now():
                alarm_time += timedelta(days=1)

            self.memory.setdefault("alarms", []).append({
                "time": time_str,
                "message": message,
                "datetime": str(alarm_time),
                "active": True,
            })
            self._save_memory()

            return f"Reminder set for {alarm_time.strftime('%I:%M %p').lstrip('0')}: {message}"
        except Exception:
            return "I could not set that reminder. Use a time like 07:30 or 7:30 pm."

    def _load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2)
        except Exception:
            pass

    # ── Alarm background thread ────────────────────────────────────────────
    def start_alarm_thread(self):
        """Start a background daemon thread that polls for due alarms."""
        if getattr(self, "_alarm_thread_running", False):
            return
        self._alarm_thread_running = True
        t = threading.Thread(target=self._alarm_loop, daemon=True)
        t.start()

    def _alarm_loop(self):
        """Poll every 10 seconds and fire any due alarms."""
        while self._alarm_thread_running:
            try:
                self._check_due_alarms()
            except Exception:
                pass
            time.sleep(10)

    def _check_due_alarms(self):
        """Check memory for alarms that are due and fire them."""
        alarms = self.memory.get("alarms", [])
        if not alarms:
            return
        now = datetime.now()
        fired = []
        for alarm in alarms:
            if not alarm.get("active", False):
                continue
            try:
                alarm_dt = datetime.fromisoformat(alarm["datetime"])
                if now >= alarm_dt:
                    msg = alarm.get("message", "Reminder")
                    print(f"🔔 ALARM: {msg}")
                    self.tts.speak(f"Reminder: {msg}")
                    alarm["active"] = False
                    fired.append(alarm)
            except Exception:
                alarm["active"] = False
        if fired:
            self._save_memory()

    def stop_alarm_thread(self):
        """Stop the alarm background thread."""
        self._alarm_thread_running = False


if __name__ == "__main__":
    brain = JarvisBrain()
    tests = [
        "hello jarvis",
        "what time is it",
        "turn on the bulb",
        "set alarm for 7:30 wake up",
        "play some music",
        "book tickets",
        "what is python",
    ]
    for cmd in tests:
        intent = brain.analyze_intent(cmd)
        response = brain.generate_response(intent, cmd)
        print(f"{cmd} -> {intent} -> {response}")
