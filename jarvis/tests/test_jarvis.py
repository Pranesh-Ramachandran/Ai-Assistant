"""
JARVIS consolidated test suite.
Run: python -m pytest jarvis/tests/ -v
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

# Suppress noisy warnings from optional missing dependencies during tests
logging.disable(logging.WARNING)


# ── Brain tests ───────────────────────────────────────────────────────────────

class TestJarvisBrain:
    @pytest.fixture
    def brain(self):
        from jarvis.core.brain import JarvisBrain
        b = JarvisBrain(tts_engine=MagicMock())
        b.stop_alarm_thread()
        return b

    def test_normalize_command(self, brain):
        assert brain._normalize_command("  Hello JARVIS!  ") == "hello jarvis"

    def test_analyze_intent_greeting(self, brain):
        assert brain.analyze_intent("hello jarvis") == "greeting"

    def test_analyze_intent_time(self, brain):
        assert brain.analyze_intent("what time is it") == "time_date"

    def test_analyze_intent_weather(self, brain):
        assert brain.analyze_intent("what is the weather in Chennai") == "weather"

    def test_analyze_intent_iot(self, brain):
        assert brain.analyze_intent("turn on the bulb") == "iot_control"

    def test_analyze_intent_alarm(self, brain):
        assert brain.analyze_intent("set alarm for 7:30") == "alarm_reminder"

    def test_analyze_intent_exit(self, brain):
        assert brain.analyze_intent("goodbye") == "exit"

    def test_generate_response_greeting(self, brain):
        resp = brain.generate_response("greeting", "hello")
        assert isinstance(resp, str) and len(resp) > 0

    def test_generate_response_time(self, brain):
        resp = brain.generate_response("time_date", "what time is it")
        assert "It is" in resp

    def test_duplicate_detection(self, brain):
        brain.generate_response("greeting", "hello")
        import time; time.sleep(0.01)
        resp = brain.generate_response("greeting", "hello")
        assert "heard that already" in resp

    def test_set_alarm_valid(self, brain):
        result = brain.set_alarm_reminder("07:30", "wake up")
        assert "07:30" in result or "7:30" in result

    def test_set_alarm_invalid(self, brain):
        result = brain.set_alarm_reminder("notaTime", "test")
        assert "could not" in result.lower()

    def test_get_time_date_format(self, brain):
        result = brain.get_current_time_date()
        assert "It is" in result and "on" in result

    def test_memory_persistence(self, brain, tmp_path):
        brain.MEMORY_FILE = str(tmp_path / "mem.json")
        brain.memory["test_key"] = "test_value"
        brain._memory_dirty = True
        brain._save_memory()
        brain.memory = {}
        brain.memory = brain._load_memory()
        assert brain.memory.get("test_key") == "test_value"

    def test_dirty_flag_prevents_unnecessary_write(self, brain, tmp_path):
        brain.MEMORY_FILE = str(tmp_path / "mem.json")
        brain._memory_dirty = False
        brain._save_memory()
        assert not (tmp_path / "mem.json").exists()


# ── NLP tests ─────────────────────────────────────────────────────────────────

class TestJarvisNLP:
    @pytest.fixture
    def nlp(self):
        from jarvis.core.nlp import JarvisNLP
        return JarvisNLP()

    def test_preprocess_strips_fillers(self, nlp):
        assert "turn on light" in nlp.preprocess("hey jarvis turn on light")

    def test_classify_greeting(self, nlp):
        intent, conf = nlp.classify_intent("hello there")
        assert intent == "greeting" and conf > 0

    def test_classify_weather(self, nlp):
        intent, _ = nlp.classify_intent("what is the weather today")
        assert intent == "weather_query"

    def test_classify_calculation(self, nlp):
        intent, conf = nlp.classify_intent("what is 12 + 5")
        assert intent == "calculation" and conf >= 0.8

    def test_extract_entities_time(self, nlp):
        entities = nlp.extract_entities("set alarm at 7:30 am")
        assert "time" in entities

    def test_extract_entities_location(self, nlp):
        entities = nlp.extract_entities("weather in Chennai")
        assert "location" in entities

    def test_process_returns_dict(self, nlp):
        result = nlp.process("hello jarvis")
        assert all(k in result for k in ("intent", "confidence", "entities", "response"))

    def test_process_empty(self, nlp):
        result = nlp.process("")
        assert result["intent"] == "unknown"


# ── Data collector tests ──────────────────────────────────────────────────────

class TestDataCollector:
    def test_extract_location(self):
        from jarvis.services.data_collector import _extract_location
        assert _extract_location("weather in Chennai") == "Chennai"

    def test_try_calculate_addition(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("12 + 5") == "17"

    def test_try_calculate_division(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("10 / 2") == "5"

    def test_try_calculate_invalid(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("hello world") is None

    def test_try_calculate_division_by_zero(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("5 / 0") is None

    def test_extract_search_term(self):
        from jarvis.services.data_collector import _extract_search_term
        assert _extract_search_term("what is Python") == "python"

    @patch("jarvis.services.data_collector.requests.get")
    def test_get_weather_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, text="Chennai: +30C")
        from jarvis.services.data_collector import get_weather
        result = get_weather("weather in Chennai")
        assert "Chennai" in result

    @patch("jarvis.services.data_collector.requests.get")
    def test_get_information_wikipedia(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"extract": "Python is a programming language."}
        )
        from jarvis.services.data_collector import get_information
        result = get_information("what is Python")
        assert "Python" in result


# ── IoT tests ─────────────────────────────────────────────────────────────────

class TestIoTAssistant:
    @pytest.fixture
    def iot(self, tmp_path, monkeypatch):
        import jarvis.services.iot as iot_mod
        monkeypatch.setattr(iot_mod, "_BULB_FILE", str(tmp_path / "bulbs.json"))
        monkeypatch.setattr(iot_mod, "_DEVICE_FILE", str(tmp_path / "devices.json"))
        monkeypatch.setattr(iot_mod, "_cache", {})
        from jarvis.services.iot import IoTAssistant
        return IoTAssistant()

    def test_unknown_bulb(self, iot):
        result = iot.handle_iot_command("turn on the bulb")
        assert "couldn't identify" in result

    def test_unknown_device(self, iot):
        result = iot.handle_iot_command("turn on the fan")
        assert "No matching device" in result or "couldn't identify" in result


# ── Web route tests ───────────────────────────────────────────────────────────

class TestWebRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key-32chars-padding!!")
        from jarvis.ui.app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_login_page(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_auth_missing_fields(self, client):
        resp = client.post(
            "/auth",
            json={"action": "login", "email": "", "password": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_send_message_unauthenticated(self, client):
        resp = client.post(
            "/send_message",
            json={"message": "hello"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_send_message_too_long(self, client):
        with client.session_transaction() as sess:
            sess["user"] = "test@test.com"
        resp = client.post(
            "/send_message",
            json={"message": "x" * 1001},
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── Cache tests ───────────────────────────────────────────────────────────────

class TestCache:
    @pytest.fixture(autouse=True)
    def patch_db(self, tmp_path, monkeypatch):
        import jarvis.core.cache as cache_mod
        monkeypatch.setattr(cache_mod, "_DB_PATH", str(tmp_path / "test_cache.db"))
        monkeypatch.setattr(cache_mod, "_local", cache_mod.__import__("threading").local())

    def test_put_and_get(self):
        from jarvis.core.cache import put, get
        put("hello world", "Hi there!")
        assert get("hello world") == "Hi there!"

    def test_get_missing(self):
        from jarvis.core.cache import get
        assert get("nonexistent query xyz") is None

    def test_fuzzy_match(self):
        from jarvis.core.cache import put, get
        put("what is python programming", "Python is a language.")
        result = get("what is python programming language")
        assert result == "Python is a language."

    def test_stats(self):
        from jarvis.core.cache import put, stats
        put("test query", "test response")
        s = stats()
        assert s["total_entries"] >= 1
