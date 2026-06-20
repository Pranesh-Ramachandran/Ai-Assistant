"""
Proactive Assistance - Tier 3 Feature
Anticipate needs and offer help before user asks.

Examples:
  "Remind you of upcoming events"
  "Suggest relevant information based on patterns"
  "Offer to schedule meeting when discussing deadlines"
  "Suggest weather-appropriate actions"
"""

import re
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta


class ProactiveAssistant:
    """
    Detects user needs and proactively offers help.
    Learns from conversation patterns.
    """
    
    def __init__(self):
        """Initialize proactive assistant."""
        self.patterns = self._load_patterns()
        self.user_context = {}
        self.suggestion_history = []
        self.max_suggestions_per_session = 3
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load proactive assistance patterns."""
        patterns_file = os.path.join(os.path.dirname(__file__), ".proactive_patterns.json")
        if os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default patterns
        return {
            "deadline_keywords": ["meeting", "deadline", "tomorrow", "today", "urgent", "asap", "due"],
            "travel_keywords": ["flight", "train", "drive", "airport", "destination", "travel"],
            "health_keywords": ["tired", "sick", "headache", "fever", "pain", "doctor"],
            "work_keywords": ["project", "presentation", "report", "deadline", "meeting"],
            "social_keywords": ["friend", "family", "birthday", "anniversary", "party"],
        }
    
    def analyze_context(self, conversation_history: List[str]) -> Dict[str, Any]:
        """
        Analyze conversation to understand context.
        
        Returns: {
            "topic": str,
            "sentiment": str,
            "intent": str,
            "urgency": str,
            "entities": list
        }
        """
        if not conversation_history:
            return {}
        
        last_messages = " ".join(conversation_history[-3:]).lower()
        
        context = {
            "topic": self._classify_topic(last_messages),
            "sentiment": self._analyze_sentiment(last_messages),
            "urgency": self._assess_urgency(last_messages),
            "entities": self._extract_entities(last_messages)
        }
        
        return context
    
    def _classify_topic(self, text: str) -> str:
        """Classify conversation topic."""
        topics = {
            "work": self.patterns.get("work_keywords", []),
            "travel": self.patterns.get("travel_keywords", []),
            "health": self.patterns.get("health_keywords", []),
            "social": self.patterns.get("social_keywords", []),
            "general": []
        }
        
        for topic, keywords in topics.items():
            if any(kw in text for kw in keywords):
                return topic
        
        return "general"
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text."""
        positive_words = ["good", "great", "happy", "excellent", "nice", "wonderful"]
        negative_words = ["bad", "sad", "angry", "terrible", "awful", "frustrated"]
        
        pos_count = sum(text.count(w) for w in positive_words)
        neg_count = sum(text.count(w) for w in negative_words)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"
    
    def _assess_urgency(self, text: str) -> str:
        """Assess urgency of request."""
        urgent_keywords = ["urgent", "asap", "immediately", "now", "quickly", "hurry"]
        normal_keywords = ["tomorrow", "next week", "soon", "when you can"]
        low_keywords = ["whenever", "no rush", "eventually", "later"]
        
        if any(kw in text for kw in urgent_keywords):
            return "high"
        elif any(kw in text for kw in normal_keywords):
            return "normal"
        elif any(kw in text for kw in low_keywords):
            return "low"
        else:
            return "normal"
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities from text."""
        entities = []
        
        # Extract names (capitalized words or after "with")
        names = re.findall(r'\b([A-Z][a-z]+)\b', text)
        entities.extend(names)
        
        # Extract names mentioned after "with"
        with_names = re.findall(r'with\s+([a-zA-Z]+)', text, re.IGNORECASE)
        entities.extend(with_names)
        
        # Extract dates/times
        if re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text, re.IGNORECASE):
            entities.append("date_reference")
        if re.search(r'\b(tomorrow|today|tonight|next week|this week)\b', text, re.IGNORECASE):
            entities.append("temporal_reference")
        
        # Extract locations (after "in", "to", "from")
        locations = re.findall(r'(?:in|to|from)\s+([a-zA-Z\s]+?)(?:\s+(?:and|,|with|$))', text, re.IGNORECASE)
        entities.extend([loc.strip() for loc in locations if len(loc.strip()) > 2])
        
        return list(set(entities))
    
    def detect_need_for_assistance(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect if user might need proactive assistance.
        
        Returns list of suggested assistances.
        """
        suggestions = []
        text_lower = text.lower()
        
        # Pattern 1: Deadline/Meeting mentioned → Offer scheduling
        if any(kw in text_lower for kw in self.patterns.get("deadline_keywords", [])):
            if not any(s["type"] == "calendar" for s in suggestions):
                suggestions.append({
                    "type": "calendar",
                    "action": "schedule",
                    "message": "Would you like me to schedule this meeting or add it to your calendar?",
                    "confidence": 0.85
                })
        
        # Pattern 2: Travel mentioned → Offer travel assistance
        if any(kw in text_lower for kw in self.patterns.get("travel_keywords", [])):
            suggestions.append({
                "type": "travel",
                "action": "search",
                "message": "Should I search for flights/trains or check the weather for your destination?",
                "confidence": 0.80
            })
        
        # Pattern 3: Health mentioned → Offer health tips
        if any(kw in text_lower for kw in self.patterns.get("health_keywords", [])):
            suggestions.append({
                "type": "health",
                "action": "suggest",
                "message": "Would you like some health suggestions or should I find nearby doctors?",
                "confidence": 0.75
            })
        
        # Pattern 4: Negative sentiment + work topic → Offer support
        if context.get("sentiment") == "negative" and context.get("topic") == "work":
            suggestions.append({
                "type": "support",
                "action": "help",
                "message": "Sounds like you're stressed about work. Want to talk about it or focus on something else?",
                "confidence": 0.70
            })
        
        # Pattern 5: Time-sensitive language → Offer reminders
        if context.get("urgency") == "high":
            suggestions.append({
                "type": "reminder",
                "action": "set_alarm",
                "message": "This seems urgent. Should I set a reminder so you don't forget?",
                "confidence": 0.80
            })
        
        # Pattern 6: Research/Learning topic → Offer resources
        if any(w in text_lower for w in ["how to", "learn", "teach", "understand"]):
            suggestions.append({
                "type": "learning",
                "action": "search",
                "message": "Want me to find tutorials or resources on this?",
                "confidence": 0.75
            })
        
        # Pattern 7: Multiple entities mentioned → Offer email/note
        if len(context.get("entities", [])) > 2:
            suggestions.append({
                "type": "communication",
                "action": "compose",
                "message": "Should I send an email or compose a note about this?",
                "confidence": 0.60
            })
        
        return suggestions
    
    def prioritize_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize suggestions by confidence and relevance.
        
        Limit to max suggestions per session.
        """
        # Sort by confidence (descending)
        sorted_suggestions = sorted(suggestions, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Check frequency to avoid spamming same suggestion type
        recent_types = [s["type"] for s in self.suggestion_history[-5:]]
        
        filtered = []
        for suggestion in sorted_suggestions:
            if suggestion["type"] not in recent_types and len(filtered) < self.max_suggestions_per_session:
                filtered.append(suggestion)
                self.suggestion_history.append(suggestion)
        
        return filtered
    
    def generate_proactive_offer(self, suggestion: Dict[str, Any]) -> str:
        """Generate natural language proactive offer."""
        base_message = suggestion.get("message", "")
        action = suggestion.get("action", "")
        
        # Add context-specific phrases
        if action == "schedule":
            return base_message + " Just tell me the details and I'll add it."
        elif action == "search":
            return base_message + " I can search right away."
        elif action == "set_alarm":
            return base_message + " Just say the time."
        elif action == "help":
            return base_message + " I'm here to help."
        
        return base_message
    
    def should_make_suggestion(self, confidence: float = 0.75) -> bool:
        """
        Decide if current moment is appropriate to make suggestion.
        
        Avoid interrupting or being too pushy.
        """
        # Don't suggest if user just had suggestion
        if self.suggestion_history and len(self.suggestion_history) > 0:
            last_suggestion_age = len(self.suggestion_history[-1].get("timestamp", "")) 
            if last_suggestion_age < 2:  # Less than 2 suggestions since last
                return False
        
        # Check confidence threshold
        return confidence >= 0.75
    
    def learn_from_interaction(self, query: str, response: str, user_accepted: bool) -> None:
        """Learn from user interaction to improve future suggestions."""
        # Track what suggestions user accepted
        if user_accepted:
            # Increase confidence for similar patterns
            pass
        else:
            # Decrease confidence for similar patterns
            pass


# Singleton instance
PROACTIVE_ASSISTANT = ProactiveAssistant()


def detect_proactive_needs(query: str, conversation_history: List[str] = None) -> Dict[str, Any]:
    """
    Detect and generate proactive assistance suggestions.
    
    Usage:
      detect_proactive_needs("I have a meeting tomorrow with John about the project")
      detect_proactive_needs("I'm flying to Paris next week")
    """
    if conversation_history is None:
        conversation_history = [query]
    
    # Analyze context
    context = PROACTIVE_ASSISTANT.analyze_context(conversation_history)
    
    # Detect needs
    suggestions = PROACTIVE_ASSISTANT.detect_need_for_assistance(query, context)
    
    if not suggestions:
        return {
            "has_suggestions": False,
            "message": None
        }
    
    # Prioritize suggestions
    prioritized = PROACTIVE_ASSISTANT.prioritize_suggestions(suggestions)
    
    if not prioritized:
        return {
            "has_suggestions": False,
            "message": None
        }
    
    # Get best suggestion
    best_suggestion = prioritized[0]
    
    if not PROACTIVE_ASSISTANT.should_make_suggestion(best_suggestion.get("confidence", 0.75)):
        return {
            "has_suggestions": False,
            "message": None
        }
    
    return {
        "has_suggestions": True,
        "suggestion_type": best_suggestion.get("type"),
        "action": best_suggestion.get("action"),
        "message": PROACTIVE_ASSISTANT.generate_proactive_offer(best_suggestion),
        "confidence": best_suggestion.get("confidence")
    }
