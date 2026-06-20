#!/usr/bin/env python3
"""
Debug script to check:
1. What language detect_language returns
2. If responses are being cached
3. What messages are sent to LLM
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from tamil_ai import detect_language
from jarvis_cache import get as cache_get

test_queries = [
    "what is pi",
    "what is the capital of france",
    "tell me something about the moon"
]

print("Detecting language and checking cache:\n")

for query in test_queries:
    detected = detect_language(query)
    cached = cache_get(query)
    print(f"Query: {query}")
    print(f"  Detected Language: {detected}")
    print(f"  Cached: {'Yes' if cached else 'No'}")
    if cached:
        has_tamil = any('\u0b80' <= char <= '\u0bff' for char in cached)
        print(f"  Cached response is in: {'Tamil' if has_tamil else 'English'}")
    print()
