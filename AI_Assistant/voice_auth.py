"""Simple voice enrollment and verification scaffold.

This is a lightweight proof-of-concept using MFCC embeddings (via librosa).
It is NOT production-ready: it lacks anti-replay, liveness checks, secure storage,
and multi-sample enrollment. Use this as a starting point for integrating
proper biometric models or cloud services.

Usage (examples):
  Enroll:
    python -m AI_Assistant.voice_auth enroll Pranesh path/to/sample.wav

  Verify:
    python -m AI_Assistant.voice_auth verify path/to/verify_sample.wav

Outputs a JSON with the best-match profile and a similarity score (0..1).
"""
from __future__ import annotations

import json
import os
from typing import Dict, Any, Tuple

import numpy as np
import librosa

from . import secure_store


# Use encrypted store filename
VOICE_STORE_FILE = "voice_profiles.enc"


def _audio_embedding(path: str, sr: int = 16000, n_mfcc: int = 20) -> np.ndarray:
    y, _ = librosa.load(path, sr=sr)
    # Compute MFCCs and use the mean over time as a simple embedding
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    emb = np.mean(mfcc, axis=1)
    # L2 normalize
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm
    return emb


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a)
    b = np.asarray(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def enroll_voice(profile_name: str, audio_path: str) -> None:
    """Enroll a voice sample under `profile_name`.

    Stores a single embedding and a reference to the example audio file.
    For robustness, enroll multiple samples per user in a real system.
    """
    # simple liveness check before enrolling
    if not liveness_check(audio_path):
        raise RuntimeError("Liveness check failed. Use a real, live sample.")
    profiles = secure_store.load_secure_json(VOICE_STORE_FILE)
    emb = _audio_embedding(audio_path)
    profiles[profile_name] = {
        "embedding": emb.tolist(),
        "example_audio": os.path.abspath(audio_path),
    }
    secure_store.save_secure_json(profiles, VOICE_STORE_FILE)


def verify_voice(audio_path: str, min_confidence: float = 0.9) -> Tuple[str | None, float]:
    """Verify an audio sample against enrolled profiles.

    Returns (best_profile_name or None, confidence 0..1).
    """
    # basic liveness check to mitigate replay attacks
    if not liveness_check(audio_path):
        return None, 0.0
    profiles = secure_store.load_secure_json(VOICE_STORE_FILE)
    if not profiles:
        return None, 0.0
    emb = _audio_embedding(audio_path)
    best_name = None
    best_score = 0.0
    for name, data in profiles.items():
        stored = np.asarray(data.get("embedding", []))
        score = _cosine_similarity(emb, stored)
        if score > best_score:
            best_score = score
            best_name = name
    # Map cosine (which can be -1..1) to 0..1 range (clamped)
    conf = max(0.0, min(1.0, (best_score + 1) / 2))
    if conf >= min_confidence:
        return best_name, conf
    return None, conf


def liveness_check(audio_path: str, min_duration: float = 0.6, min_rms: float = 0.005) -> bool:
    """Basic anti-replay / liveness heuristic.

    This is a lightweight check: it verifies duration, RMS energy, and
    (when available) a VAD-based voiced frame ratio. It is NOT a full
    anti-spoofing system. For production use specialized liveness models.
    """
    try:
        y, sr = librosa.load(audio_path, sr=16000)
    except Exception:
        return False
    duration = len(y) / 16000.0
    if duration < min_duration:
        return False
    rms = float(np.mean(librosa.feature.rms(y=y)))
    if rms < min_rms:
        return False
    # optional: use webrtcvad if available to count voiced frames
    try:
        import webrtcvad

        vad = webrtcvad.Vad(2)
        # frame size 30ms
        frame_ms = 30
        frame_len = int(0.001 * frame_ms * sr)
        voiced = 0
        total = 0
        # convert to 16-bit PCM
        pcm = (y * 32767).astype("int16").tobytes()
        for i in range(0, len(pcm), frame_len * 2):
            frame = pcm[i : i + frame_len * 2]
            if len(frame) < frame_len * 2:
                break
            total += 1
            if vad.is_speech(frame, sr):
                voiced += 1
        if total > 0 and (voiced / total) < 0.3:
            return False
    except Exception:
        # if webrtcvad unavailable, skip
        pass
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice enrollment & verification (scaffold)")
    sub = parser.add_subparsers(dest="cmd")

    p_enroll = sub.add_parser("enroll")
    p_enroll.add_argument("name")
    p_enroll.add_argument("audio")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("audio")
    p_verify.add_argument("--min", type=float, default=0.9)

    args = parser.parse_args()
    if args.cmd == "enroll":
        enroll_voice(args.name, args.audio)
        print(f"Enrolled profile '{args.name}' with sample: {args.audio}")
    elif args.cmd == "verify":
        name, conf = verify_voice(args.audio, min_confidence=args.min)
        if name:
            print(f"Verified: {name} ({conf*100:.1f}%)")
        else:
            print(f"No match (confidence {conf*100:.1f}%)")
    else:
        parser.print_help()
