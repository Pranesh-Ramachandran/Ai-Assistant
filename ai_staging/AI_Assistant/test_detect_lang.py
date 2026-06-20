#!/usr/bin/env python3
"""Debug language detection."""
import os
os.environ["JARVIS_AI_MODE"] = "hybrid"

from tamil_ai import detect_language

test_queries = [
    "tell me somethingabout the moon",
    "what is pi",
    "hello jarvis",
    "news today",
    "திறையொறிய பூமி கூறு",  # Tamil query
]

for q in test_queries:
    lang = detect_language(q)
    print(f"Query: {q[:40]}")
    print(f"Detected language: {lang}")
    print(f"JARVIS_STT_LANG: {os.getenv('JARVIS_STT_LANG', 'not set')}")
    print()
