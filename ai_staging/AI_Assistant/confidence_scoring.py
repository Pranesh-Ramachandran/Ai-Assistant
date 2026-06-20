"""
Confidence Scoring - Tier 2 Feature
Assesses AI confidence in responses and flags uncertain answers.

Examples:
  Response: "The weather in Kerala is 32°C"
    -> Confidence: 0.95 (data from weather API)
  
  Response: "I'm not sure, but it might be..."
    -> Confidence: 0.4 (hedging language detected)
  
  Response: "That's outside my knowledge"
    -> Confidence: 0.1 (explicit inability)
"""

import re
from typing import Dict, Any, Tuple
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence level classifications."""
    VERY_HIGH = (0.9, 1.0)    # Definite facts, verified data
    HIGH = (0.75, 0.9)         # Confident response
    MEDIUM = (0.5, 0.75)       # Fairly confident but with caveats
    LOW = (0.25, 0.5)          # Uncertain, speculation
    VERY_LOW = (0.0, 0.25)     # Guessing, admission of ignorance


class ConfidenceScorer:
    """
    Scores confidence in AI responses based on multiple factors.
    """
    
    # Language indicators of uncertainty
    HEDGING_WORDS = {
        "maybe": 0.3,
        "perhaps": 0.3,
        "might": 0.35,
        "could": 0.35,
        "possibly": 0.3,
        "apparently": 0.4,
        "allegedly": 0.3,
        "supposedly": 0.3,
        "somewhat": 0.4,
        "sort of": 0.3,
        "kind of": 0.3,
        "i think": 0.5,
        "i believe": 0.5,
        "in my opinion": 0.45,
        "likely": 0.6,
        "probably": 0.6,
        "seems": 0.5,
        "appears": 0.5,
    }
    
    # Language indicators of certainty
    CERTAINTY_WORDS = {
        "definitely": 0.95,
        "certainly": 0.95,
        "absolutely": 0.95,
        "clearly": 0.9,
        "obviously": 0.9,
        "undoubtedly": 0.95,
        "no doubt": 0.93,
        "for sure": 0.85,
        "without question": 0.95,
        "it is": 0.8,
        "this is": 0.8,
        "exactly": 0.9,
        "precisely": 0.9,
        "verified": 0.95,
        "confirmed": 0.95,
    }
    
    # Phrases indicating inability to answer
    INABILITY_PHRASES = {
        "i don't know": 0.1,
        "i'm not sure": 0.2,
        "i can't": 0.1,
        "i cannot": 0.1,
        "outside my knowledge": 0.05,
        "beyond my": 0.1,
        "not equipped to": 0.1,
        "unable to": 0.1,
        "no information": 0.05,
        "don't have": 0.1,
        "can't help": 0.15,
    }
    
    # Source reliability scores
    SOURCE_CONFIDENCE = {
        "weather_api": 0.95,
        "time_system": 0.98,
        "location_data": 0.85,
        "rule_based": 0.8,
        "llm_groq": 0.75,
        "llm_gemini": 0.75,
        "web_search": 0.65,
        "user_memory": 0.7,
        "offline": 0.5,
    }
    
    def score_response(self, response: str, source: str = "llm_groq", 
                      intent: str = "REQUEST", has_context: bool = True) -> Dict[str, Any]:
        """
        Score confidence in a response.
        
        Args:
            response: The AI response text
            source: Where the response came from (weather_api, llm_groq, etc.)
            intent: The user's intent (QUESTION, REQUEST, etc.)
            has_context: Whether we have conversation context
        
        Returns:
            {
                "confidence_score": float (0-1),
                "confidence_level": str (VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW),
                "factors": Dict (contributing factors),
                "should_clarify": bool,
                "clarification_prompt": str (if needed)
            }
        """
        response_lower = response.lower()
        
        # Start with source baseline
        base_score = self.SOURCE_CONFIDENCE.get(source, 0.6)
        
        # Check for inability indicators
        inability_score = self._check_inability(response_lower)
        if inability_score is not None:
            return {
                "confidence_score": inability_score,
                "confidence_level": self._score_to_level(inability_score),
                "factors": {
                    "source": source,
                    "direct_admission": inability_score
                },
                "should_clarify": True,
                "clarification_prompt": "Would you like me to search for this information or provide what I know?"
            }
        
        # Check for hedging language
        hedging_score = self._check_hedging(response_lower)
        
        # Check for certainty language
        certainty_score = self._check_certainty(response_lower)
        
        # Check response structure
        structure_score = self._check_response_structure(response)
        
        # Combine scores
        # Certainty overrides hedging if present
        if certainty_score > 0.7:
            linguistic_score = certainty_score
        elif hedging_score < 0.7:
            linguistic_score = hedging_score
        else:
            linguistic_score = (certainty_score + (1 - hedging_score)) / 2
        
        # Adjust for context
        context_adjustment = 0.05 if has_context else -0.1
        
        # Adjust for intent type
        intent_adjustment = {
            "QUESTION": 0.0,
            "REQUEST": -0.05,
            "BOOKING": -0.1,  # Need high confidence for bookings
            "INFORMATION": 0.05,
            "GREETING": 0.1,
        }.get(intent, 0.0)
        
        # Final score
        final_score = base_score * 0.4 + linguistic_score * 0.4 + structure_score * 0.2
        final_score += context_adjustment + intent_adjustment
        final_score = max(0.0, min(1.0, final_score))  # Clamp to [0, 1]
        
        return {
            "confidence_score": round(final_score, 2),
            "confidence_level": self._score_to_level(final_score),
            "factors": {
                "source": source,
                "linguistic": round(linguistic_score, 2),
                "structure": round(structure_score, 2),
                "intent": intent,
                "has_context": has_context
            },
            "should_clarify": final_score < 0.6,
            "clarification_prompt": self._get_clarification_prompt(final_score, response)
        }
    
    def _check_inability(self, text: str) -> float:
        """Check for phrases indicating inability to answer."""
        for phrase, score in self.INABILITY_PHRASES.items():
            if phrase in text:
                return score
        return None
    
    def _check_hedging(self, text: str) -> float:
        """Check for hedging/uncertain language."""
        max_hedging = 1.0
        hedging_found = False
        
        for word, score in self.HEDGING_WORDS.items():
            if word in text:
                hedging_found = True
                max_hedging = min(max_hedging, score)
        
        if not hedging_found:
            return 0.8  # No hedging = more confident
        
        return max_hedging
    
    def _check_certainty(self, text: str) -> float:
        """Check for certainty language."""
        max_certainty = 0.0
        
        for word, score in self.CERTAINTY_WORDS.items():
            if word in text:
                max_certainty = max(max_certainty, score)
        
        return max_certainty
    
    def _check_response_structure(self, response: str) -> float:
        """Check quality of response structure."""
        score = 0.6  # Base score
        
        # Longer, detailed responses are more confident
        word_count = len(response.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1
        
        # Responses with multiple sentences show structure
        sentence_count = len(re.split(r'[.!?]+', response))
        if sentence_count >= 2:
            score += 0.1
        
        # Specific details increase confidence
        if re.search(r'\d+', response):  # Contains numbers
            score += 0.1
        
        if re.search(r'\b(because|therefore|since|as|due to)\b', response, re.IGNORECASE):
            score += 0.05  # Provides reasoning
        
        return min(1.0, score)
    
    def _score_to_level(self, score: float) -> str:
        """Convert numeric score to confidence level."""
        if score >= 0.9:
            return "VERY_HIGH"
        elif score >= 0.75:
            return "HIGH"
        elif score >= 0.5:
            return "MEDIUM"
        elif score >= 0.25:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _get_clarification_prompt(self, score: float, response: str) -> str:
        """Generate appropriate clarification prompt based on confidence."""
        if score < 0.2:
            return "I'm not confident in this answer. Would you like me to search for more reliable information?"
        elif score < 0.5:
            return "I'm not entirely sure about this. Can I help clarify or would you like another perspective?"
        elif score < 0.7:
            return "I think that's right, but would you like me to verify that information?"
        else:
            return None
    
    def adjust_for_conversation(self, response: str, conversation_context: str) -> float:
        """
        Adjust confidence based on conversation context.
        
        Higher confidence if:
        - Response follows naturally from conversation
        - Same topic as previous messages
        - User has confirmed similar responses before
        """
        base_score = self.score_response(response)["confidence_score"]
        
        # If similar to conversation context, boost confidence slightly
        if conversation_context:
            # Very simple: if response mentions words from context, boost by 5%
            context_words = set(conversation_context.lower().split())
            response_words = set(response.lower().split())
            overlap = len(context_words & response_words)
            
            if overlap > 3:
                base_score = min(1.0, base_score + 0.05)
        
        return round(base_score, 2)


# Singleton instance
CONFIDENCE_SCORER = ConfidenceScorer()


def score_response(response: str, source: str = "llm_groq", intent: str = "REQUEST") -> Dict[str, Any]:
    """
    Public function to score response confidence.
    
    Returns:
        {
            "confidence": float (0-1),
            "level": str,
            "should_clarify": bool,
            "clarification": str (if needed)
        }
    """
    result = CONFIDENCE_SCORER.score_response(response, source=source, intent=intent)
    
    return {
        "confidence": result["confidence_score"],
        "level": result["confidence_level"],
        "should_clarify": result["should_clarify"],
        "clarification": result.get("clarification_prompt"),
        "factors": result["factors"]
    }
