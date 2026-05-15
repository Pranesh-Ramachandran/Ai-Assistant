#!/usr/bin/env python3
"""
Test that English is the default language for responses
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

# Test queries
test_queries = [
    "what is pi",
    "tell me something about the moon",
    "what is the capital of france",
    "hello jarvis"
]

print("Testing language defaults (should all be in English):\n")

for query in test_queries:
    print(f"Query: {query}")
    try:
        response = ask(query)
        # Check if response contains Tamil characters (\u0b80-\u0bff)
        has_tamil = any('\u0b80' <= char <= '\u0bff' for char in response)
        print(f"Language: {'Tamil' if has_tamil else 'English'}")
        print(f"Response: {response[:100]}...\n" if len(response) > 100 else f"Response: {response}\n")
    except Exception as e:
        print(f"Error: {e}\n")
