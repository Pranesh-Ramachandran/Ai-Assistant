"""
Personalization Engine - Tier 2 Feature
Learns user preferences, adapts responses, and maintains user profile context.

Examples:
  "My name is John"         -> store name=John
  "I prefer coffee over tea" -> store preference: beverages=coffee
  "Call me on my phone"      -> store device preference
  User asks same question repeatedly -> recognize pattern, offer shortcuts
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading


class PersonalizationEngine:
    """
    Learns and adapts to user preferences over time.
    """
    
    # Preference patterns to extract from conversations
    PREFERENCE_PATTERNS = {
        "name": {
            "patterns": [
                r"(?:my name is|i'm|i am|call me|name's)\s+([a-zA-Z]+?)(?:\s+(?:and|from|here|,|\.)|$)",
                r"^([a-zA-Z]+)\s+(?:here|speaking|is me)(?:\s|$)",
            ],
            "storage_key": "user_name",
            "type": "string"
        },
        "location": {
            "patterns": [
                r"(?:i'm from|i'm in|i live in|from|in|city (?:is|:))\s+([a-zA-Z\s]+?)(?:\s+(?:and|here|,|\.)|$)",
                r"(?:my city|my place|my house) (?:is|:)?\s+([a-zA-Z\s]+?)(?:\.|,|$)",
            ],
            "storage_key": "location",
            "type": "string"
        },
        "language": {
            "patterns": [
                r"(?:i speak|i know|language is|speaks?)\s+([a-zA-Z]+?)(?:\.|,|$)",
                r"(?:prefer|language)\s+(?:is|:)?\s+([a-zA-Z]+?)(?:\.|,|$)",
            ],
            "storage_key": "preferred_language",
            "type": "string"
        },
        "device": {
            "patterns": [
                r"(?:using|on)\s+(?:my\s+)?([a-zA-Z\s]+?)(?:phone|tablet|computer|laptop|desktop)",
                r"(?:my device|i use|using)\s+([a-zA-Z\s]+?)(?:\.|,|$)",
            ],
            "storage_key": "device_type",
            "type": "string"
        },
        "occupation": {
            "patterns": [
                r"(?:i'm|i am|i work as|occupation|job)\s+(?:a|an)?\s*([a-zA-Z\s]+?)(?:\.|,|$)",
                r"(?:works? in|profession)\s+(?:is|:)?\s+([a-zA-Z\s]+?)(?:\.|,|$)",
            ],
            "storage_key": "occupation",
            "type": "string"
        },
        "interests": {
            "patterns": [
                r"(?:interest|hobby|like|enjoy|love)\s+([a-zA-Z\s]+?)(?:\.|,|$)",
                r"(?:fan of|interested in)\s+([a-zA-Z\s]+?)(?:\.|,|$)",
            ],
            "storage_key": "interests",
            "type": "list"
        },
        "time_preference": {
            "patterns": [
                r"(?:prefer|like)\s+(?:to|talking|waking)\s+(?:in|at|during)\s+(?:the\s+)?([a-zA-Z]+?)(?:\.|,|$)",
                r"(?:morning|afternoon|evening|night)\s+(?:person|time)",
            ],
            "storage_key": "active_time",
            "type": "string"
        }
    }
    
    def __init__(self, profile_file: str = ".jarvis_user_profile.json"):
        """
        Initialize personalization engine.
        
        Args:
            profile_file: Path to store user profile (relative to AI_Assistant dir)
        """
        self.profile_file = os.path.join(os.path.dirname(__file__), profile_file)
        self.user_profile = self._load_profile()
        self.interaction_history = []  # Track what we've learned
        self.lock = threading.Lock()
    
    def _load_profile(self) -> Dict[str, Any]:
        """Load user profile from disk."""
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default profile structure
        return {
            "user_name": None,
            "location": None,
            "preferred_language": "en",
            "device_type": None,
            "occupation": None,
            "interests": [],
            "active_time": None,
            "communication_style": "friendly",
            "learned_at": [],
            "response_frequency": {},  # Track repeated questions
            "preferences": {}  # Custom key-value preferences
        }
    
    def _save_profile(self):
        """Atomically save profile to disk."""
        try:
            with open(self.profile_file, 'w') as f:
                json.dump(self.user_profile, f, indent=2)
        except Exception as e:
            print(f"[Personalization] Failed to save profile: {e}")
    
    def extract_preferences(self, text: str) -> Dict[str, Any]:
        """
        Extract preference information from user text.
        
        Returns:
            {
                "extracted": Dict[key, value],
                "confidence": float,
                "new_preferences": bool
            }
        """
        import re
        
        text_lower = text.lower()
        extracted = {}
        
        for pref_type, data in self.PREFERENCE_PATTERNS.items():
            for pattern in data["patterns"]:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    value = match.group(1).strip() if match.groups() else None
                    if value:
                        storage_key = data["storage_key"]
                        
                        # Handle different data types
                        if data["type"] == "list":
                            if storage_key not in self.user_profile:
                                self.user_profile[storage_key] = []
                            if value not in self.user_profile[storage_key]:
                                self.user_profile[storage_key].append(value)
                                extracted[storage_key] = self.user_profile[storage_key]
                        else:
                            if self.user_profile.get(storage_key) != value:
                                self.user_profile[storage_key] = value
                                extracted[storage_key] = value
                        
                        break
        
        if extracted:
            self.user_profile["learned_at"].append({
                "extracted": extracted,
                "timestamp": datetime.now().isoformat()
            })
            self._save_profile()
        
        return {
            "extracted": extracted,
            "confidence": 0.85,
            "new_preferences": len(extracted) > 0
        }
    
    def get_personalized_greeting(self) -> str:
        """Generate a personalized greeting."""
        name = self.user_profile.get("user_name")
        if name:
            return f"Hello {name}! How can I help you today?"
        return "Hello! How can I help you today?"
    
    def adapt_response(self, response: str, intent: str) -> str:
        """
        Adapt an AI response based on user profile and preferences.
        
        Examples:
          - If user prefers formal: replace casual language
          - If user is in location X: localize references
          - If user is busy (active_time specific), keep it brief
        """
        name = self.user_profile.get("user_name")
        language = self.user_profile.get("preferred_language", "en")
        location = self.user_profile.get("location")
        communication = self.user_profile.get("communication_style", "friendly")
        
        # Add personalization to response
        if name and "Hello" in response:
            response = response.replace("Hello", f"Hi {name}").replace("you", f"{name}")
        
        # Localize references if location is known
        if location and location.lower() in ["kerala", "tamil nadu", "karnataka"]:
            # Could add region-specific info here
            pass
        
        # Adjust formality
        if communication == "formal":
            response = response.replace("gonna", "will").replace("wanna", "want to")
            response = response.replace("Yeah", "Yes").replace("Nope", "No")
        elif communication == "casual":
            response = response.replace("you could", "you can")
        
        return response
    
    def track_interaction(self, query: str, response: str, intent: str):
        """
        Track user interactions to detect patterns.
        Useful for recognizing repeated questions and suggesting shortcuts.
        """
        # Track query frequency
        query_key = intent or query[:20]
        if query_key not in self.user_profile["response_frequency"]:
            self.user_profile["response_frequency"][query_key] = 0
        self.user_profile["response_frequency"][query_key] += 1
        
        # Store interaction
        self.interaction_history.append({
            "query": query[:50],
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 100 interactions
        if len(self.interaction_history) > 100:
            self.interaction_history.pop(0)
    
    def suggest_shortcut(self) -> Optional[str]:
        """
        Suggest a shortcut based on repeated interactions.
        
        Example: If user repeatedly asks "What's the weather?",
        suggest: "You can just say 'weather' next time"
        """
        # Find most frequent interaction in last 20
        if len(self.interaction_history) < 5:
            return None
        
        recent = self.interaction_history[-20:]
        intents = {}
        
        for interaction in recent:
            intent = interaction.get("intent", "")
            intents[intent] = intents.get(intent, 0) + 1
        
        # If we see same intent 3+ times in recent history
        for intent, count in intents.items():
            if count >= 3:
                return f"Tip: You've asked about {intent} {count} times. You can save time with shortcuts!"
        
        return None
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """Get a summary of the user profile."""
        return {
            "user_name": self.user_profile.get("user_name"),
            "location": self.user_profile.get("location"),
            "language": self.user_profile.get("preferred_language"),
            "occupation": self.user_profile.get("occupation"),
            "interests": self.user_profile.get("interests", []),
            "device": self.user_profile.get("device_type"),
            "communication_style": self.user_profile.get("communication_style"),
            "learned_preferences_count": len(self.user_profile.get("learned_at", []))
        }
    
    def set_preference(self, key: str, value: Any):
        """Manually set a preference."""
        with self.lock:
            self.user_profile["preferences"][key] = value
            self._save_profile()
    
    def get_preference(self, key: str, default=None) -> Any:
        """Get a custom preference."""
        return self.user_profile.get("preferences", {}).get(key, default)


# Singleton instance
PERSONALIZATION_ENGINE = PersonalizationEngine()


def personalize(text: str, intent: str = "REQUEST", extract_prefs: bool = True) -> Dict[str, Any]:
    """
    Public function to extract preferences and personalize responses.
    
    Args:
        text: User input
        intent: Query intent (for tracking)
        extract_prefs: Whether to extract preferences from text
    
    Returns:
        {
            "extracted_preferences": Dict,
            "greeting": str (if greeting should be used),
            "should_adapt_response": bool,
            "suggestion": str (if there's a shortcut to suggest)
        }
    """
    result = {}
    
    if extract_prefs:
        prefs = PERSONALIZATION_ENGINE.extract_preferences(text)
        result["extracted_preferences"] = prefs["extracted"]
        
        if prefs["new_preferences"]:
            result["greeting"] = PERSONALIZATION_ENGINE.get_personalized_greeting()
    
    # Track the interaction
    PERSONALIZATION_ENGINE.track_interaction(text, "", intent)
    
    # Check if we should suggest a shortcut
    suggestion = PERSONALIZATION_ENGINE.suggest_shortcut()
    result["suggestion"] = suggestion
    result["should_adapt_response"] = bool(PERSONALIZATION_ENGINE.user_profile.get("user_name"))
    
    return result
