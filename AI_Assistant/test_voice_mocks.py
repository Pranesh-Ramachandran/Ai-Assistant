import os


def test_tts_mock():
    from AI_Assistant import fast_tts

    # clear any previous mock calls
    fast_tts._mock_calls = []
    fast_tts.speak("unittest-tts")
    assert len(fast_tts._mock_calls) >= 1
    assert fast_tts._mock_calls[-1][0] == "unittest-tts"


def test_stt_mock():
    # set environment override that the mock listens for
    os.environ["TEST_STT_TEXT"] = "simulated speech"
    from AI_Assistant import stt

    text = stt.listen()
    assert text == "simulated speech"
