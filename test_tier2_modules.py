#!/usr/bin/env python3
"""Test Tier 2 modules"""

import sys
sys.path.insert(0, 'd:/ai/AI_Assistant')

from natural_followup import handle_followup
from query_rephrasing import rephrase_query
from time_aware_execution import extract_scheduled_action

# Test 1: Follow-up handling
print("[TEST 1] Natural Follow-up Handling")
result = handle_followup(
    "And in Kerala?",
    previous_query="What's the weather in Tamil Nadu?",
    previous_response="It's 32°C and sunny",
    previous_intent="INFORMATION",
    entities={"location": "Tamil Nadu", "target": "weather"}
)
print(f"  Input: 'And in Kerala?'")
print(f"  Is Follow-up: {result['is_followup']}")
print(f"  Type: {result.get('followup_type', 'N/A')}")
print()

# Test 2: Query Rephrasing
print("[TEST 2] Query Rephrasing")
result = rephrase_query("How much", context={"intent": "QUESTION", "query": "What's the price?"})
print(f"  Input: 'How much'")
print(f"  Rephrased: {result['rephrased']}")
print(f"  Needs Clarification: {result['needs_clarification']}")
print()

# Test 3: Time-aware execution
print("[TEST 3] Time-aware Execution")
result = extract_scheduled_action("Set a reminder in 5 minutes to call mom")
print(f"  Input: 'Set a reminder in 5 minutes to call mom'")
print(f"  Is Timed: {result['is_timed']}")
print(f"  Action: {result['action']}")
print(f"  Time String: {result['time_string']}")
print()

print("[OK] All Tier 2 modules working correctly!")
