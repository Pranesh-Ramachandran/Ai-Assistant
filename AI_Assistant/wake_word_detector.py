"""
JARVIS Wake Word Detector — continuous background listening.
Uses sr.listen_in_background() so the mic is always open — no gaps.
Wake phrases: "hey jarvis" or "aria" (configurable)
"""

import threading
import time
import speech_recognition as sr
from typing import Callable, Optional


class EfficientWakeWordSystem:
    def __init__(self, wake_phrase: str = "hey jarvis"):
        self.wake_phrase  = wake_phrase.lower().strip()
        self.is_listening = False
        self.wake_callback: Optional[Callable] = None
        self._stop_fn     = None
        self._worker_thread = None
        self._listen_once = None
        self._backend = "pyaudio"
        self._cooldown    = 0.0
        self._recognizer  = sr.Recognizer()
        self._recognizer.energy_threshold        = 1200
        self._recognizer.dynamic_energy_threshold = False  # Don't auto-raise — causes deafness over time
        self._recognizer.pause_threshold          = 0.3
        self._recognizer.non_speaking_duration    = 0.2

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, wake_callback: Callable = None):
        if self.is_listening:
            return
        self.wake_callback = wake_callback
        self.is_listening  = True

        try:
            from stt import listen_candidates, sounddevice_enabled
            if sounddevice_enabled:
                self._listen_once = listen_candidates
                self._backend = "sounddevice"
                self._worker_thread = threading.Thread(
                    target=self._sounddevice_loop,
                    daemon=True,
                    name="jarvis-wake-sounddevice",
                )
                self._worker_thread.start()
                print(f"[Wake] Listening for '{self.wake_phrase}' via SoundDevice...")
                return
        except Exception as exc:
            print(f"[Wake] SoundDevice backend unavailable, using PyAudio: {exc}")

        mic = sr.Microphone()
        with mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.2)

        self._stop_fn = self._recognizer.listen_in_background(
            mic, self._audio_callback, phrase_time_limit=2.0
        )
        print(f"[Wake] Listening for '{self.wake_phrase}'...")

    def stop(self):
        self.is_listening = False
        if self._stop_fn:
            try:
                self._stop_fn(wait_for_stop=True)
            except Exception as e:
                print(f"[Wake] Stop error: {e}")
            self._stop_fn = None
            time.sleep(0.2)
        if self._worker_thread and self._worker_thread is not threading.current_thread():
            self._worker_thread.join(timeout=4)
        self._worker_thread = None
        print("[Wake] Stopped.")

    def is_active(self) -> bool:
        return self.is_listening

    # ── Internal ──────────────────────────────────────────────────────────────

    def _sounddevice_loop(self):
        """Continuously capture short phrases with the working STT backend."""
        while self.is_listening:
            try:
                candidates = self._listen_once(timeout=5, phrase_limit=3.0)
                if candidates and self.is_listening:
                    print(f"[Wake] Heard candidates: {candidates[:5]}")
                    for text in candidates:
                        if self._handle_text(text):
                            break
            except Exception as exc:
                if self.is_listening:
                    print(f"[Wake] SoundDevice capture error: {exc!r}")
                    time.sleep(0.3)

    def _handle_text(self, text: str) -> bool:
        if not self.is_listening or time.time() - self._cooldown < 3.0:
            return False
        words = text.lower().split()
        triggered = (
            any(w in ("hey", "hi") for w in words)
            and any(w in ("jarvis", "jar", "jarvish") for w in words)
        ) or "aria" in words
        normalized = " ".join(word.strip(".,!?;:-") for word in words)
        if normalized in {"how are you", "hey service", "hey travis", "hey jervis"}:
            triggered = True
        if not triggered:
            for word in words:
                cleaned = word.strip(".,!?;:-")
                if cleaned.startswith("jar") or cleaned in {"aria", "arya"}:
                    triggered = True
                    break
        if triggered:
            self._cooldown = time.time()
            print(f"[Wake] ✓ TRIGGERED on '{text}'!")
            if self.wake_callback:
                threading.Thread(target=self.wake_callback, daemon=True).start()
            return True
        else:
            print(f"[Wake] Not a wake word: {text}")
            return False

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData):
        """Called by listen_in_background on every phrase captured."""
        if not self.is_listening:
            return
        if time.time() - self._cooldown < 3.0:
            return
        try:
            text = None
            try:
                text = recognizer.recognize_google(audio, language="en-IN").lower()
                print(f"[Wake] Heard (en-IN): {text}")
            except sr.UnknownValueError:
                try:
                    text = recognizer.recognize_google(audio, language="en-US").lower()
                    print(f"[Wake] Heard (en-US): {text}")
                except sr.UnknownValueError:
                    print("[Wake] Could not understand audio")
                    return
            except sr.RequestError as e:
                print(f"[Wake] Google API error: {e}")
                return

            if not text:
                return

            self._handle_text(text)
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"[Wake] STT req error: {e}")
        except Exception as e:
            print(f"[Wake] Unexpected error: {e}")
