"""Secure JSON storage using Fernet symmetric encryption.

This helper stores encrypted JSON blobs to disk. It uses an application
key read from the environment variable `JARVIS_SECRET_KEY` (base64 urlsafe),
or generates and saves a key to `AI_Assistant/.jarvis_key` if none is present.

Warning: Key management is critical. For production, use a secure vault.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


def _key_file_path() -> str:
    return os.path.join(os.path.dirname(__file__), ".jarvis_key")


def get_or_create_key() -> bytes:
    env = os.environ.get("JARVIS_SECRET_KEY")
    if env:
        # user-provided key (should be base64 urlsafe)
        return env.encode()
    path = _key_file_path()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    # write key to disk for convenience (restrict permissions if you can)
    try:
        with open(path, "wb") as f:
            f.write(key)
    except Exception:
        pass
    return key


def _fernet(key: Optional[bytes] = None) -> Fernet:
    if key is None:
        key = get_or_create_key()
    return Fernet(key)


def save_secure_json(obj: Dict[str, Any], filename: str = "voice_profiles.enc", key: Optional[bytes] = None) -> None:
    path = os.path.join(os.path.dirname(__file__), filename)
    f = _fernet(key)
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    token = f.encrypt(raw)
    with open(path, "wb") as fh:
        fh.write(token)


def load_secure_json(filename: str = "voice_profiles.enc", key: Optional[bytes] = None) -> Dict[str, Any]:
    path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(path):
        return {}
    f = _fernet(key)
    with open(path, "rb") as fh:
        token = fh.read()
    try:
        raw = f.decrypt(token)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        # If decryption fails, return empty dict to avoid crashes.
        return {}
