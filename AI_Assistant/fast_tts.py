"""
JARVIS Fast TTS — Azure Speech (female neural voice) as DEFAULT when configured.
Falls back to edge-tts Aria, then pyttsx3 (Windows SAPI) only when offline.

Architecture:
  - Primary:  Azure Speech (en-US-AriaNeural by default) — natural female voice
  - Fallback: edge-tts streaming (en-US-AriaNeural) — natural female voice
  - Fallback: pyttsx3 (Windows SAPI) — offline, instant but robotic
  - Emergency: print + beep

Public API:
  speak(text)              → Azure Speech Aria (default when configured)
  speak_fast(text)         → pyttsx3 instant (offline fallback)
  stop_speaking()          → stop all audio
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import queue
import threading
import time
from typing import Optional

LOGGER = logging.getLogger(__name__)

# ── Audio cache ───────────────────────────────────────────────────────────────
_CACHE_DIR     = os.path.join(os.path.dirname(__file__), ".tts_cache")
_CACHE_MAX_MB  = 30          # delete oldest files when cache exceeds this
_CACHE_MAX_AGE = 86400 * 14  # 14 days
os.makedirs(_CACHE_DIR, exist_ok=True)

def _cache_key(text: str, voice: str) -> str:
    return hashlib.md5(f"{voice}:{text.strip().lower()}".encode()).hexdigest()

def _cache_path(key: str) -> str:
    return os.path.join(_CACHE_DIR, f"{key}.mp3")

def _cache_get(text: str, voice: str) -> Optional[bytes]:
    path = _cache_path(_cache_key(text, voice))
    if os.path.exists(path):
        os.utime(path, None)  # bump access time
        with open(path, "rb") as f:
            return f.read()
    return None

def _cache_put(text: str, voice: str, data: bytes) -> None:
    path = _cache_path(_cache_key(text, voice))
    with open(path, "wb") as f:
        f.write(data)
    _cache_evict()

def _cache_evict() -> None:
    """Delete oldest files if cache exceeds size limit or age limit."""
    try:
        files = [(os.path.getmtime(p), os.path.getsize(p), p)
                 for f in os.listdir(_CACHE_DIR)
                 if (p := os.path.join(_CACHE_DIR, f)).endswith(".mp3")]
        now = time.time()
        # delete by age first
        for mtime, _, path in files:
            if now - mtime > _CACHE_MAX_AGE:
                os.remove(path)
        # delete oldest if over size cap
        files = sorted((os.path.getmtime(p), os.path.getsize(p), p)
                       for f in os.listdir(_CACHE_DIR)
                       if (p := os.path.join(_CACHE_DIR, f)).endswith(".mp3"))
        total = sum(s for _, s, _ in files)
        for mtime, size, path in files:
            if total <= _CACHE_MAX_MB * 1024 * 1024:
                break
            os.remove(path)
            total -= size
    except Exception:
        pass

# ─── pyttsx3 (offline fallback) ──────────────────────────────────────────────
try:
    import pyttsx3 as _pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _pyttsx3 = None
    _PYTTSX3_AVAILABLE = False

# ─── edge-tts (online, high quality — PRIMARY) ──────────────────────────────
try:
    import edge_tts as _edge_tts
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _edge_tts = None
    _EDGE_TTS_AVAILABLE = False

# ─── Azure Speech SDK (primary when configured) ─────────────────────────────
try:
    import azure.cognitiveservices.speech as _speechsdk
    _AZURE_AVAILABLE = True
except ImportError:
    _speechsdk = None
    _AZURE_AVAILABLE = False

# ─── pygame (for audio playback) ─────────────────────────────────────────────
try:
    import pygame as _pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _pygame = None
    _PYGAME_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# pyttsx3 worker — single persistent engine in dedicated thread (FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════════

class _PyTTSWorker:
    """Dedicated thread holding a persistent pyttsx3 engine."""

    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._ready = threading.Event()
        self._engine: Optional[object] = None
        self._t = threading.Thread(target=self._run, daemon=True, name="jarvis-sapi-tts")
        self._t.start()
        self._ready.wait(timeout=5)  # wait for engine init

    def _run(self):
        if not _PYTTSX3_AVAILABLE:
            self._ready.set()
            return
        try:
            engine = _pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.setProperty("volume", 1.0)
            # Prefer female voice (Zira) on Windows if available
            voices = engine.getProperty("voices")
            for v in voices:
                if "zira" in v.id.lower() or "female" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            self._engine = engine
        except Exception as exc:
            LOGGER.warning("pyttsx3 init failed: %s", exc)
            self._ready.set()
            return

        self._ready.set()

        while True:
            item = self._q.get()
            if item is None:
                break
            text, interrupt = item
            try:
                if interrupt:
                    try:
                        self._engine.stop()
                    except Exception:
                        pass
                self._engine.say(text)
                self._engine.runAndWait()
                _notify_playback_end()
            except Exception as exc:
                LOGGER.warning("pyttsx3 speak error: %s", exc)
            finally:
                self._q.task_done()

    def speak(self, text: str, interrupt: bool = False):
        if not self._engine:
            return False
        if interrupt:
            # Drain old requests
            while not self._q.empty():
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
        self._q.put((text, interrupt))
        return True

    def stop(self):
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break


_SAPI_WORKER: Optional[_PyTTSWorker] = None
_SAPI_LOCK = threading.Lock()


def _get_sapi_worker() -> Optional[_PyTTSWorker]:
    global _SAPI_WORKER
    if _SAPI_WORKER is not None:
        return _SAPI_WORKER
    if not _PYTTSX3_AVAILABLE:
        return None
    with _SAPI_LOCK:
        if _SAPI_WORKER is None:
            _SAPI_WORKER = _PyTTSWorker()
    return _SAPI_WORKER


# ═══════════════════════════════════════════════════════════════════════════════
# edge-tts — streaming, persistent event loop, no temp files (PRIMARY)
# ═══════════════════════════════════════════════════════════════════════════════

_PYGAME_READY = False
_PYGAME_LOCK = threading.Lock()


def _azure_enabled() -> bool:
    return _AZURE_AVAILABLE and bool(os.getenv("AZURE_SPEECH_KEY")) and bool(os.getenv("AZURE_SPEECH_REGION"))


def _azure_voice(lang: str, text: str) -> str:
    if lang in ("ta", "mixed") or _contains_tamil(text):
        return os.getenv("AZURE_TTS_TAMIL_VOICE", "ta-IN-PallaviNeural")
    return os.getenv("AZURE_TTS_VOICE", "en-US-AriaNeural")


def _ensure_pygame() -> bool:
    global _PYGAME_READY
    if not _PYGAME_AVAILABLE:
        return False
    if _PYGAME_READY:
        return True
    with _PYGAME_LOCK:
        if _PYGAME_READY:
            return True
        try:
            # frequency=22050, buffer=512 minimises latency
            _pygame.mixer.pre_init(22050, -16, 1, 512)
            _pygame.mixer.init()
            _PYGAME_READY = True
        except Exception as exc:
            LOGGER.warning("pygame mixer init failed: %s", exc)
    return _PYGAME_READY


def _contains_tamil(text: str) -> bool:
    return any("\u0b80" <= ch <= "\u0bff" for ch in text)


def _select_voice(text: str, lang: str) -> str:
    if lang in ("ta", "mixed") or _contains_tamil(text):
        return "ta-IN-PallaviNeural"
    return "en-US-AriaNeural"      # Female, natural tone


def _azure_speak(text: str, lang: str = "en") -> bool:
    if not _azure_enabled():
        return False
    try:
        key = os.getenv("AZURE_SPEECH_KEY", "")
        region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        cfg = _speechsdk.SpeechConfig(subscription=key, region=region)
        cfg.speech_synthesis_voice_name = _azure_voice(lang, text)
        audio_cfg = _speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        synthesizer = _speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=audio_cfg)
        _notify_playback_start()
        result = synthesizer.speak_text_async(text).get()
        _notify_playback_end()
        return result.reason == _speechsdk.ResultReason.SynthesizingAudioCompleted
    except Exception as exc:
        LOGGER.warning("Azure TTS speak failed: %s", exc)
        return False


async def _stream_to_bytes(text: str, voice: str) -> bytes:
    """Stream edge-tts audio into a BytesIO buffer (no temp file)."""
    buf = io.BytesIO()
    comm = _edge_tts.Communicate(text, voice)
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


# ── pydub + sounddevice for stutter-free PCM playback ────────────────────
try:
    from pydub import AudioSegment as _AudioSegment
    import sounddevice as _sd
    import numpy as _np
    _PCM_PLAY = True
except ImportError:
    _PCM_PLAY = False

_play_lock = threading.Lock()   # one audio stream at a time
_stop_flag = threading.Event()
_on_playback_start = None   # callback set by server when audio actually begins


def set_playback_start_callback(fn):
    """Server registers this to get notified when audio actually starts."""
    global _on_playback_start
    _on_playback_start = fn

_on_playback_end = None


def set_playback_end_callback(fn):
    """Server registers this to get notified when audio actually ends."""
    global _on_playback_end
    _on_playback_end = fn


def _notify_playback_start():
    if _on_playback_start:
        try:
            _on_playback_start()
        except Exception:
            pass


def _notify_playback_end():
    if _on_playback_end:
        try:
            _on_playback_end()
        except Exception:
            pass


def _play_mp3_bytes(audio_bytes: bytes) -> bool:
    """Decode MP3 → PCM → play via sounddevice. Falls back to pygame, then temp-file.
    Returns True if audio was played, False if all methods failed."""
    _stop_flag.clear()

    if _PCM_PLAY:
        try:
            with _play_lock:
                seg = _AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                seg = seg.set_channels(1).set_frame_rate(22050)
                pcm = _np.frombuffer(seg.raw_data, dtype=_np.int16).astype(_np.float32) / 32768.0
                _notify_playback_start()
                _sd.play(pcm, samplerate=22050)
                while _sd.get_stream().active:
                    if _stop_flag.is_set():
                        _sd.stop()
                        break
                    time.sleep(0.05)
                _sd.wait()
                _notify_playback_end()
            return True
        except Exception as exc:
            LOGGER.warning("PCM play failed, falling back to pygame: %s", exc)

    # pygame fallback — independent of PCM, init attempted here not before
    if _PYGAME_AVAILABLE:
        if _ensure_pygame():
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            try:
                tmp.write(audio_bytes); tmp.flush(); tmp.close()
                _notify_playback_start()
                _pygame.mixer.music.load(tmp.name)
                _pygame.mixer.music.play()
                while _pygame.mixer.music.get_busy():
                    if _stop_flag.is_set():
                        _pygame.mixer.music.stop()
                        break
                    time.sleep(0.05)
                _notify_playback_end()
                return True
            except Exception as exc:
                LOGGER.warning("pygame play failed: %s", exc)
            finally:
                try:
                    _pygame.mixer.music.unload()
                    os.unlink(tmp.name)
                except Exception:
                    pass

    # last resort: write to temp file and let OS play it
    try:
        import tempfile, subprocess
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(audio_bytes); tmp.flush(); tmp.close()
        _notify_playback_start()
        subprocess.Popen(["start", "", tmp.name], shell=True)
        _notify_playback_end()
        return True
    except Exception as exc:
        LOGGER.warning("OS fallback play failed: %s", exc)

    return False


def _edge_tts_speak(text: str, lang: str = "en") -> bool:
    """Fetch audio via edge-tts, play via PCM/pygame/OS. Returns False only if
    audio fetch fails or playback completely unavailable — never gates on pygame."""
    if not _EDGE_TTS_AVAILABLE:
        return False
    try:
        voice = _select_voice(text, lang)

        cached = _cache_get(text, voice)
        if cached:
            return _play_mp3_bytes(cached)

        loop = asyncio.new_event_loop()
        audio_bytes = loop.run_until_complete(_stream_to_bytes(text, voice))
        loop.close()
        if not audio_bytes:
            return False
        _cache_put(text, voice, audio_bytes)
        return _play_mp3_bytes(audio_bytes)
    except Exception as exc:
        LOGGER.warning("edge-tts speak failed: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def speak(text: str, lang: str = "en", interrupt: bool = False) -> None:
    """
    Speak text using edge-tts AriaNeural (female, natural).
    Non-blocking — runs in a daemon thread.
    Falls back to pyttsx3 if edge-tts / network is unavailable.

    Args:
        text:      Text to speak.
        lang:      'en' or 'ta' (Tamil).
        interrupt: Stop current speech and flush queued items.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return

    if interrupt:
        stop_speaking()

    def _worker():
        # PRIMARY: Azure Speech (natural female voice)
        if _azure_speak(cleaned, lang):
            return

        # SECONDARY: edge-tts (natural female voice)
        if _edge_tts_speak(cleaned, lang):
            return

        # FALLBACK: pyttsx3 (offline, robotic but instant)
        worker = _get_sapi_worker()
        if worker and worker.speak(cleaned, False):
            return

        # EMERGENCY: just print
        LOGGER.warning("All TTS engines failed, printing text")
        print(f"🔊 JARVIS: {cleaned}")
        _beep()

    t = threading.Thread(target=_worker, daemon=True, name="jarvis-tts")
    t.start()


def speak_fast(text: str, lang: str = "en", interrupt: bool = False) -> None:
    """
    Speak with pyttsx3 (instant, offline). Use for short UI confirmations
    where you don't want the ~2s edge-tts lag.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return

    if lang in ("ta", "mixed") or _contains_tamil(cleaned):
        # Tamil needs Azure/edge-tts, no SAPI voice available
        speak(cleaned, lang, interrupt)
        return

    if _azure_speak(cleaned, lang):
        return

    worker = _get_sapi_worker()
    if worker and worker.speak(cleaned, interrupt):
        return

    # Fallback to edge-tts
    speak(cleaned, lang, interrupt)


def stop_speaking() -> None:
    """Stop all current speech immediately."""
    _stop_flag.set()
    if _PCM_PLAY:
        try:
            _sd.stop()
        except Exception:
            pass
    worker = _get_sapi_worker()
    if worker:
        worker.stop()
    if _PYGAME_AVAILABLE and _PYGAME_READY:
        try:
            _pygame.mixer.music.stop()
        except Exception:
            pass


def set_voice_quality(mode: str) -> None:
    """
    Switch TTS quality mode (kept for backward compat).
    mode='fast' → pyttsx3 SAPI
    mode='hq'   → edge-tts (now the default)
    """
    os.environ["JARVIS_TTS_MODE"] = mode.lower()


def _beep() -> None:
    try:
        import winsound
        winsound.MessageBeep()
    except Exception:
        pass


# ─── Status info ──────────────────────────────────────────────────────────────
def get_tts_status() -> dict:
    worker = _get_sapi_worker()
    return {
        "azure_available": _azure_enabled(),
        "azure_voice": _azure_voice("en", "sample"),
        "pyttsx3_available": _PYTTSX3_AVAILABLE,
        "pyttsx3_engine_ready": worker is not None and worker._engine is not None,
        "edge_tts_available": _EDGE_TTS_AVAILABLE,
        "pygame_available": _PYGAME_AVAILABLE,
        "default_voice": "en-US-AriaNeural (Azure Speech, female)" if _azure_enabled() else "en-US-AriaNeural (edge-tts, female)",
        "fallback_voice": "Windows SAPI (pyttsx3)",
        "mode": "azure speech primary" if _azure_enabled() else "edge-tts primary",
    }


if __name__ == "__main__":
    print("TTS Status:", get_tts_status())
    print("Speaking with edge-tts Aria (default)...")
    speak("Hello, I am JARVIS. This is the natural female voice using edge T T S.")
    time.sleep(8)
    print("Speaking Tamil with edge-tts...")
    speak("வணக்கம்! நான் ஜார்விஸ்.", lang="ta")
    time.sleep(6)
    print("Done.")
