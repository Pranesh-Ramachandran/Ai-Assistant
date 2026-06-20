"""
JARVIS TTS Service — multi-engine text-to-speech with graceful fallbacks.
Priority: pyttsx3 (offline) → gTTS (online) → console print
"""

import logging
import os
import tempfile
import time
import threading

logger = logging.getLogger(__name__)

try:
    import pyttsx3
    _PYTTSX3 = True
except ImportError:
    _PYTTSX3 = False

try:
    from gtts import gTTS
    import pygame
    _GTTS = True
except ImportError:
    _GTTS = False


_SUPPRESS_PRINT = False


class EnhancedTTS:
    def __init__(self):
        self._engine = None
        self._engine_type = "none"
        self._lock = threading.Lock()
        self._init_engine()

    def _select_female_voice(self) -> None:
        """Prefer a female voice when pyttsx3 is available."""
        voices = self._engine.getProperty("voices")
        if not voices:
            return

        preferred_tokens = ("zira", "susan", "hazel", "female", "aria")
        for voice in voices:
            voice_id = getattr(voice, "id", "").lower()
            voice_name = getattr(voice, "name", "").lower()
            if any(token in voice_id or token in voice_name for token in preferred_tokens):
                self._engine.setProperty("voice", voice.id)
                return

        # Fallback: keep the first installed voice if no female voice is available.
        self._engine.setProperty("voice", voices[0].id)

    def _init_engine(self) -> None:
        if _PYTTSX3:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 180)
                self._engine.setProperty("volume", 0.9)
                self._select_female_voice()
                self._engine_type = "pyttsx3"
                logger.info("TTS engine: pyttsx3")
                return
            except Exception as e:
                logger.warning("pyttsx3 init failed: %s", e)

        if _GTTS:
            try:
                pygame.mixer.init()
                self._engine_type = "gtts"
                logger.info("TTS engine: gTTS")
                return
            except Exception as e:
                logger.warning("gTTS/pygame init failed: %s", e)

        logger.warning("No TTS engine available — using console output")
        self._engine_type = "none"

    def speak(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if not _SUPPRESS_PRINT:
            print(f"JARVIS: {text}")
        with self._lock:
            if self._engine_type == "pyttsx3":
                self._speak_pyttsx3(text)
            elif self._engine_type == "gtts":
                self._speak_gtts(text)

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            logger.error("pyttsx3 speak error: %s", e)

    def _speak_gtts(self, text: str) -> None:
        tmp = None
        try:
            if not _GTTS:
                return
            try:
                pygame.mixer.get_init() or pygame.mixer.init()
            except Exception as e:
                logger.warning("pygame mixer init failed: %s", e)
                return
            tts = gTTS(text=text, lang="en", slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                tmp = f.name
            tts.save(tmp)
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            logger.error("gTTS speak error: %s", e)
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def speak_async(self, text: str) -> None:
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()


# Module-level singleton and convenience function
_tts = EnhancedTTS()


def speak(text: str) -> None:
    _tts.speak(text)
