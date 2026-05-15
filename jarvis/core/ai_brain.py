"""
JARVIS AI Brain — Hybrid Groq + Gemini with tool calling.
Architecture:
  1. Rule-based fast path  (free, instant)
  2. Fuzzy cache           (free, instant)
  3. Groq LLM + tools      (primary,  ~500ms)
  4. Gemini LLM + tools    (fallback, ~800ms)
  5. Offline reply         (always works)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from jarvis.core.cache import get as cache_get, put as cache_put
from jarvis.core.rate_guard import can_call, record_call, get_mode, status_report
from jarvis.services.data_collector import get_weather, get_information

logger = logging.getLogger(__name__)

GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODE    = os.getenv("JARVIS_AI_MODE", "hybrid")

# ── Optional LLM libraries ────────────────────────────────────────────────────
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
    try:
        import google.generativeai as _genai  # legacy fallback
        _GEMINI_LIB = True
    except ImportError:
        _genai = None
        _GEMINI_LIB = False

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are JARVIS, a smart, concise AI assistant. "
    "Be direct. No filler like 'Certainly!' or 'Of course!'. "
    "Keep answers SHORT — 1-3 sentences unless asked to elaborate. "
    "Use tools when relevant. Never mention Groq/Gemini. You are JARVIS."
)
_STRICT_ADDENDUM = " Answer in 1-2 sentences maximum."

# ── Tool definitions (Groq format) ────────────────────────────────────────────
_TOOLS_GROQ = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]},
    }},
    {"type": "function", "function": {
        "name": "get_information",
        "description": "Get factual information or Wikipedia summary",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "get_time",
        "description": "Get the current date and time",
        "parameters": {"type": "object", "properties": {}},
    }},
]


def _execute_tool(name: str, args: dict) -> str:
    try:
        if name == "get_weather":
            return get_weather(f"weather in {args.get('location', '')}")
        if name == "get_information":
            return get_information(args.get("query", ""))
        if name == "get_time":
            now = datetime.now()
            return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
        return f"Tool '{name}' not implemented."
    except Exception as e:
        logger.warning("Tool '%s' error: %s", name, e)
        return f"Tool error: {e}"


# ── Conversation memory (persisted across restarts) ──────────────────────────
_HISTORY_FILE = str(Path(__file__).resolve().parent.parent.parent / "data" / "conversation_history.json")


class _ConversationMemory:
    MAX_TURNS = 8

    def __init__(self):
        self._history: list[dict] = self._load()

    def add_user(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._trim()
        self._save()

    def add_assistant(self, text: str) -> None:
        self._history.append({"role": "assistant", "content": text})
        self._trim()
        self._save()

    def _trim(self) -> None:
        max_msgs = self.MAX_TURNS * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

    def get_messages(self, system: str) -> list[dict]:
        return [{"role": "system", "content": system}] + self._history

    def clear(self) -> None:
        self._history.clear()
        self._save()

    def _load(self) -> list[dict]:
        if os.path.exists(_HISTORY_FILE):
            try:
                with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data[-(self.MAX_TURNS * 2):]
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load conversation history: %s", e)
        return []

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
            with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history, f)
        except OSError as e:
            logger.warning("Could not save conversation history: %s", e)


_MEMORY = _ConversationMemory()

# ── Fast rule-based path ──────────────────────────────────────────────────────
_SIMPLE_RULES = {
    ("hello", "hi", "hey", "vanakkam", "good morning", "good evening"):
        lambda: f"Hello! It's {datetime.now().strftime('%I:%M %p')}. What do you need?",
    ("what time", "current time", "time now"):
        lambda: f"It's {datetime.now().strftime('%I:%M %p')} on {datetime.now().strftime('%A')}.",
    ("what date", "today's date", "what day"):
        lambda: f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.",
    ("thank you", "thanks", "nandri"):
        lambda: "You're welcome.",
    ("bye", "goodbye", "exit"):
        lambda: "Goodbye. I'll be here when you need me.",
    ("who are you", "what are you", "your name"):
        lambda: "I'm JARVIS — your AI assistant.",
}


def _try_rule(text: str) -> Optional[str]:
    t = text.lower().strip()
    for triggers, handler in _SIMPLE_RULES.items():
        if any(t.startswith(kw) or kw in t for kw in triggers):
            return handler()
    return None


# ── Groq client ───────────────────────────────────────────────────────────────
_groq_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None and _GROQ_LIB and GROQ_KEY:
        _groq_client = _Groq(api_key=GROQ_KEY)
    return _groq_client


def _call_groq(messages: list[dict], strict: bool = False) -> Optional[str]:
    client = _get_groq()
    if not client:
        return None

    system = _SYSTEM_PROMPT + (_STRICT_ADDENDUM if strict else "")
    msgs = [m if m["role"] != "system" else {"role": "system", "content": system} for m in messages]
    max_tokens = 120 if strict else 400

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=msgs,
            tools=_TOOLS_GROQ,
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=0.7,
        )
        record_call("groq")
        msg = resp.choices[0].message

        if msg.tool_calls:
            tool_results = []
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = _execute_tool(tc.function.name, args)
                tool_results.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            resp2 = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=msgs + [msg] + tool_results,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            record_call("groq")
            return resp2.choices[0].message.content or ""

        return msg.content or ""

    except Exception as exc:
        err = str(exc)
        if "rate_limit" in err.lower() or "429" in err:
            return None
        logger.warning("Groq error: %s", exc)
        return None


# ── Gemini client ─────────────────────────────────────────────────────────────
_gemini_model = None


def _get_gemini():
    global _gemini_model
    if _gemini_model is None and _GEMINI_LIB and GEMINI_KEY:
        try:
            # New google.genai SDK
            client = _genai.Client(api_key=GEMINI_KEY)
            _gemini_model = client
        except AttributeError:
            # Legacy google.generativeai SDK
            _genai.configure(api_key=GEMINI_KEY)
            _gemini_model = _genai.GenerativeModel(
                model_name="gemini-1.5-flash-latest",
                system_instruction=_SYSTEM_PROMPT,
            )
    return _gemini_model


def _call_gemini(history: list[dict], user_text: str, strict: bool = False) -> Optional[str]:
    model = _get_gemini()
    if not model:
        return None

    prompt = user_text + (" Answer in 1-2 sentences only." if strict else "")
    try:
        # New google.genai SDK (Client-based)
        if hasattr(model, "models"):
            response = model.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
            )
            record_call("gemini")
            return response.text

        # Legacy google.generativeai SDK
        gemini_history = []
        for m in history:
            if m["role"] == "system":
                continue
            role = "model" if m["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [m["content"]]})
        if gemini_history and gemini_history[-1]["role"] == "user":
            gemini_history = gemini_history[:-1]
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(prompt)
        record_call("gemini")
        return response.text

    except Exception as exc:
        err = str(exc)
        if "429" in err or "quota" in err.lower():
            return None
        logger.warning("Gemini error: %s", exc)
        return None


# ── Offline fallback ──────────────────────────────────────────────────────────
_OFFLINE_RESPONSES = [
    "I'm currently offline. I can still help with time, alarms, and device control.",
    "No internet connection. Basic commands still work — try asking the time or setting an alarm.",
    "I'm in offline mode. For AI responses I need a connection.",
]
_offline_idx = 0


def _offline_reply(query: str) -> str:
    global _offline_idx
    q = query.lower()
    if any(w in q for w in ("time", "clock")):
        return _execute_tool("get_time", {})
    resp = _OFFLINE_RESPONSES[_offline_idx % len(_OFFLINE_RESPONSES)]
    _offline_idx += 1
    return resp


# ── Public API ────────────────────────────────────────────────────────────────

def ask(user_input: str, personality: str = "default") -> str:
    text = (user_input or "").strip()
    if not text:
        return "I didn't catch that."

    rule_result = _try_rule(text)
    if rule_result:
        _MEMORY.add_user(text)
        _MEMORY.add_assistant(rule_result)
        return rule_result

    cached = cache_get(text)
    if cached:
        _MEMORY.add_user(text)
        _MEMORY.add_assistant(cached)
        return cached

    _MEMORY.add_user(text)
    messages = _MEMORY.get_messages(_SYSTEM_PROMPT)

    groq_mode = get_mode("groq")
    strict = personality == "strict" or groq_mode in ("strict", "warn")
    response: Optional[str] = None

    if AI_MODE in ("hybrid", "groq") and GROQ_KEY and _GROQ_LIB and groq_mode != "blocked":
        allowed, reason = can_call("groq")
        if allowed:
            response = _call_groq(messages, strict=strict)
        else:
            logger.info("Groq skipped: %s", reason)

    if response is None and AI_MODE in ("hybrid", "gemini") and GEMINI_KEY and _GEMINI_LIB:
        gemini_mode = get_mode("gemini")
        if gemini_mode != "blocked":
            allowed, reason = can_call("gemini")
            if allowed:
                response = _call_gemini(messages, text, strict=gemini_mode in ("strict", "warn"))
            else:
                logger.info("Gemini skipped: %s", reason)

    if response is None:
        response = _offline_reply(text)

    response = (response or "").strip()
    if response:
        _MEMORY.add_assistant(response)
        if len(response) > 20:
            cache_put(text, response)

    return response


def clear_memory() -> None:
    _MEMORY.clear()


def get_status() -> dict:
    return {
        "ai_mode": AI_MODE,
        "groq_available": bool(_GROQ_LIB and GROQ_KEY),
        "gemini_available": bool(_GEMINI_LIB and GEMINI_KEY),
        "api_usage": status_report(),
    }
