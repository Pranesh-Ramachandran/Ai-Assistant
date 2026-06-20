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
    from jarvis.core.brain import JarvisBrain
    from jarvis.services.tts import speak
    from jarvis.services.stt import listen, listen_with_identity
    from jarvis.services.voice_id import list_profiles

    brain = JarvisBrain()
    profiles = list_profiles()
    use_voice_id = bool(profiles)

    if use_voice_id:
        speak(f"Voice authentication active. Enrolled users: {', '.join(profiles)}.")
    else:
        speak("No voice profiles enrolled. Running in open mode. Say 'enroll voice' to register.")

    speak("JARVIS online. How can I help?")
    logger.info("Voice loop started (voice_id=%s)", use_voice_id)

    while True:
        try:
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

            # Allow enrollment via voice
            if "enroll voice" in command or "register voice" in command:
                from jarvis.services.voice_id import enroll
                speak("What name should I save your voice as?")
                name_audio = listen()
                if name_audio:
                    speak(f"Starting enrollment for {name_audio}. Follow the prompts.")
                    enroll(name_audio, samples=5)
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
    app.run(host="0.0.0.0", port=port, debug=debug)


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
