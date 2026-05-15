"""
Query Rephrasing - Tier 2 Feature
Clarifies and restructures queries for better LLM understanding.

Examples:
  Input: "how much is it"
  Output: "What is the price of [item from context]?"
  
  Input: "can i book online"
  Output: "Can I make a booking online using your service?"
  
  Input: "what's trending"
  Output: "What content/topics are trending right now?"
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime


class QueryRephraser:
    """
    Detects ambiguous queries and rephrases them for clarity.
    """
    
    # Ambiguity patterns (high-entropy questions that need context)
    AMBIGUOUS_PATTERNS = {
        "pronoun_reference": {
            "patterns": [
                r"^(?:it|that|this|them|those|these)(?:\s|$)",
                r"^how (?:much|many|long|often|big)",
                r"^what(?:'s)? (?:is )?(?:it|that|this) ",
            ],
            "needs_context": True,
            "rephrase_template": "Can you clarify what you're asking about? (asking about: {context_hint})"
        },
        "vague_verb": {
            "patterns": [
                r"(?:do|make|have|get|see|find|check)\s(?:it|that|this)?(?:\s|$)",
                r"^(?:can|could|should|would|might) i ",
                r"^(?:is there|are there|can i|could i) a way",
            ],
            "needs_context": True,
            "rephrase_template": "More clearly: {rephrased_action}?"
        },
        "missing_subject": {
            "patterns": [
                r"^(?:cost|price)(?:\s|$)",
                r"^(?:available|open|good|bad|safe)(?:\s|$)",
                r"^(?:how|when|where|why)(?:\s|$)(?!.*\b(?:weather|time|location|reason)\b)",
            ],
            "needs_context": True,
            "rephrase_template": "What is the {missing_subject} of {likely_target}?"
        },
        "assumed_knowledge": {
            "patterns": [
                r"^(?:what|who|where) (?:is|are) (?:they?|you|we)",
                r"^(?:tell me|give me|show me|find me) it",
                r"^(?:does|do|did|have) (?:you|they) ",
            ],
            "needs_context": True, 
            "rephrase_template": "Can you clarify what you're referring to?"
        }
    }
    
    # Incomplete patterns (queries that seem cut off)
    INCOMPLETE_PATTERNS = [
        r"^(?:how|what|when|where|why)(?:\?|$)",  # Just a question word
        r"^[a-z]{1,3}(?:\?|$)",  # Very short (like "wtf", "omg")
        r"^(?:um|uh|uhh|hmm|hmmmm)(?:\s|$)",  # Hesitation words
    ]
    
    def __init__(self):
        """Initialize rephraser."""
        self.last_context = {}
        self.entity_history = {}  # Track previously mentioned entities
    
    def set_context(self, context: Dict[str, Any]):
        """Set conversation context for rephrasing."""
        self.last_context = context
        if "entities" in context:
            # Track mentioned entities
            for key, val in context["entities"].items():
                if val:
                    self.entity_history[key] = val
    
    def detect_ambiguity(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detect if query is ambiguous and needs rephrasing.
        
        Returns:
            {
                "is_ambiguous": bool,
                "ambiguity_type": str,
                "confidence": float,
                "missing_context": List[str]
            }
        """
        text_lower = text.lower().strip()
        
        # Check for incomplete patterns first
        for pattern in self.INCOMPLETE_PATTERNS:
            if re.match(pattern, text_lower):
                return {
                    "is_ambiguous": True,
                    "ambiguity_type": "incomplete",
                    "confidence": 0.8,
                    "missing_context": ["What specifically?"]
                }
        
        # Check for known ambiguity patterns
        for ambig_type, data in self.AMBIGUOUS_PATTERNS.items():
            for pattern in data["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    missing = self._infer_missing_context(text_lower, ambig_type)
                    return {
                        "is_ambiguous": True,
                        "ambiguity_type": ambig_type,
                        "confidence": 0.85,
                        "missing_context": missing,
                        "pattern_type": data
                    }
        
        # Check length-based ambiguity (very short queries are often ambiguous)
        word_count = len(text.split())
        if word_count <= 2 and text_lower not in ["yes", "no", "ok", "thanks", "okay"]:
            return {
                "is_ambiguous": True,
                "ambiguity_type": "too_short",
                "confidence": 0.6,
                "missing_context": ["Need more details"]
            }
        
        return None
    
    def _infer_missing_context(self, text: str, ambig_type: str) -> list:
        """Infer what context is missing."""
        missing = []
        
        if ambig_type == "pronoun_reference":
            missing.append("What are you referring to?")
            if self.last_context.get("intent") == "QUESTION":
                missing.append(f"Previous topic: {self.last_context.get('query', '')}")
        
        elif ambig_type == "vague_verb":
            missing.append("What action do you want?")
            if self.last_context.get("entities", {}).get("target"):
                missing.append(f"For: {self.last_context['entities']['target']}")
        
        elif ambig_type == "missing_subject":
            missing.append("Cost/price of what?")
            if self.entity_history:
                missing.append(f"Recent items: {list(self.entity_history.values())[:2]}")
        
        elif ambig_type == "assumed_knowledge":
            missing.append("Who/what are you asking about?")
        
        return missing
    
    def rephrase_query(self, text: str) -> Dict[str, Any]:
        """
        Rephrase an ambiguous query for clarity.
        
        Returns:
            {
                "original": str,
                "rephrased": str,
                "confidence": float,
                "needs_user_clarification": bool,
                "clarification_questions": List[str]
            }
        """
        ambiguity = self.detect_ambiguity(text)
        
        if not ambiguity:
            return {
                "original": text,
                "rephrased": text,
                "confidence": 1.0,
                "needs_user_clarification": False,
                "clarification_questions": []
            }
        
        # If truly ambiguous, ask user first
        if ambiguity["confidence"] < 0.7:
            return {
                "original": text,
                "rephrased": text,
                "confidence": ambiguity["confidence"],
                "needs_user_clarification": True,
                "clarification_questions": ambiguity["missing_context"]
            }
        
        # Try to rephrase with context
        rephrased = self._apply_rephrasing(text, ambiguity)
        
        return {
            "original": text,
            "rephrased": rephrased,
            "confidence": ambiguity["confidence"],
            "needs_user_clarification": False,
            "clarification_questions": []
        }
    
    def _apply_rephrasing(self, text: str, ambiguity: Dict[str, Any]) -> str:
        """Apply specific rephrasing rules."""
        ambig_type = ambiguity["ambiguity_type"]
        text_lower = text.lower().strip()
        
        # Pronoun reference rephrasing
        if ambig_type == "pronoun_reference":
            if text_lower.startswith(("how much", "how many")):
                entity = self.last_context.get("entities", {}).get("object") or "that"
                return f"What is the quantity/amount of {entity}?"
            elif re.search(r"^what(?:'s)? (?:is )?(?:it|that)", text_lower):
                prev_query = self.last_context.get("query", "")
                return f"Explain further about: {prev_query}"
        
        # Vague verb rephrasing
        elif ambig_type == "vague_verb":
            if re.search(r"^can i", text_lower, re.IGNORECASE):
                target = self.last_context.get("entities", {}).get("target") or "this"
                return f"Is it possible to {text.replace('can i ', '')[:30]}?"
            elif re.search(r"^(?:do|make|have|get)", text_lower):
                return f"Can you help me with {text}?"
        
        # Missing subject rephrasing
        elif ambig_type == "missing_subject":
            if re.search(r"^(?:cost|price)", text_lower):
                target = self.entity_history.get("target") or self.last_context.get("entities", {}).get("target") or "it"
                return f"What is the price of {target}?"
            elif re.search(r"^(?:available|open)", text_lower):
                return f"Is it available or open?"
        
        # Incomplete query rephrasing
        elif ambig_type == "incomplete":
            if text_lower in ("how", "what", "when", "where", "why"):
                prev = self.last_context.get("query", "")
                return f"{text.capitalize()} about {prev}?" if prev else text
        
        return text  # Fallback - return original
    
    def suggest_clarification(self, text: str) -> Optional[str]:
        """
        Suggest a clarifying question if needed.
        
        Returns: Clarification prompt or None
        """
        result = self.rephrase_query(text)
        
        if result["needs_user_clarification"]:
            questions = result["clarification_questions"]
            if questions:
                return f"Could you clarify? {questions[0]}"
        
        return None
    
    def improve_query(self, text: str, intent: str, entities: Dict[str, Any]) -> str:
        """
        Polish a query for better LLM understanding.
        Adds more structure without changing meaning.
        """
        rephrased = self.rephrase_query(text)["rephrased"]
        
        # Add intent hints if it's a QUESTION
        if intent == "QUESTION":
            if not rephrased.endswith("?"):
                rephrased += "?"
        
        # Add context hints if available
        if entities and "target" in entities:
            if "about" not in rephrased.lower() and "of" not in rephrased.lower():
                rephrased = f"{rephrased} regarding {entities['target']}"
        
        return rephrased


# Singleton
QUERY_REPHRASER = QueryRephraser()


def rephrase_query(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Public function to rephrase a query.
    
    Args:
        text: User query
        context: Optional context dict with previous intent/entities
    
    Returns:
        {
            "original": str,
            "rephrased": str,
            "confidence": float,
            "needs_clarification": bool,
            "clarification_prompt": str (if needed)
        }
    """
    if context:
        QUERY_REPHRASER.set_context(context)
    
    result = QUERY_REPHRASER.rephrase_query(text)
    
    return {
        "original": result["original"],
        "rephrased": result["rephrased"],
        "confidence": result["confidence"],
        "needs_clarification": result["needs_user_clarification"],
        "clarification_prompt": QUERY_REPHRASER.suggest_clarification(text) if result["needs_user_clarification"] else None
    }
