"""
JARVIS — single authoritative entry point.

Modes:
  python -m jarvis            → voice loop
  python -m jarvis --web      → Flask web UI
  python -m jarvis --text     → text input loop (no mic)
"""

import argparse
import logging
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _setup_logging(data_dir: str) -> logging.Logger:
    """Configure logging after data/ is guaranteed to exist."""
    log_file = os.path.join(data_dir, "jarvis.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return logging.getLogger("jarvis")


def _run_voice_loop(logger: logging.Logger) -> None:
    import atexit
    from jarvis.core.brain import JarvisBrain
    from jarvis.services.tts import speak
    from jarvis.services.stt import listen, listen_with_identity
    from jarvis.services.voice_id import list_profiles

    # ── Wake-word detector (optional) ────────────────────────────────────────
    _wake_word_active = False
    try:
        from jarvis.AI_Assistant.wake_word_detector import WakeWordDetector
        _wwd = WakeWordDetector()
        _wake_word_active = True
        logger.info("Wake-word detection enabled")
    except Exception:
        _wwd = None
        logger.info("Wake-word detector not available — always listening")

    brain = JarvisBrain()
    atexit.register(brain.stop_alarm_thread)  # Fix #16: clean shutdown

    profiles = list_profiles()
    use_voice_id = bool(profiles)

    if use_voice_id:
        speak(f"Voice authentication active. Enrolled users: {', '.join(profiles)}.")
    else:
        speak("No voice profiles enrolled. Running in open mode. Say 'enroll voice' to register.")

    speak("JARVIS online. How can I help?")
    logger.info("Voice loop started (voice_id=%s, wake_word=%s)", use_voice_id, _wake_word_active)

    while True:
        try:
            # ── Wake-word gate ────────────────────────────────────────────────
            if _wake_word_active and _wwd:
                logger.debug("Waiting for wake word...")
                if not _wwd.wait_for_wake_word(timeout=30):
                    continue  # no wake word heard — saves battery

            if use_voice_id:
                command, speaker, confidence = listen_with_identity(duration=4.0)
                if command:
                    if speaker == "unknown":
                        speak("I don't recognize your voice. Access denied.")
                        logger.warning("Rejected unrecognized speaker (conf=%.2f)", confidence)
                        continue
                    logger.info("Speaker: %s (conf=%.2f) | Command: %s", speaker, confidence, command)
            else:
                command = listen()
                speaker = "user"

            if not command:
                continue

            # Allow enrollment via voice — Fix #15: validate name
            if "enroll voice" in command or "register voice" in command:
                from jarvis.services.voice_id import enroll
                speak("What name should I save your voice as?")
                name_audio = listen().strip()
                clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name_audio)[:32]
                if not clean_name:
                    speak("I could not catch a valid name. Please try again.")
                    continue
                speak(f"Starting enrollment for {clean_name}. Follow the prompts.")
                enroll(clean_name, samples=5)
                use_voice_id = True
                continue

            intent = brain.analyze_intent(command)
            response = brain.generate_response(intent, command)
            speak(response)
            if intent == "exit":
                break

        except KeyboardInterrupt:
            speak("Goodbye.")
            break
        except Exception:
            logger.exception("Voice loop error")

    brain.stop_alarm_thread()


def _run_text_loop() -> None:
    from jarvis.core.brain import JarvisBrain

    brain = JarvisBrain()
    print("JARVIS text mode. Type 'exit' to quit.\n")

    while True:
        try:
            command = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not command:
            continue
        intent = brain.analyze_intent(command)
        response = brain.generate_response(intent, command)
        print(f"JARVIS: {response}\n")
        if intent == "exit":
            break


def _run_web(logger: logging.Logger) -> None:
    import jarvis.services.tts as tts_mod
    tts_mod._SUPPRESS_PRINT = True
    from jarvis.ui.app import app
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting web UI on port %d", port)
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    ssl_cert = os.getenv("JARVIS_SSL_CERT", "")
    ssl_key  = os.getenv("JARVIS_SSL_KEY", "")
    ssl_ctx  = (ssl_cert, ssl_key) if (ssl_cert and ssl_key) else None
    if ssl_ctx:
        os.environ["JARVIS_HTTPS"] = "true"
    logger.info("Web UI binding to %s:%d (TLS=%s)", host, port, bool(ssl_ctx))
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_ctx)


def main() -> None:
    # Ensure data/ exists BEFORE setting up logging (FileHandler needs the dir)
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    logger = _setup_logging(data_dir)

    parser = argparse.ArgumentParser(description="JARVIS AI Assistant")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--web",     action="store_true", help="Start Flask web UI")
    group.add_argument("--text",    action="store_true", help="Text input mode (no mic)")
    group.add_argument("--desktop", action="store_true", help="Native desktop window (default)")
    args = parser.parse_args()

    if args.web:
        _run_web(logger)
    elif args.text:
        _run_text_loop()
    else:
        # Default: desktop window
        import jarvis.services.tts as tts_mod
        tts_mod._SUPPRESS_PRINT = True
        from jarvis.desktop import run as run_desktop
        run_desktop()


if __name__ == "__main__":
    main()
