"""
JARVIS Voice Provider Integration — Bridges provider system with existing TTS/STT.

This module provides high-level voice I/O functions that respect the configured
providers while maintaining backward compatibility with existing JARVIS code.

Usage:
  from voice_provider_integration import speak, listen, get_voice_info
  
  # Speak with current provider
  speak("Hello world")
  
  # Listen with current provider
  text = listen()
  
  # Get current voice info
  info = get_voice_info()
"""

import os
import logging

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
from typing import Optional, Dict, Any
import asyncio
import os

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports to avoid circular dependencies
# ─────────────────────────────────────────────────────────────────────────────

def _import_voice_provider():
    """Safely import voice provider module."""
    try:
        from voice_provider import get_voice_provider, get_voice_config
        return get_voice_provider, get_voice_config
    except ImportError:
        LOGGER.warning("voice_provider module not available, using defaults")
        return None, None


def _import_stt():
    """Safely import STT module."""
    try:
        from stt import listen as stt_listen
        return stt_listen
    except ImportError:
        LOGGER.warning("stt module not available")
        return None


def _import_tts():
    """Safely import TTS modules."""
    try:
        from tts import AdvancedTTS
        from fast_tts import speak as fast_speak, speak_fast as fast_speak_fast, stop_speaking
        return AdvancedTTS, fast_speak, fast_speak_fast, stop_speaking
    except ImportError:
        LOGGER.warning("tts/fast_tts modules not available")
        return None, None, None, None


# ─────────────────────────────────────────────────────────────────────────────
# High-level Voice I/O API
# ─────────────────────────────────────────────────────────────────────────────

def speak(text: str, interrupt: bool = False, provider_hint: Optional[str] = None) -> bool:
    """
    Speak the given text using the configured TTS provider.
    
    Args:
        text: Text to speak
        interrupt: Whether to interrupt current speech
        provider_hint: Force a provider ("azure", "openai", "edge-tts", "pyttsx3")
        
    Returns:
        True if successful, False otherwise
    """
    if not text or not text.strip():
        return False

    try:
        get_vp, get_cfg = _import_voice_provider()
        if get_vp and get_cfg:
            config = get_cfg()
            provider = provider_hint or get_vp().get_tts_provider()
        else:
            provider = provider_hint or "azure"

        # Route to appropriate provider
        AdvancedTTS, fast_speak, fast_speak_fast, stop_speaking = _import_tts()
        
        if provider.lower() in ["azure", "openai"]:
            # Use fast_speak for cloud providers
            if fast_speak:
                fast_speak(text.strip(), interrupt=interrupt)
                return True
        elif provider.lower() == "edge-tts":
            # Free natural Aria voice (internet connection required).
            if fast_speak:
                fast_speak(text.strip(), interrupt=interrupt)
                return True
        elif provider.lower() == "pyttsx3":
            # Fully offline Windows SAPI fallback.
            if fast_speak_fast:
                fast_speak_fast(text.strip(), interrupt=interrupt)
                return True
        
        # Ultimate fallback: try AdvancedTTS
        if AdvancedTTS:
            tts = AdvancedTTS()
            return tts.speak(text.strip())
        
        # Last resort: print to console
        print(f"🤖 JARVIS: {text.strip()}")
        return True

    except Exception as e:
        LOGGER.error(f"Error speaking text: {e}")
        print(f"🤖 JARVIS: {text.strip()}")
        return False


def speak_fast(text: str) -> bool:
    """
    Speak the given text as fast as possible (pyttsx3 instant).
    
    Args:
        text: Text to speak
        
    Returns:
        True if successful, False otherwise
    """
    if not text or not text.strip():
        return False

    try:
        AdvancedTTS, fast_speak, fast_speak_fast, stop_speaking = _import_tts()
        
        if fast_speak_fast:
            return fast_speak_fast(text.strip())
        elif fast_speak:
            return fast_speak(text.strip())
        
        print(f"🤖 JARVIS: {text.strip()}")
        return True

    except Exception as e:
        LOGGER.error(f"Error speaking text fast: {e}")
        print(f"🤖 JARVIS: {text.strip()}")
        return False


def stop_speaking() -> None:
    """Stop all ongoing speech synthesis."""
    try:
        AdvancedTTS, fast_speak, fast_speak_fast, stop_speaking_fn = _import_tts()
        if stop_speaking_fn:
            stop_speaking_fn()
    except Exception as e:
        LOGGER.error(f"Error stopping speech: {e}")


def listen(timeout: Optional[int] = None) -> str:
    """
    Listen for user input using the configured STT provider.
    
    Args:
        timeout: Maximum time to listen in seconds
        
    Returns:
        Recognized text, or empty string if failed
    """
    try:
        get_vp, get_cfg = _import_voice_provider()
        if get_vp and get_cfg:
            config = get_cfg()
            provider = config.stt_provider
        else:
            provider = "google"

        stt_listen = _import_stt()
        if stt_listen:
            text = stt_listen(timeout=timeout)
            return text or ""
        
        return ""

    except Exception as e:
        LOGGER.error(f"Error listening to input: {e}")
        return ""


def get_voice_info() -> Dict[str, Any]:
    """
    Get current voice provider information and status.
    
    Returns:
        Dictionary with provider status and configuration
    """
    try:
        get_vp, get_cfg = _import_voice_provider()
        
        if get_vp:
            provider_mgr = get_vp()
            return provider_mgr.get_validation_report()
        
        # Fallback info
        return {
            "config": {
                "stt_provider": "google",
                "lm_provider": "internal",
                "tts_provider": "azure",
                "voice_name": "Aria",
            },
            "status": "default_config",
        }

    except Exception as e:
        LOGGER.error(f"Error getting voice info: {e}")
        return {"error": str(e)}


def set_voice_provider(provider_type: str, provider_name: str) -> bool:
    """
    Switch to a different voice provider at runtime.
    
    Args:
        provider_type: "stt", "lm", or "tts"
        provider_name: Name of the provider
        
    Returns:
        True if successful, False otherwise
    """
    try:
        get_vp, get_cfg = _import_voice_provider()
        
        if get_vp:
            provider_mgr = get_vp()
            return provider_mgr.switch_provider(provider_type, provider_name)
        
        LOGGER.warning("voice_provider not available for switching")
        return False

    except Exception as e:
        LOGGER.error(f"Error switching voice provider: {e}")
        return False


def get_supported_providers() -> Dict[str, list]:
    """
    Get list of all supported voice providers.
    
    Returns:
        Dictionary with supported STT, LM, and TTS providers
    """
    return {
        "stt": ["google", "sarvam", "vosk", "whisper"],
        "lm": ["internal", "gemini", "openai", "groq"],
        "tts": ["azure", "openai", "edge-tts", "pyttsx3"],
    }


def is_voice_ready() -> bool:
    """
    Check if voice system is properly initialized and ready.
    
    Returns:
        True if voice system is ready, False otherwise
    """
    try:
        info = get_voice_info()
        return "error" not in info and info.get("active") is not None
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Voice Provider Status Display
# ─────────────────────────────────────────────────────────────────────────────

def print_voice_status() -> None:
    """Print formatted voice provider status to console."""
    info = get_voice_info()
    
    if "error" in info:
        print(f"❌ Voice system error: {info['error']}")
        return
    
    print("\n" + "="*60)
    print("🎙️  JARVIS VOICE SYSTEM STATUS")
    print("="*60)
    
    # Active providers
    active = info.get("active", {})
    print("\n📡 Active Providers:")
    print(f"  • STT:  {active.get('stt', 'unknown').upper()}")
    print(f"  • LLM:  {active.get('lm', 'unknown').upper()}")
    print(f"  • TTS:  {active.get('tts', 'unknown').upper()}")
    
    # Configuration
    config = info.get("config", {})
    print("\n⚙️  Configuration:")
    print(f"  • Voice:  {config.get('voice_name', 'Aria')}")
    print(f"  • Speed:  {config.get('voice_speed', 1.0)}x")
    print(f"  • Lang:   {config.get('language', 'en-US')}")
    print(f"  • Cache:  {'✓' if config.get('cache_enabled') else '✗'}")
    print(f"  • Offline: {'Yes' if config.get('offline_mode') else 'No'}")
    
    # Validation status
    print("\n✅ Validation Status:")
    for provider_type in ["stt", "lm", "tts"]:
        status = info.get(provider_type, {})
        available = "✓" if status.get("available") else "✗"
        api_ok = "✓" if not status.get("api_key_required") or status.get("api_key_present") else "✗"
        print(f"  • {provider_type.upper()}: {available} (API: {api_ok})")
        if status.get("error"):
            print(f"      Error: {status['error']}")
    
    print("="*60 + "\n")


__all__ = [
    "speak",
    "speak_fast",
    "stop_speaking",
    "listen",
    "get_voice_info",
    "set_voice_provider",
    "get_supported_providers",
    "is_voice_ready",
    "print_voice_status",
]
