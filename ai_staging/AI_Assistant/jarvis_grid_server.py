"""
JARVIS Neural Grid API Server — Full Feature Build
Endpoints:
  POST /api/chat          — text chat
  POST /api/listen        — STT: record mic → return transcript + AI reply
  POST /api/voice_id      — identify speaker from mic
  POST /api/enroll        — enroll new voice profile
  POST /api/status        — system + AI status
  POST /api/clear         — clear conversation memory
  POST /api/system        — system info (battery, cpu, ram, wifi)
  POST /api/wake          — start/stop wake word listener
"""
import sys, os, json, threading, time, re, glob, logging

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "server.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JARVIS")

# ── Load Environment Variables ────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), "jarvis.env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()
    logger.info(f"Loaded environment variables from jarvis.env")
else:
    logger.warning("jarvis.env not found!")

sys.path.insert(0, os.path.dirname(__file__))

# ── Startup cleanup: remove stale tmp JSON files ──────────────────────────────
for _f in glob.glob(os.path.join(os.path.dirname(__file__), "tmp*.json")):
    try:
        os.remove(_f)
    except Exception:
        pass

from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import base64

UI_DIR = os.path.join(os.path.dirname(__file__), "neural_grid_ui")
HOST   = "localhost"
PORT   = 7890

# ── AI Brain ──────────────────────────────────────────────────────────────────
try:
    from jarvis_ai_brain import ask as ai_ask, get_status as ai_status, clear_memory
    AI_READY = True
    print("[JARVIS] AI brain loaded OK")
except Exception as e:
    AI_READY = False
    print(f"[JARVIS] AI brain unavailable: {e}")
    def ai_ask(text, **kw): return f"AI brain offline. You said: {text}"
    def ai_status(): return {"ai_mode": "offline"}
    def clear_memory(): pass

# ── TTS ───────────────────────────────────────────────────────────────────────
try:
    from fast_tts import speak as tts_speak, stop_speaking, set_playback_start_callback, set_playback_end_callback
    TTS_READY = True
    print("[JARVIS] TTS loaded OK")
except Exception as e:
    TTS_READY = False
    def tts_speak(t, **kw): print(f"[TTS] {t}")
    def stop_speaking(): pass
    def set_playback_start_callback(fn): pass
    def set_playback_end_callback(fn): pass

_tts_speaking = False
_tts_lock = threading.Lock()

def _on_tts_started():
    """Called by fast_tts the moment audio begins playing."""
    try:
        _push_event("tts_start", {})
    except Exception as e:
        print(f"[TTS] Start callback error: {e}")

def _on_tts_ended():
    """Called by fast_tts when audio playback really ends."""
    global _tts_speaking, _passive_listen_active, _passive_listen_timer
    # Always reset speaking flag first so it can't get stuck
    with _tts_lock:
        _tts_speaking = False
    try:
        _push_event("tts_done", {})
    except Exception as e:
        print(f"[TTS] End push error: {e}")
    
    try:
        # Activate passive listening for 5 seconds after TTS ends
        with _passive_listen_lock:
            _passive_listen_active = True
            if _passive_listen_timer:
                _passive_listen_timer.cancel()
            def _end_passive_listen():
                global _passive_listen_active
                with _passive_listen_lock:
                    _passive_listen_active = False
                print("[JARVIS] Passive listening window closed.")
            _passive_listen_timer = threading.Timer(PASSIVE_LISTEN_TIMEOUT, _end_passive_listen)
            _passive_listen_timer.daemon = True
            _passive_listen_timer.start()
            print(f"[JARVIS] Passive listening active for {PASSIVE_LISTEN_TIMEOUT}s")
            threading.Thread(target=_passive_listen_monitor, daemon=True).start()
    except Exception as e:
        print(f"[TTS] Passive listen setup error: {e}")


def _passive_listen_monitor():
    """Monitor microphone during passive listening window - no wake word needed."""
    global _passive_listen_active
    
    # Reuse stt module's listen() instead of creating new Recognizer/Microphone instances
    if not STT_READY:
        return
    
    try:
        start_time = time.time()
        while _passive_listen_active and (time.time() - start_time) < PASSIVE_LISTEN_TIMEOUT:
            # Disable passive mode before recording to prevent re-entry
            with _passive_listen_lock:
                if not _passive_listen_active:
                    break
                _passive_listen_active = False
                if _passive_listen_timer:
                    _passive_listen_timer.cancel()
            
            print("[Passive] Listening for command...")
            transcript = stt_listen()
            
            if transcript:
                print(f"[Passive] Recognized: {transcript}")
                _push_event("stt", {"text": transcript})
                reply = _clean_ai_text(ai_ask(transcript))
                print(f"[JARVIS] {reply}")
                _push_event("reply", {"text": reply})
                if TTS_READY and reply:
                    _speak_tracked(reply)
            else:
                print("[Passive] No speech detected in window")
            return  # Exit after one attempt
    except Exception as e:
        print(f"[Passive Listen] Error: {e}")

# ── TTS worker queue — prevents blocking HTTP threads on audio playback ─────
import queue as _queue
_tts_queue: _queue.Queue = _queue.Queue(maxsize=2)

def _tts_worker_loop():
    """Dedicated daemon thread: drains TTS queue so HTTP threads never block."""
    while True:
        try:
            text = _tts_queue.get(timeout=1)
            tts_speak(text)
            _tts_queue.task_done()
        except _queue.Empty:
            pass
        except Exception as e:
            print(f"[TTS Worker] error: {e}")

_tts_worker_thread = threading.Thread(target=_tts_worker_loop, daemon=True, name="jarvis-tts-worker")
_tts_worker_thread.start()

def _speak_tracked(text):
    """Queue text for TTS. Never blocks the calling thread."""
    global _tts_speaking
    with _tts_lock:
        _tts_speaking = True
    # Drop oldest item if queue is full (don't let stale replies pile up)
    if _tts_queue.full():
        try:
            _tts_queue.get_nowait()
        except _queue.Empty:
            pass
    try:
        _tts_queue.put_nowait(text)
    except _queue.Full:
        pass  # Already full after drain attempt — skip this speak

def _clean_ai_text(text):
    """Remove leaked tool markup and JSON before returning or speaking it."""
    if text is None:
        return ""
    text = str(text)
    # Remove <function> tags
    text = re.sub(r'<function[^>]*>.*?</function>', '', text,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<function[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</function>', '', text, flags=re.IGNORECASE)
    if '<function' in text.lower():
        match = re.search(r'<function', text, flags=re.IGNORECASE)
        if match:
            text = text[:match.start()]
    # Remove raw JSON tool calls: {"name":"...","parameters":{...}}
    text = re.sub(r'\{\s*"name"\s*:\s*"[^"]*"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}', '', text, flags=re.DOTALL)
    # Remove shorthand JSON without parameters wrapper: {"name":"...","category":"..."}
    text = re.sub(r'\{\s*"name"\s*:\s*"[^"]*"\s*,', '', text)
    # Fallback: remove any JSON that starts a tool call pattern
    text = re.sub(r'\{\s*"(name|function)"\s*:', 'REMOVED ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_tts_speaking():
    with _tts_lock:
        return _tts_speaking

# register callback after TTS is loaded
if TTS_READY:
    set_playback_start_callback(_on_tts_started)
    set_playback_end_callback(_on_tts_ended)

# ── STT ───────────────────────────────────────────────────────────────────────
try:
    from stt import listen as stt_listen
    STT_READY = True
    print("[JARVIS] STT loaded OK")
except Exception as e:
    STT_READY = False
    def stt_listen(): return ""
    print(f"[JARVIS] STT unavailable: {e}")

# ── Voice ID ──────────────────────────────────────────────────────────────────
try:
    from voice_id import identify_from_mic, enroll_from_mic, get_profiles, delete_profile
    VOICE_ID_READY = True
    print("[JARVIS] Voice ID loaded OK")
except Exception as e:
    VOICE_ID_READY = False
    def identify_from_mic(**kw): return ("Guest", 0.0)
    def enroll_from_mic(name, **kw): return False
    def get_profiles(): return []
    def delete_profile(name): return False
    print(f"[JARVIS] Voice ID unavailable: {e}")

# ── Wake Word ─────────────────────────────────────────────────────────────────
try:
    from wake_word_detector import EfficientWakeWordSystem
    WAKE_READY = True
except Exception as e:
    WAKE_READY = False
    print(f"[JARVIS] Wake word unavailable: {e}")

# ── System Access ─────────────────────────────────────────────────────────────
try:
    from system_access import get_system_info, get_battery, get_wifi_info, get_cpu_usage, get_ram_usage
    SYSTEM_READY = True
    print("[JARVIS] System access loaded OK")
except Exception as e:
    SYSTEM_READY = False
    def get_system_info(): return "System info unavailable."
    def get_battery(): return "Battery info unavailable."
    def get_wifi_info(): return "WiFi info unavailable."
    def get_cpu_usage(): return "CPU info unavailable."
    def get_ram_usage(): return "RAM info unavailable."

# ── Wake word state ───────────────────────────────────────────────────────────
_wake_system = None
_wake_active = False
_wake_lock   = threading.Lock()

# ── Passive listening state (after JARVIS speaks) ─────────────────────────────
_passive_listen_active = False  # True during passive listening window
_passive_listen_timer = None    # Timer to end passive listening after 5 seconds
_passive_listen_lock = threading.Lock()
PASSIVE_LISTEN_TIMEOUT = 5.0   # Wait 5 seconds after response for user to speak

# SSE clients for push events (wake word, voice ID)
_sse_clients: list = []
_sse_lock = threading.Lock()

def _init_wake_listener():
    """Start wake word listener on server startup."""
    global _wake_system, _wake_active
    if not WAKE_READY:
        print("[Wake] Wake word detector not available")
        return
    try:
        with _wake_lock:
            _wake_system = EfficientWakeWordSystem(wake_phrase="aria")
            _wake_system.start(wake_callback=_on_wake_word)
            _wake_active = True
        print("[Wake] Auto-started on server startup")
    except Exception as e:
        print(f"[Wake] Failed to auto-start: {e}")

def _push_event(event: str, data: dict):
    """Push a server-sent event to all connected clients."""
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for client in _sse_clients[:]:  # ← Snapshot list to prevent iteration issues
            try:
                client.wfile.write(msg.encode())
                client.wfile.flush()
            except Exception:
                dead.append(client)
        for c in dead:
            if c in _sse_clients:  # ← Guard removal against race condition
                _sse_clients.remove(c)

def _on_wake_word():
    """Called when wake word detected — pause wake listener, listen for command, resume."""
    global _wake_active
    print("[JARVIS] Wake word detected!")
    _push_event("wake", {"state": "listening"})

    # Pause wake listener so mic is free for STT
    with _wake_lock:
        if _wake_system:
            _wake_system.stop()

    time.sleep(0.3)  # let mic release
    threading.Thread(target=_auto_listen_respond, daemon=True).start()


def _auto_listen_respond():
    """Listen for command → AI → TTS → push reply → restart wake listener."""
    global _wake_system, _wake_active
    try:
        if not STT_READY:
            print("[STT] STT not ready")
            return
        print("[STT] Listening for command...")
        transcript = stt_listen()
        print(f"[STT] Transcript: {transcript}")
        if not transcript:
            _push_event("stt", {"text": "", "error": "No speech detected"})
            print("[STT] No speech detected")
            return
        _push_event("stt", {"text": transcript})
        
        print(f"[AI] Processing: {transcript}")
        reply = _clean_ai_text(ai_ask(transcript))
        print(f"[JARVIS] {reply}")
        _push_event("reply", {"text": reply})
        
        if TTS_READY and reply:
            _speak_tracked(reply)
    except Exception as e:
        print(f"[ERROR] _auto_listen_respond failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always restart wake listener after responding
        with _wake_lock:
            if _wake_active and WAKE_READY:
                # CRITICAL: Stop old listener FIRST to prevent zombie threads
                if _wake_system:
                    try:
                        _wake_system.stop()
                    except Exception:
                        pass
                
                time.sleep(0.5)  # Ensure complete thread cleanup
                try:
                    _wake_system = EfficientWakeWordSystem(wake_phrase="aria")
                    _wake_system.start(wake_callback=_on_wake_word)
                except Exception as e:
                    print(f"[Wake] Failed to restart: {e}")
                    _wake_system = None
                    _wake_active = False


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Handler
# ═══════════════════════════════════════════════════════════════════════════════

class JarvisHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def log_message(self, fmt, *args): pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Server-Sent Events stream for push notifications
        if self.path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._cors()
            self.end_headers()
            with _sse_lock:
                _sse_clients.append(self)
            # Keep connection alive
            try:
                while True:
                    time.sleep(15)
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except Exception:
                with _sse_lock:
                    if self in _sse_clients:
                        _sse_clients.remove(self)
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length)
        payload = json.loads(body or "{}")

        if path == "/api/chat":
            self._handle_chat(payload)

        elif path == "/api/listen":
            self._handle_listen(payload)

        elif path == "/api/voice_id":
            self._handle_voice_id(payload)

        elif path == "/api/enroll":
            self._handle_enroll(payload)

        elif path == "/api/status":
            self._handle_status()

        elif path == "/api/clear":
            clear_memory()
            self._json({"ok": True})

        elif path == "/api/system":
            self._handle_system(payload)

        elif path == "/api/wake":
            self._handle_wake(payload)

        elif path == "/api/tts_stop":
            stop_speaking()
            self._json({"ok": True})

        elif path == "/api/tts_status":
            self._json({"speaking": is_tts_speaking()})

        elif path == "/api/calendar":
            self._handle_calendar(payload)

        elif path == "/api/maps":
            self._handle_maps(payload)

        elif path == "/api/smarthome":
            self._handle_smarthome(payload)

        elif path == "/api/desktop":
            self._handle_desktop(payload)

        elif path == "/api/vision":
            self._handle_vision(payload)

        elif path == "/api/callsms":
            self._handle_callsms(payload)

        elif path == "/api/web":
            self._handle_web(payload)

        elif path == "/api/memory":
            self._handle_memory(payload)

        elif path == "/api/stt_lang":
            lang = (payload.get("lang") or "en").lower()
            if lang in ("en", "ta"):
                os.environ["JARVIS_STT_LANG"] = lang
            self._json({"lang": os.getenv("JARVIS_STT_LANG", "en")})

        elif path == "/api/game":
            self._handle_game(payload)

        elif path == "/api/booking":
            self._handle_booking(payload)

        elif path == "/api/music":
            self._handle_music(payload)

        else:
            self._json({"error": "not found"}, 404)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _handle_chat(self, payload):
        message = (payload.get("message") or "").strip()
        if not message:
            self._json({"error": "empty message"}, 400)
            return
        # Log raw input (task example shows leak here if ai_ask returns raw JSON)
        print(f"[USER ] {message}")

        # Intercept wake word commands — LLM just says it's done, doesn't act
        _m = message.lower()
        if any(kw in _m for kw in ("wake word", "wakeword", "wake board", "wakeboard", "hey jarvis", "aria", "start listening", "stop listening")):
            if any(w in _m for w in ("turn off", "disable", "deactivate", "stop")):
                reply = self._toggle_wake("stop")
            else:
                reply = self._toggle_wake("start")
            print(f"[JARVIS] {reply}")
            if TTS_READY:
                threading.Thread(target=_speak_tracked, args=(reply,), daemon=True).start()
            self._json({"reply": reply, "wake_active": _wake_active})
            return

        reply = _clean_ai_text(ai_ask(message))
        # Safe log - _clean_ai_text strips tool JSON/tags
        print(f"[JARVIS] {reply}")
        if TTS_READY and reply:
            _speak_tracked(reply)   # non-blocking — queued to TTS worker thread
        self._json({"reply": reply})

    def _toggle_wake(self, action: str) -> str:
        global _wake_system, _wake_active
        if action == "stop":
            with _wake_lock:
                if _wake_system:
                    _wake_system.stop()
                    _wake_system = None
                _wake_active = False
            _push_event("wake_state", {"active": False})
            return "Wake word disabled."
        if not WAKE_READY:
            return "Wake word detection unavailable — check that SpeechRecognition is installed."
        try:
            with _wake_lock:
                if not _wake_active:
                    _wake_system = EfficientWakeWordSystem(wake_phrase="aria")
                    _wake_system.start(wake_callback=_on_wake_word)
                    _wake_active = True
            _push_event("wake_state", {"active": True})
            return "Wake listener is now active. Say 'Hey Jarvis' or 'Aria' to trigger me."
        except Exception as e:
            with _wake_lock:
                if _wake_system:
                    try:
                        _wake_system.stop()
                    except Exception:
                        pass
                _wake_system = None
                _wake_active = False
            _push_event("wake_state", {"active": False, "error": str(e)})
            return f"Wake listener failed to start: {e}"

    def _handle_listen(self, payload):
        """Record mic → STT → AI → TTS → return all."""
        if not STT_READY:
            self._json({"error": "STT not available"}, 503)
            return
        transcript = stt_listen()
        if not transcript:
            self._json({"transcript": "", "reply": "", "error": "No speech detected"})
            return
        # Log raw input (task example shows leak here if ai_ask returns raw JSON)
        print(f"[STT  ] {transcript}")

        # Intercept wake word commands same as chat
        _m = transcript.lower()
        if any(kw in _m for kw in ("wake word", "wakeword", "wake board", "wakeboard", "hey jarvis", "aria", "start listening", "stop listening")):
            if any(w in _m for w in ("turn off", "disable", "deactivate", "stop")):
                reply = self._toggle_wake("stop")
            else:
                reply = self._toggle_wake("start")
        else:
            reply = _clean_ai_text(ai_ask(transcript))
        # Safe log - _clean_ai_text strips tool JSON/tags
        print(f"[JARVIS] {reply}")
        if TTS_READY:
            threading.Thread(target=_speak_tracked, args=(reply,), daemon=True).start()
        self._json({"transcript": transcript, "reply": reply, "wake_active": _wake_active})

    def _handle_voice_id(self, payload):
        """Identify speaker from mic."""
        if not VOICE_ID_READY:
            self._json({"name": "Guest", "confidence": 0, "error": "Voice ID not available"})
            return
        duration = float(payload.get("duration", 3.0))
        name, confidence = identify_from_mic(duration=duration)
        self._json({"name": name, "confidence": round(confidence, 2)})

    def _handle_enroll(self, payload):
        """Enroll a new voice profile."""
        if not VOICE_ID_READY:
            self._json({"ok": False, "error": "Voice ID not available"})
            return
        name = (payload.get("name") or "").strip()
        if not name:
            self._json({"ok": False, "error": "Name required"}, 400)
            return
        duration = float(payload.get("duration", 4.0))
        ok = enroll_from_mic(name, duration=duration)
        profiles = get_profiles()
        self._json({"ok": ok, "profiles": profiles})

    def _handle_status(self):
        status = {
            "ai_ready":      AI_READY,
            "tts_ready":     TTS_READY,
            "stt_ready":     STT_READY,
            "voice_id_ready": VOICE_ID_READY,
            "system_ready":  SYSTEM_READY,
            "speaking":      is_tts_speaking(),
            "wake_active":   _wake_active,
            "voice_profiles": get_profiles() if VOICE_ID_READY else [],
        }
        if AI_READY:
            status.update(ai_status())
        self._json(status)

    def _handle_smarthome(self, payload):
        try:
            from smart_home import control, set_scene, list_devices, get_status, add_device, remove_device
            action = (payload.get("action") or "control").lower()
            if action == "scene":
                result = set_scene(payload.get("scene", ""))
            elif action == "list":
                result = list_devices()
            elif action == "status":
                self._json(get_status()); return
            elif action == "add_device":
                result = add_device(
                    payload.get("name", ""),
                    payload.get("ip", ""),
                    payload.get("device_type", "tasmota"),
                    payload.get("tuya_id", ""),
                    payload.get("tuya_key", ""),
                )
                # also store hass_entity if provided
                if payload.get("hass_entity"):
                    from smart_home import _load_devices, _save_devices
                    devs = _load_devices()
                    key = payload["name"].lower()
                    if key in devs:
                        devs[key]["hass_entity"] = payload["hass_entity"]
                        _save_devices(devs)
            elif action == "remove_device":
                result = remove_device(payload.get("name", ""))
            else:
                result = control(payload.get("command", ""))
            if TTS_READY and result:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            self._json({"result": result})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_desktop(self, payload):
        try:
            from desktop_control import handle, list_windows, find_recent_files
            action = (payload.get("action") or "command").lower()
            if action == "windows":   result = list_windows()
            elif action == "recent":  result = find_recent_files(payload.get("ext",""))
            else:                     result = handle(payload.get("command",""))
            self._json({"result": result})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_vision(self, payload):
        try:
            from vision_module import (
                handle, capture_and_describe, read_screen_and_describe,
                scan_qr_from_screen, scan_qr_from_camera,
                analyze_image_bytes, _scan_qr_bytes, read_image_text,
            )
            action     = (payload.get("action") or "command").lower()
            image_b64  = payload.get("image_b64") or payload.get("imageData") or ""
            prompt     = payload.get("prompt", "")
            use_cloud  = action == "analyze" or (payload.get("mode") or "").lower() == "cloud"

            if image_b64:
                if "," in image_b64:
                    image_b64 = image_b64.split(",", 1)[1]
                image_bytes = base64.b64decode(image_b64)

                if action == "qr" or "qr" in prompt.lower():
                    # Always local — never needs cloud
                    qr = _scan_qr_bytes(image_bytes)
                    result = f"QR code: {qr}" if qr else "No QR code found in image."
                elif use_cloud:
                    result = analyze_image_bytes(image_bytes,
                                                 prompt or "Describe this image clearly and briefly.",
                                                 use_cloud=True)
                else:
                    # Free: OCR only
                    result = analyze_image_bytes(image_bytes, use_cloud=False)
            elif action == "camera":
                result = capture_and_describe(use_cloud=use_cloud)
            elif action == "screen":
                result = read_screen_and_describe(use_cloud=use_cloud)
            elif action == "qr":
                result = scan_qr_from_screen()
            else:
                result = handle(payload.get("command", "what do you see"))

            if TTS_READY and result:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            self._json({"result": result})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_callsms(self, payload):
        try:
            from call_sms import handle, announce_call
            from web_automation import get_pending, clear_pending
            action = (payload.get("action") or "command").lower()
            if action == "confirm":
                pending = get_pending()
                if pending:
                    result = pending.confirm()
                    clear_pending()
                else:
                    result = "Nothing pending confirmation."
            elif action == "cancel":
                clear_pending()
                result = "Cancelled."
            elif action == "announce":
                result = announce_call(payload.get("caller","Unknown"))
            else:
                result = handle(payload.get("command",""))
            if TTS_READY and result:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            pending = get_pending()
            self._json({"result": result,
                        "needs_confirm": pending is not None,
                        "confirm_prompt": pending.prompt if pending else ""})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_web(self, payload):
        try:
            from web_automation import handle, get_pending, resolve
            action = (payload.get("action") or "command").lower()
            if action == "confirm":
                pending = get_pending()
                if pending:
                    result = pending.confirm()
                    from web_automation import clear_pending
                    clear_pending()
                else:
                    result = "Nothing pending confirmation."
            elif action == "cancel":
                from web_automation import clear_pending
                clear_pending()
                result = "Cancelled."
            else:
                result = handle(payload.get("command",""))
            if TTS_READY and result:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            pending = get_pending()
            self._json({"result": result, "needs_confirm": pending is not None,
                        "confirm_prompt": pending.prompt if pending else ""})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_calendar(self, payload):
        try:
            from calendar_integration import (get_events_today, get_events_week,
                                               get_next_event, add_event,
                                               find_free_slots, is_connected)
            action = (payload.get("action") or "today").lower()
            if action == "today":    result = get_events_today()
            elif action == "week":   result = get_events_week()
            elif action == "next":   result = get_next_event()
            elif action == "free":   result = find_free_slots(int(payload.get("duration", 60)))
            elif action == "add":
                result = add_event(payload.get("summary","Meeting"),
                                   payload.get("when","tomorrow 10am"),
                                   int(payload.get("duration", 60)))
            else: result = get_events_today()
            if TTS_READY and payload.get("speak"):
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            self._json({"result": result, "connected": is_connected()})
        except Exception as e:
            self._json({"result": f"Calendar error: {e}", "connected": False})

    def _handle_maps(self, payload):
        try:
            from maps_assistant import maps_assistant
            query = payload.get("query", "")
            if not query:
                self._json({"error": "No query"}); return
            result = maps_assistant.handle_location_query(query)
            if TTS_READY:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            self._json({"result": result})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_memory(self, payload):
        try:
            from user_memory import (get_profile, set_profile, set_preference,
                                      get_preference, save_place, get_all_places,
                                      remember_contact, get_contact, get_summary,
                                      get_active_alarms, _load)
            action = (payload.get("action") or "get").lower()
            if action == "get":
                self._json({
                    "profile":     get_profile(),
                    "preferences": _load().get("preferences", {}),
                    "places":      get_all_places(),
                    "alarms":      get_active_alarms(),
                    "summary":     get_summary(),
                })
            elif action == "set_profile":
                set_profile(payload.get("name",""), payload.get("city",""),
                            payload.get("language","en"))
                self._json({"ok": True})
            elif action == "save_place":
                save_place(payload.get("label",""), payload.get("name",""),
                           float(payload.get("lat",0)), float(payload.get("lon",0)))
                self._json({"ok": True})
            elif action == "set_pref":
                set_preference(payload.get("key",""), payload.get("value",""))
                self._json({"ok": True})
            else:
                self._json({"error": "Unknown action"})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_system(self, payload):
        """Return system stats."""
        query = (payload.get("query") or "all").lower()
        if query == "battery":
            self._json({"result": get_battery()})
        elif query == "wifi":
            self._json({"result": get_wifi_info()})
        elif query == "cpu":
            self._json({"result": get_cpu_usage()})
        elif query == "ram":
            self._json({"result": get_ram_usage()})
        else:
            self._json({"result": get_system_info()})

    def _handle_game(self, payload):
        try:
            from offline_entertainment import offline_entertainment as ent
            action = (payload.get("action") or "riddle").lower()
            if action == "riddle":      result = ent.get_random_riddle()
            elif action == "joke":      result = ent.get_random_joke()
            elif action == "quote":     result = ent.get_motivational_quote()
            elif action == "number":    result = ent.start_number_guessing_game()
            elif action == "math":      result = ent.start_math_quiz()
            elif action == "guess":
                guess = int(payload.get("guess", 0))
                result = ent.process_number_guess(guess)
            elif action == "answer":
                ans = payload.get("answer", "")
                result = ent.check_riddle_answer(ans)
            else:
                result = ent.get_random_riddle()
            if TTS_READY:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            self._json({"result": result})
        except Exception as e:
            self._json({"result": f"Game error: {e}"})

    def _handle_booking(self, payload):
        try:
            from ticket_booking_hybrid import booking_adapter
            action = (payload.get("action") or "list").lower()
            city   = payload.get("city", "Chennai")

            if action == "list":
                movies = booking_adapter.search_movies(payload.get("query", ""), city)
                source = booking_adapter.source()
                response = {"movies": movies, "source": source}
                if not movies:
                    response["error"] = (
                        "Live booking data is unavailable right now."
                        if source != "demo" else
                        "Demo booking is disabled."
                    )
                self._json(response)

            elif action == "theaters":
                theaters = booking_adapter.get_theaters(payload.get("movie_id", ""), city)
                source = booking_adapter.source()
                response = {"theaters": theaters, "source": source}
                if not theaters:
                    response["error"] = (
                        "Live theater data is unavailable right now."
                        if source != "demo" else
                        "Demo booking is disabled."
                    )
                self._json(response)

            elif action == "showtimes":
                shows = booking_adapter.get_showtimes(
                    payload.get("movie_id", ""),
                    payload.get("venue_id", ""), city)
                source = booking_adapter.source()
                response = {"showtimes": shows, "source": source}
                if not shows:
                    response["error"] = (
                        "Live showtime data is unavailable right now."
                        if source != "demo" else
                        "Demo booking is disabled."
                    )
                self._json(response)

            elif action == "confirm":
                # Voice summary + return needs_confirm so UI shows banner
                seats   = int(payload.get("seats", 1))
                summary = booking_adapter.confirm_summary(
                    payload.get("movie", ""), payload.get("theater", ""),
                    payload.get("showtime", ""), seats)
                if TTS_READY:
                    threading.Thread(target=_speak_tracked, args=(summary,), daemon=True).start()
                self._json({"summary": summary, "needs_confirm": True,
                            "confirm_prompt": summary, "source": booking_adapter.source()})

            elif action == "checkout":
                url = booking_adapter.checkout_url(
                    payload.get("movie_id", ""), payload.get("venue_id", ""),
                    payload.get("show_id", ""), int(payload.get("seats", 1)))
                source = booking_adapter.source()
                if not url:
                    self._json({
                        "error": "Live checkout is unavailable right now.",
                        "source": source,
                    })
                    return
                # Return URL to UI — browser open happens client-side so it
                # works on both desktop and mobile (window.open respects mobile browser)
                seats = int(payload.get("seats", 1))
                movie = payload.get("movie", "")
                showtime = payload.get("showtime", "")
                theater  = payload.get("theater", "")
                msg = (f"Opening BookMyShow for {movie} — {showtime} at {theater}. "
                       f"{seats} seat{'s' if seats > 1 else ''}. Complete payment on the site.")
                if TTS_READY:
                    threading.Thread(target=_speak_tracked, args=(msg,), daemon=True).start()
                self._json({"url": url, "result": msg, "open_url": True, "source": source})

        except Exception as e:
            self._json({"error": str(e)})

    def _handle_music(self, payload):
        try:
            import webbrowser
            query = (payload.get("query") or "").strip()
            if not query:
                self._json({"error": "No query provided"})
                return
            url = f"https://music.youtube.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            result = f"Opening YouTube Music for '{query}'."
            if TTS_READY:
                threading.Thread(target=_speak_tracked, args=(result,), daemon=True).start()
            self._json({"result": result, "url": url})
        except Exception as e:
            self._json({"error": str(e)})

    def _handle_wake(self, payload):
        """Start or stop wake word listener."""
        global _wake_system, _wake_active
        action = (payload.get("action") or "start").lower()

        if action == "stop":
            with _wake_lock:
                if _wake_system:
                    _wake_system.stop()
                    _wake_system = None
                _wake_active = False
            self._json({"ok": True, "wake_active": False})
            return

        if not WAKE_READY:
            self._json({"ok": False, "wake_active": False, "error": "Wake word not available"})
            return

        try:
            with _wake_lock:
                if not _wake_active:
                    _wake_system = EfficientWakeWordSystem(wake_phrase="aria")
                    _wake_system.start(wake_callback=_on_wake_word)
                    _wake_active = True

            self._json({"ok": True, "wake_active": True, "message": "Wake listener is now active."})
        except Exception as e:
            with _wake_lock:
                if _wake_system:
                    try:
                        _wake_system.stop()
                    except Exception:
                        pass
                _wake_system = None
                _wake_active = False
            self._json({"ok": False, "wake_active": False, "error": str(e)})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data: dict, code: int = 200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), JarvisHandler)
    print(f"[JARVIS] Neural Grid running → http://{HOST}:{PORT}")
    print(f"  AI:{' OK' if AI_READY else ' --'}  TTS:{' OK' if TTS_READY else ' --'}  STT:{' OK' if STT_READY else ' --'}  VoiceID:{' OK' if VOICE_ID_READY else ' --'}  System:{' OK' if SYSTEM_READY else ' --'}  Wake:{' OK' if WAKE_READY else ' --'}")
    
    # Auto-start wake word listener
    _init_wake_listener()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[JARVIS] Shutting down.")
