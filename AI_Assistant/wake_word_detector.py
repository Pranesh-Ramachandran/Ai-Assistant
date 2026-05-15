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
        self._stop_fn     = None          # returned by listen_in_background
        self._cooldown    = 0.0           # prevent double-firing
        self._recognizer  = sr.Recognizer()
        # Configure for wake word detection — LOWERED threshold for better sensitivity
        self._recognizer.energy_threshold        = 1500  # Lower = more sensitive (300 was too high, required shouting)
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold          = 0.3  # Reduced from 0.5 for faster detection

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, wake_callback: Callable = None):
        if self.is_listening:
            return
        self.wake_callback = wake_callback
        self.is_listening  = True

        mic = sr.Microphone()
        # Faster calibration (0.2s instead of 0.5s) for quicker startup
        with mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.2)

        # listen_in_background keeps mic open continuously — no gaps
        # Reduced phrase_time_limit from 3 to 1.5 seconds for faster detection
        self._stop_fn = self._recognizer.listen_in_background(
            mic, self._audio_callback, phrase_time_limit=1.5
        )
        print(f"[Wake] Listening for '{self.wake_phrase}'...")

    def stop(self):
        self.is_listening = False
        if self._stop_fn:
            try:
                self._stop_fn(wait_for_stop=True)  # ← Wait for thread to fully finish
            except Exception as e:
                print(f"[Wake] Stop error: {e}")
            self._stop_fn = None
            time.sleep(0.2)  # ← Additional buffer to ensure mic fully released
        print("[Wake] Stopped.")

    def is_active(self) -> bool:
        return self.is_listening

    # ── Internal ──────────────────────────────────────────────────────────────

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData):
        """Called by listen_in_background on every phrase captured."""
        if not self.is_listening:
            return
        if time.time() - self._cooldown < 3.0:
            return
        try:
            # Try US English first, fallback to Indian English
            text = None
            try:
                text = recognizer.recognize_google(audio, language="en-US").lower()
                print(f"[Wake] Heard (en-US): {text}")
            except sr.UnknownValueError:
                try:
                    text = recognizer.recognize_google(audio, language="en-IN").lower()
                    print(f"[Wake] Heard (en-IN): {text}")
                except sr.UnknownValueError:
                    print(f"[Wake] Could not understand audio")
                    return
            except sr.RequestError as e:
                print(f"[Wake] Google API error: {e}")
                return
            
            if not text:
                return
            
            # Direct word match or fuzzy match for "hey jarvis" or "aria"
            words = text.split()
            triggered = False
            
            # Check for "hey jarvis" (requires both words)
            if any(w in ("hey", "hi") for w in words) and any(w in ("jarvis", "jar", "jarvish") for w in words):
                triggered = True
            # Check for "aria" (exact or fuzzy)
            elif "aria" in words:
                triggered = True
            else:
                # Fuzzy matching for variations - strip punctuation for better matching
                for word in words:
                    word_clean = word.strip(".,!?;:-")  # Remove trailing punctuation
                    if word_clean.startswith("jar"):  # jarvis, jarvish, etc.
                        triggered = True
                        break
                    if word_clean.startswith("ar"):  # aria, arya, etc.
                        triggered = True
                        break
                    # Also check for exact match after cleaning
                    if word_clean == "aria":
                        triggered = True
                        break
            
            if triggered:
                self._cooldown = time.time()
                print(f"[Wake] ✓ TRIGGERED on '{text}'!")
                if self.wake_callback:
                    threading.Thread(target=self.wake_callback, daemon=True).start()
            else:
                print(f"[Wake] Not a wake word: {text}")
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"[Wake] STT req error: {e}")
        except Exception as e:
            print(f"[Wake] Unexpected error: {e}")
