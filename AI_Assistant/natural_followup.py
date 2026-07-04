"""
Natural Follow-up Handling - Tier 2 Feature
Detects and contextualizes yes/no responses, follow-up queries, and implicit continuations.

Example:
  User: "What's the weather in Kerala?"  -> [Reply with weather data]
  User: "And in Tamil Nadu?"              -> [Contextually understood as location follow-up]
  User: "Should I take an umbrella?"      -> [Based on weather context from previous response]
  User: "Yes"                             -> [Understood as response to umbrella question]
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime


class NaturalFollowupHandler:
    """
    Detects and processes follow-up queries that build on previous conversation context.
    """
    
    # Follow-up patterns (regex-based for speed)
    FOLLOWUP_PATTERNS = {
        "confirmation": {
            "patterns": [
                r"^(?:yes|yeah|yep|yup|ok|okay|fine|alright|sure|absolutely|definitely|certainly)(?:\s|$)",
                r"^(?:no|nope|nah|not|never|don't?|won't?|can't?)(?:\s|$)",
            ],
            "action": "confirm_previous"
        },
        "continuation": {
            "patterns": [
                r"^(?:and|also|what about|how about)(?:\s+(?:the|a)?)",
                r"^(?:same|ditto|me too|both|either)",
            ],
            "action": "continue_topic"
        },
        "comparison": {
            "patterns": [
                r"^(?:instead|but|however|or|versus|vs\.?|compared to|rather than)",
                r"^(?:what's?\s+the\s+difference|difference between)",
            ],
            "action": "compare_entities"
        },
        "elaboration": {
            "patterns": [
                # Only trigger for genuine clarification words followed by reference words (that/this/it/previous)
                r"^(?:why|when|how exactly|which one|where exactly)\s+(?:is that|does that|did that|do you|is it|was that)",
                r"^tell me (?:more about that|more about this|why|when exactly)",
                r"^(?:what did you mean|what do you mean|can you elaborate|can you explain more)",
            ],
            "action": "elaborate_on_previous"
        },
        "context_shift": {
            "patterns": [
                r"^(?:by the way|anyway|speaking of|unrelated but|so)",
                r"^(?:never mind|forget that)",
            ],
            "action": "shift_context"
        },
    }
    
    def __init__(self):
        """Initialize follow-up handler with compiled patterns."""
        self.last_query = None
        self.last_response = None
        self.last_intent = None
        self.extracted_entities = {}
        self.conversation_stack = []  # Stack of (query, entities, timestamp)
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self.compiled_patterns = {}
        for category, data in self.FOLLOWUP_PATTERNS.items():
            self.compiled_patterns[category] = {
                "compiled": [re.compile(p, re.IGNORECASE) for p in data["patterns"]],
                "action": data["action"]
            }
    
    def set_context(self, query: str, response: str, intent: str, entities: Dict[str, Any]):
        """
        Set the current conversation context for follow-up analysis.
        
        Args:
            query: User's last query
            response: AI's last response
            intent: Classified intent of the query
            entities: Extracted entities (what, when, where, etc.)
        """
        self.last_query = query
        self.last_response = response
        self.last_intent = intent
        self.extracted_entities = entities
        
        # Keep stack of last 5 conversational turns
        if len(self.conversation_stack) >= 5:
            self.conversation_stack.pop(0)
        self.conversation_stack.append({
            "query": query,
            "entities": entities,
            "intent": intent,
            "timestamp": datetime.now()
        })
    
    def detect_followup(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detect if text is a follow-up to previous context.
        
        Returns:
            Dict with:
              - followup_type: str (confirmation, continuation, comparison, etc.)
              - confidence: float (0-1)
              - action: str (what to do with this follow-up)
              - context: Dict (previous query info to use)
              - suggested_context: str (text to prepend for LLM)
        """
        if not self.last_query:
            return None
        
        text_lower = text.lower().strip()
        
        # Match against follow-up patterns
        for category, data in self.compiled_patterns.items():
            for compiled_pattern in data["compiled"]:
                if compiled_pattern.match(text_lower):
                    return {
                        "followup_type": category,
                        "confidence": 0.95,
                        "action": data["action"],
                        "context": {
                            "previous_query": self.last_query,
                            "previous_intent": self.last_intent,
                            "previous_entities": self.extracted_entities,
                        },
                        "suggested_context": self._build_context_string(category, text_lower)
                    }
        
        # No clear pattern match - likely implicit reference
        # Only treat very short queries as implicit follow-ups if they are genuinely ambiguous
        # (not standalone commands like "tell me a joke", "play music", etc.)
        SELF_CONTAINED_PATTERNS = re.compile(
            r"^(tell me|play|show(?: me)?|turn|switch|open|close|find|search|set|start|stop|pause|resume|calculate|what(?:'s| is| are| time| date)|who|when|where|why|how|remind|book|call|text|email)",
            re.IGNORECASE
        )
        if len(text.split()) <= 5 and not SELF_CONTAINED_PATTERNS.match(text.strip()):
            return {
                "followup_type": "implicit_reference",
                "confidence": 0.6,
                "action": "interpret_with_context",
                "context": {
                    "previous_query": self.last_query,
                    "previous_intent": self.last_intent,
                    "previous_entities": self.extracted_entities,
                },
                "suggested_context": f"Context: User previously asked '{self.last_query}'"
            }
        
        return None
    
    def _build_context_string(self, category: str, text: str) -> str:
        """Build a context string to prepend to the current query for LLM."""
        if category == "confirmation":
            action_word = "yes" if any(t in text for t in ["yes", "yeah", "yep", "ok"]) else "no"
            return f"User said '{action_word}' in response to: {self.last_query}"
        
        elif category == "continuation":
            return f"User is continuing from: {self.last_query}. Previous context: {self.last_response[:100]}..."
        
        elif category == "comparison":
            entity = self.extracted_entities.get("object") or self.extracted_entities.get("target") or "previous topic"
            return f"User wants to compare with: {entity} (previously discussed in: {self.last_query})"
        
        elif category == "elaboration":
            return f"User wants elaboration on: {self.last_query}"
        
        elif category == "context_shift":
            return "User is shifting context from previous topic"
        
        return ""
    
    def rewrite_followup(self, text: str) -> str:
        """
        Rewrite a follow-up query with full context for better LLM understanding.
        
        Args:
            text: Short follow-up text (e.g., "Yes", "And in Kerala?")
        
        Returns:
            Rewritten query with full context for LLM
        """
        followup = self.detect_followup(text)
        if not followup:
            return text
        
        action = followup["action"]
        context = followup["context"]
        
        # Rewrite based on action type
        if action == "confirm_previous":
            answer = "yes" if any(w in text.lower() for w in ["yes", "yeah", "yep", "ok", "sure"]) else "no"
            return f"{answer} to: {context['previous_query']}"
        
        elif action == "continue_topic":
            # Extract what's being asked about from the continuation
            continuation_entity = self._extract_continuation_entity(text)
            return f"What about {continuation_entity}? (context: {context['previous_query']})"
        
        elif action == "compare_entities":
            return f"Compare with {context['previous_query']}: {text}"
        
        elif action == "elaborate_on_previous":
            # Don't nest context if previous_query already contains context markers
            prev = context['previous_query']
            if "(Context:" in prev or "about:" in prev:
                return text  # Already has context, don't chain further
            return f"{text} (relating to: {prev[:60]})"
        
        elif action == "shift_context":
            return text  # Keep as-is, separate from previous context
        
        else:  # interpret_with_context
            # Don't chain context onto context strings
            prev = context['previous_query']
            if "(Context:" in prev:
                return text
            return f"(Context: {prev[:80]}) {text}"
    
    def _extract_continuation_entity(self, text: str) -> str:
        """Extract what entity is being asked about in a continuation."""
        # Simple pattern matching for locations, things, etc.
        # "and in Kerala?" -> "Kerala"
        # "what about prices?" -> "prices"
        # "both?" -> "both options"
        
        match = re.search(r"(?:in|for|about|with)\s+([a-zA-Z\s]+)(?:\?|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        match = re.search(r"^(?:the|a)?\s*([a-zA-Z\s]+)(?:\?|$)", text)
        if match:
            return match.group(1).strip()
        
        return "same thing"
    
    def get_conversation_summary(self) -> str:
        """Get a brief summary of the conversation thread for context."""
        if not self.conversation_stack:
            return ""
        
        summary_parts = []
        for turn in self.conversation_stack[-3:]:  # Last 3 turns
            summary_parts.append(f"- {turn['intent']}: {turn['query'][:50]}...")
        
        return "Recent context:\n" + "\n".join(summary_parts)


# Singleton instance
FOLLOWUP_HANDLER = NaturalFollowupHandler()


def handle_followup(text: str, previous_query: str, previous_response: str, 
                   previous_intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a potential follow-up query.
    
    Returns:
        {
            "is_followup": bool,
            "followup_type": str (if followup),
            "rewritten_query": str (if followup),
            "context": Dict (previous turn context)
        }
    """
    FOLLOWUP_HANDLER.set_context(previous_query, previous_response, previous_intent, entities)
    
    followup = FOLLOWUP_HANDLER.detect_followup(text)
    if not followup:
        return {
            "is_followup": False,
            "rewritten_query": text,
            "context": {}
        }
    
    rewritten = FOLLOWUP_HANDLER.rewrite_followup(text)
    return {
        "is_followup": True,
        "followup_type": followup["followup_type"],
        "confidence": followup["confidence"],
        "rewritten_query": rewritten,
        "context": followup["context"],
        "action": followup["action"]
    }
