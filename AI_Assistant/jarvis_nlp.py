"""
JARVIS NLP Engine - spoken-language normalization and intent shaping.
"""

import random
import re
from datetime import datetime
from typing import Dict, List, Tuple


class JarvisNLP:
    def __init__(self):
        self.entities = {}
        self.context = {}
        self.load_nlp_data()

    def load_nlp_data(self):
        """Load pattern and keyword data used for light-weight NLP."""
        self.patterns = {
            "greeting": [
                r"\b(hello|hi|hey|vanakkam|good morning|good evening|good afternoon|howdy)\b",
            ],
            "thanks": [
                r"\b(thank you|thanks|nandri|appreciate it|cheers|well done)\b",
            ],
            "time_query": [
                r"\b(what(?:'s| is)? the time|current time|time now|time please|mani enna|neram sollu|time is it)\b",
            ],
            "weather_query": [
                r"\b(weather|temperature|forecast|rain|raining|sunny|climate|vaanilai|kaalam|humidity|snow|wind)\b",
            ],
            "light_control": [
                r"\b(turn|switch|set|make)\b.*\b(light|lamp|bulb|vilakku|fan|ac)\b",
                r"\b(light|lamp|bulb|vilakku|fan|ac)\b.*\b(on|off|bright|dim|red|blue|green|white)\b",
            ],
            "music": [
                r"\b(play|pause|resume|stop|skip|next|previous)\b.*\b(music|song|audio|track|playlist|album)\b",
                r"\b(music|song|playlist|radio)\b",
                r"\b(volume up|volume down|louder|quieter|mute)\b",
            ],
            "alarm_reminder": [
                r"\b(alarm|remind|reminder|wake me|schedule|set a reminder|notify me)\b",
            ],
            "booking": [
                r"\b(book|booking|reserve|reservation|ticket|hotel|flight|train|bus|cab|uber)\b",
            ],
            "calculation": [
                r"\b(calculate|compute|what is|how much is|solve|math|equals|plus|minus|times|divided by|percent)\b",
                r"\d+\s*[+\-*/]\s*\d+",  # numeric expressions like "12 + 5"
            ],
            "news_query": [
                r"\b(news|headlines|latest|breaking|current events|today's news|what happened|update)\b",
            ],
            "definition": [
                r"\b(define|definition|meaning of|what does .+ mean|what is the meaning|dictionary)\b",
            ],
            "joke": [
                r"\b(joke|funny|make me laugh|tell me a joke|humor|humour|prank)\b",
            ],
            "capability_query": [
                r"\b(what can you do|help me with|your features|capabilities|what do you know|how can you help)\b",
            ],
            "farewell": [
                r"\b(bye|goodbye|see you|quit|exit|shutdown|close|good night|cya|take care)\b",
            ],
            "info_request": [
                r"\b(who is|who are|what is|what are|where is|when did|how does|how do|tell me about|explain|describe)\b",
            ],
        }

        self.intent_keywords = {
            "greeting": {"hello", "hi", "hey", "vanakkam", "howdy"},
            "thanks": {"thanks", "thank", "nandri", "appreciate", "cheers"},
            "time_query": {"time", "clock", "now", "date", "day", "mani", "neram", "hour", "minute"},
            "weather_query": {"weather", "temperature", "forecast", "rain", "sunny", "climate", "vaanilai",
                             "humid", "humidity", "snow", "wind", "hot", "cold", "fog"},
            "light_control": {"light", "lamp", "bulb", "switch", "turn", "bright", "dim",
                              "red", "blue", "green", "white", "vilakku", "fan", "ac"},
            "music": {"music", "song", "audio", "track", "playlist", "volume", "play",
                      "pause", "skip", "next", "previous", "radio", "mute", "louder"},
            "alarm_reminder": {"alarm", "remind", "reminder", "schedule", "wake", "notify"},
            "booking": {"book", "booking", "ticket", "reserve", "reservation",
                        "hotel", "flight", "train", "bus", "cab"},
            "calculation": {"calculate", "compute", "math", "plus", "minus", "times",
                           "divide", "percent", "percentage", "sum", "total"},
            "news_query": {"news", "headlines", "latest", "breaking", "update", "current"},
            "definition": {"define", "definition", "meaning", "dictionary"},
            "joke": {"joke", "funny", "laugh", "humor", "prank"},
            "capability_query": {"help", "feature", "features", "capabilities", "can", "able"},
            "farewell": {"bye", "goodbye", "exit", "quit", "shutdown", "close", "night"},
            "info_request": {"who", "what", "where", "when", "why", "how", "which",
                            "tell", "explain", "describe", "about", "information"},
        }

        self.entities_patterns = {
            "time": r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
            "date": r"\b(today|tomorrow|yesterday|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
            "device": r"\b(light|fan|ac|tv|bulb|lamp|vilakku)\b",
            "color": r"\b(red|blue|green|white|yellow|purple|orange|pink|sivappu|neelam)\b",
        }

        self.location_pattern = re.compile(
            r"\b(?:in|at|for|near)\s+([a-zA-Z][a-zA-Z\s]{1,30})\b",
            re.IGNORECASE,
        )

        self.filler_phrases = (
            "hey jarvis",
            "okay jarvis",
            "ok jarvis",
            "jarvis",
            "can you",
            "could you",
            "would you",
            "please",
            "i want you to",
            "i need you to",
        )

    def preprocess_text(self, text: str) -> str:
        """Normalize spoken text before classification."""
        if not text:
            return ""

        clean = text.lower().strip()
        clean = clean.replace("what's", "what is")
        clean = clean.replace("how's", "how is")
        clean = clean.replace("can't", "cannot")
        clean = clean.replace("it's", "it is")
        clean = re.sub(r"[^\w\s:]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        for phrase in self.filler_phrases:
            if clean.startswith(phrase + " "):
                clean = clean[len(phrase):].strip()

        words = []
        for word in clean.split():
            if words and words[-1] == word:
                continue
            words.append(word)

        return " ".join(words).strip()

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract lightweight entities from normalized text."""
        entities = {}

        for entity_type, pattern in self.entities_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = [match if isinstance(match, str) else match[0] for match in matches]

        location_matches = [match.strip() for match in self.location_pattern.findall(text)]
        if location_matches:
            entities["location"] = location_matches

        return entities

    def classify_intent(self, text: str) -> Tuple[str, float]:
        """Classify intent with a more realistic confidence score."""
        clean_text = self.preprocess_text(text)
        keywords = set(self.extract_keywords(clean_text))
        best_intent = "unknown"
        best_score = 0.0

        scores: dict = {}
        for intent, patterns in self.patterns.items():
            regex_hits = sum(1 for pattern in patterns if re.search(pattern, clean_text, re.IGNORECASE))
            keyword_hits = len(self.intent_keywords.get(intent, set()) & keywords)
            total_keywords = max(1, len(self.intent_keywords.get(intent, ())))

            regex_score = min(1.0, regex_hits * 0.65)
            keyword_score = min(0.35, keyword_hits / total_keywords)
            score = min(1.0, regex_score + keyword_score)
            scores[intent] = score

            if score > best_score:
                best_score = score
                best_intent = intent

        # Priority override: specific intents beat generic info_request when both fired
        # e.g. "what is the weather in Delhi" → weather_query, not info_request
        HIGH_PRIORITY = ("weather_query", "time_query", "calculation", "light_control",
                         "music", "alarm_reminder", "booking", "farewell", "greeting",
                         "thanks", "joke", "definition", "news_query")
        if best_intent == "info_request":
            for hp in HIGH_PRIORITY:
                if scores.get(hp, 0) >= 0.30:
                    best_intent = hp
                    best_score = max(best_score, scores[hp])
                    break

        # Numeric expression → calculation
        if re.search(r"\d+\s*[+\-*/]\s*\d+", clean_text):
            best_intent = "calculation"
            best_score = max(best_score, 0.80)

        # Fallbacks for low-confidence results
        if best_score < 0.35 and clean_text.endswith("?"):
            best_intent = "info_request"
            best_score = 0.42
        elif best_score < 0.3 and any(word in keywords for word in
                                       {"what", "who", "why", "how", "when", "where", "which",
                                        "explain", "tell", "describe"}):
            best_intent = "info_request"
            best_score = 0.45

        return best_intent, round(best_score, 2)

    def analyze_sentiment(self, text: str) -> str:
        """Very light sentiment analysis for more natural replies."""
        positive_words = {"good", "great", "excellent", "nice", "happy", "nalla", "awesome"}
        negative_words = {"bad", "terrible", "awful", "sad", "angry", "ketta", "upset"}

        words = set(self.preprocess_text(text).split())
        pos_count = len(positive_words & words)
        neg_count = len(negative_words & words)

        if pos_count > neg_count:
            return "positive"
        if neg_count > pos_count:
            return "negative"
        return "neutral"

    def extract_keywords(self, text: str) -> List[str]:
        """Extract basic content words."""
        stop_words = {
            "the", "is", "at", "which", "on", "a", "an", "and", "or", "but",
            "in", "with", "to", "for", "of", "as", "by", "that", "this",
            "oru", "onnu", "enna", "eppo", "eppadi", "yaar", "please",
            "jarvis", "can", "you", "could", "would",
        }

        words = re.findall(r"\b\w+\b", text.lower())
        return [word for word in words if word not in stop_words and len(word) > 2]

    def update_context(self, intent: str, entities: Dict, text: str):
        """Keep the last turn for slightly more natural replies."""
        self.context = {
            "last_intent": intent,
            "last_entities": entities,
            "last_text": text,
            "timestamp": datetime.now().isoformat(),
            "keywords": self.extract_keywords(text),
        }

    def get_context_aware_response(self, intent: str, entities: Dict, text: str) -> str:
        """Generate a natural short response for the detected intent."""
        self.update_context(intent, entities, text)
        now = datetime.now()

        if intent == "time_query":
            return f"It is {now.strftime('%I:%M %p').lstrip('0')} right now."

        if intent == "weather_query":
            location = (entities.get("location") or ["your area"])[0]
            return f"I can check the weather for {location}. Tell me if you want current conditions or a forecast."

        if intent == "light_control":
            device = (entities.get("device") or ["lights"])[0]
            color = (entities.get("color") or [None])[0]

            if "off" in text:
                return f"Okay, turning the {device} off."
            if color:
                return f"Okay, setting the {device} to {color}."
            if any(word in text for word in ("bright", "brighter", "dim", "dimmer")):
                return f"Sure, adjusting the {device}."
            return f"Okay, updating the {device} settings."

        if intent == "music":
            return random.choice([
                "Sure, I can help with music. Tell me what you want to play.",
                "Ready for music. Name a song, artist, or playlist.",
            ])

        if intent == "alarm_reminder":
            return "Sure, tell me the time and what you want me to remember."

        if intent == "booking":
            return "I can help with that booking. Tell me what you want to book."

        if intent == "capability_query":
            return "I can help with time, weather, reminders, device control, and quick questions."

        if intent == "greeting":
            sentiment = self.analyze_sentiment(text)
            if sentiment == "positive":
                return random.choice([
                    "Hi. You sound in good shape. What do you need?",
                    "Hello. What can I help you with?",
                ])
            return random.choice([
                "Hi. What can I do for you?",
                "Hello. I am here when you are ready.",
            ])

        if intent == "thanks":
            return random.choice([
                "You are welcome.",
                "Any time.",
                "Glad to help.",
            ])

        if intent == "farewell":
            return random.choice([
                "All right. Talk soon.",
                "Okay. See you later.",
                "Closing out for now.",
            ])

        keywords = self.extract_keywords(text)
        if keywords:
            joined = ", ".join(keywords[:3])
            return f"I caught {joined}. Tell me a bit more so I can act on it."
        return "I did not catch the goal yet. Rephrase it once more."

    def process_text(self, text: str) -> Dict:
        """Complete NLP processing pipeline."""
        if not text:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "sentiment": "neutral",
                "keywords": [],
                "response": "I did not hear anything clearly.",
            }

        clean_text = self.preprocess_text(text)
        intent, confidence = self.classify_intent(clean_text)
        entities = self.extract_entities(clean_text)
        sentiment = self.analyze_sentiment(clean_text)
        keywords = self.extract_keywords(clean_text)
        response = self.get_context_aware_response(intent, entities, clean_text)

        return {
            "original_text": text,
            "clean_text": clean_text,
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "sentiment": sentiment,
            "keywords": keywords,
            "response": response,
            "context": self.context,
        }


jarvis_nlp = JarvisNLP()


def process_natural_language(text: str) -> Dict:
    """Process text with NLP and return structured result."""
    return jarvis_nlp.process_text(text)


__all__ = ["JarvisNLP", "jarvis_nlp", "process_natural_language"]
