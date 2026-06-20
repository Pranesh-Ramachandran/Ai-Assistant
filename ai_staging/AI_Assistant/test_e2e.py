"""End-to-end smoke coverage for the AI_Assistant package."""

from AI_Assistant.time_aware_execution import extract_scheduled_action
from AI_Assistant.tts import AdvancedTTS


def test_time_aware_execution_parses_relative_time():
    result = extract_scheduled_action("Remind me in 5 minutes")

    assert result["is_timed"] is True
    assert result["action"]
    assert result["target_time"] is not None


def test_tts_wrapper_exposes_legacy_api():
    tts = AdvancedTTS()

    assert tts.speak("Hello from the smoke test") is True
    info = tts.get_voice_info()
    history = tts.get_history()

    assert isinstance(info, dict)
    assert isinstance(history, list)
    assert history[-1]["text"] == "Hello from the smoke test"
