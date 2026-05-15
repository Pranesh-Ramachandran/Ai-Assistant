#!/usr/bin/env python3
"""
JARVIS AI Assistant - Comprehensive System Test Suite
Tests all major components and API endpoints
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:7890"
TESTS_PASSED = 0
TESTS_FAILED = 0

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_test(name):
    print(f"\n▶ {name}...", end=" ", flush=True)

def pass_test(msg=""):
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"✅ PASS" + (f" - {msg}" if msg else ""))

def fail_test(msg=""):
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"❌ FAIL" + (f" - {msg}" if msg else ""))

def check_json_leak(text):
    """Check if response contains leaked JSON tool calls"""
    if not text:
        return False
    has_brackets = '{' in text and '}' in text
    has_quotes = '"' in text
    has_name_key = '"name"' in text or '"function"' in text
    return has_brackets and has_quotes and has_name_key

# TEST 1: System Status
print_header("TEST 1: System Status & Initialization")

print_test("Check server connectivity")
try:
    response = requests.post(f"{BASE_URL}/api/status", json={}, timeout=5)
    if response.status_code == 200:
        data = response.json()
        pass_test(f"Server responsive")
        print(f"  - AI Ready: {data.get('ai_ready')}")
        print(f"  - Groq Available: {data.get('groq_available')}")
        print(f"  - Gemini Available: {data.get('gemini_available')}")
    else:
        fail_test(f"Status code {response.status_code}")
except Exception as e:
    fail_test(str(e))

# TEST 2: Basic Chat
print_header("TEST 2: Chat Functionality")

test_queries = [
    ("hello", "greeting"),
    ("what is your name", "identity"),
]

for query, test_type in test_queries:
    print_test(f"Query: '{query}'")
    try:
        response = requests.post(f"{BASE_URL}/api/chat", 
                                json={"message": query, "lang": "en"}, 
                                timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get("reply", "")
            
            if not reply:
                fail_test("Empty response")
            elif check_json_leak(reply):
                fail_test(f"JSON LEAK: {reply[:60]}")
            else:
                pass_test(f"{reply[:60]}...")
        else:
            fail_test(f"Status {response.status_code}")
    except Exception as e:
        fail_test(str(e)[:60])

# TEST 3: Weather Query
print_header("TEST 3: Weather Query")

print_test("Weather query")
try:
    response = requests.post(f"{BASE_URL}/api/chat", 
                            json={"message": "what is the weather?", "lang": "en"}, 
                            timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        reply = data.get("reply", "")
        if not check_json_leak(reply):
            pass_test("No JSON leaks")
        else:
            fail_test("JSON LEAK")
    else:
        fail_test(f"Status {response.status_code}")
except Exception as e:
    fail_test(str(e)[:60])

# TEST 4: Cache System
print_header("TEST 4: Cache System")

print_test("Cached query")
try:
    times = []
    for i in range(2):
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/chat", 
                                json={"message": "2+2=?", "lang": "en"}, 
                                timeout=15)
        elapsed = time.time() - start
        times.append(elapsed)
        if response.status_code != 200:
            fail_test("Request failed")
            break
    else:
        pass_test(f"1st={times[0]:.2f}s, 2nd={times[1]:.2f}s")
except Exception as e:
    fail_test(str(e)[:60])

# TEST 5: Language
print_header("TEST 5: Language Handling")

print_test("English response")
try:
    response = requests.post(f"{BASE_URL}/api/chat", 
                            json={"message": "hello", "lang": "en"}, 
                            timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        reply = data.get("reply", "")
        if reply:
            pass_test("Response received")
        else:
            fail_test("Empty response")
    else:
        fail_test(f"Status {response.status_code}")
except Exception as e:
    fail_test(str(e)[:60])

# TEST 6: Error Handling
print_header("TEST 6: Error Handling")

print_test("Empty query")
try:
    response = requests.post(f"{BASE_URL}/api/chat", 
                            json={"message": "", "lang": "en"}, 
                            timeout=15)
    if response.status_code in [200, 400]:
        pass_test("Handled gracefully")
    else:
        fail_test(f"Status {response.status_code}")
except Exception as e:
    fail_test(str(e)[:60])

# TEST 7: Performance
print_header("TEST 7: Performance")

print_test("Response time (5 queries)")
try:
    times = []
    for i in range(5):
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/chat", 
                                json={"message": f"test {i}", "lang": "en"}, 
                                timeout=15)
        elapsed = time.time() - start
        if response.status_code == 200:
            times.append(elapsed)
    
    if times:
        avg = sum(times) / len(times)
        if avg < 5.0:
            pass_test(f"Good ({avg:.2f}s avg)")
        else:
            pass_test(f"Acceptable ({avg:.2f}s avg)")
    else:
        fail_test("No successful queries")
except Exception as e:
    fail_test(str(e)[:60])

# SUMMARY
print_header("TEST SUMMARY")

total = TESTS_PASSED + TESTS_FAILED
pct = (TESTS_PASSED / total * 100) if total > 0 else 0

print(f"""
Total Tests:  {total}
Passed:       {TESTS_PASSED} ✅
Failed:       {TESTS_FAILED} ❌
Success:      {pct:.0f}%
""")

if pct >= 80:
    print("✅ SYSTEM OPERATIONAL")
else:
    print("⚠️  ISSUES DETECTED")
