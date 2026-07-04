"""Scaffold for face enrollment and verification.

Uses `face_recognition` when available for face encodings. Falls back to
image-hash (PIL + imagehash) if `face_recognition` is not installed.

Note: `face_recognition` depends on dlib and can be heavy to install on some platforms.
"""
from __future__ import annotations

import os
from typing import Dict, Any, Tuple

from . import secure_store


FACE_STORE_FILE = "face_profiles.enc"


def _load_profiles() -> Dict[str, Any]:
    return secure_store.load_secure_json(FACE_STORE_FILE)


def _save_profiles(p: Dict[str, Any]) -> None:
    secure_store.save_secure_json(p, FACE_STORE_FILE)


def enroll_face(profile_name: str, image_path: str) -> None:
    profiles = _load_profiles()
    try:
        import face_recognition

        img = face_recognition.load_image_file(image_path)
        encs = face_recognition.face_encodings(img)
        if not encs:
            raise RuntimeError("No face found in image")
        profiles[profile_name] = {"encoding": encs[0].tolist(), "image": os.path.abspath(image_path)}
    except Exception:
        # fallback: use imagehash
        from PIL import Image
        import imagehash

        h = str(imagehash.average_hash(Image.open(image_path)))
        profiles[profile_name] = {"hash": h, "image": os.path.abspath(image_path)}
    _save_profiles(profiles)


def verify_face(image_path: str, tolerance: float = 0.6) -> Tuple[str | None, float]:
    profiles = _load_profiles()
    if not profiles:
        return None, 0.0
    try:
        import face_recognition
        import numpy as np

        img = face_recognition.load_image_file(image_path)
        encs = face_recognition.face_encodings(img)
        if not encs:
            return None, 0.0
        probe = encs[0]
        best = None
        best_score = 1e9
        for name, data in profiles.items():
            if "encoding" not in data:
                continue
            stored = np.asarray(data["encoding"])
            dist = float(np.linalg.norm(probe - stored))
            if dist < best_score:
                best_score = dist
                best = name
        # convert distance to confidence-like score
        conf = max(0.0, 1.0 - (best_score / tolerance))
        if conf > 0:
            return best, conf
        return None, conf
    except Exception:
        # fallback: use imagehash Hamming distance
        from PIL import Image
        import imagehash

        probe = imagehash.average_hash(Image.open(image_path))
        best_name = None
        best_score = 1e9
        for name, data in profiles.items():
            if "hash" not in data:
                continue
            h = imagehash.hex_to_hash(data["hash"]) if isinstance(data["hash"], str) else data["hash"]
            dist = probe - h
            if dist < best_score:
                best_score = dist
                best_name = name
        # Map hamming distance to confidence (rough)
        max_bits = 64
        conf = max(0.0, 1.0 - (best_score / max_bits))
        if conf > 0.2:
            return best_name, conf
        return None, conf


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Face enrollment & verification (scaffold)")
    sub = parser.add_subparsers(dest="cmd")

    p_enroll = sub.add_parser("enroll")
    p_enroll.add_argument("name")
    p_enroll.add_argument("image")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("image")

    args = parser.parse_args()
    if args.cmd == "enroll":
        enroll_face(args.name, args.image)
        print(f"Enrolled face profile '{args.name}'")
    elif args.cmd == "verify":
        name, conf = verify_face(args.image)
        if name:
            print(f"Verified: {name} ({conf*100:.1f}%)")
        else:
            print(f"No match (confidence {conf*100:.1f}%)")
    else:
        parser.print_help()
