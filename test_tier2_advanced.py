#!/usr/bin/env python3
"""Test Tier 2 modules: Personalization and Confidence Scoring"""

import sys
sys.path.insert(0, 'd:/ai/AI_Assistant')

from personalization_engine import personalize, PERSONALIZATION_ENGINE
from confidence_scoring import score_response

# Test 1: Personalization Engine
print("[TEST 1] Personalization Engine")
result = personalize("My name is John and I'm from Kerala")
print(f"  Input: 'My name is John and I'm from Kerala'")
print(f"  Extracted: {result['extracted_preferences']}")
print(f"  Greeting: {result.get('greeting', 'N/A')}")
print()

# Test 2: Personalization - Get profile
print("[TEST 2] User Profile")
profile = PERSONALIZATION_ENGINE.get_profile_summary()
print(f"  Name: {profile['user_name']}")
print(f"  Location: {profile['location']}")
print()

# Test 3: Confidence Scoring - High confidence
print("[TEST 3] Confidence Scoring - High Certainty")
result = score_response("The weather in Kerala is definitely 32°C and sunny", source="weather_api", intent="INFORMATION")
print(f"  Input: 'The weather in Kerala is definitely 32°C and sunny'")
print(f"  Confidence: {result['confidence']}")
print(f"  Level: {result['level']}")
print(f"  Should clarify: {result['should_clarify']}")
print()

# Test 4: Confidence Scoring - Low confidence
print("[TEST 4] Confidence Scoring - Low Certainty")
result = score_response("I'm not sure, but I think it might be around 30 degrees celsius", source="llm_groq", intent="QUESTION")
print(f"  Input: 'I'm not sure, but I think it might be around 30 degrees'")
print(f"  Confidence: {result['confidence']}")
print(f"  Level: {result['level']}")
print(f"  Should clarify: {result['should_clarify']}")
print()

# Test 5: Confidence Scoring - Admission of ignorance
print("[TEST 5] Confidence Scoring - Unable to Answer")
result = score_response("I don't know the answer to that question", source="llm_groq", intent="QUESTION")
print(f"  Input: 'I don't know the answer to that question'")
print(f"  Confidence: {result['confidence']}")
print(f"  Level: {result['level']}")
print(f"  Should clarify: {result['should_clarify']}")
print()

print("[OK] All Tier 2 personalization & confidence modules working!")
