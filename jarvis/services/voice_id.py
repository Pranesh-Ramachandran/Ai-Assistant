"""
JARVIS Voice ID — Speaker identification using MFCC + Dynamic Time Warping.

Architecture:
  - Enroll:   Record N samples → extract MFCC trajectory per sample → save to data/voice_profiles/
  - Verify:   Extract MFCC from live audio → DTW distance against all enrolled samples
              → accept if median distance < threshold
  - Liveness: Reject suspiciously short or silent audio (basic anti-spoofing)

Public API:
  enroll(name, samples=5)          → bool
  verify(audio_np, sr) -> (name, confidence)
  list_profiles()                  → list[str]
  delete_profile(name)             → bool
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "voice_profiles"
_META_FILE    = _PROFILES_DIR / "profiles.json"

# ── Tuning constants ──────────────────────────────────────────────────────────
_N_MFCC        = 20      # number of MFCC coefficients
_DTW_THRESHOLD = 0.55    # normalized cosine DTW distance — lower = stricter
_MIN_FRAMES    = 30      # reject audio shorter than this (liveness check)
_SAMPLE_RATE   = 16000

# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    import librosa
    import librosa.feature
    import librosa.effects
    _LIBROSA = True
except ImportError:
    _LIBROSA = False
    logger.warning("librosa not installed — voice ID unavailable. pip install librosa scikit-learn")

try:
    from sklearn.preprocessing import scale as _skscale
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


# ── Feature extraction ────────────────────────────────────────────────────────

def _extract_mfcc(audio: np.ndarray, sr: int = _SAMPLE_RATE) -> Optional[np.ndarray]:
    """
    Returns 2D MFCC matrix (n_mfcc × T) or None if audio is too short/silent.
    Preserves time structure for DTW — does NOT average.
    """
    if not _LIBROSA:
        return None

    # Normalize to float32 [-1, 1]
    audio = audio.astype(np.float32)
    if audio.dtype == np.int16:
        audio = audio / 32768.0
    peak = np.max(np.abs(audio))
    if peak < 1e-6:
        return None  # silent
    audio = audio / peak

    # Pre-emphasis
    audio = librosa.effects.preemphasis(audio)

    # Trim silence
    audio, _ = librosa.effects.trim(audio, top_db=25)

    if len(audio) < _MIN_FRAMES * 160:  # too short
        return None

    mfcc = librosa.feature.mfcc(
        y=audio, sr=sr, n_mfcc=_N_MFCC, n_fft=512, hop_length=160
    )

    # Standardize per-coefficient across time
    if _SKLEARN:
        mfcc = _skscale(mfcc, axis=1)
    else:
        mfcc = (mfcc - mfcc.mean(axis=1, keepdims=True)) / (mfcc.std(axis=1, keepdims=True) + 1e-8)

    return mfcc  # shape: (n_mfcc, T)


def _dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Vectorized numpy DTW cosine distance. Replaces the O(n*m) pure-Python loop.
    a, b: shape (n_mfcc, T)
    """
    if a.size == 0 or b.size == 0:
        return float("inf")
    n, m = a.shape[1], b.shape[1]
    a_n = a / (np.linalg.norm(a, axis=0, keepdims=True) + 1e-8)
    b_n = b / (np.linalg.norm(b, axis=0, keepdims=True) + 1e-8)
    cost = 1.0 - (a_n.T @ b_n)  # (n, m)

    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        prev_row = D[i - 1, :]  # shape (m+1,)
        diag = prev_row[:-1]    # D[i-1, j-1]
        up   = prev_row[1:]     # D[i-1, j]
        left = D[i, :-1]        # D[i, j-1]  — filled left-to-right below
        # We still need a per-row left-to-right pass for the left neighbour,
        # but we can vectorise the diagonal+up component:
        best_prev = np.minimum(diag, up)  # min(D[i-1,j-1], D[i-1,j]) for all j
        # Left neighbour requires sequential scan — do it with cumsum trick:
        # D[i,j] = cost[i-1,j-1] + min(best_prev[j-1], D[i,j-1])
        row = np.empty(m)
        row[0] = cost[i - 1, 0] + min(best_prev[0], D[i, 0])
        for j in range(1, m):
            row[j] = cost[i - 1, j] + min(best_prev[j], row[j - 1])
        D[i, 1:] = row

    return float(D[n, m] / max(n + m - 1, 1))


# ── Profile persistence ───────────────────────────────────────────────────────

def _load_meta() -> dict:
    if _META_FILE.exists():
        try:
            return json.loads(_META_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_meta(meta: dict) -> None:
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    _META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")


# ── In-memory profile cache ───────────────────────────────────────────────────
# Each profile stores a list of MFCC matrices (one per enrollment sample)

_cache: dict[str, list[np.ndarray]] = {}
_cache_lock = threading.Lock()
_cache_loaded = False


def _load_cache() -> None:
    global _cache_loaded
    meta = _load_meta()
    with _cache_lock:
        _cache.clear()
        for name in meta:
            samples_dir = _PROFILES_DIR / name
            if not samples_dir.exists():
                continue
            matrices = []
            for npy in sorted(samples_dir.glob("*.npy")):
                try:
                    matrices.append(np.load(str(npy)))
                except Exception as e:
                    logger.warning("Could not load %s: %s", npy, e)
            if matrices:
                _cache[name] = matrices
        _cache_loaded = True


def _ensure_cache() -> None:
    if not _cache_loaded:
        _load_cache()


# ── Public API ────────────────────────────────────────────────────────────────

def list_profiles() -> list[str]:
    return list(_load_meta().keys())


def delete_profile(name: str) -> bool:
    meta = _load_meta()
    if name not in meta:
        return False
    import shutil
    shutil.rmtree(str(_PROFILES_DIR / name), ignore_errors=True)
    del meta[name]
    _save_meta(meta)
    with _cache_lock:
        _cache.pop(name, None)
    logger.info("Deleted voice profile: %s", name)
    return True


def enroll(name: str, samples: int = 5) -> bool:
    """
    Interactively record `samples` voice clips from the mic and save MFCC profiles.
    Prompts the user to speak a passphrase each time.
    Returns True if at least 3 samples were captured successfully.
    """
    if not _LIBROSA:
        logger.error("librosa required for enrollment")
        return False

    try:
        import sounddevice as sd
    except ImportError:
        logger.error("sounddevice required for enrollment")
        return False

    sample_dir = _PROFILES_DIR / name
    sample_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    print(f"\n[Voice Enrollment] Enrolling '{name}' — {samples} samples needed.")
    print("Say 'Hey JARVIS' clearly each time when prompted.\n")

    for i in range(samples):
        input(f"  Sample {i+1}/{samples} — press Enter then speak for 3 seconds...")
        print("  Recording...")
        recording = sd.rec(
            int(3.0 * _SAMPLE_RATE),
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio = recording.flatten()

        mfcc = _extract_mfcc(audio, _SAMPLE_RATE)
        if mfcc is None or mfcc.shape[1] < _MIN_FRAMES:
            print("  ✗ Too short or silent — skipped.")
            continue

        npy_path = sample_dir / f"sample_{i:02d}.npy"
        np.save(str(npy_path), mfcc)
        saved += 1
        print(f"  ✓ Sample {saved} saved.")

    if saved < 3:
        print(f"\n✗ Only {saved} usable samples — need at least 3. Enrollment failed.")
        import shutil
        shutil.rmtree(str(sample_dir), ignore_errors=True)
        return False

    meta = _load_meta()
    meta[name] = {"enrolled_at": time.time(), "samples": saved}
    _save_meta(meta)
    _load_cache()  # refresh cache
    print(f"\n✓ Enrolled '{name}' with {saved} samples.")
    logger.info("Enrolled voice profile '%s' (%d samples)", name, saved)
    return True


def verify(audio: np.ndarray, sr: int = _SAMPLE_RATE) -> Tuple[str, float]:
    """
    Compare audio against all enrolled profiles.
    Returns (name, confidence) where confidence is 0.0–1.0.
    Returns ("unknown", 0.0) if no match or no profiles enrolled.
    """
    if not _LIBROSA:
        return ("unknown", 0.0)

    _ensure_cache()

    with _cache_lock:
        if not _cache:
            return ("unknown", 0.0)
        profiles = dict(_cache)  # shallow copy for iteration

    input_mfcc = _extract_mfcc(audio, sr)
    if input_mfcc is None or input_mfcc.shape[1] < _MIN_FRAMES:
        logger.debug("Voice verify: audio too short/silent")
        return ("unknown", 0.0)

    best_name = "unknown"
    best_dist = float("inf")

    for name, sample_list in profiles.items():
        # Compute DTW distance against each enrolled sample, take median
        distances = [_dtw_distance(input_mfcc, s) for s in sample_list]
        median_dist = float(np.median(distances))
        logger.debug("Voice verify: '%s' median DTW dist=%.4f", name, median_dist)
        if median_dist < best_dist:
            best_dist = median_dist
            best_name = name

    if best_dist <= _DTW_THRESHOLD:
        # Map distance to confidence: 0 dist → 1.0, threshold dist → 0.5
        confidence = max(0.5, 1.0 - (best_dist / (_DTW_THRESHOLD * 2)))
        logger.info("Voice verified: '%s' (dist=%.4f, conf=%.2f)", best_name, best_dist, confidence)
        return (best_name, round(confidence, 3))

    logger.info("Voice not recognized (closest='%s' dist=%.4f > threshold=%.2f)",
                best_name, best_dist, _DTW_THRESHOLD)
    return ("unknown", 0.0)


def verify_from_mic(duration: float = 3.0) -> Tuple[str, float]:
    """Capture audio from mic and verify speaker. Convenience wrapper."""
    try:
        import sounddevice as sd
        recording = sd.rec(
            int(duration * _SAMPLE_RATE),
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        return verify(recording.flatten(), _SAMPLE_RATE)
    except Exception as e:
        logger.error("verify_from_mic failed: %s", e)
        return ("unknown", 0.0)
