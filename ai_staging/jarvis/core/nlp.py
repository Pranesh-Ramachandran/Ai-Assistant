"""
JARVIS NLP Engine — spoken-language normalization and intent classification.
"""

import logging
import random
import re
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class JarvisNLP:
    def __init__(self):
        self.context: dict = {}
        self._build_patterns()

    def _build_patterns(self) -> None:
        self.patterns = {
            "greeting":        [r"\b(hello|hi|hey|vanakkam|good morning|good evening|good afternoon|howdy)\b"],
            "thanks":          [r"\b(thank you|thanks|nandri|appreciate it|cheers)\b"],
            "time_query":      [r"\b(what(?:'s| is)? the time|current time|time now|time please|time is it)\b"],
            "weather_query":   [r"\b(weather|temperature|forecast|rain|raining|sunny|climate|humidity|snow|wind)\b"],
            "light_control":   [
                r"\b(turn|switch|set|make)\b.*\b(light|lamp|bulb|fan|ac)\b",
                r"\b(light|lamp|bulb|fan|ac)\b.*\b(on|off|bright|dim|red|blue|green|white)\b",
            ],
            "music":           [
                r"\b(play|pause|resume|stop|skip|next|previous)\b.*\b(music|song|audio|track|playlist|album)\b",
                r"\b(music|song|playlist|radio)\b",
                r"\b(volume up|volume down|louder|quieter|mute)\b",
            ],
            "alarm_reminder":  [r"\b(alarm|remind|reminder|wake me|schedule|set a reminder|notify me)\b"],
            "booking":         [r"\b(book|booking|reserve|reservation|ticket|hotel|flight|train|bus|cab)\b"],
            "calculation":     [r"\b(calculate|compute|what is|how much is|solve|math|equals|plus|minus|times|divided by|percent)\b", r"\d+\s*[+\-*/]\s*\d+"],
            "news_query":      [r"\b(news|headlines|latest|breaking|current events|today's news|what happened|update)\b"],
            "definition":      [r"\b(define|definition|meaning of|what does .+ mean|what is the meaning|dictionary)\b"],
            "joke":            [r"\b(joke|funny|make me laugh|tell me a joke|humor|humour|prank)\b"],
            "capability_query":[r"\b(what can you do|help me with|your features|capabilities|what do you know|how can you help)\b"],
            "farewell":        [r"\b(bye|goodbye|see you|quit|exit|shutdown|close|good night|cya|take care)\b"],
            "info_request":    [r"\b(who is|who are|what is|what are|where is|when did|how does|how do|tell me about|explain|describe)\b"],
        }

        self.intent_keywords: Dict[str, set] = {
            "greeting":        {"hello", "hi", "hey", "vanakkam", "howdy"},
            "thanks":          {"thanks", "thank", "nandri", "appreciate", "cheers"},
            "time_query":      {"time", "clock", "now", "date", "day", "hour", "minute"},
            "weather_query":   {"weather", "temperature", "forecast", "rain", "sunny", "climate", "humid", "snow", "wind"},
            "light_control":   {"light", "lamp", "bulb", "switch", "turn", "bright", "dim", "red", "blue", "green", "white"},
            "music":           {"music", "song", "audio", "track", "playlist", "volume", "play", "pause", "skip", "next", "radio", "mute"},
            "alarm_reminder":  {"alarm", "remind", "reminder", "schedule", "wake", "notify"},
            "booking":         {"book", "booking", "ticket", "reserve", "reservation", "hotel", "flight", "train", "bus", "cab"},
            "calculation":     {"calculate", "compute", "math", "plus", "minus", "times", "divide", "percent", "sum", "total"},
            "news_query":      {"news", "headlines", "latest", "breaking", "update", "current"},
            "definition":      {"define", "definition", "meaning", "dictionary"},
            "joke":            {"joke", "funny", "laugh", "humor", "prank"},
            "capability_query":{"help", "feature", "features", "capabilities", "can", "able"},
            "farewell":        {"bye", "goodbye", "exit", "quit", "shutdown", "close", "night"},
            "info_request":    {"who", "what", "where", "when", "why", "how", "which", "tell", "explain", "describe", "about", "information"},
        }

        self._stop_words = {
            "the", "is", "at", "which", "on", "a", "an", "and", "or", "but",
            "in", "with", "to", "for", "of", "as", "by", "that", "this",
            "please", "jarvis", "can", "you", "could", "would",
        }

        self._filler_phrases = (
            "hey jarvis", "okay jarvis", "ok jarvis", "jarvis",
            "can you", "could you", "would you", "please",
            "i want you to", "i need you to",
        )

        self._entity_patterns = {
            "time":   r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
            "date":   r"\b(today|tomorrow|yesterday|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
            "device": r"\b(light|fan|ac|tv|bulb|lamp)\b",
            "color":  r"\b(red|blue|green|white|yellow|purple|orange|pink)\b",
        }

        self._location_re = re.compile(
            r"\b(?:in|at|for|near)\s+([a-zA-Z][a-zA-Z\s]{1,30})\b", re.IGNORECASE
        )

    # ── Text preprocessing ────────────────────────────────────────────────────

    def preprocess(self, text: str) -> str:
        if not text:
            return ""
        clean = text.lower().strip()
        for src, dst in (("what's", "what is"), ("how's", "how is"), ("can't", "cannot"), ("it's", "it is")):
            clean = clean.replace(src, dst)
        clean = re.sub(r"[^\w\s:\+\-\*/\(\)%\=\.]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        for phrase in self._filler_phrases:
            if clean.startswith(phrase + " "):
                clean = clean[len(phrase):].strip()
        # Deduplicate consecutive words
        words, prev = [], None
        for w in clean.split():
            if w != prev:
                words.append(w)
            prev = w
        return " ".join(words)

    def extract_keywords(self, text: str) -> List[str]:
        return [w for w in re.findall(r"\b\w+\b", text.lower())
                if w not in self._stop_words and len(w) > 2]

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {}
        for etype, pattern in self._entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[etype] = [m if isinstance(m, str) else m[0] for m in matches]
        locs = [m.strip() for m in self._location_re.findall(text)]
        if locs:
            entities["location"] = locs
        return entities

    # ── Intent classification ─────────────────────────────────────────────────

    def classify_intent(self, text: str) -> Tuple[str, float]:
        clean = self.preprocess(text)
        keywords = set(self.extract_keywords(clean))
        best_intent, best_score = "unknown", 0.0
        scores: Dict[str, float] = {}

        for intent, patterns in self.patterns.items():
            regex_hits = sum(1 for p in patterns if re.search(p, clean, re.IGNORECASE))
            kw_hits = len(self.intent_keywords.get(intent, set()) & keywords)
            total_kw = max(1, len(self.intent_keywords.get(intent, ())))
            score = min(1.0, min(1.0, regex_hits * 0.65) + min(0.35, kw_hits / total_kw))
            scores[intent] = score
            if score > best_score:
                best_score, best_intent = score, intent

        # High-priority intents beat generic info_request
        HIGH_PRIORITY = ("weather_query", "time_query", "calculation", "light_control",
                         "music", "alarm_reminder", "booking", "farewell", "greeting",
                         "thanks", "joke", "definition", "news_query")
        if best_intent == "info_request":
            for hp in HIGH_PRIORITY:
                if scores.get(hp, 0) >= 0.30:
                    best_intent, best_score = hp, max(best_score, scores[hp])
                    break

        if re.search(r"\d+\s*[+\-*/]\s*\d+", clean):
            best_intent, best_score = "calculation", max(best_score, 0.80)

        if best_score < 0.35 and clean.endswith("?"):
            best_intent, best_score = "info_request", 0.42
        elif best_score < 0.3 and any(w in keywords for w in {"what", "who", "why", "how", "when", "where", "explain", "tell"}):
            best_intent, best_score = "info_request", 0.45

        # Boost calculation confidence for unambiguous math expressions
        if re.search(r"\d+\s*[+\-*/]\s*\d+", clean):
            best_intent, best_score = "calculation", max(best_score, 0.85)

        return best_intent, round(best_score, 2)

    # ── Context-aware response ────────────────────────────────────────────────

    def get_response(self, intent: str, entities: Dict, text: str) -> str:
        self.context = {
            "last_intent": intent,
            "last_entities": entities,
            "last_text": text,
            "timestamp": datetime.now().isoformat(),
        }
        now = datetime.now()

        if intent == "time_query":
            return f"It is {now.strftime('%I:%M %p').lstrip('0')} right now."
        if intent == "weather_query":
            location = (entities.get("location") or ["your area"])[0]
            return f"I can check the weather for {location}."
        if intent == "light_control":
            device = (entities.get("device") or ["lights"])[0]
            color = (entities.get("color") or [None])[0]
            if "off" in text:
                return f"Okay, turning the {device} off."
            if color:
                return f"Okay, setting the {device} to {color}."
            return f"Okay, adjusting the {device}."
        if intent == "music":
            return random.choice(["Sure, I can help with music. Tell me what you want to play.",
                                   "Ready for music. Name a song, artist, or playlist."])
        if intent == "alarm_reminder":
            return "Sure, tell me the time and what you want me to remember."
        if intent == "booking":
            return "I can help with that booking. Tell me what you want to book."
        if intent == "greeting":
            return random.choice(["Hi. What can I do for you?", "Hello. I am here when you are ready."])
        if intent == "thanks":
            return random.choice(["You are welcome.", "Any time.", "Glad to help."])
        if intent == "farewell":
            return random.choice(["All right. Talk soon.", "Okay. See you later."])
        if intent == "capability_query":
            return "I can help with time, weather, reminders, device control, and quick questions."

        keywords = self.extract_keywords(text)
        if keywords:
            return f"I caught {', '.join(keywords[:3])}. Tell me a bit more so I can act on it."
        return "I did not catch the goal yet. Rephrase it once more."

    # ── Full pipeline ─────────────────────────────────────────────────────────

    def process(self, text: str) -> Dict:
        if not text:
            return {"intent": "unknown", "confidence": 0.0, "entities": {},
                    "sentiment": "neutral", "keywords": [], "response": "I did not hear anything clearly."}

        clean = self.preprocess(text)
        intent, confidence = self.classify_intent(clean)
        entities = self.extract_entities(clean)
        keywords = self.extract_keywords(clean)
        response = self.get_response(intent, entities, clean)

        return {
            "original_text": text,
            "clean_text": clean,
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "keywords": keywords,
            "response": response,
            "context": self.context,
        }


# Module-level singleton
_nlp = JarvisNLP()


def process_natural_language(text: str) -> Dict:
    return _nlp.process(text)


__all__ = ["JarvisNLP", "process_natural_language"]
