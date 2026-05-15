#!/usr/bin/env python3
"""
JARVIS AI Assistant — Comprehensive Test Suite
Tests: chat, weather, tools, memory, error handling, performance, UI, API endpoints
"""

import requests
import json
import time
import sys
import re
from datetime import datetime

BASE_URL = "http://localhost:7890"
PASS = 0
FAIL = 0
WARN = 0
RESULTS = []

def hdr(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")

def ok(name, msg=""):
    global PASS
    PASS += 1
    label = f"✅ PASS"
    suffix = f" — {msg}" if msg else ""
    print(f"  {label}  {name}{suffix}")
    RESULTS.append(("PASS", name, msg))

def fail(name, msg=""):
    global FAIL
    FAIL += 1
    label = f"❌ FAIL"
    suffix = f" — {msg}" if msg else ""
    print(f"  {label}  {name}{suffix}")
    RESULTS.append(("FAIL", name, msg))

def warn(name, msg=""):
    global WARN
    WARN += 1
    label = f"⚠️  WARN"
    suffix = f" — {msg}" if msg else ""
    print(f"  {label}  {name}{suffix}")
    RESULTS.append(("WARN", name, msg))

def chat(msg, timeout=20):
    r = requests.post(f"{BASE_URL}/api/chat",
                      json={"message": msg},
                      timeout=timeout)
    r.raise_for_status()
    return r.json().get("reply", "")

def has_json_leak(text):
    """Returns True if response has leaked raw tool call JSON."""
    if not text:
        return False
    patterns = [
        r'\{"name"\s*:',
        r'<function[^>]*>',
        r'get_weather\s*>\s*\{',
        r'"parameters"\s*:\s*\{',
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)

def has_mock_result(text):
    """Returns True if mock web search result was injected."""
    return "(Mock result)" in text or "example1.com" in text

# ─── 1. Server Health ──────────────────────────────────────────────────────────
hdr("1. SERVER HEALTH & STATUS")

try:
    r = requests.post(f"{BASE_URL}/api/status", json={}, timeout=5)
    data = r.json()
    if r.status_code == 200 and data.get("ai_ready"):
        ok("Server reachable", f"status={r.status_code}")
    else:
        fail("Server reachable", f"status={r.status_code}")
except Exception as e:
    fail("Server reachable", str(e))
    print("\n🚫 Cannot reach server. Start jarvis_grid_server.py first.\n")
    sys.exit(1)

# Check components
for key in ("ai_ready", "tts_ready", "stt_ready", "voice_id_ready", "system_ready"):
    val = data.get(key)
    if val:
        ok(f"Component: {key}")
    else:
        warn(f"Component: {key}", "not ready")

for api in ("groq", "gemini"):
    avail = data.get(f"{api}_available")
    if avail:
        ok(f"API: {api} available")
    else:
        warn(f"API: {api} available", "missing key or library")

# ─── 2. Basic Chat / Greetings ────────────────────────────────────────────────
hdr("2. BASIC CHAT & GREETINGS")

greetings = [
    ("hello",           ["hello", "hi", "help", "what"]),
    ("how are you",     ["doing", "great", "help", "ready"]),
    ("who are you",     ["jarvis", "assistant", "ai"]),
    ("goodbye",         ["goodbye", "bye", "here"]),
    ("thank you",       ["welcome", "anytime", "glad"]),
]

for q, expected_words in greetings:
    try:
        t0 = time.time()
        reply = chat(q)
        elapsed = time.time() - t0
        low = reply.lower()
        if not reply:
            fail(f"Greeting: '{q}'", "empty reply")
        elif has_json_leak(reply):
            fail(f"Greeting: '{q}'", f"JSON LEAK: {reply[:60]}")
        elif has_mock_result(reply):
            fail(f"Greeting: '{q}'", "mock web search injected")
        elif any(w in low for w in expected_words):
            ok(f"Greeting: '{q}'", f"{elapsed:.2f}s — {reply[:50]}")
        else:
            warn(f"Greeting: '{q}'", f"unexpected: {reply[:60]}")
    except Exception as e:
        fail(f"Greeting: '{q}'", str(e)[:60])

# ─── 3. Time & Date ───────────────────────────────────────────────────────────
hdr("3. TIME & DATE")

time_queries = [
    ("what time is it",  ["pm", "am", ":"]),
    ("what is today's date", ["2026", "may", "friday", "saturday"]),
    ("what day is it",   ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]),
]

for q, expected in time_queries:
    try:
        reply = chat(q)
        low = reply.lower()
        if not reply:
            fail(f"Time: '{q}'", "empty")
        elif any(w in low for w in expected):
            ok(f"Time: '{q}'", reply[:50])
        elif has_json_leak(reply):
            fail(f"Time: '{q}'", f"JSON LEAK: {reply[:50]}")
        else:
            warn(f"Time: '{q}'", f"missing expected word: {reply[:50]}")
    except Exception as e:
        fail(f"Time: '{q}'", str(e)[:60])

# ─── 4. Math & Simple Facts ───────────────────────────────────────────────────
hdr("4. MATH & SIMPLE FACTS")

math_tests = [
    ("what is 2 + 2",  "4"),
    ("what is 10 times 5", "50"),
    ("what is 100 divided by 4", "25"),
]

for q, expected in math_tests:
    try:
        reply = chat(q)
        if not reply:
            fail(f"Math: '{q}'", "empty")
        elif has_mock_result(reply):
            fail(f"Math: '{q}'", f"mock search injected: {reply[:80]}")
        elif expected in reply:
            ok(f"Math: '{q}'", reply[:50])
        else:
            warn(f"Math: '{q}'", f"expected '{expected}' in: {reply[:60]}")
    except Exception as e:
        fail(f"Math: '{q}'", str(e)[:60])

# ─── 5. Weather Queries ───────────────────────────────────────────────────────
hdr("5. WEATHER QUERIES")

weather_tests = [
    "what is the weather",
    "weather in Chennai",
    "will it rain today",
]

for q in weather_tests:
    try:
        t0 = time.time()
        reply = chat(q, timeout=25)
        elapsed = time.time() - t0
        low = reply.lower()
        if not reply:
            fail(f"Weather: '{q}'", "empty")
        elif has_json_leak(reply):
            fail(f"Weather: '{q}'", f"JSON LEAK: {reply[:60]}")
        elif any(w in low for w in ["temperature", "rain", "cloud", "wind", "sunny", "clear",
                                     "partly", "weather", "humid", "degree", "celsius"]):
            ok(f"Weather: '{q}'", f"{elapsed:.1f}s — {reply[:55]}")
        else:
            warn(f"Weather: '{q}'", f"no weather keywords: {reply[:60]}")
    except Exception as e:
        fail(f"Weather: '{q}'", str(e)[:60])

# ─── 6. General Knowledge ─────────────────────────────────────────────────────
hdr("6. GENERAL KNOWLEDGE")

knowledge_tests = [
    ("what is the capital of France",    ["paris"]),
    ("who invented the telephone",       ["bell", "alexander", "graham"]),
    ("what is Python programming",       ["language", "python", "programming", "code"]),
    ("tell me a fun fact",               ["fact", "did", "know", "interesting"]),
]

for q, expected in knowledge_tests:
    try:
        t0 = time.time()
        reply = chat(q, timeout=25)
        elapsed = time.time() - t0
        low = reply.lower()
        if not reply:
            fail(f"Knowledge: '{q}'", "empty")
        elif has_json_leak(reply):
            fail(f"Knowledge: '{q}'", f"JSON LEAK")
        elif has_mock_result(reply):
            fail(f"Knowledge: '{q}'", f"mock search injected")
        elif any(w in low for w in expected):
            ok(f"Knowledge: '{q}'", f"{elapsed:.1f}s — {reply[:55]}")
        else:
            warn(f"Knowledge: '{q}'", f"missing expected: {reply[:60]}")
    except Exception as e:
        fail(f"Knowledge: '{q}'", str(e)[:60])

# ─── 7. Tool Calls ────────────────────────────────────────────────────────────
hdr("7. TOOL CALLS (Alarm, Light, Music)")

tool_tests = [
    ("set alarm for 8 AM",       ["alarm", "reminder", "set", "8"]),
    ("turn on the lights",       ["light", "on", "turn"]),
    ("tell me a joke",           ["joke", "why", "what", "ha", "laugh", "pun"]),
    ("give me a motivational quote", ["success", "dream", "life", "believe", "never", "always"]),
]

for q, expected in tool_tests:
    try:
        reply = chat(q, timeout=25)
        low = reply.lower()
        if not reply:
            fail(f"Tool: '{q}'", "empty")
        elif has_json_leak(reply):
            fail(f"Tool: '{q}'", f"JSON LEAK: {reply[:60]}")
        elif any(w in low for w in expected):
            ok(f"Tool: '{q}'", reply[:55])
        else:
            warn(f"Tool: '{q}'", f"unexpected: {reply[:60]}")
    except Exception as e:
        fail(f"Tool: '{q}'", str(e)[:60])

# ─── 8. Conversation Memory ───────────────────────────────────────────────────
hdr("8. CONVERSATION MEMORY & CONTEXT")

try:
    # Clear first
    requests.post(f"{BASE_URL}/api/clear", json={}, timeout=5)
    time.sleep(0.5)

    r1 = chat("my name is TestUser")
    r2 = chat("what is my name?")

    if "testuser" in r2.lower() or "test" in r2.lower():
        ok("Name recall", f"'{r2[:60]}'")
    else:
        warn("Name recall", f"May not remember: '{r2[:60]}'")

    # Test follow-up context
    r3 = chat("what is photosynthesis")
    r4 = chat("can you explain more about it")
    if r4 and len(r4) > 20 and not has_json_leak(r4):
        ok("Follow-up context", r4[:55])
    else:
        warn("Follow-up context", r4[:55] if r4 else "empty")

except Exception as e:
    fail("Conversation memory", str(e)[:60])

# ─── 9. Clear Memory Endpoint ─────────────────────────────────────────────────
hdr("9. MEMORY MANAGEMENT ENDPOINTS")

try:
    r = requests.post(f"{BASE_URL}/api/clear", json={}, timeout=5)
    if r.status_code == 200 and r.json().get("ok"):
        ok("Clear memory", "memory wiped")
    else:
        fail("Clear memory", f"status={r.status_code}")
except Exception as e:
    fail("Clear memory", str(e)[:60])

try:
    r = requests.post(f"{BASE_URL}/api/memory", json={"action": "get"}, timeout=5)
    data = r.json()
    if "profile" in data:
        ok("Get memory profile", str(data.get("profile", {}))[:50])
    else:
        warn("Get memory profile", str(data)[:60])
except Exception as e:
    fail("Get memory profile", str(e)[:60])

# ─── 10. System Info Endpoints ────────────────────────────────────────────────
hdr("10. SYSTEM INFO ENDPOINTS")

sys_queries = [("battery", "battery"), ("cpu", "cpu"), ("ram", "ram"), ("wifi", "wifi")]
for q, label in sys_queries:
    try:
        r = requests.post(f"{BASE_URL}/api/system", json={"query": q}, timeout=5)
        data = r.json()
        if data.get("result"):
            ok(f"System/{label}", str(data["result"])[:55])
        else:
            warn(f"System/{label}", "no result field")
    except Exception as e:
        fail(f"System/{label}", str(e)[:60])

# ─── 11. TTS Endpoints ────────────────────────────────────────────────────────
hdr("11. TTS CONTROL ENDPOINTS")

try:
    r = requests.post(f"{BASE_URL}/api/tts_status", json={}, timeout=5)
    data = r.json()
    if "speaking" in data:
        ok("TTS status endpoint", f"speaking={data['speaking']}")
    else:
        fail("TTS status endpoint", str(data)[:50])
except Exception as e:
    fail("TTS status endpoint", str(e)[:60])

try:
    r = requests.post(f"{BASE_URL}/api/tts_stop", json={}, timeout=5)
    if r.json().get("ok"):
        ok("TTS stop endpoint")
    else:
        warn("TTS stop endpoint", str(r.json()))
except Exception as e:
    fail("TTS stop endpoint", str(e)[:60])

# ─── 12. Smart Home Endpoint ──────────────────────────────────────────────────
hdr("12. SMART HOME ENDPOINT")

try:
    r = requests.post(f"{BASE_URL}/api/smarthome",
                      json={"action": "control", "command": "turn on living room light"},
                      timeout=15)
    data = r.json()
    if data.get("result") or data.get("error"):
        ok("Smart home control", (data.get("result") or data.get("error", ""))[:55])
    else:
        warn("Smart home control", str(data)[:55])
except Exception as e:
    fail("Smart home control", str(e)[:60])

try:
    r = requests.post(f"{BASE_URL}/api/smarthome",
                      json={"action": "list"}, timeout=8)
    data = r.json()
    if "result" in data:
        ok("Smart home list devices", str(data["result"])[:55])
    else:
        warn("Smart home list devices", str(data)[:55])
except Exception as e:
    fail("Smart home list devices", str(e)[:60])

# ─── 13. Calendar Endpoint ────────────────────────────────────────────────────
hdr("13. CALENDAR ENDPOINT")

try:
    r = requests.post(f"{BASE_URL}/api/calendar",
                      json={"action": "today"}, timeout=8)
    data = r.json()
    if "result" in data:
        ok("Calendar today", str(data["result"])[:55])
    else:
        warn("Calendar today", str(data)[:55])
except Exception as e:
    fail("Calendar today", str(e)[:60])

# ─── 14. Games Endpoint ───────────────────────────────────────────────────────
hdr("14. GAMES ENDPOINT")

game_types = ["riddle", "joke", "quote", "number", "math"]
for gtype in game_types:
    try:
        r = requests.post(f"{BASE_URL}/api/game",
                          json={"action": gtype}, timeout=8)
        data = r.json()
        result = data.get("result", "")
        if result and len(result) > 5:
            ok(f"Game: {gtype}", result[:55])
        else:
            warn(f"Game: {gtype}", str(data)[:55])
    except Exception as e:
        fail(f"Game: {gtype}", str(e)[:60])

# ─── 15. Error Handling ───────────────────────────────────────────────────────
hdr("15. ERROR HANDLING & EDGE CASES")

# Empty message
try:
    r = requests.post(f"{BASE_URL}/api/chat", json={"message": ""}, timeout=8)
    if r.status_code in (200, 400):
        ok("Empty message handled", f"status={r.status_code}")
    else:
        fail("Empty message handled", f"status={r.status_code}")
except Exception as e:
    fail("Empty message handled", str(e)[:60])

# Very long message
try:
    long_msg = "tell me about " + "artificial intelligence " * 20
    r = requests.post(f"{BASE_URL}/api/chat", json={"message": long_msg}, timeout=25)
    if r.status_code == 200:
        ok("Long message handled", f"{len(long_msg)} chars → status=200")
    else:
        warn("Long message handled", f"status={r.status_code}")
except Exception as e:
    fail("Long message handled", str(e)[:60])

# Special characters
try:
    r = requests.post(f"{BASE_URL}/api/chat",
                      json={"message": "hello <script>alert(1)</script>"}, timeout=15)
    reply = r.json().get("reply", "")
    if "<script>" not in reply:
        ok("XSS sanitization", "no script tags in reply")
    else:
        fail("XSS sanitization", "script tag reflected!")
except Exception as e:
    fail("XSS sanitization", str(e)[:60])

# Unknown API endpoint → 404
try:
    r = requests.post(f"{BASE_URL}/api/nonexistent", json={}, timeout=5)
    if r.status_code == 404:
        ok("Unknown endpoint → 404", "correctly handled")
    else:
        warn("Unknown endpoint → 404", f"got {r.status_code}")
except Exception as e:
    fail("Unknown endpoint → 404", str(e)[:60])

# ─── 16. Response Quality (no leaks, reasonable length) ───────────────────────
hdr("16. RESPONSE QUALITY CHECKS")

quality_tests = [
    ("what is machine learning", 20, 500),
    ("tell me about India",       20, 600),
    ("what is 15 + 27",          1,  100),
    ("what is water",            10,  400),
]

for q, min_len, max_len in quality_tests:
    try:
        reply = chat(q, timeout=25)
        if not reply:
            fail(f"Quality: '{q}'", "empty reply")
        elif has_json_leak(reply):
            fail(f"Quality: '{q}'", f"JSON LEAK")
        elif has_mock_result(reply):
            fail(f"Quality: '{q}'", "mock web data injected")
        elif len(reply) < min_len:
            warn(f"Quality: '{q}'", f"too short ({len(reply)} chars)")
        elif len(reply) > max_len:
            warn(f"Quality: '{q}'", f"too long ({len(reply)} chars)")
        else:
            ok(f"Quality: '{q}'", f"{len(reply)} chars — {reply[:45]}")
    except Exception as e:
        fail(f"Quality: '{q}'", str(e)[:60])

# ─── 17. Performance ──────────────────────────────────────────────────────────
hdr("17. PERFORMANCE BENCHMARKS")

perf_tests = [
    ("hello",                   2.0,  "rule-based"),
    ("what time is it",         2.0,  "rule-based"),
    ("what is the weather",    12.0,  "tool call"),
    ("what is photosynthesis", 15.0,  "LLM"),
]

for q, max_sec, category in perf_tests:
    try:
        t0 = time.time()
        reply = chat(q, timeout=max_sec + 5)
        elapsed = time.time() - t0
        if elapsed <= max_sec:
            ok(f"Perf [{category}]: '{q}'", f"{elapsed:.2f}s ≤ {max_sec}s")
        else:
            warn(f"Perf [{category}]: '{q}'", f"{elapsed:.2f}s > {max_sec}s target")
    except Exception as e:
        fail(f"Perf [{category}]: '{q}'", str(e)[:60])

# ─── 18. Concurrent Requests ──────────────────────────────────────────────────
hdr("18. CONCURRENCY (DEADLOCK CHECK)")

import threading

concurrent_results = []
lock_r = threading.Lock()

def send_concurrent(q, idx):
    try:
        t0 = time.time()
        reply = chat(q, timeout=30)
        elapsed = time.time() - t0
        with lock_r:
            concurrent_results.append((idx, True, elapsed, reply[:40]))
    except Exception as e:
        with lock_r:
            concurrent_results.append((idx, False, 0, str(e)[:40]))

concurrent_queries = [
    "hello", "what time is it", "what is 5 + 3", "what day is it", "who are you"
]

threads = [threading.Thread(target=send_concurrent, args=(q, i))
           for i, q in enumerate(concurrent_queries)]

t_start = time.time()
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=40)
t_total = time.time() - t_start

passed_concurrent = sum(1 for r in concurrent_results if r[1])
if passed_concurrent == len(concurrent_queries):
    ok("Concurrent requests (no deadlock)", f"{passed_concurrent}/{len(concurrent_queries)} in {t_total:.1f}s")
elif passed_concurrent > 0:
    warn("Concurrent requests", f"only {passed_concurrent}/{len(concurrent_queries)} succeeded in {t_total:.1f}s")
else:
    fail("Concurrent requests", f"all {len(concurrent_queries)} failed — possible deadlock")

# ─── 19. STT Lang Switch ──────────────────────────────────────────────────────
hdr("19. STT LANGUAGE SWITCH")

try:
    r = requests.post(f"{BASE_URL}/api/stt_lang", json={"lang": "en"}, timeout=5)
    data = r.json()
    if data.get("lang") == "en":
        ok("STT lang switch to English")
    else:
        warn("STT lang switch", str(data))
except Exception as e:
    fail("STT lang switch", str(e)[:60])

# ─── 20. Index HTML Served ────────────────────────────────────────────────────
hdr("20. FRONTEND SERVED")

try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    if r.status_code == 200 and "JARVIS" in r.text:
        ok("index.html served", f"{len(r.text)} bytes, contains JARVIS")
    elif r.status_code == 200:
        ok("index.html served", f"{len(r.text)} bytes")
    else:
        fail("index.html served", f"status={r.status_code}")
except Exception as e:
    fail("index.html served", str(e)[:60])

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
total = PASS + FAIL + WARN
pct   = (PASS / (PASS + FAIL) * 100) if (PASS + FAIL) > 0 else 0

hdr("FINAL TEST SUMMARY")
print(f"""
  Total Tests:   {total}
  ✅ Passed:     {PASS}
  ❌ Failed:     {FAIL}
  ⚠️  Warnings:  {WARN}
  Pass Rate:     {pct:.0f}%
""")

if FAIL == 0:
    print("🎉  ALL TESTS PASSED — JARVIS is fully operational!\n")
elif pct >= 80:
    print("✅  SYSTEM OPERATIONAL — minor issues detected.\n")
elif pct >= 60:
    print("⚠️   PARTIAL FUNCTIONALITY — some features degraded.\n")
else:
    print("🚫  CRITICAL ISSUES — significant failures detected.\n")

if FAIL > 0:
    print("Failed tests:")
    for status, name, msg in RESULTS:
        if status == "FAIL":
            print(f"  ❌ {name}: {msg}")

sys.exit(0 if FAIL == 0 else 1)
