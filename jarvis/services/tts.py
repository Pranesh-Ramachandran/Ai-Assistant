"""
JARVIS TTS Service — multi-engine text-to-speech with graceful fallbacks.
Priority: Azure Speech (female neural voice) → pyttsx3 (offline) → gTTS (online) → console print
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

try:
    import azure.cognitiveservices.speech as speechsdk
    _AZURE = True
except ImportError:
    speechsdk = None
    _AZURE = False


_SUPPRESS_PRINT = False


def _azure_enabled() -> bool:
    return _AZURE and bool(os.getenv("AZURE_SPEECH_KEY")) and bool(os.getenv("AZURE_SPEECH_REGION"))


def _azure_voice() -> str:
    return os.getenv("AZURE_TTS_VOICE", "en-US-AriaNeural")


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
        if _azure_enabled():
            self._engine_type = "azure"
            logger.info("TTS engine: Azure Speech (%s)", _azure_voice())
            return

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
            if self._engine_type == "azure":
                if self._speak_azure(text):
                    return
                # Fall through to local engines if Azure fails at runtime.
            if self._engine_type == "pyttsx3":
                self._speak_pyttsx3(text)
            elif self._engine_type == "gtts":
                self._speak_gtts(text)
            elif self._engine_type == "azure":
                # Azure was selected but failed; try local fallback chain.
                if _PYTTSX3:
                    self._speak_pyttsx3(text)
                elif _GTTS:
                    self._speak_gtts(text)

    def _speak_azure(self, text: str) -> bool:
        if not _azure_enabled():
            return False
        try:
            key = os.getenv("AZURE_SPEECH_KEY", "")
            region = os.getenv("AZURE_SPEECH_REGION", "eastus")
            speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
            speech_config.speech_synthesis_voice_name = _azure_voice()
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            result = synthesizer.speak_text_async(text).get()
            return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
        except Exception as e:
            logger.warning("Azure TTS speak failed: %s", e)
            return False

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            if self._engine is None and _PYTTSX3:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 180)
                self._engine.setProperty("volume", 0.9)
                self._select_female_voice()
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


def speak_fast(text: str) -> None:
    _tts.speak(text)


def stop_speaking() -> None:
    """Compatibility no-op for the sync TTS service."""
    return None


def set_voice_quality(mode: str) -> None:
    """Compatibility hook for callers that still toggle TTS modes."""
    os.environ["JARVIS_TTS_MODE"] = (mode or "").lower()


def get_tts_status() -> dict:
    return {
        "engine_type": getattr(_tts, "_engine_type", "none"),
        "azure_available": _azure_enabled(),
        "azure_voice": _azure_voice(),
        "pyttsx3_available": _PYTTSX3,
        "gtts_available": _GTTS,
        "default_voice": _azure_voice() if _azure_enabled() else "Windows SAPI (pyttsx3)",
    }
