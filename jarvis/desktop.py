"""
JARVIS Desktop App — pywebview native window + neural grid UI.

The brain runs in a background thread. State changes are pushed
into the HTML canvas via window.evaluate_js() calls:
  setState('idle' | 'listening' | 'thinking' | 'speaking' | 'error')
  addMsg('user' | 'jarvis', 'text')
"""

import logging
import os
import threading
from pathlib import Path

import webview

logger = logging.getLogger(__name__)

_HTML = str(Path(__file__).resolve().parent / "ui" / "static" / "index.html")


class JarvisAPI:
    """
    Exposed to JS via window.pywebview.api.*
    JS calls these; Python calls window.evaluate_js() to push state back.
    """

    def __init__(self):
        self._window = None
        self._brain = None
        self._tts = None
        self._stt_thread = None
        self._running = False
        self._lock = threading.Lock()

    def _set_window(self, window):
        self._window = window

    def _js(self, code: str):
        """Thread-safe JS evaluation."""
        if self._window:
            try:
                self._window.evaluate_js(code)
            except Exception as e:
                logger.warning("evaluate_js failed: %s", e)

    def _set_state(self, state: str):
        self._js(f"setState('{state}')")

    def _add_msg(self, role: str, text: str):
        safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        self._js(f"addMsg('{role}', '{safe}')")

    # ── Called by JS ──────────────────────────────────────────────────────────

    def send_message(self, text: str) -> dict:
        """JS calls this when user types and hits send."""
        if not text or not text.strip():
            return {"ok": False}
        threading.Thread(target=self._process, args=(text.strip(),), daemon=True).start()
        return {"ok": True}

    def get_status(self) -> dict:
        try:
            from jarvis.core.ai_brain import get_status
            return get_status()
        except Exception:
            return {"ai_mode": "offline", "groq_available": False, "gemini_available": False}

    def start_voice(self):
        """JS calls this when mic button pressed."""
        if self._stt_thread and self._stt_thread.is_alive():
            return
        self._stt_thread = threading.Thread(target=self._voice_loop_once, daemon=True)
        self._stt_thread.start()

    # ── Internal processing ───────────────────────────────────────────────────

    def _process(self, text: str):
        self._set_state("thinking")
        try:
            with self._lock:
                intent = self._brain.analyze_intent(text)
                response = self._brain.generate_response(intent, text)
        except Exception:
            logger.exception("Brain error")
            response = "Something went wrong."
            self._set_state("error")
            self._add_msg("jarvis", response)
            threading.Timer(2.0, lambda: (self._set_state("idle"), self._js("onBrainDone()"))).start()
            return

        self._set_state("speaking")
        self._add_msg("jarvis", response)

        try:
            self._tts.speak(response)
        except Exception as e:
            logger.warning("TTS error: %s", e)

        self._set_state("idle")
        self._js("onBrainDone()")

    def _voice_loop_once(self):
        """Capture one voice command, process it."""
        try:
            from jarvis.services.stt import listen_with_identity
            from jarvis.services.voice_id import list_profiles

            self._set_state("listening")
            profiles = list_profiles()

            if profiles:
                text, speaker, confidence = listen_with_identity(duration=4.0)
                if text and speaker == "unknown":
                    self._set_state("error")
                    self._add_msg("jarvis", "Voice not recognized. Access denied.")
                    threading.Timer(2.0, lambda: self._set_state("idle")).start()
                    return
            else:
                from jarvis.services.stt import listen
                text = listen()

            if not text:
                self._set_state("idle")
                return

            self._add_msg("user", text)
            self._js("onVoiceDone()")
            self._process(text)

        except Exception as e:
            logger.exception("Voice loop error")
            self._set_state("error")
            threading.Timer(2.0, lambda: self._set_state("idle")).start()


def run():
    import atexit
    from jarvis.core.brain import JarvisBrain
    from jarvis.services.tts import EnhancedTTS

    api = JarvisAPI()
    api._brain = JarvisBrain()
    api._tts = EnhancedTTS()

    atexit.register(api._brain.stop_alarm_thread)  # Fix #16: clean shutdown

    window = webview.create_window(
        title="JARVIS",
        url=f"file:///{_HTML}",
        js_api=api,
        width=560,
        height=780,
        resizable=True,
        frameless=False,
        min_size=(400, 600),
    )

    def on_loaded():
        api._set_window(window)
        status = api.get_status()
        ai_ok = status.get("groq_available") or status.get("gemini_available")
        mode = status.get("ai_mode", "offline")
        ai_sym = "OK" if ai_ok else "X"
        window.evaluate_js(
            f"document.getElementById('ftxt').textContent = 'JARVIS v3 · AI:{ai_sym} · {mode}'"
        )

    window.events.loaded += on_loaded
    webview.start(debug=False)
