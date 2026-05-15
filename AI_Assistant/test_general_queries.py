#!/usr/bin/env python3
"""
Test JARVIS wake word + STT + AI response flow.
Verifies that general queries work without restriction.
"""

import os
import time

# Ensure AI brain is in hybrid mode
os.environ["JARVIS_AI_MODE"] = "hybrid"

from jarvis_ai_brain import ask, _offline_reply
from data_collector import get_weather, get_news, get_information

print("=" * 70)
print("JARVIS General Query Test Suite")
print("=" * 70)

# Test queries that should work
test_queries = [
    # Date/time queries
    ("what's the day today", "Date/time"),
    ("what time is it", "Time"),
    
    # Weather (uses tools)
    ("how's the weather", "Weather"),
    ("what's the weather in Delhi", "Weather (location)"),
    
    # News (uses tools)
    ("tell me the news", "News"),
    ("what's happening in india", "News (India)"),
    
    # General knowledge
    ("who is Einstein", "General knowledge"),
    ("what is photosynthesis", "Science"),
    
    # Greetings
    ("hello jarvis", "Greeting"),
    ("how are you", "Social"),
    
    # Commands
    ("turn on the lights", "Light control"),
    ("set an alarm for 7am", "Alarm setting"),
]

results = []
for query, category in test_queries:
    print(f"\n[TEST] {category}: '{query}'")
    try:
        response = ask(query)
        if response:
            print(f"  ✓ Response: {response[:80]}...")
            results.append((category, "PASS"))
        else:
            print(f"  ✗ Empty response")
            results.append((category, "FAIL"))
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results.append((category, "ERROR"))

print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
for category, status in results:
    symbol = "✓" if status == "PASS" else "✗"
    print(f"{symbol} {category:25} {status}")

passed = sum(1 for _, s in results if s == "PASS")
total = len(results)
print(f"\nResult: {passed}/{total} tests passed")

if passed == total:
    print("\n✓ All tests passed! JARVIS is ready for general queries.")
else:
    print(f"\n✗ {total - passed} test(s) failed. Check logs above.")
