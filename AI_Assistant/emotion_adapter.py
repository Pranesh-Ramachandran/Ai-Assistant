"""
Emotion & Tone Adaptation for Jarvis AI
Adapts response tone based on context and user patterns
"""

import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class EmotionTone(Enum):
    NEUTRAL = "neutral"
    ENCOURAGING = "encouraging"
    SYMPATHETIC = "sympathetic"
    ALERT = "alert"
    BRIEF = "brief"
    EXCITED = "excited"
    CALM = "calm"
    IMPRESSED = "impressed"
    CONCERNED = "concerned"
    PLAYFUL = "playful"
    CONFIDENT = "confident"

@dataclass
class ContextClue:
    keyword: str
    tone: EmotionTone
    response_modifier: str

class EmotionAdapter:
    def __init__(self):
        self.recent_commands = []  # Track last 5 commands
        self.command_history = {}  # Count command repetitions
        self.user_mood_score = 0  # Track user satisfaction (-10 to +10)
        self.last_interaction = None
        self.session_start = datetime.now()
        
        # Expanded context-based tone mapping
        self.context_clues = [
            # Weather contexts
            ContextClue("storm", EmotionTone.ALERT, "Heads up — "),
            ContextClue("rain", EmotionTone.ALERT, "☔ "),
            ContextClue("heavy rain", EmotionTone.ALERT, "Heads up — looks like heavy rain out there ☔"),
            ContextClue("sunny", EmotionTone.EXCITED, "Beautiful day out there! "),
            ContextClue("perfect weather", EmotionTone.EXCITED, "What a gorgeous day, sir! "),
            
            # Gaming contexts
            ContextClue("low score", EmotionTone.SYMPATHETIC, "Oof — tough round. "),
            ContextClue("high score", EmotionTone.EXCITED, "Wow! Crushing it, sir! "),
            ContextClue("new record", EmotionTone.IMPRESSED, "Incredible! New personal best! "),
            ContextClue("game over", EmotionTone.ENCOURAGING, "Want to try again? "),
            ContextClue("victory", EmotionTone.EXCITED, "Outstanding work, sir! "),
            
            # Task completion
            ContextClue("completed quickly", EmotionTone.IMPRESSED, "That was fast! "),
            ContextClue("finished early", EmotionTone.EXCITED, "Ahead of schedule — nice! "),
            ContextClue("100% complete", EmotionTone.CONFIDENT, "Perfect execution, sir. "),
            
            # Time-based contexts
            ContextClue("late night", EmotionTone.CONCERNED, "Getting late, sir. "),
            ContextClue("early morning", EmotionTone.CALM, "Good morning, sir. "),
            ContextClue("working late", EmotionTone.CONCERNED, "Long day, sir? "),
            
            # Error contexts
            ContextClue("error", EmotionTone.SYMPATHETIC, "Hmm, "),
            ContextClue("not found", EmotionTone.SYMPATHETIC, "Can't seem to find that. "),
            ContextClue("timeout", EmotionTone.SYMPATHETIC, "Taking longer than expected. "),
            ContextClue("connection failed", EmotionTone.CONCERNED, "Network seems spotty. "),
            
            # Success contexts
            ContextClue("successful", EmotionTone.CONFIDENT, "Done and dusted, sir. "),
            ContextClue("perfect", EmotionTone.IMPRESSED, "Flawless! "),
            ContextClue("excellent", EmotionTone.EXCITED, "Superb work! "),
        ]

    def track_command(self, command: str):
        """Track user commands for repetition detection"""
        # Clean command for comparison
        clean_cmd = command.lower().strip()
        
        # Add to recent commands (keep last 5)
        self.recent_commands.append(clean_cmd)
        if len(self.recent_commands) > 5:
            self.recent_commands.pop(0)
            
        # Count repetitions
        self.command_history[clean_cmd] = self.command_history.get(clean_cmd, 0) + 1

    def is_repeated_command(self, command: str) -> bool:
        """Check if command was recently repeated"""
        clean_cmd = command.lower().strip()
        return self.recent_commands.count(clean_cmd) >= 2

    def get_tone_for_context(self, context: str) -> Optional[EmotionTone]:
        """Determine appropriate tone based on context"""
        context_lower = context.lower()
        
        for clue in self.context_clues:
            if clue.keyword in context_lower:
                return clue.tone
        return None

    def adapt_response(self, base_response: str, context: str = "", command: str = "") -> str:
        """
        Adapt response based on context and user patterns
        
        Args:
            base_response: Original response text
            context: Context information (weather, game state, etc.)
            command: User command that triggered response
            
        Returns:
            Adapted response with appropriate tone
        """
        # Track this command and update mood
        if command:
            self.track_command(command)
            self._update_mood(context)
        
        # Add time-based context
        time_context = self._get_time_context()
        full_context = f"{context} {time_context}".strip()
        
        # Check for repeated commands - use brief response
        if command and self.is_repeated_command(command):
            return self._make_brief(base_response)
        
        # Apply context-based tone adaptation
        tone = self.get_tone_for_context(full_context)
        if tone:
            return self._apply_tone(base_response, tone, full_context)
        
        # Apply mood-based subtle adjustments
        return self._apply_mood_adjustment(base_response)

    def _make_brief(self, response: str) -> str:
        """Make response brief for repeated commands"""
        # Common brief acknowledgements
        brief_responses = {
            "weather": "Still the same, sir",
            "time": "Same time, sir", 
            "status": "All good, sir",
            "volume": "Adjusted, sir",
            "lights": "Done, sir"
        }
        
        # Try to find a brief version
        for key, brief in brief_responses.items():
            if key in response.lower():
                return brief
                
        # Default brief response
        if len(response) > 20:
            return "Got it, sir"
        return response

    def _get_time_context(self) -> str:
        """Get time-based contextual information"""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            return "early morning"
        elif 22 <= hour or hour < 5:
            return "late night"
        elif now - self.session_start > timedelta(hours=8):
            return "working late"
        return ""
    
    def _update_mood(self, context: str):
        """Update user mood based on context"""
        context_lower = context.lower()
        
        # Positive indicators
        if any(word in context_lower for word in ["success", "complete", "perfect", "excellent", "high score"]):
            self.user_mood_score = min(10, self.user_mood_score + 1)
        
        # Negative indicators  
        elif any(word in context_lower for word in ["error", "failed", "timeout", "not found", "low score"]):
            self.user_mood_score = max(-10, self.user_mood_score - 1)
    
    def _apply_mood_adjustment(self, response: str) -> str:
        """Apply subtle mood-based adjustments"""
        if self.user_mood_score >= 3:
            # User seems happy - be more enthusiastic
            if random.random() < 0.3:  # 30% chance
                return f"{response} 👍"
        elif self.user_mood_score <= -3:
            # User seems frustrated - be more supportive
            if "sir" not in response.lower():
                return f"{response}, sir"
        return response
    
    def _apply_tone(self, response: str, tone: EmotionTone, context: str) -> str:
        """Apply specific tone to response with soft personality limits"""
        context_lower = context.lower()
        
        # Find matching context clue for modifier
        for clue in self.context_clues:
            if clue.keyword in context_lower and clue.tone == tone:
                # Apply the modifier
                if clue.response_modifier.endswith(" — "):
                    return f"{clue.response_modifier}{response.lower()}"
                elif clue.response_modifier.endswith(" "):
                    # Ends with space but not " — ", so it's a prefix
                    return f"{clue.response_modifier}{response}"
                else:
                    # No space, so replace entirely only if response is empty/vague
                    if not response or len(response.strip()) < 3:
                        return clue.response_modifier
                    # Otherwise prepend it
                    return f"{clue.response_modifier}{response}"
        
        # Soft personality limits - keep responses polite, warm, slightly friendly
        tone_responses = {
            EmotionTone.ENCOURAGING: ["You're doing well, sir. ", "That's good, sir. ", "Nice work, sir. "],
            EmotionTone.SYMPATHETIC: ["I understand, sir. ", "I see, sir. ", "Let me help with that, sir. "],
            EmotionTone.ALERT: ["Just to let you know, sir — ", "Please note, sir — ", "For your information, sir — "],
            EmotionTone.EXCITED: ["Excellent, sir! ", "Very good, sir! ", "Well done, sir! "],
            EmotionTone.IMPRESSED: ["That's impressive, sir. ", "Very nice, sir. ", "Good job, sir. "],
            EmotionTone.CONFIDENT: ["Certainly, sir. ", "Of course, sir. ", "Absolutely, sir. "],
            EmotionTone.CONCERNED: ["I want to make sure, sir — ", "Let me check, sir — ", "Just to be safe, sir — "],
            EmotionTone.CALM: ["Understood, sir. ", "Very well, sir. ", "Right away, sir. "]
        }
        
        if tone in tone_responses:
            prefix = random.choice(tone_responses[tone])
            return f"{prefix}{response.lower() if prefix.endswith(' — ') else response}"
            
        return response

# Global instance
emotion_adapter = EmotionAdapter()

def adapt_jarvis_response(response: str, context: str = "", command: str = "") -> str:
    """
    Main function to adapt Jarvis responses
    
    Usage:
        adapted = adapt_jarvis_response("The weather is stormy today", 
                                      context="heavy rain storm", 
                                      command="weather")
    """
    return emotion_adapter.adapt_response(response, context, command)