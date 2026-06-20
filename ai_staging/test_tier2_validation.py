#!/usr/bin/env python3
"""
Quick validation test - Tests all Tier 2 features without network delays
Focuses on core logic paths
"""

import sys
sys.path.insert(0, 'd:/ai/AI_Assistant')

from intent_classifier import classify_query
from extended_memory import EXTENDED_MEMORY
from natural_followup import FOLLOWUP_HANDLER
from query_rephrasing import QUERY_REPHRASER
from time_aware_execution import TIME_HANDLER
from personalization_engine import PERSONALIZATION_ENGINE
from confidence_scoring import CONFIDENCE_SCORER

# Test counters
tests_run = 0
tests_passed = 0

def check(name, condition, expected=True):
    """Run a test"""
    global tests_run, tests_passed
    tests_run += 1
    status = condition == expected
    if status:
        tests_passed += 1
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} (got {condition}, expected {expected})")
    return status


test = check
test.__test__ = False

print("\n" + "="*70)
print("  TIER 2 VALIDATION TEST - Core Logic")
print("="*70 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
print("[TIER 1] Intent Classification")
result = classify_query("What's the weather?")
test("Classifies QUESTION intent", result['intent'], "QUESTION")
test("Has confidence score", result['confidence'] > 0, True)

result = classify_query("Hello there!")
test("Classifies GREETING intent", result['intent'], "GREETING")

result = classify_query("Book a flight")
test("Classifies BOOKING intent", result['intent'], "BOOKING")

# ─────────────────────────────────────────────────────────────────────────────
print("\n[TIER 1] Extended Memory")
EXTENDED_MEMORY.add_turn("What's the weather?", "It's sunny", {"intent": "QUESTION"})
test("Stores conversation turn", len(EXTENDED_MEMORY.get_context()) > 0, True)

EXTENDED_MEMORY.add_turn("How are you", "Good, thanks", {"intent": "GREETING"})
test("Accumulates multiple turns", len(EXTENDED_MEMORY.get_context()) >= 2, True)

# ─────────────────────────────────────────────────────────────────────────────
print("\n[TIER 2] Natural Follow-up Detection")
FOLLOWUP_HANDLER.set_context("What's the weather in Kerala?", 
                             "It's 32°C and sunny", "INFORMATION", 
                             {"location": "Kerala"})
followup = FOLLOWUP_HANDLER.detect_followup("And in Tamil Nadu?")
test("Detects location continuation", followup is not None, True)
test("Identifies as 'continuation' type", followup['followup_type'], "continuation")

# Test yes/no response
FOLLOWUP_HANDLER.set_context("Should I bring an umbrella?", 
                             "Yes, there's rain expected", "QUESTION", {})
followup = FOLLOWUP_HANDLER.detect_followup("Yes")
test("Detects confirmation response", followup is not None, True)

# ─────────────────────────────────────────────────────────────────────────────
print("\n[TIER 2] Query Rephrasing")
QUERY_REPHRASER.set_context({"intent": "QUESTION", "entities": {"target": "price"}})
rephrased = QUERY_REPHRASER.rephrase_query("How much?")
test("Detects ambiguity in 'How much?'", rephrased['is_ambiguous'], True)
test("Rephrases with context", "quantity" in rephrased['rephrased'].lower() or "amount" in rephrased['rephrased'].lower(), True)

rephrased = QUERY_REPHRASER.rephrase_query("Hello world")
test("Doesn't flag clear query as ambiguous", rephrased['is_ambiguous'], False)

# ─────────────────────────────────────────────────────────────────────────────
print("\n[TIER 2] Time-aware Execution")
result = TIME_HANDLER.extract_time_expression("Set a reminder in 5 minutes")
test("Extracts relative time", result is not None, True)
test("Identifies as 'relative' type", result['time_type'], "relative")
test("Has time_delta for 5 minutes", result['time_delta'], 300)

result = TIME_HANDLER.extract_time_expression("tomorrow at 3 PM")
test("Extracts absolute time", result is not None, True)
test("Identifies as 'clock' or 'absolute' type", result['time_type'] in ["clock", "absolute"], True)

result = TIME_HANDLER.extract_time_expression("What's the weather?")
test("Returns None for non-timed query", result is None, True)

# ─────────────────────────────────────────────────────────────────────────────
print("\n[TIER 2] Personalization Engine")
# Clear and rebuild profile
PERSONALIZATION_ENGINE.user_profile = PERSONALIZATION_ENGINE._load_profile()

prefs = PERSONALIZATION_ENGINE.extract_preferences("My name is John from Kerala")
test("Extracts name preference", "user_name" in prefs['extracted'], True)
test("Name value is correct", PERSONALIZATION_ENGINE.user_profile['user_name'], "john")

prefs = PERSONALIZATION_ENGINE.extract_preferences("I love playing cricket")
test("Extracts interests", len(PERSONALIZATION_ENGINE.user_profile.get('interests', [])) > 0, True)

greeting = PERSONALIZATION_ENGINE.get_personalized_greeting()
test("Generates personalized greeting", "john" in greeting.lower(), True)

# ─────────────────────────────────────────────────────────────────────────────
print("\n[TIER 2] Confidence Scoring")
# High confidence
score = CONFIDENCE_SCORER.score_response(
    "The weather in Kerala is definitely 32°C and sunny",
    source="weather_api"
)
test("Scores high confidence for API response", score['confidence_score'] >= 0.9, True)
test("Classifies as VERY_HIGH", score['confidence_level'], "VERY_HIGH")

# Low confidence
score = CONFIDENCE_SCORER.score_response(
    "I'm not sure, but maybe it could be...",
    source="llm_groq"
)
test("Scores low confidence for hedged response", score['confidence_score'] < 0.65, True)
test("Classifies as MEDIUM or LOW", score['confidence_level'] in ["MEDIUM", "LOW"], True)

# Admission of ignorance
score = CONFIDENCE_SCORER.score_response(
    "I don't know the answer",
    source="llm_groq"
)
test("Scores very low for 'I don't know'", score['confidence_score'] <= 0.2, True)
test("Should prompt clarification", score['should_clarify'], True)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print(f"  RESULTS: {tests_passed}/{tests_run} tests passed")
print("="*70)

if tests_passed == tests_run:
    print("\n✓ All Tier 2 features validated successfully!")
    print("  System is ready for production use.\n")
else:
    print(f"\n⚠ {tests_run - tests_passed} test(s) failed\n")
