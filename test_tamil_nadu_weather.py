#!/usr/bin/env python3
"""
Simple test: just ask for Tamil Nadu weather
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

print("\n" + "=" * 70)
print("TEST: Voice command weather query for Tamil Nadu")
print("=" * 70 + "\n")

# This is the exact query from the user's complaint
query = "what's the weather today on tamil nadu"

print(f"Query: {query}\n")

response = ask(query)

print(f"Response:\n{response}\n")

# Verify
has_tamil_chars = any('\u0b80' <= char <= '\u0bff' for char in response)
has_tamil_nadu = "tamil nadu" in response.lower()
is_english = not has_tamil_chars

print("Verification:")
print(f"  ✓ Response is in English: {is_english}")
print(f"  ✓ Response mentions Tamil Nadu: {has_tamil_nadu}")
print(f"  ✓ No Tamil script characters: {not has_tamil_chars}")

if is_english and has_tamil_nadu:
    print("\n✓ SUCCESS - Weather query for Tamil Nadu working correctly!")
    print("✓ Response is in English (not Tamil)")
    print("✓ Correct location is used")
else:
    print("\n❌ FAILED - Issue still present")
