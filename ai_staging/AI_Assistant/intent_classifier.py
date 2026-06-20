"""
Intent Classifier — Categorizes user queries into actionable intents.

Intents:
  • GREETING: "hello", "hi", "good morning"
  • QUESTION: "what is", "how do I", "tell me about"
  • REQUEST: "do this", "can you", "please"
  • CONTROL: "turn on light", "set alarm"
  • BOOKING: "book ticket", "reserve table"
  • INFORMATION: "where is", "what's the weather"
  • AFFIRMATION: "yes", "okay", "sure"
  • NEGATION: "no", "don't", "cancel"
  • CLARIFICATION: "what do you mean", "explain that"
  • SMALL_TALK: "how are you", "what's up"
"""

import re
from typing import Tuple, Dict, Any, List


class IntentClassifier:
    """Fast intent classification without ML."""
    
    INTENT_PATTERNS = {
        "GREETING": [
            r"^(hello|hi|hey|good morning|good afternoon|good evening|greetings|namaste|vanakkam)",
        ],
        "SMALL_TALK": [
            r"(how are you|how's it going|what's up|you okay|how do you feel)",
        ],
        "QUESTION": [
            r"^(what|how|why|when|where|who|which|is it|can you|could you|would you)\b",
            r"(what is|how do|why is|when is|where is|tell me about|who is|who are)",
        ],
        "REQUEST": [
            r"(please|kindly|can you|could you|would you mind|help me|do this)",
        ],
        "CONTROL": [
            r"(turn (on|off)|switch|control|set|activate|deactivate)",
            r"(light|fan|ac|music|alarm|reminder|temperature)",
            r"(remind me|notify me|wake me|alert me|schedule a reminder|set a reminder)",
        ],
        "BOOKING": [
            r"(book|reserve|schedule|ticket|table|appointment|meeting|hotel)",
        ],
        "INFORMATION": [
            r"(weather|temperature|news|time|date|location|address|phone)",
        ],
        "ENTERTAINMENT": [
            r"(joke|funny|make me laugh|tell me a joke|humor|humour|prank)",
            r"(play|pause|stop|skip|next).*(music|song|audio|track|playlist|radio)",
            r"(music|song|playlist|radio)",
            r"(riddle|quiz|game|trivia)",
        ],
        "AFFIRMATION": [
            r"^(yes|yeah|yep|okay|ok|sure|of course|absolutely|definitely|nandri|sari)",
        ],
        "NEGATION": [
            r"^(no|nope|nah|don't|not|never|cancel|remove|delete|skip)",
        ],
        "CLARIFICATION": [
            r"(what do you mean|explain|clarify|rephrase|say that again|repeat)",
        ],
    }

    # Intents that are never ambiguous — never ask for clarification
    NO_CLARIFY_INTENTS = {
        "GREETING", "SMALL_TALK", "INFORMATION", "AFFIRMATION",
        "NEGATION", "CLARIFICATION", "ENTERTAINMENT", "REQUEST",
        "CONTROL", "BOOKING",
    }

    # High-signal QUESTION patterns that need no clarification
    CLEAR_QUESTION_PATTERNS = [
        re.compile(r"(who|what|where|when|why|how).+(is|are|was|were|do|does|did|means|mean)", re.IGNORECASE),
        re.compile(r"(tell me|explain|describe).+about", re.IGNORECASE),
        re.compile(r"(define|definition|meaning of)", re.IGNORECASE),
    ]
    
    def __init__(self):
        self.compiled_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self.compiled_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def classify(self, text: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Classify user intent from text.
        
        Returns:
            (intent_name, confidence, metadata)
        """
        text_lower = text.lower().strip()
        scores = {}
        matched_patterns = set()
        
        # Score each intent based on pattern matches
        for intent, patterns in self.compiled_patterns.items():
            match_count = 0
            for pattern in patterns:
                if pattern.search(text_lower):
                    match_count += 1
                    matched_patterns.add(intent)
            
            if match_count > 0:
                # Confidence based on number of pattern matches
                scores[intent] = match_count / len(patterns)
        
        if not scores:
            # Default: QUESTION if starts with interrogative
            if any(text_lower.startswith(w) for w in ["what", "how", "why", "when", "where", "who"]):
                return "QUESTION", 0.5, {"matched_patterns": []}
            return "REQUEST", 0.3, {"matched_patterns": []}  # Default to REQUEST
        
        # Return highest scoring intent
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent], 1.0)

        # Heuristic boost: some intents (entertainment, control, requests,
        # greetings, small talk) are high-signal for short commands —
        # increase confidence slightly to avoid spurious clarifications.
        if best_intent in ("ENTERTAINMENT", "CONTROL", "REQUEST", "GREETING", "SMALL_TALK"):
            confidence = max(confidence, 0.6)

        return best_intent, confidence, {
            "matched_patterns": list(matched_patterns),
            "all_scores": scores,
        }
    
    def extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract relevant entities from text based on intent."""
        entities = {}
        text_lower = text.lower()
        
        if intent == "QUESTION":
            # Extract question type
            for q_word in ["what", "how", "why", "when", "where", "who", "which"]:
                if text_lower.startswith(q_word):
                    entities["question_type"] = q_word
                    break
            
            # Extract subject (what comes after question word)
            parts = text.split()
            if len(parts) > 1:
                entities["subject"] = " ".join(parts[1:6])  # First few words
        
        elif intent == "REQUEST" or intent == "CONTROL":
            # Extract action verb and target
            for match in re.finditer(r"(turn|switch|set|control|activate)\s+(on|off|to|at)\s+(\w+)", text_lower):
                entities["action"] = match.group(1)
                entities["state"] = match.group(2)
                entities["target"] = match.group(3)
        
        elif intent == "BOOKING":
            # Extract what's being booked and when
            for match in re.finditer(r"book\s+(\w+.+?)\s+(for|on|at|in)\s+(.+?)(?:\.|$)", text_lower):
                entities["item"] = match.group(1)
                entities["time_ref"] = match.group(3)
        
        return entities
    
    def get_follow_up_questions(self, intent: str, entities: Dict) -> List[str]:
        """
        Suggest clarification questions for ambiguous intents.
        
        Example: User says "book something"
        Returns: ["Book what?", "When would you like to book?", "How many?"]
        """
        questions = []
        
        if intent == "BOOKING":
            if "item" not in entities:
                questions.append("What would you like to book?")
            if "time_ref" not in entities:
                questions.append("When would you like to book?")
            questions.append("How many people/items?")
        
        elif intent == "REQUEST":
            if "target" not in entities:
                questions.append("What would you like me to do?")
        
        elif intent == "QUESTION":
            if "subject" not in entities:
                questions.append("What specifically would you like to know?")
        
        # Generic follow-up if highly ambiguous
        if len(questions) == 0 and len(entities) == 0:
            questions.append("Could you be more specific?")
        
        return questions[:2]  # Return max 2 clarification questions


# Global instance
INTENT_CLASSIFIER = IntentClassifier()


def classify_query(text: str) -> Dict[str, Any]:
    """Classify a query and return comprehensive intent info."""
    intent, confidence, metadata = INTENT_CLASSIFIER.classify(text)
    entities = INTENT_CLASSIFIER.extract_entities(text, intent)

    # Only generate clarification questions when confidence is very low
    # Tighter threshold to reduce spurious clarifications
    follow_ups = INTENT_CLASSIFIER.get_follow_up_questions(intent, entities) if confidence < 0.35 else []

    # Determine whether clarification is truly needed
    # Never clarify for well-understood intents
    never_clarify = intent in INTENT_CLASSIFIER.NO_CLARIFY_INTENTS

    # Never clarify for clear question patterns ("who is X", "what is X", etc.)
    is_clear_question = any(
        p.search(text) for p in INTENT_CLASSIFIER.CLEAR_QUESTION_PATTERNS
    )

    # Only ask for clarification when genuinely ambiguous
    requires_clarification = (
        not never_clarify
        and not is_clear_question
        and confidence < 0.4
        and len(follow_ups) > 0
    )

    return {
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "requires_clarification": requires_clarification,
        "clarification_questions": follow_ups,
        "metadata": metadata,
    }
