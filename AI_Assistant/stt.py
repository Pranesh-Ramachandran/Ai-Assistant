"""
JARVIS STT — Clean, reliable speech-to-text.

Priority:
  1. Google STT (online, English by default, Tamil if JARVIS_STT_LANG=ta)
  2. Vosk      (offline fallback, if model exists)
  3. Empty string (graceful fail)

Audio capture uses sounddevice + energy VAD for accurate phrase detection.
Falls back to PyAudio (sr.Microphone) if sounddevice unavailable.
"""

import os
import json
import queue
import re
import socket
import threading
import time
from typing import Optional

import speech_recognition as sr

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import sounddevice as sd
    import numpy as np
    _SD = True
except ImportError:
    _SD = False

try:
    import webrtcvad as _webrtcvad
    _VAD = _webrtcvad.Vad(2)   # mode 2 = balanced
    _VAD_OK = True
except ImportError:
    _VAD = None
    _VAD_OK = False

try:
    from vosk import Model as _VoskModel, KaldiRecognizer as _KaldiRec
    _VOSK_OK = True
except ImportError:
    _VOSK_OK = False

_RECOGNIZER = sr.Recognizer()
_RECOGNIZER.pause_threshold            = 0.3      # Shorter pause = faster detection (reduced from 0.4)
_RECOGNIZER.non_speaking_duration      = 0.2      # Must not exceed pause_threshold
_RECOGNIZER.energy_threshold           = 1500     # Lower = more sensitive (reduced from 300 to match wake detector)
_RECOGNIZER.dynamic_energy_threshold = True      # Auto-calibrate to environment
_RECOGNIZER.phrase_threshold           = 0.3      # Minimum energy for valid phrase (reduced from 0.5)
_RECOGNIZER.operation_timeout         = 10       # Max time to wait for response

VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-en-us-0.15")
_vosk_model: Optional[object] = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def check_internet() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 80), 2)
        return True
    except OSError:
        return False


def _clean(text: str, strip_wake: bool = True) -> str:
    """Normalize recognized text."""
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    if strip_wake:
        # strip wake word prefix if accidentally captured
        for prefix in ("hey jarvis ", "ok jarvis ", "jarvis "):
            if t.startswith(prefix):
                t = t[len(prefix):]
    return t.strip()


def _get_vosk_model():
    global _vosk_model
    if _vosk_model is None and _VOSK_OK:
        path = os.path.join(os.path.dirname(__file__), VOSK_MODEL_PATH)
        if not os.path.exists(path):
            path = VOSK_MODEL_PATH
        if os.path.exists(path):
            try:
                _vosk_model = _VoskModel(path)
            except Exception:
                pass
    return _vosk_model


# ── Audio capture ─────────────────────────────────────────────────────────────

def _capture_sd(timeout: float = 8.0, phrase_limit: float = 7.0):
    """
    Capture one phrase using sounddevice + VAD.
    Returns (raw_bytes, sample_rate) or (None, 16000).
    """
    RATE  = 16000
    CHUNK = 320   # 20ms frames for VAD

    q: queue.Queue = queue.Queue()

    def _cb(indata, frames, t, status):
        q.put(bytes(indata))

    voiced, silence, started = [], 0, False
    voice_start = 0.0
    MAX_SILENCE = int(RATE / CHUNK * 1.5)   # 1.5s silence ends phrase (was 1s — too short for wake word)
    MIN_VOICE_FRAMES = int(RATE / CHUNK * 0.2)  # ignore sub-200ms blips
    NOISE_FRAMES = int(RATE / CHUNK * 0.3)  # 300ms noise baseline

    try:
        with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK,
                               dtype="int16", channels=1, callback=_cb):
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    data = q.get(timeout=0.5)
                except queue.Empty:
                    continue

                # VAD decision
                if _VAD_OK:
                    is_speech = _VAD.is_speech(data, RATE)
                else:
                    # energy-based fallback
                    import numpy as np
                    frame = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                    rms = float(np.sqrt(np.mean(frame ** 2))) if frame.size else 0.0
                    is_speech = rms > 300.0  # fixed low threshold

                if is_speech:
                    if not started:
                        started = True
                        voice_start = time.time()
                    voiced.append(data)
                    silence = 0
                elif started:
                    voiced.append(data)
                    silence += 1
                    if silence > MAX_SILENCE:
                        break

                if started and (time.time() - voice_start) > phrase_limit:
                    break

    except Exception:
        pass

    if voiced:
        return b"".join(voiced), RATE
    return None, RATE


# ── Recognition ───────────────────────────────────────────────────────────────

def _recognize_google(audio: sr.AudioData) -> str:
    lang = os.getenv("JARVIS_STT_LANG", "en").lower()
    google_lang = "ta-IN" if lang == "ta" else "en-IN"
    try:
        text = _recognize_google_https(audio, language=google_lang, show_all=False)
        return _clean(text)
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"[STT] Google error: {e}")
        return ""


def _recognize_google_https(audio: sr.AudioData, language: str, show_all: bool = False):
    """Google Web Speech via HTTPS + requests instead of failing urllib path."""
    import requests
    from speech_recognition.recognizers.google import (
        OutputParser,
        create_request_builder,
    )

    builder = create_request_builder(
        endpoint="https://www.google.com/speech-api/v2/recognize",
        language=language,
    )
    request = builder.build(audio)
    response = requests.post(
        request.full_url,
        data=request.data,
        headers=dict(request.header_items()),
        timeout=_RECOGNIZER.operation_timeout or 10,
    )
    response.raise_for_status()
    return OutputParser(show_all=show_all, with_confidence=False).parse(response.text)


def _recognize_vosk(raw: bytes, rate: int) -> str:
    model = _get_vosk_model()
    if not model:
        return ""
    try:
        rec = _KaldiRec(model, rate)
        rec.AcceptWaveform(raw)
        result = json.loads(rec.FinalResult())
        return _clean(result.get("text", ""))
    except Exception as e:
        print(f"[STT] Vosk error: {e}")
        return ""


# ── Public API ────────────────────────────────────────────────────────────────

def listen(timeout: float = 8.0, phrase_limit: float = 7.0) -> str:
    """
    Record one phrase and return recognized text.
    Tries Google first (online), falls back to Vosk (offline).
    """
    online = check_internet()

    # ── Capture audio ─────────────────────────────────────────────────────────
    if _SD:
        raw, rate = _capture_sd(timeout=timeout, phrase_limit=phrase_limit)
        if not raw:
            print("[STT] No speech detected.")
            return ""
        audio = sr.AudioData(raw, rate, 2)
    else:
        # PyAudio fallback
        try:
            with sr.Microphone() as source:
                _RECOGNIZER.adjust_for_ambient_noise(source, duration=0.3)
                audio = _RECOGNIZER.listen(source, timeout=timeout,
                                           phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            print("[STT] Timeout — no speech.")
            return ""
        except Exception as e:
            print(f"[STT] Mic error: {e}")
            return ""
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        rate = 16000

    # ── Recognize ─────────────────────────────────────────────────────────────
    if online:
        text = _recognize_google(audio)
        if text:
            print(f"[STT] {text}")
            return text
        # Google returned nothing — try Vosk if available
        if _VOSK_OK:
            text = _recognize_vosk(raw, rate)
            if text:
                print(f"[STT-Vosk] {text}")
                return text
    else:
        # Offline — Vosk only
        text = _recognize_vosk(raw, rate)
        if text:
            print(f"[STT-Vosk] {text}")
            return text
        print("[STT] Offline and no Vosk model — cannot recognize.")

    return ""


def listen_candidates(timeout: float = 4.0, phrase_limit: float = 2.5) -> list[str]:
    """Capture one phrase and return Google STT's ranked alternatives.

    Wake-word detection benefits from alternatives because accented
    "hey Jarvis" is sometimes ranked below a phrase such as "how are you".
    """
    if not _SD or not check_internet():
        text = listen(timeout=timeout, phrase_limit=phrase_limit)
        return [text] if text else []

    raw, rate = _capture_sd(timeout=timeout, phrase_limit=phrase_limit)
    if not raw:
        return []
    audio = sr.AudioData(raw, rate, 2)
    candidates: list[str] = []
    for language in ("en-IN", "en-US"):
        try:
            result = _recognize_google_https(audio, language=language, show_all=True)
            alternatives = result.get("alternative", []) if isinstance(result, dict) else []
            for alternative in alternatives:
                # Don't strip wake word — wake detector needs the full phrase
                cleaned = _clean(alternative.get("transcript", ""), strip_wake=False)
                if cleaned and cleaned not in candidates:
                    candidates.append(cleaned)
        except (sr.UnknownValueError, sr.RequestError, OSError):
            continue
    return candidates


# ── Status ────────────────────────────────────────────────────────────────────

def get_stt_status() -> dict:
    return {
        "sounddevice": _SD,
        "vad": _VAD_OK,
        "vosk": _VOSK_OK and _get_vosk_model() is not None,
        "internet": check_internet(),
        "lang": os.getenv("JARVIS_STT_LANG", "en"),
        "engine": "google" if check_internet() else "vosk",
    }


# kept for backward compat
def listen_google() -> str:
    return listen()

def listen_text() -> str:
    return listen()

# check_internet already defined above (lines 58-63) — no duplicate needed

def get_engine_override() -> str:
    return os.getenv("JARVIS_STT_ENGINE", "auto")

def set_engine_override(v: str):
    os.environ["JARVIS_STT_ENGINE"] = v

def get_vad_sensitivity() -> int:
    try:
        return int(os.getenv("JARVIS_VAD_SENSITIVITY", "75"))
    except Exception:
        return 75

def set_vad_sensitivity(value: int):
    os.environ["JARVIS_VAD_SENSITIVITY"] = str(max(0, min(100, int(value))))
    if _VAD_OK and _VAD:
        mode = 3 if value >= 75 else 2 if value >= 50 else 1 if value >= 25 else 0
        _VAD.set_mode(mode)

sounddevice_enabled = _SD
vad_enabled         = _VAD_OK
vosk_enabled        = _VOSK_OK
