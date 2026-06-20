#!/usr/bin/env python3
"""Test language handling."""
from jarvis_ai_brain import ask

queries = [
    'tell me something about the moon',
    'what is pi',
    'hello jarvis',
]

for q in queries:
    result = ask(q)
    # Check if response contains Tamil script
    is_tamil = any('\u0b80' <= ch <= '\u0bff' for ch in result)
    lang_label = "Tamil" if is_tamil else "English"
    print(f'Q: {q}')
    print(f'A: {result[:100]}')
    print(f'Language: {lang_label}')
    print()
