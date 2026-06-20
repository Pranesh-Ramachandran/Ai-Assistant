import os
import pytest


@pytest.fixture(autouse=True)
def mock_voice_and_stt(monkeypatch):
    """Autouse fixture that replaces heavy audio/network voice components with
    lightweight mocks so tests run without real audio devices or online services.
    """
    # Mock TTS: record calls instead of playing audio
    try:
        from AI_Assistant import fast_tts

        if not hasattr(fast_tts, "_mock_calls"):
            fast_tts._mock_calls = []

        def _mock_speak(text, lang="en", interrupt=False):
            fast_tts._mock_calls.append((text, lang, bool(interrupt)))
            return None

        monkeypatch.setattr(fast_tts, "speak", _mock_speak)
        monkeypatch.setattr(fast_tts, "speak_fast", _mock_speak)
        monkeypatch.setattr(fast_tts, "stop_speaking", lambda: None)
    except Exception:
        # best-effort: if module missing, ignore
        pass

    # Mock STT: return deterministic text from env var TEST_STT_TEXT (or empty)
    try:
        from AI_Assistant import stt

        def _mock_listen(timeout: float = 8.0, phrase_limit: float = 7.0):
            return os.getenv("TEST_STT_TEXT", "")

        monkeypatch.setattr(stt, "listen", _mock_listen)
    except Exception:
        pass

    yield


def pytest_collection_modifyitems(config, items):
    """Deselect known heavy/integration tests that require external services
    or corrupted binaries so the local unit-test run stays fast and stable.
    """
    skip_filenames = {
        "AI_Assistant/test_e2e.py",
        "AI_Assistant/test_tier3_comprehensive.py",
        "AI_Assistant/test_tier3_integration.py",
        "AI_Assistant/test_regex_cleanup.py",
    }

    deselected = []
    kept = []
    for item in items:
        # item.nodeid looks like 'AI_Assistant/test_intent.py::test_...'
        node = item.nodeid.split("::")[0]
        # Normalize path separators
        node = node.replace("\\", "/")
        if any(node.endswith(name) for name in skip_filenames):
            deselected.append(item)
        else:
            kept.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept


def pytest_ignore_collect(path, config):
    """Ignore heavy integration tests early during collection to avoid
    import-time side effects (like trying to contact local servers).
    """
    skip_basenames = {
        "test_comprehensive_jarvis.py",
        "AI_Assistant/test_comprehensive_jarvis.py",
        "test_tier3_comprehensive.py",
        "test_tier3_integration.py",
        "test_e2e.py",
    }
    try:
        name = path.basename
    except Exception:
        name = str(path)
    if name in skip_basenames or any(str(path).replace('\\', '/').endswith(n) for n in skip_basenames):
        return True
    return False
