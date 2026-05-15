"""
JARVIS Voice ID — Advanced Speaker Identification using Librosa MFCC + DTW.

Architecture:
  - Enroll:   Record ~3s of speech → extract 2D MFCC trajectory → save to voice_profiles/{name}.npy
  - Identify: Extract 2D MFCC → use Dynamic Time Warping (DTW) to compute distance
  - Advanced Biometrics: Preserves time-domain structure (unlike simple averaging)

Public API:
  enroll(name, audio_data=None)
  identify(audio_data)
  get_profiles()
  delete_profile(name)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Optional, Tuple, List
import queue

import numpy as np
import librosa

LOGGER = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(_BASE_DIR, "voice_profiles")
PROFILES_META = os.path.join(PROFILES_DIR, "profiles.json")

os.makedirs(PROFILES_DIR, exist_ok=True)

# ─── Advanced MFCC feature extraction ────────────────────────────────────────

def extract_advanced_mfcc(audio_data: np.ndarray, sample_rate: int = 16000,
                          n_mfcc: int = 20) -> np.ndarray:
    """
    Extract MFCC features from raw audio data over time.
    Instead of averaging, keep the sequence to preserve spoken rhythm and phonetic shape.

    Args:
        audio_data: 1D numpy array of audio samples (float32, normalized -1..1)
        sample_rate: Audio sample rate
        n_mfcc: Number of Mel-frequency cepstral coefficients

    Returns:
        2D numpy array (n_mfcc, T) representing the voiceprint trajectory
    """
    # Normalize
    audio = audio_data.astype(np.float64)
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))

    # Pre-emphasis (High-pass filter to balance frequency spectrum)
    audio = librosa.effects.preemphasis(audio)

    # Trim leading/trailing silence (top_db=20)
    audio, _ = librosa.effects.trim(audio, top_db=20)

    # Extract MFCCs
    mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=n_mfcc, n_fft=512, hop_length=160)

    # Standardize features across time (Zero mean, unit variance)
    import sklearn.preprocessing
    mfcc = sklearn.preprocessing.scale(mfcc, axis=1)

    return mfcc


def _dtw_distance(target: np.ndarray, reference: np.ndarray) -> float:
    """
    Compute normalized Dynamic Time Warping (DTW) distance.
    Smaller distance = higher similarity.
    """
    if target.size == 0 or reference.size == 0:
        return float('inf')

    # Compute DTW alignment
    D, wp = librosa.sequence.dtw(X=target, Y=reference, metric='cosine')
    
    # Normalized distance based on path length
    match_distance = D[-1, -1] / len(wp)
    return float(match_distance)


# ═══════════════════════════════════════════════════════════════════════════════
# Profile management
# ═══════════════════════════════════════════════════════════════════════════════

def _load_meta() -> dict:
    if os.path.exists(PROFILES_META):
        try:
            with open(PROFILES_META, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_meta(meta: dict):
    with open(PROFILES_META, "w") as f:
        json.dump(meta, f, indent=2)


def get_profiles() -> List[str]:
    """Return list of enrolled profile names."""
    meta = _load_meta()
    return list(meta.keys())


def delete_profile(name: str) -> bool:
    meta = _load_meta()
    if name in meta:
        npy_path = os.path.join(PROFILES_DIR, f"{name}.npy")
        if os.path.exists(npy_path):
            os.remove(npy_path)
        del meta[name]
        _save_meta(meta)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Enrollment
# ═══════════════════════════════════════════════════════════════════════════════

def enroll_from_audio(name: str, audio_data: np.ndarray,
                      sample_rate: int = 16000) -> bool:
    try:
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0

        voiceprint = extract_advanced_mfcc(audio_data, sample_rate)

        if voiceprint.size == 0:
            LOGGER.warning("Audio too short or silent.")
            return False

        npy_path = os.path.join(PROFILES_DIR, f"{name}.npy")
        np.save(npy_path, voiceprint)

        meta = _load_meta()
        meta[name] = {
            "enrolled_at": time.time(),
            "sample_rate": sample_rate,
            "frames": voiceprint.shape[1],
        }
        _save_meta(meta)

        LOGGER.info("Enrolled advanced DTW profile for '%s'", name)
        return True

    except Exception as exc:
        LOGGER.error("Enrollment failed for '%s': %s", name, exc)
        return False


def enroll_from_mic(name: str, duration: float = 3.0) -> bool:
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        with sr.Microphone(sample_rate=16000) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            LOGGER.info("Recording %s seconds for enrollment...", duration)
            audio = recognizer.listen(source, timeout=duration + 2, phrase_time_limit=duration)

        raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

        if len(audio_np) < 8000:
            return False

        return enroll_from_audio(name, audio_np, 16000)

    except Exception as exc:
        LOGGER.error("Mic enrollment failed: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Identification
# ═══════════════════════════════════════════════════════════════════════════════

# Distance threshold (DTW normalized cosine distance). Lower = more strict.
DTW_THRESHOLD = 0.65  

_profile_cache: dict[str, np.ndarray] = {}
_cache_lock = threading.Lock()

def _load_profiles_into_cache():
    global _profile_cache
    meta = _load_meta()
    with _cache_lock:
        _profile_cache.clear()
        for name in meta:
            npy_path = os.path.join(PROFILES_DIR, f"{name}.npy")
            if os.path.exists(npy_path):
                try:
                    _profile_cache[name] = np.load(npy_path)
                except Exception as exc:
                    LOGGER.warning("Failed to load %s: %s", name, exc)


def identify(audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[str, float]:
    """
    Identify the speaker using DTW sequence matching against known profiles.
    Returns: (name, similarity_score_0_to_1)
    """
    try:
        if not _profile_cache:
            _load_profiles_into_cache()

        if not _profile_cache:
            return ("Guest", 0.0)

        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0

        input_print = extract_advanced_mfcc(audio_data, sample_rate)
        if input_print.size == 0 or input_print.shape[1] < 10:
            # Audio is too short or just empty noise
            return ("Guest", 0.0)

        best_name = "Guest"
        best_dist = float('inf')

        with _cache_lock:
            for name, profile in _profile_cache.items():
                # Compute Dynamic Time Warping alignment distance
                dist = _dtw_distance(input_print, profile)
                if dist < best_dist:
                    best_dist = dist
                    best_name = name

        # Convert distance to a 0.0 - 1.0 "confidence" score for UI
        # Threshold mapping: 0 distance = 1.0 similarity. Threshold distance = 0% confidence.
        if best_dist <= DTW_THRESHOLD:
            # Scale so DTW_THRESHOLD = 0.5 confidence, 0.0 = 1.0 confidence
            confidence = max(0.5, 1.0 - (best_dist / (DTW_THRESHOLD * 2)))
            LOGGER.info("DTW Voice ID: identified '%s' (dist: %.3f)", best_name, best_dist)
            return (best_name, confidence)
        else:
            LOGGER.debug("DTW Voice ID: no match (closest: '%s' dist %.3f)", best_name, best_dist)
            return ("Guest", 0.0)

    except Exception as exc:
        LOGGER.error("Voice identification failed: %s", exc)
        return ("Guest", 0.0)

def reload_profiles():
    _load_profiles_into_cache()

def identify_from_mic(duration: float = 3.0) -> Tuple[str, float]:
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        with sr.Microphone(sample_rate=16000) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=duration + 2, phrase_time_limit=duration)

        raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

        return identify(audio_np, 16000)

    except Exception as exc:
        LOGGER.error("Mic identify failed: %s", exc)
        return ("Guest", 0.0)
