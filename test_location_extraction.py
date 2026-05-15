#!/usr/bin/env python3
"""
Test location extraction from weather queries
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from data_collector import _extract_location, get_weather

test_queries = [
    ("what's the weather today on tamil nadu", "Tamil Nadu"),
    ("what's the weather in tamil nadu", "Tamil Nadu"),
    ("weather on kerala", "Kerala"),
    ("what's the weather today", ""),
    ("temperature in delhi", "Delhi"),
    ("weather for mumbai", "Mumbai"),
]

print("Testing location extraction:\n")

for query, expected in test_queries:
    extracted = _extract_location(query)
    status = "✓" if extracted == expected else "❌"
    print(f"{status} Query: {query}")
    print(f"   Expected: '{expected}' | Got: '{extracted}'\n")

print("\nTesting full weather response for Tamil Nadu:")
response = get_weather("what's the weather today on tamil nadu")
print(f"Response: {response}\n")

if "Tamil Nadu" in response or "Tamil Nadu" in response:
    print("✓ SUCCESS - Tamil Nadu weather retrieved")
else:
    print("❌ FAILED - Not returning Tamil Nadu weather")
