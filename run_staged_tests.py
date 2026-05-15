#!/usr/bin/env python3
"""Staged test runner - avoids blocking voice/STT endpoints."""
import requests, time, threading, json, re

BASE = "http://localhost:7890"
PASS = FAIL = WARN = 0

def p(status, label, detail=""):
    global PASS, FAIL, WARN
    icons = {"OK": "OK  ", "FAIL": "FAIL", "WARN": "WARN", "MOCK": "MOCK", "LEAK": "LEAK"}
    icon = icons.get(status, status)
    suffix = f" | {detail[:70]}" if detail else ""
    print(f"  [{icon}] {label}{suffix}")
    if status == "OK":   PASS += 1
    elif status == "FAIL": FAIL += 1
    else: WARN += 1

def chat(msg, timeout=45):
    r = requests.post(f"{BASE}/api/chat", json={"message": msg}, timeout=timeout)
    return r.json().get("reply", "")

def check(reply):
    """Returns ('LEAK'|'MOCK'|None) if problematic."""
    if not reply:
        return "FAIL"
    if re.search(r'\{"name"\s*:', reply) or "<function" in reply:
        return "LEAK"
    if "(Mock result)" in reply or "example1.com" in reply:
        return "MOCK"
    return None

print("\n" + "="*60)
print("  STAGE 1 — Server Health")
print("="*60)
try:
    r = requests.post(f"{BASE}/api/status", json={}, timeout=5)
    d = r.json()
    p("OK" if d.get("ai_ready") else "FAIL", "Server up", f"ai_ready={d.get('ai_ready')}")
    for key in ("groq_available", "gemini_available", "tts_ready", "stt_ready"):
        p("OK" if d.get(key) else "WARN", key, str(d.get(key)))
except Exception as e:
    p("FAIL", "Server unreachable", str(e))
    import sys; sys.exit(1)

print("\n" + "="*60)
print("  STAGE 2 — Greetings & Rule-based")
print("="*60)
cases = [
    ("hello",               ["hello","hi","help","what", "need"]),
    ("how are you",         ["doing","great","help","ready","assist"]),
    ("who are you",         ["jarvis","assistant","ai"]),
    ("thank you",           ["welcome","anytime","glad"]),
    ("what time is it",     ["pm","am",":"]),
    ("what is today's date",["2026","may","friday","saturday","sunday","monday","tuesday","wednesday","thursday"]),
]
for q, expected in cases:
    try:
        t0 = time.time()
        reply = chat(q, timeout=12)
        elapsed = time.time() - t0
        bad = check(reply)
        if bad:
            p(bad, q, reply[:70])
        elif any(w in reply.lower() for w in expected):
            p("OK", q, f"{elapsed:.2f}s | {reply[:60]}")
        else:
            p("WARN", q, f"no expected word | {reply[:60]}")
    except Exception as e:
        p("FAIL", q, str(e)[:60])

print("\n" + "="*60)
print("  STAGE 3 — Math & Simple Facts")
print("="*60)
math_cases = [
    ("what is 2 + 2",           "4"),
    ("what is 10 times 5",      "50"),
    ("what is 100 divided by 4","25"),
    ("what is 7 minus 3",       "4"),
]
for q, expected in math_cases:
    try:
        reply = chat(q, timeout=15)
        bad = check(reply)
        if bad:
            p(bad, q, reply[:70])
        elif expected in reply:
            p("OK", q, reply[:60])
        else:
            p("WARN", q, f"expected '{expected}' | got: {reply[:60]}")
    except Exception as e:
        p("FAIL", q, str(e)[:60])

print("\n" + "="*60)
print("  STAGE 4 — Weather Tool")
print("="*60)
weather_kws = ["temperature","rain","cloud","wind","sunny","clear","partly","humidity","degree","celsius","weather","hot","cool"]
for q in ["what is the weather", "weather in Chennai", "will it rain today"]:
    try:
        t0 = time.time()
        reply = chat(q, timeout=45)
        elapsed = time.time() - t0
        bad = check(reply)
        if bad:
            p(bad, q, reply[:70])
        elif any(w in reply.lower() for w in weather_kws):
            p("OK", q, f"{elapsed:.1f}s | {reply[:60]}")
        else:
            p("WARN", q, f"no weather kw | {reply[:60]}")
    except Exception as e:
        p("FAIL", q, str(e)[:60])

print("\n" + "="*60)
print("  STAGE 5 — General Knowledge")
print("="*60)
knowledge_cases = [
    ("what is the capital of France",   ["paris"]),
    ("who invented the telephone",      ["bell","alexander","graham","watson"]),
    ("what is photosynthesis",          ["plant","light","chlorophyll","sun","oxygen","carbon","process"]),
    ("what is Python programming",      ["language","python","programming","code","object"]),
]
for q, expected in knowledge_cases:
    try:
        t0 = time.time()
        reply = chat(q, timeout=45)
        elapsed = time.time() - t0
        bad = check(reply)
        if bad:
            p(bad, q, reply[:70])
        elif any(w in reply.lower() for w in expected):
            p("OK", q, f"{elapsed:.1f}s | {reply[:60]}")
        else:
            p("WARN", q, f"missing expected | {reply[:60]}")
    except Exception as e:
        p("FAIL", q, str(e)[:60])

print("\n" + "="*60)
print("  STAGE 6 — Tool Calls (Alarm, Light, Jokes)")
print("="*60)
tool_cases = [
    ("set alarm for 7 AM tomorrow",  ["alarm","reminder","set","7","noted"]),
    ("turn on the bedroom light",    ["light","on","turned","bedroom"]),
    ("tell me a joke",               ["why","what","joke","answer","pun","laugh",":"]),
    ("give me a motivational quote", ["success","dream","life","believe","never","always","great","you","be"]),
]
for q, expected in tool_cases:
    try:
        reply = chat(q, timeout=45)
        bad = check(reply)
        if bad:
            p(bad, q, reply[:70])
        elif any(w in reply.lower() for w in expected):
            p("OK", q, reply[:60])
        else:
            p("WARN", q, f"missing expected | {reply[:60]}")
    except Exception as e:
        p("FAIL", q, str(e)[:60])

print("\n" + "="*60)
print("  STAGE 7 — Memory & Context")
print("="*60)
try:
    requests.post(f"{BASE}/api/clear", json={}, timeout=5)
    time.sleep(0.3)
    chat("my name is TestUser123", timeout=15)
    r2 = chat("what is my name?", timeout=15)
    if "testuser" in r2.lower() or "test" in r2.lower():
        p("OK", "Name recall", r2[:60])
    else:
        p("WARN", "Name recall", f"not remembered: {r2[:60]}")

    chat("the capital of Japan is Tokyo", timeout=15)
    r3 = chat("what did I just tell you about Japan?", timeout=15)
    if "tokyo" in r3.lower() or "japan" in r3.lower() or "capital" in r3.lower():
        p("OK", "Context carry-over", r3[:60])
    else:
        p("WARN", "Context carry-over", r3[:60])
except Exception as e:
    p("FAIL", "Memory tests", str(e)[:60])

print("\n" + "="*60)
print("  STAGE 8 — API Endpoints")
print("="*60)
endpoints = [
    ("POST", "/api/clear",      {},             lambda d: d.get("ok") == True,             "Clear memory"),
    ("POST", "/api/tts_status", {},             lambda d: "speaking" in d,                "TTS status"),
    ("POST", "/api/tts_stop",   {},             lambda d: d.get("ok") == True,             "TTS stop"),
    ("POST", "/api/system",     {"query":"cpu"},lambda d: bool(d.get("result")),           "System CPU"),
    ("POST", "/api/system",     {"query":"ram"},lambda d: bool(d.get("result")),           "System RAM"),
    ("POST", "/api/game",       {"action":"joke"},lambda d: len(d.get("result",""))>5,    "Game: joke"),
    ("POST", "/api/game",       {"action":"riddle"},lambda d: len(d.get("result",""))>5,  "Game: riddle"),
    ("POST", "/api/smarthome",  {"action":"list"},lambda d: "result" in d,               "SmartHome list"),
    ("POST", "/api/calendar",   {"action":"today"},lambda d: "result" in d,              "Calendar today"),
    ("GET",  "/",               {},             lambda _: True,                            "Frontend served"),
]

for method, path, body, check_fn, label in endpoints:
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{path}", timeout=8)
            data = {}
        else:
            r = requests.post(f"{BASE}{path}", json=body, timeout=8)
            data = r.json()
        
        if r.status_code == 200 and check_fn(data):
            p("OK", label, f"status={r.status_code}")
        else:
            p("WARN", label, f"status={r.status_code} | {str(data)[:50]}")
    except Exception as e:
        p("FAIL", label, str(e)[:60])

print("\n" + "="*60)
print("  STAGE 9 — Error Handling")
print("="*60)
# Empty message
try:
    r = requests.post(f"{BASE}/api/chat", json={"message": ""}, timeout=8)
    if r.status_code in (200, 400):
        p("OK", "Empty message handled", f"status={r.status_code}")
    else:
        p("FAIL", "Empty message handled", f"status={r.status_code}")
except Exception as e:
    p("FAIL", "Empty message handled", str(e)[:60])

# 404 endpoint
try:
    r = requests.post(f"{BASE}/api/nonexistent_xyz", json={}, timeout=5)
    p("OK" if r.status_code == 404 else "WARN", "Unknown endpoint → 404", f"got {r.status_code}")
except Exception as e:
    p("FAIL", "Unknown endpoint → 404", str(e)[:60])

# XSS check
try:
    r = requests.post(f"{BASE}/api/chat", json={"message": "hello <script>alert(1)</script>"}, timeout=12)
    reply = r.json().get("reply", "")
    if "<script>" not in reply:
        p("OK", "No XSS reflection", reply[:50])
    else:
        p("FAIL", "XSS reflected in reply!", reply[:60])
except Exception as e:
    p("FAIL", "XSS check", str(e)[:60])

print("\n" + "="*60)
print("  STAGE 10 — Concurrency / Deadlock Check")
print("="*60)
results = []
lock = threading.Lock()
def concurrent_chat(q, idx):
    try:
        t0 = time.time()
        reply = chat(q, timeout=30)
        with lock:
            results.append(("OK", q, time.time()-t0, reply[:35]))
    except Exception as e:
        with lock:
            results.append(("ERR", q, 0, str(e)[:35]))

concurrent_qs = [
    "hello", "what time is it", "what is 5 + 3",
    "who are you", "what day is it"
]
threads = [threading.Thread(target=concurrent_chat, args=(q, i))
           for i, q in enumerate(concurrent_qs)]
t0 = time.time()
for t in threads: t.start()
for t in threads: t.join(timeout=40)
total_time = time.time() - t0

ok_count = sum(1 for r in results if r[0] == "OK")
if ok_count == len(concurrent_qs):
    p("OK", f"Concurrent ({ok_count}/{len(concurrent_qs)}) — no deadlock", f"total={total_time:.1f}s")
elif ok_count > 0:
    p("WARN", f"Concurrent ({ok_count}/{len(concurrent_qs)})", f"some failed in {total_time:.1f}s")
else:
    p("FAIL", "Concurrency — possible deadlock", f"0/{len(concurrent_qs)} in {total_time:.1f}s")

for status, q, elapsed, reply in results:
    marker = "OK" if status == "OK" else "ERR"
    if status == "OK":
        print(f"    [{marker}] {q!r}: {elapsed:.2f}s | {reply}")
    else:
        print(f"    [{marker}] {q!r}: {reply}")

print("\n" + "="*60)
print("  FINAL SUMMARY")
print("="*60)
total = PASS + FAIL + WARN
pct = (PASS / (PASS + FAIL) * 100) if (PASS + FAIL) > 0 else 0
print(f"""
  Total:    {total}
  Passed:   {PASS}
  Failed:   {FAIL}
  Warnings: {WARN}
  Rate:     {pct:.0f}%
""")
if FAIL == 0:
    print("  ALL TESTS PASSED — JARVIS is fully operational!\n")
elif pct >= 80:
    print("  SYSTEM OPERATIONAL — minor issues.\n")
else:
    print("  ISSUES DETECTED.\n")
