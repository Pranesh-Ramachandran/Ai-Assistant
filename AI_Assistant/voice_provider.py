"""
JARVIS Voice Provider System — Friday-inspired modular voice architecture.

Supports multiple providers for STT, LLM, and TTS with easy switching.
Keeps the original JARVIS UI and features intact while upgrading voice capabilities.

Environment Variables:
  - STT_PROVIDER: "google" | "sarvam" | "vosk" | "whisper" (default: "google")
  - LLM_PROVIDER: "gemini" | "openai" | "groq" (default: None, uses internal NLP)
  - TTS_PROVIDER: "azure" | "openai" | "edge-tts" | "pyttsx3" (default: "azure")
  - SARVAM_API_KEY: For Sarvam STT
  - OPENAI_API_KEY: For OpenAI TTS or LLM
  - GOOGLE_API_KEY: For Google Gemini LLM
  - GROQ_API_KEY: For Groq LLM
"""

import os
import json
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import logging

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Provider Enums
# ─────────────────────────────────────────────────────────────────────────────

class STTProvider(Enum):
    """Speech-to-Text providers."""
    GOOGLE = "google"          # Google Cloud STT (default, best quality)
    SARVAM = "sarvam"          # Sarvam Saaras v3 (Indian-English optimized)
    VOSK = "vosk"              # Vosk (offline, lightweight)
    WHISPER = "whisper"        # OpenAI Whisper (accurate, multilingual)


class LLMProvider(Enum):
    """Language Model providers for extended reasoning."""
    INTERNAL = "internal"      # JARVIS internal NLP (default, no API cost)
    GEMINI = "gemini"          # Google Gemini 2.5 Flash (free tier available)
    OPENAI = "openai"          # OpenAI GPT-4 (powerful)
    GROQ = "groq"              # Groq (fast inference)


class TTSProvider(Enum):
    """Text-to-Speech providers."""
    AZURE = "azure"            # Azure Speech (default, natural neural voice)
    OPENAI = "openai"          # OpenAI TTS with Nova voice (high quality)
    EDGE_TTS = "edge-tts"      # Edge TTS (free, Aria voice)
    PYTTSX3 = "pyttsx3"        # pyttsx3 (offline, instant)


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VoiceConfig:
    """Voice provider configuration."""
    stt_provider: str = "google"
    lm_provider: str = "internal"
    tts_provider: str = "azure"
    voice_name: str = "Aria"           # for Azure: Aria, Guy, etc.
    voice_speed: float = 1.0           # 0.5 to 2.0
    language: str = "en-US"            # Language code
    cache_enabled: bool = True         # Enable TTS caching
    offline_mode: bool = False         # Force offline providers

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: str) -> None:
        """Save configuration to JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'VoiceConfig':
        """Load configuration from JSON file."""
        if os.path.exists(path):
            with open(path, "r") as f:
                return cls.from_dict(json.load(f))
        return cls()

    @classmethod
    def from_env(cls) -> 'VoiceConfig':
        """Load configuration from environment variables."""
        return cls(
            stt_provider=os.getenv("STT_PROVIDER", "google"),
            lm_provider=os.getenv("LLM_PROVIDER", "internal"),
            tts_provider=os.getenv("TTS_PROVIDER", "azure"),
            voice_name=os.getenv("VOICE_NAME", "Aria"),
            voice_speed=float(os.getenv("VOICE_SPEED", "1.0")),
            language=os.getenv("JARVIS_STT_LANG", "en-US"),
            cache_enabled=os.getenv("VOICE_CACHE", "true").lower() == "true",
            offline_mode=os.getenv("OFFLINE_MODE", "false").lower() == "true",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Provider Status & Validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProviderStatus:
    """Status of a voice provider."""
    provider: str
    available: bool
    api_key_required: bool
    api_key_present: bool
    error: Optional[str] = None

    def is_usable(self) -> bool:
        """Check if provider can be used."""
        return self.available and (not self.api_key_required or self.api_key_present)


class VoiceProviderManager:
    """Manages voice provider selection, validation, and fallbacks."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        """Initialize provider manager.
        
        Args:
            config: VoiceConfig instance. If None, loads from env vars.
        """
        self.config = config or VoiceConfig.from_env()
        self._validate_providers()

    def _validate_providers(self) -> None:
        """Validate that required API keys are present."""
        validation = {
            "stt": self._validate_stt(),
            "lm": self._validate_lm(),
            "tts": self._validate_tts(),
        }
        self._validation_results = validation

    def _validate_stt(self) -> ProviderStatus:
        """Validate STT provider."""
        provider = self.config.stt_provider.lower()
        
        if provider == "google":
            return ProviderStatus(provider, True, False, True)
        elif provider == "sarvam":
            api_key = os.getenv("SARVAM_API_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="SARVAM_API_KEY not set" if not api_key else None,
            )
        elif provider == "vosk":
            return ProviderStatus(provider, True, False, True)
        elif provider == "whisper":
            api_key = os.getenv("OPENAI_API_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="OPENAI_API_KEY not set" if not api_key else None,
            )
        else:
            return ProviderStatus(provider, False, False, False, f"Unknown STT provider: {provider}")

    def _validate_lm(self) -> ProviderStatus:
        """Validate LM provider."""
        provider = self.config.lm_provider.lower()
        
        if provider == "internal":
            return ProviderStatus(provider, True, False, True)
        elif provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="GOOGLE_API_KEY not set" if not api_key else None,
            )
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="OPENAI_API_KEY not set" if not api_key else None,
            )
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="GROQ_API_KEY not set" if not api_key else None,
            )
        else:
            return ProviderStatus(provider, False, False, False, f"Unknown LM provider: {provider}")

    def _validate_tts(self) -> ProviderStatus:
        """Validate TTS provider."""
        provider = self.config.tts_provider.lower()
        
        if provider == "azure":
            api_key = os.getenv("AZURE_SPEECH_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="AZURE_SPEECH_KEY not set" if not api_key else None,
            )
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            return ProviderStatus(
                provider,
                available=True,
                api_key_required=True,
                api_key_present=bool(api_key),
                error="OPENAI_API_KEY not set" if not api_key else None,
            )
        elif provider == "edge-tts":
            return ProviderStatus(provider, True, False, True)
        elif provider == "pyttsx3":
            return ProviderStatus(provider, True, False, True)
        else:
            return ProviderStatus(provider, False, False, False, f"Unknown TTS provider: {provider}")

    def get_stt_provider(self) -> str:
        """Get the active STT provider (with fallback)."""
        status = self._validation_results["stt"]
        if status.is_usable():
            return status.provider
        
        # Fallback chain
        fallback_chain = ["google", "vosk"]
        for provider in fallback_chain:
            if provider != status.provider:
                return provider
        return "google"

    def get_lm_provider(self) -> str:
        """Get the active LM provider (with fallback)."""
        status = self._validation_results["lm"]
        if status.is_usable():
            return status.provider
        return "internal"

    def get_tts_provider(self) -> str:
        """Get the active TTS provider (with fallback)."""
        status = self._validation_results["tts"]
        if status.is_usable():
            return status.provider
        
        # Fallback chain
        fallback_chain = ["edge-tts", "pyttsx3"]
        for provider in fallback_chain:
            if provider != status.provider:
                return provider
        return "pyttsx3"

    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report."""
        return {
            "config": self.config.to_dict(),
            "stt": asdict(self._validation_results["stt"]),
            "lm": asdict(self._validation_results["lm"]),
            "tts": asdict(self._validation_results["tts"]),
            "active": {
                "stt": self.get_stt_provider(),
                "lm": self.get_lm_provider(),
                "tts": self.get_tts_provider(),
            },
        }

    def switch_provider(self, provider_type: str, provider_name: str) -> bool:
        """Switch to a different provider at runtime.
        
        Args:
            provider_type: "stt", "lm", or "tts"
            provider_name: Name of the provider (e.g., "gemini", "openai")
            
        Returns:
            True if switch was successful, False otherwise.
        """
        if provider_type == "stt":
            try:
                STTProvider(provider_name)
                self.config.stt_provider = provider_name
                self._validate_providers()
                return self._validation_results["stt"].is_usable()
            except ValueError:
                LOGGER.error(f"Unknown STT provider: {provider_name}")
                return False
        elif provider_type == "lm":
            try:
                LLMProvider(provider_name)
                self.config.lm_provider = provider_name
                self._validate_providers()
                return self._validation_results["lm"].is_usable()
            except ValueError:
                LOGGER.error(f"Unknown LM provider: {provider_name}")
                return False
        elif provider_type == "tts":
            try:
                TTSProvider(provider_name)
                self.config.tts_provider = provider_name
                self._validate_providers()
                return self._validation_results["tts"].is_usable()
            except ValueError:
                LOGGER.error(f"Unknown TTS provider: {provider_name}")
                return False
        else:
            LOGGER.error(f"Unknown provider type: {provider_type}")
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────────────────────────────────────

_global_manager: Optional[VoiceProviderManager] = None


def init_voice_provider(config: Optional[VoiceConfig] = None) -> VoiceProviderManager:
    """Initialize the global voice provider manager."""
    global _global_manager
    _global_manager = VoiceProviderManager(config)
    return _global_manager


def get_voice_provider() -> VoiceProviderManager:
    """Get the global voice provider manager (auto-initializes if needed)."""
    global _global_manager
    if _global_manager is None:
        _global_manager = VoiceProviderManager()
    return _global_manager


def get_voice_config() -> VoiceConfig:
    """Get the current voice configuration."""
    return get_voice_provider().config


def switch_voice_provider(provider_type: str, provider_name: str) -> bool:
    """Switch to a different voice provider."""
    return get_voice_provider().switch_provider(provider_type, provider_name)


def get_voice_status() -> Dict[str, Any]:
    """Get current voice provider status and validation report."""
    return get_voice_provider().get_validation_report()


__all__ = [
    "VoiceConfig",
    "VoiceProviderManager",
    "ProviderStatus",
    "STTProvider",
    "LLMProvider",
    "TTSProvider",
    "init_voice_provider",
    "get_voice_provider",
    "get_voice_config",
    "switch_voice_provider",
    "get_voice_status",
]
