"""
Compatibility wrapper for the legacy ``AI_Assistant.tts`` import path.

The current implementation lives in ``jarvis.services.tts``. This module keeps
the older ``AdvancedTTS`` class API available for existing tests and callers.
"""

from __future__ import annotations

from typing import Any, Dict, List

from jarvis.services.tts import (
    get_tts_status,
    set_voice_quality,
    speak,
    speak_fast,
    stop_speaking,
)


class AdvancedTTS:
    """Backward-compatible facade over the shared TTS functions."""

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def speak(self, text: str, lang: str = "en", interrupt: bool = False) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return False
        self._history.append({"text": cleaned, "lang": lang, "interrupt": interrupt})
        speak(cleaned, lang=lang, interrupt=interrupt)
        return True

    def speak_fast(self, text: str, lang: str = "en", interrupt: bool = False) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return False
        self._history.append(
            {"text": cleaned, "lang": lang, "interrupt": interrupt, "fast": True}
        )
        speak_fast(cleaned, lang=lang, interrupt=interrupt)
        return True

    def stop_speaking(self) -> None:
        stop_speaking()

    def set_voice_quality(self, mode: str) -> None:
        set_voice_quality(mode)

    def get_voice_info(self) -> Dict[str, Any]:
        status = get_tts_status()
        return {
            "default_voice": status.get("default_voice"),
            "fallback_voice": status.get("fallback_voice"),
            "mode": status.get("mode"),
            "available": {
                "edge_tts": status.get("edge_tts_available", False),
                "pyttsx3": status.get("pyttsx3_available", False),
            },
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)


__all__ = [
    "AdvancedTTS",
    "get_tts_status",
    "set_voice_quality",
    "speak",
    "speak_fast",
    "stop_speaking",
]
