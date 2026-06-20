"""
JARVIS STT Service — speech-to-text with engine fallback chain.
Priority: Azure → Google → Vosk (offline)
"""

import json
import logging
import os
import queue
import re
import socket
import sys
import threading
import time
from typing import Tuple

import speech_recognition as sr

logger = logging.getLogger(__name__)

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import sounddevice as sd
    _SD = True
except ImportError:
    _SD = False

try:
    from vosk import Model, KaldiRecognizer
    _VOSK = True
except ImportError:
    _VOSK = False

try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False

try:
    import webrtcvad as _webrtcvad
    _VAD = _webrtcvad.Vad(2)  # aggressiveness 0-3; 2 = balanced
    _WEBRTCVAD = True
except Exception:
    _VAD = None
    _WEBRTCVAD = False

try:
    import azure.cognitiveservices.speech as speechsdk
    _AZURE = True
except ImportError:
    _AZURE = False

_recognizer = sr.Recognizer()
_recognizer.pause_threshold = 0.8
_recognizer.energy_threshold = 300

_LAST_TEXT = ""
_LAST_AT = 0.0


def _check_internet() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 80), 2)
        return True
    except OSError:
        return False


def _normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s:]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    words, prev = [], None
    for w in t.split():
        if w != prev:
            words.append(w)
        prev = w
    return " ".join(words)


def _deduplicate(text: str) -> str:
    global _LAST_TEXT, _LAST_AT
    normalized = _normalize(text)
    if not normalized:
        return ""
    now = time.time()
    if normalized == _LAST_TEXT and (now - _LAST_AT) < 2.5:
        logger.debug("Duplicate transcript ignored: %s", normalized)
        return ""
    _LAST_TEXT, _LAST_AT = normalized, now
    return normalized


def _vosk_model_path() -> str:
    return os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-en-us-0.15")


def _listen_azure() -> str:
    key = os.getenv("AZURE_SPEECH_KEY", "")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    if not key:
        return ""
    try:
        cfg = speechsdk.SpeechConfig(subscription=key, region=region)
        cfg.speech_recognition_language = "en-IN"
        audio_cfg = speechsdk.audio.AudioConfig(use_default_microphone=True)
        rec = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_cfg)
        result = rec.recognize_once_async().get()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text.lower()
    except Exception as e:
        logger.warning("Azure STT error: %s", e)
    return ""


def _listen_google() -> str:
    try:
        if _SD:
            RATE, CHUNK = 16000, 320
            q: queue.Queue = queue.Queue()

            def _cb(indata, frames, time_info, status):
                q.put(bytes(indata))

            voiced, silence, started = [], 0, False
            max_silence = int(RATE / CHUNK * 1.2)

            with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype="int16", channels=1, callback=_cb):
                deadline = time.time() + 8
                while time.time() < deadline:
                    data = q.get()
                    if _NP:
                        if _WEBRTCVAD:
                            # webrtcvad expects 16-bit PCM, 10/20/30ms frames at 8/16/32/48 kHz
                            # CHUNK=320 @ 16kHz = 20ms — exactly what webrtcvad needs
                            try:
                                is_speech = _VAD.is_speech(data, RATE)
                            except Exception:
                                frame = np.frombuffer(data, dtype="int16").astype("float32")
                                is_speech = float(np.sqrt(np.mean(frame ** 2))) > 300
                        else:
                            frame = np.frombuffer(data, dtype="int16").astype("float32")
                            is_speech = float(np.sqrt(np.mean(frame ** 2))) > 300
                    else:
                        is_speech = True
                    if is_speech:
                        started = True
                        voiced.append(data)
                        silence = 0
                    elif started:
                        silence += 1
                        if silence > max_silence:
                            break

            if not voiced:
                return ""
            audio = sr.AudioData(b"".join(voiced), RATE, 2)
        else:
            with sr.Microphone() as source:
                _recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = _recognizer.listen(source, timeout=8, phrase_time_limit=7)

        results = {"en": "", "ta": ""}

        def _req(lang):
            try:
                results[lang] = _recognizer.recognize_google(audio, language=lang).strip()
            except Exception:
                pass

        t1 = threading.Thread(target=_req, args=("en-IN",))
        t2 = threading.Thread(target=_req, args=("ta-IN",))
        t1.start(); t2.start()
        t1.join(); t2.join()

        en, ta = results["en"].lower(), results["ta"].lower()
        if any("\u0b80" <= c <= "\u0bff" for c in ta):
            return ta
        return en if len(en) >= len(ta) else ta

    except Exception as e:
        logger.warning("Google STT error: %s", e)
        return ""


def _listen_vosk() -> str:
    model_path = _vosk_model_path()
    if not (_VOSK and _SD and os.path.exists(model_path)):
        return ""
    try:
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)
        q: queue.Queue = queue.Queue()

        def _cb(indata, frames, time_info, status):
            q.put(bytes(indata))

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=_cb):
            deadline = time.time() + 10
            while time.time() < deadline:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        return text.lower()
    except Exception as e:
        logger.warning("Vosk STT error: %s", e)
    return ""


def listen_with_identity(duration: float = 4.0) -> Tuple[str, str, float]:
    """
    Capture audio, run STT and speaker verification simultaneously.
    Returns (text, speaker_name, confidence).
    """
    try:
        import sounddevice as sd
        from jarvis.services.voice_id import verify

        RATE = 16000
        recording = sd.rec(int(duration * RATE), samplerate=RATE, channels=1, dtype="float32")
        sd.wait()
        audio_flat = recording.flatten()

        # Run STT and voice ID in parallel
        text_result: list = [""]
        id_result: list = [("unknown", 0.0)]

        def _stt():
            audio_bytes = (audio_flat * 32767).astype("int16").tobytes()
            audio_data = sr.AudioData(audio_bytes, RATE, 2)
            results = {"en": "", "ta": ""}
            def _req(lang):
                try:
                    results[lang] = _recognizer.recognize_google(audio_data, language=lang).strip()
                except Exception:
                    pass
            t1 = threading.Thread(target=_req, args=("en-IN",))
            t2 = threading.Thread(target=_req, args=("ta-IN",))
            t1.start(); t2.start(); t1.join(); t2.join()
            en, ta = results["en"].lower(), results["ta"].lower()
            text_result[0] = ta if any("\u0b80" <= c <= "\u0bff" for c in ta) else (en if len(en) >= len(ta) else ta)

        def _vid():
            id_result[0] = verify(audio_flat, RATE)

        t_stt = threading.Thread(target=_stt)
        t_vid = threading.Thread(target=_vid)
        t_stt.start(); t_vid.start()
        t_stt.join(); t_vid.join()

        text = _deduplicate(text_result[0])
        name, conf = id_result[0]
        return (text, name, conf)

    except Exception as e:
        logger.warning("listen_with_identity failed: %s", e)
        return (listen(), "unknown", 0.0)


def listen() -> str:
    """Capture audio and return recognized text."""
    override = os.getenv("JARVIS_STT_ENGINE", "auto").lower()
    online = _check_internet()

    if override == "azure" and _AZURE and os.getenv("AZURE_SPEECH_KEY"):
        text = _listen_azure()
    elif override == "vosk":
        text = _listen_vosk()
    elif override == "google":
        text = _listen_google()
    else:
        # Auto: prefer Azure if key present, else Google, else Vosk offline
        if _AZURE and os.getenv("AZURE_SPEECH_KEY") and online:
            text = _listen_azure() or _listen_google()
        elif online:
            text = _listen_google()
        else:
            text = _listen_vosk()

    return _deduplicate(text)
