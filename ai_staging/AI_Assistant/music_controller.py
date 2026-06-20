"""
Jarvis YouTube Music Controller
Clean, battery-friendly music control using Android intents
"""

import subprocess
import webbrowser
from typing import Optional, Tuple
from enum import Enum
from tamil_speech_simple import Language
from emotion_adapter import adapt_jarvis_response

class MusicApp(Enum):
    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"
    AUTO = "auto"

class JarvisMusicController:
    def __init__(self):
        self.last_app = MusicApp.YOUTUBE_MUSIC
        self.music_preferences = {}
        
        # Music intent patterns
        self.music_keywords = {
            # YouTube Music indicators
            'music': MusicApp.YOUTUBE_MUSIC,
            'songs': MusicApp.YOUTUBE_MUSIC,
            'playlist': MusicApp.YOUTUBE_MUSIC,
            'album': MusicApp.YOUTUBE_MUSIC,
            'melody': MusicApp.YOUTUBE_MUSIC,
            
            # YouTube indicators  
            'video': MusicApp.YOUTUBE,
            'tutorial': MusicApp.YOUTUBE,
            'comedy': MusicApp.YOUTUBE,
            'movie': MusicApp.YOUTUBE,
            'trailer': MusicApp.YOUTUBE
        }
        
        # Tamil music keywords
        self.tamil_music_words = {
            'paadal', 'paatu', 'melody', 'gaana', 'kuthu', 'bgm'
        }

    def process_music_command(self, command: str, language: Language) -> Tuple[str, str, MusicApp]:
        """
        Process voice command and extract music intent
        
        Returns:
            (search_query, response_text, target_app)
        """
        command_lower = command.lower().strip()
        
        # Extract search query and determine app
        search_query, target_app = self._extract_music_intent(command_lower)
        
        # Generate natural response
        response = self._generate_music_response(search_query, target_app, language)
        
        return search_query, response, target_app

    def _extract_music_intent(self, command: str) -> Tuple[str, MusicApp]:
        """Extract search query and determine target app"""
        
        # Remove command prefixes
        prefixes = ['play ', 'search ', 'open ', 'find ', 'jarvis ']
        for prefix in prefixes:
            if command.startswith(prefix):
                command = command[len(prefix):].strip()
        
        # Remove app-specific suffixes
        suffixes = [
            ' on youtube', ' in youtube', ' youtube la',
            ' on youtube music', ' in youtube music', 
            ' youtube music la', ' pannunga', ' kodu', ' sollu'
        ]
        
        target_app = MusicApp.AUTO
        clean_query = command
        
        for suffix in suffixes:
            if suffix in command:
                clean_query = command.replace(suffix, '').strip()
                if 'youtube music' in suffix:
                    target_app = MusicApp.YOUTUBE_MUSIC
                elif 'youtube' in suffix:
                    target_app = MusicApp.YOUTUBE
                break
        
        # Auto-detect app based on keywords if not specified
        if target_app == MusicApp.AUTO:
            target_app = self._detect_music_app(clean_query)
        
        return clean_query, target_app

    def _detect_music_app(self, query: str) -> MusicApp:
        """Auto-detect appropriate music app based on query"""
        
        # Check for explicit app keywords
        for keyword, app in self.music_keywords.items():
            if keyword in query:
                return app
        
        # Check for Tamil music words (prefer YouTube Music)
        for tamil_word in self.tamil_music_words:
            if tamil_word in query:
                return MusicApp.YOUTUBE_MUSIC
        
        # Default to last used app or YouTube Music
        return self.last_app

    def _generate_music_response(self, query: str, app: MusicApp, language: Language) -> str:
        """Generate natural response for music command"""
        
        app_names = {
            MusicApp.YOUTUBE: "YouTube",
            MusicApp.YOUTUBE_MUSIC: "YouTube Music"
        }
        
        if language == Language.TAMIL:
            if app == MusicApp.YOUTUBE_MUSIC:
                responses = [
                    f"சரி, YouTube Music-ல {query} ஓடுக்கிறேன் 🎵",
                    f"YouTube Music-ல {query} பாடல்கள் ஓடுக்கிறேன் 🎶"
                ]
            else:
                responses = [
                    f"சரி, YouTube-ல {query} ஓபன் பண்றேன் 📺",
                    f"YouTube-ல {query} காட்டுறேன் 🎬"
                ]
        else:
            if app == MusicApp.YOUTUBE_MUSIC:
                responses = [
                    f"Sure — opening {query} in YouTube Music 🎵",
                    f"Playing {query} on YouTube Music 🎶"
                ]
            else:
                responses = [
                    f"Got it — opening {query} on YouTube 📺", 
                    f"Searching {query} on YouTube 🎬"
                ]
        
        import random
        return random.choice(responses)

    def launch_music_app(self, query: str, app: MusicApp) -> bool:
        """
        Launch music app with search query
        
        For demo purposes, uses web browser.
        In real Android app, would use Android intents.
        """
        
        try:
            if app == MusicApp.YOUTUBE_MUSIC:
                # YouTube Music search URL
                url = f"https://music.youtube.com/search?q={query.replace(' ', '+')}"
                self._play_chime()
                webbrowser.open(url)
                
            else:  # YouTube
                # YouTube search URL  
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                self._play_chime()
                webbrowser.open(url)
            
            # Remember last used app
            self.last_app = app
            return True
            
        except Exception as e:
            print(f"Failed to launch music app: {e}")
            return False

    def _play_chime(self):
        """Play short chime before launching music"""
        print("🎵 *music chime*")

    def get_music_suggestions(self, language: Language) -> str:
        """Get contextual music suggestions"""
        
        if language == Language.TAMIL:
            suggestions = [
                "கடைசியா என்ன பாடல் கேட்டீங்க?",
                "Tamil melody songs வேணுமா?",
                "YouTube Music-ல playlist continue பண்ணலாமா?"
            ]
        else:
            suggestions = [
                "Want to continue your last playlist?",
                "Should I play some relaxing music?",
                "Do you want YouTube or YouTube Music?"
            ]
        
        import random
        return random.choice(suggestions)

# Integration with existing Tamil speech system
def handle_music_command(command: str, language: Language) -> str:
    """
    Handle music commands in Jarvis speech system
    
    Usage:
        response = handle_music_command("play tamil songs", Language.ENGLISH)
    """
    
    controller = JarvisMusicController()
    
    # Process command
    search_query, response_text, target_app = controller.process_music_command(command, language)
    
    # Add emotional adaptation
    adapted_response = adapt_jarvis_response(response_text, "music request")
    
    # Launch app (in real implementation)
    success = controller.launch_music_app(search_query, target_app)
    
    if not success:
        if language == Language.TAMIL:
            adapted_response = "மன்னிச்சுங்க, music app ஓபன் பண்ண முடியல"
        else:
            adapted_response = "Sorry, couldn't open the music app"
    
    return adapted_response

# Global controller instance
music_controller = JarvisMusicController()