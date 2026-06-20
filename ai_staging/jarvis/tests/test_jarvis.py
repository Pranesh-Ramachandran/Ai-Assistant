"""
JARVIS consolidated test suite.
Run: python -m pytest jarvis/tests/ -v
"""

import logging
import threading
import time
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

    def test_analyze_intent_alarm_relative(self, brain):
        assert brain.analyze_intent("remind me in 5 minutes") == "alarm_reminder"

    def test_analyze_intent_list_alarms(self, brain):
        assert brain.analyze_intent("list my alarms") == "list_alarms"

    def test_analyze_intent_cancel_alarm(self, brain):
        assert brain.analyze_intent("cancel all alarms") == "cancel_alarm"

    def test_analyze_intent_capabilities(self, brain):
        assert brain.analyze_intent("what can you do") == "capabilities"

    def test_analyze_intent_clear_memory(self, brain):
        assert brain.analyze_intent("clear memory") == "clear_memory"

    def test_analyze_intent_news(self, brain):
        assert brain.analyze_intent("what is the latest news") == "news"

    def test_generate_response_news(self, brain):
        resp = brain.generate_response("news", "latest headlines")
        assert "news" in resp.lower() or "headline" in resp.lower()

    def test_analyze_intent_exit(self, brain):
        assert brain.analyze_intent("goodbye") == "exit"

    def test_generate_response_greeting(self, brain):
        resp = brain.generate_response("greeting", "hello")
        assert isinstance(resp, str) and len(resp) > 0

    def test_generate_response_time(self, brain):
        resp = brain.generate_response("time_date", "what time is it")
        assert "It is" in resp

    def test_generate_response_capabilities(self, brain):
        resp = brain.generate_response("capabilities", "what can you do")
        assert "Time" in resp or "Weather" in resp

    def test_generate_response_list_alarms_empty(self, brain):
        brain.memory["alarms"] = []
        resp = brain.generate_response("list_alarms", "list my alarms")
        assert "no active" in resp.lower()

    def test_generate_response_cancel_alarm_none(self, brain):
        brain.memory["alarms"] = []
        resp = brain.generate_response("cancel_alarm", "cancel alarms")
        assert "No active" in resp

    def test_generate_response_clear_memory(self, brain):
        resp = brain.generate_response("clear_memory", "clear memory")
        assert "cleared" in resp.lower()

    def test_duplicate_detection(self, brain):
        brain.generate_response("greeting", "hello")
        time.sleep(0.01)
        resp = brain.generate_response("greeting", "hello")
        assert "heard that already" in resp

    def test_set_alarm_valid(self, brain):
        result = brain.set_alarm_reminder("07:30", "wake up")
        assert "07:30" in result or "7:30" in result

    def test_set_alarm_invalid(self, brain):
        result = brain.set_alarm_reminder("notaTime", "test")
        assert "could not" in result.lower()

    def test_set_alarm_relative_minutes(self, brain):
        result = brain.handle_alarm_reminder("remind me in 5 minutes")
        assert "Reminder" in result or "reminder" in result.lower()

    def test_set_alarm_relative_hours(self, brain):
        result = brain.handle_alarm_reminder("remind me in 2 hours")
        assert "Reminder" in result or "reminder" in result.lower()

    def test_list_alarms_with_items(self, brain, tmp_path):
        brain.MEMORY_FILE = str(tmp_path / "mem.json")
        from datetime import datetime, timedelta
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        brain.memory["alarms"] = [{"active": True, "datetime": future, "message": "Test alarm"}]
        resp = brain._list_alarms()
        assert "Test alarm" in resp

    def test_cancel_alarms(self, brain, tmp_path):
        brain.MEMORY_FILE = str(tmp_path / "mem.json")
        from datetime import datetime, timedelta
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        brain.memory["alarms"] = [{"active": True, "datetime": future, "message": "Test"}]
        resp = brain._cancel_alarms()
        assert "Cancelled 1" in resp

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

    def test_classify_calculation_pure_math(self, nlp):
        intent, conf = nlp.classify_intent("25 * 4")
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

    def test_try_calculate_multiplication(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("6 * 7") == "42"

    def test_try_calculate_invalid(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("hello world") is None

    def test_try_calculate_division_by_zero(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("5 / 0") is None

    def test_try_calculate_sqrt(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("sqrt(16)") == "4"
        assert _try_calculate("square root of 25") == "5"

    def test_try_calculate_percent(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("15 percent of 200") == "30"
        assert _try_calculate("20 % of 50") == "10"
        assert _try_calculate("10 percent") == "0.1"

    def test_try_calculate_modulo(self):
        from jarvis.services.data_collector import _try_calculate
        assert _try_calculate("17 mod 5") == "2"

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

    @patch("jarvis.services.data_collector.requests.get")
    def test_get_weather_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout()
        from jarvis.services.data_collector import get_weather
        result = get_weather("weather in London")
        assert isinstance(result, str) and len(result) > 0


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

    def test_send_message_authenticated(self, client):
        with client.session_transaction() as sess:
            sess["user"] = "test@test.com"
        resp = client.post(
            "/send_message",
            json={"message": "hello"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "response" in data

    def test_send_message_too_long(self, client):
        with client.session_transaction() as sess:
            sess["user"] = "test@test.com"
        resp = client.post(
            "/send_message",
            json={"message": "x" * 1001},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_send_message_empty(self, client):
        with client.session_transaction() as sess:
            sess["user"] = "test@test.com"
        resp = client.post(
            "/send_message",
            json={"message": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_register_and_login(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key-32chars-padding!!")
        import sys
        import jarvis.ui.app
        app_mod = sys.modules["jarvis.ui.app"]
        monkeypatch.setattr(app_mod, "_USERS_FILE", str(tmp_path / "users.json"))
        # Register
        resp = client.post("/auth", json={
            "action": "register", "name": "Test User",
            "email": "test@example.com", "password": "password123"
        }, content_type="application/json")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_status_endpoint(self, client):
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "version" in data

    def test_voice_profiles_empty(self, client):
        with patch("jarvis.services.voice_id.list_profiles", return_value=[]):
            resp = client.get("/voice_profiles")
            assert resp.status_code == 200
            assert resp.get_json()["profiles"] == []


# ── Cache tests ───────────────────────────────────────────────────────────────

class TestCache:
    @pytest.fixture(autouse=True)
    def patch_db(self, tmp_path, monkeypatch):
        import jarvis.core.cache as cache_mod
        monkeypatch.setattr(cache_mod, "_DB_PATH", str(tmp_path / "test_cache.db"))
        # Reset thread-local connection so tests get a fresh DB
        monkeypatch.setattr(cache_mod, "_local", threading.local())

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

    def test_cache_ttl_type_current(self):
        from jarvis.core.cache import put, get, _classify_ttl
        assert _classify_ttl("what is the weather today") == "current"

    def test_cache_ttl_type_factual(self):
        from jarvis.core.cache import _classify_ttl
        assert _classify_ttl("what is python") == "factual"

    def test_overwrite_existing(self):
        from jarvis.core.cache import put, get
        put("my query", "first response")
        put("my query", "updated response")
        assert get("my query") == "updated response"


# ── Rate guard tests ──────────────────────────────────────────────────────────

class TestRateGuard:
    @pytest.fixture(autouse=True)
    def patch_db(self, tmp_path, monkeypatch):
        import jarvis.core.rate_guard as rg_mod
        monkeypatch.setattr(rg_mod, "_DB_PATH", str(tmp_path / "test_usage.db"))
        monkeypatch.setattr(rg_mod, "_local", threading.local())

    def test_can_call_initially(self):
        from jarvis.core.rate_guard import can_call
        allowed, reason = can_call("groq")
        assert allowed is True
        assert reason == "ok"

    def test_record_call_increments(self):
        from jarvis.core.rate_guard import record_call, get_daily_calls
        record_call("groq")
        assert get_daily_calls("groq") == 1

    def test_get_mode_normal(self):
        from jarvis.core.rate_guard import get_mode
        assert get_mode("groq") == "normal"

    def test_status_report_keys(self):
        from jarvis.core.rate_guard import status_report
        report = status_report()
        assert "groq" in report and "gemini" in report
        assert "daily_calls" in report["groq"]
        assert "mode" in report["groq"]
