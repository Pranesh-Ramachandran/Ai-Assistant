"""
Tamil Speech System - STT/TTS with Language Detection
Implements Tamil + English multilingual support with natural voice
"""

import time
from enum import Enum
from typing import Optional, Dict, Tuple
from capability_profiles import get_profile_config

class Language(Enum):
    TAMIL = "ta"
    ENGLISH = "en"
    MIXED = "mixed"

class TTSMode(Enum):
    HIGH_QUALITY = "high"    # Coqui neural voice
    BALANCED = "balanced"    # Google/Android TTS
    LOW_POWER = "low"       # Lightweight native

class TamilSpeechEngine:
    def __init__(self):
        self.conversation_language = "auto"  # "ta", "en", "auto"
        self.last_detected_language = Language.ENGLISH
        
        # Tamil keywords for mixed language detection
        self.tamil_keywords = {
            'pannunga', 'sollu', 'kodu', 'vaanga', 'podu', 'eduthu',
            'weather', 'time', 'light', 'fan', 'music', 'call'
        }
        
        # Language switching commands
        self.language_switch_commands = {
            # English commands
            'reply in tamil': 'ta',
            'speak in tamil': 'ta', 
            'switch to tamil': 'ta',
            'tamil mode': 'ta',
            'speak in english': 'en',
            'reply in english': 'en',
            'switch to english': 'en',
            'english mode': 'en',
            
            # Tamil commands
            'தமிழில் பேசு': 'ta',
            'இனி எல்லாம் தமிழில் பேசு': 'ta',
            'english la pesu': 'en',
            'english reply pannunga': 'en',
            'tamil la pesu': 'ta'
        }

    def detect_language(self, text: str) -> Language:
        """Lightweight language detection with mixed language support"""
        if not text:
            return self.last_detected_language
            
        text_lower = text.lower().strip()
        
        # Check for explicit language switching first
        for command, target_lang in self.language_switch_commands.items():
            if command in text_lower:
                return Language.TAMIL if target_lang == 'ta' else Language.ENGLISH
        
        # Count language indicators
        tamil_chars = sum(1 for char in text if '\u0b80' <= char <= '\u0bff')
        english_chars = sum(1 for char in text if char.isalpha() and char.isascii())
        tamil_keywords = sum(1 for keyword in self.tamil_keywords if keyword in text_lower)
        
        # Determine dominant language
        tamil_score = tamil_chars + (tamil_keywords * 2)
        english_score = english_chars
        
        if tamil_score > english_score:
            return Language.TAMIL if english_score == 0 else Language.MIXED
        elif english_score > 0:
            return Language.ENGLISH
        
        return self.last_detected_language

    def listen_tamil_stt(self) -> Optional[str]:
        """Simulate listening and converting Tamil speech to text"""
        config = get_profile_config()
        
        # Play listening chime
        self._play_chime("start")
        
        # Simulate STT processing time based on performance mode
        processing_time = config.response_timeout * 0.3
        time.sleep(min(processing_time, 1.0))  # Cap at 1 second for demo
        
        # Play done chime
        self._play_chime("end")
        
        # Return simulated speech input
        return "weather sollu"  # Simulated Tamil input

    def process_multilingual_intent(self, text: str) -> Tuple[str, Language]:
        """Process intent with conversation language state management"""
        input_language = self.detect_language(text)
        
        # Check for explicit language switching
        if self._is_language_switch_command(text):
            new_lang = self._extract_target_language(text)
            self.conversation_language = new_lang
            return "language_switch", Language.TAMIL if new_lang == 'ta' else Language.ENGLISH
        
        # Update conversation language based on input
        if input_language != Language.MIXED:
            if self.conversation_language == "auto":
                self.conversation_language = input_language.value
            self.last_detected_language = input_language
        
        # Determine response language
        response_language = self._get_response_language(input_language)
        
        # Extract intent
        if input_language == Language.TAMIL or input_language == Language.MIXED:
            intent = self._extract_tamil_intent(text)
        else:
            intent = self._extract_english_intent(text)
            
        return intent, response_language
    
    def _is_language_switch_command(self, text: str) -> bool:
        """Check if text contains language switching command"""
        text_lower = text.lower().strip()
        return any(command in text_lower for command in self.language_switch_commands.keys())
    
    def _extract_target_language(self, text: str) -> str:
        """Extract target language from switching command"""
        text_lower = text.lower().strip()
        for command, target_lang in self.language_switch_commands.items():
            if command in text_lower:
                return target_lang
        return "en"
    
    def _get_response_language(self, input_language: Language) -> Language:
        """Determine response language based on conversation state"""
        if self.conversation_language == "ta":
            return Language.TAMIL
        elif self.conversation_language == "en":
            return Language.ENGLISH
        else:  # auto mode
            if input_language == Language.MIXED:
                # For mixed input, use last detected pure language
                return self.last_detected_language
            return input_language

    def _extract_tamil_intent(self, text: str) -> str:
        """Extract intent from Tamil/mixed text"""
        text_lower = text.lower()
        
        # Music intents
        if any(word in text_lower for word in ['play', 'music', 'song', 'paadal', 'paatu', 'youtube']):
            return "music_play"
        
        # Weather intents
        if any(word in text_lower for word in ['weather', 'kaalam', 'sollu']):
            return "weather_query"
        
        # Light control
        if any(word in text_lower for word in ['light', 'vilakku']) and ('on' in text_lower or 'pannunga' in text_lower):
            return "light_on"
        if any(word in text_lower for word in ['light', 'vilakku']) and 'off' in text_lower:
            return "light_off"
            
        # Time query
        if any(word in text_lower for word in ['time', 'neram', 'mani']):
            return "time_query"
            
        return "unknown"

    def _extract_english_intent(self, text: str) -> str:
        """Extract intent from English text"""
        text_lower = text.lower()
        
        # Music intents
        if any(word in text_lower for word in ['play', 'music', 'song', 'youtube', 'playlist']):
            return "music_play"
        
        if 'weather' in text_lower:
            return "weather_query"
        elif 'time' in text_lower:
            return "time_query"
        elif 'light' in text_lower and 'on' in text_lower:
            return "light_on"
        elif 'light' in text_lower and 'off' in text_lower:
            return "light_off"
            
        return "unknown"

    def speak_tamil_tts(self, text: str, language: Language = None):
        """Convert text to speech with real TTS engines"""
        if not text:
            return
            
        config = get_profile_config()
        
        # Select language for TTS
        if language is None:
            language = self.current_language
            
        lang_code = "ta" if language == Language.TAMIL else "en"
        
        try:
            # Try pyttsx3 first (works offline)
            import pyttsx3
            engine = pyttsx3.init()
            
            # Set voice properties
            voices = engine.getProperty('voices')
            for voice in voices:
                if lang_code == "ta" and ('tamil' in voice.name.lower() or 'ta' in voice.id.lower()):
                    engine.setProperty('voice', voice.id)
                    break
                elif lang_code == "en" and ('english' in voice.name.lower() or 'en' in voice.id.lower()):
                    engine.setProperty('voice', voice.id)
                    break
            
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            engine.say(text)
            engine.runAndWait()
            
        except ImportError:
            try:
                # Fallback to gTTS
                from gtts import gTTS
                import pygame
                import io
                
                tts = gTTS(text=text, lang=lang_code, slow=False)
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)
                
                pygame.mixer.init()
                pygame.mixer.music.load(audio_buffer)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
            except Exception as e:
                # Final fallback - Windows SAPI
                try:
                    import win32com.client
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(text)
                except:
                    print(f"🗣️ {text}")

    def _play_chime(self, chime_type: str):
        """Play Alexa-style chimes"""
        config = get_profile_config()
        
        if not config.animation_enabled:
            return  # Skip chimes in low power mode
            
        if chime_type == "start":
            print("🔊 *listening chime*")
        elif chime_type == "end":
            print("🔊 *processing chime*")

    def get_natural_response(self, intent: str, language: Language) -> str:
        """Generate natural conversational responses"""
        responses = {
            Language.TAMIL: {
                "weather_query": "இன்றைக்கு வானிலை நல்லா இருக்கு",
                "time_query": "இப்ப மணி 3:30 ஆகிருக்கு", 
                "light_on": "சரி, லைட் ஆன் செய்து வைக்கிறேன்",
                "light_off": "சரி, லைட் ஆஃப் செய்துட்டேன்",
                "music_play": "சரி, YouTube Music-ல பாடல்கள் ஓடுக்கிறேன் 🎵",
                "language_switch": "சரி, இனிமேல் தமிழில் பேசுவேன்",
                "unknown": "ஒரு நிமிஷம்... பார்க்கிறேன்"
            },
            Language.ENGLISH: {
                "weather_query": "The weather looks good today",
                "time_query": "It's 3:30 PM right now",
                "light_on": "Sure, turning the light on", 
                "light_off": "Alright, light's off",
                "music_play": "Sure — opening YouTube Music 🎵",
                "language_switch": "Sure, I'll speak in English from now on",
                "unknown": "Hmm, let me check that for you"
            }
        }
        
        lang_responses = responses.get(language, responses[Language.ENGLISH])
        return lang_responses.get(intent, lang_responses["unknown"])

# Global instance
tamil_speech = TamilSpeechEngine()

def simulate_tamil_interaction():
    """Simulate Tamil speech interaction with conversation state"""
    print("🎤 Tamil Speech System Ready")
    print("Simulating conversation with language switching\n")
    
    engine = TamilSpeechEngine()
    
    # Simulate conversation flow
    interactions = [
        "weather sollu",           # Mixed language
        "switch to tamil mode",    # Language switch
        "time kodu",              # Should respond in Tamil
        "speak in english",       # Switch back
        "light on please"         # Should respond in English
    ]
    
    for i, text in enumerate(interactions, 1):
        print(f"--- Interaction {i} ---")
        print(f"User: {text}")
        
        # Process intent
        intent, response_lang = engine.process_multilingual_intent(text)
        print(f"Intent: {intent}, Response Language: {response_lang.value}")
        print(f"Conversation State: {engine.conversation_language}")
        
        # Generate and speak response
        response = engine.get_natural_response(intent, response_lang)
        engine.speak_tamil_tts(response, response_lang)
        print()