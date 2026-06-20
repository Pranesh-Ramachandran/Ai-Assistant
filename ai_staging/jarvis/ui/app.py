"""
JARVIS Flask Web UI — secure, async-capable, rate-limited.
"""

import hashlib
import json
import logging
import os
import secrets
from functools import wraps
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

_UI_DIR = str(Path(__file__).resolve().parent / "static")
_USERS_FILE = str(Path(__file__).resolve().parent.parent.parent / "data" / "users.json")

app = Flask(__name__, static_folder=_UI_DIR, static_url_path="", template_folder=_UI_DIR)
# Use env var if provided; auto-generate a secure key as fallback (not persisted across restarts)
_secret = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.secret_key = _secret
if not os.environ.get("FLASK_SECRET_KEY"):
    logger.warning("FLASK_SECRET_KEY not set — sessions won't persist across restarts")

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)

# ── Thread-safe lazy brain init ──────────────────────────────────────────────
_brain = None
_brain_lock = __import__("threading").Lock()


def _get_brain():
    global _brain
    if _brain is None:
        with _brain_lock:
            if _brain is None:
                from jarvis.core.brain import JarvisBrain
                _brain = JarvisBrain()
    return _brain


# ── User store helpers ────────────────────────────────────────────────────────

def _load_users() -> dict:
    if os.path.exists(_USERS_FILE):
        try:
            with open(_USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load users file: %s", e)
    return {}


def _save_users(users: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_USERS_FILE), exist_ok=True)
        with open(_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except OSError as e:
        logger.error("Could not save users file: %s", e)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{h}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        return secrets.compare_digest(h, hashlib.sha256(f"{salt}{password}".encode()).hexdigest())
    except ValueError:
        return False


def _validate_input(data: Optional[dict], *required_fields: str) -> Optional[str]:
    """Return error string if validation fails, else None."""
    if not data:
        return "No data provided"
    for field in required_fields:
        val = data.get(field, "")
        if not val or not str(val).strip():
            return f"Missing field: {field}"
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/auth", methods=["POST"])
@limiter.limit("10 per minute")
def authenticate():
    data = request.get_json(silent=True)
    action = (data or {}).get("action", "")

    if action == "login":
        err = _validate_input(data, "email", "password")
        if err:
            return jsonify({"success": False, "message": err}), 400

        email = data["email"].strip().lower()
        users = _load_users()
        user = users.get(email)
        if not user or not _verify_password(data["password"], user["password"]):
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        session["user"] = email
        return jsonify({"success": True, "redirect": "/"})

    if action == "register":
        err = _validate_input(data, "name", "email", "password")
        if err:
            return jsonify({"success": False, "message": err}), 400

        email = data["email"].strip().lower()
        password = data["password"]
        if len(password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"}), 400

        users = _load_users()
        if email in users:
            return jsonify({"success": False, "message": "Email already registered"}), 409

        users[email] = {"name": data["name"].strip(), "password": _hash_password(password)}
        _save_users(users)
        session["user"] = email
        return jsonify({"success": True, "message": f"Welcome {data['name'].strip()}", "redirect": "/"})

    return jsonify({"success": False, "message": "Invalid action"}), 400


@app.route("/send_message", methods=["POST"])
@limiter.limit("30 per minute")
def send_message():
    if "user" not in session:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    data = request.get_json(silent=True)
    message = ((data or {}).get("message") or "").strip()

    if not message:
        return jsonify({"success": False, "message": "Empty message"}), 400
    if len(message) > 1000:
        return jsonify({"success": False, "message": "Message too long (max 1000 chars)"}), 400

    brain = _get_brain()
    intent = brain.analyze_intent(message)
    response = brain.generate_response(intent, message)
    return jsonify({"success": True, "response": response, "intent": intent})


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/status")
def status():
    from jarvis.core.ai_brain import get_status
    data = get_status()
    data["version"] = "3.1.0"
    data["authenticated"] = "user" in session
    return jsonify(data)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "jarvis"}), 200


# ── Voice auth routes ─────────────────────────────────────────────────────────

@app.route("/voice_login", methods=["POST"])
@limiter.limit("10 per minute")
def voice_login():
    """
    Accepts raw PCM audio (float32, 16kHz, mono) as multipart/form-data field 'audio',
    or triggers mic capture server-side if no audio provided.
    Returns {success, user, confidence} or {success: false, message}.
    """
    from jarvis.services.voice_id import verify, list_profiles

    if not list_profiles():
        return jsonify({"success": False, "message": "No voice profiles enrolled yet."}), 400

    audio_file = request.files.get("audio")
    if audio_file:
        import numpy as np
        raw = audio_file.read()
        audio_np = np.frombuffer(raw, dtype=np.float32)
        name, confidence = verify(audio_np, 16000)
    else:
        # Server-side mic capture (voice mode)
        from jarvis.services.voice_id import verify_from_mic
        name, confidence = verify_from_mic(duration=3.0)

    if name != "unknown" and confidence >= 0.5:
        session["user"] = name
        session["voice_verified"] = True
        logger.info("Voice login: '%s' (conf=%.2f)", name, confidence)
        return jsonify({"success": True, "user": name, "confidence": confidence, "redirect": "/"})

    return jsonify({"success": False, "message": "Voice not recognized.", "confidence": confidence}), 401


@app.route("/voice_enroll", methods=["POST"])
@limiter.limit("5 per hour")
def voice_enroll():
    """
    Enroll a new voice profile.
    Expects JSON {"name": "<username>", "samples": N} — triggers server-side mic recording.
    Only allowed if already authenticated or no profiles exist yet (first-run).
    """
    from jarvis.services.voice_id import enroll, list_profiles

    existing = list_profiles()
    if existing and "user" not in session:
        return jsonify({"success": False, "message": "Must be logged in to enroll a new profile."}), 401

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Name required."}), 400
    if len(name) > 32 or not name.replace("_", "").replace("-", "").isalnum():
        return jsonify({"success": False, "message": "Name must be alphanumeric (max 32 chars)."}), 400

    samples = min(int(data.get("samples", 5)), 10)
    success = enroll(name, samples=samples)
    if success:
        return jsonify({"success": True, "message": f"Voice profile '{name}' enrolled."})
    return jsonify({"success": False, "message": "Enrollment failed — not enough clear samples."}), 500


@app.route("/voice_profiles", methods=["GET"])
def voice_profiles():
    from jarvis.services.voice_id import list_profiles
    return jsonify({"profiles": list_profiles()})


@app.route("/voice_profiles/<name>", methods=["DELETE"])
def delete_voice_profile(name: str):
    if "user" not in session:
        return jsonify({"success": False, "message": "Not authenticated."}), 401
    from jarvis.services.voice_id import delete_profile
    if delete_profile(name):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Profile not found."}), 404
