#!/usr/bin/env python3
"""Debug where tool call leaks are coming from."""
import os
os.environ["JARVIS_AI_MODE"] = "hybrid"

import jarvis_ai_brain as brain

# Monkey-patch to trace execution
original_clean = brain._clean_response
def debug_clean(text):
    result = original_clean(text)
    if result != text:
        print(f"[CLEAN] Changed: {repr(text[:50])} → {repr(result[:50])}")
    else:
        print(f"[CLEAN] No change: {repr(text[:50])}")
    return result
brain._clean_response = debug_clean

original_ask = brain.ask
def debug_ask(user_input, **kw):
    print(f"\n=== ask('{user_input}') ===")
    result = original_ask(user_input, **kw)
    print(f"Final result: {repr(result[:80])}")
    return result
brain.ask = debug_ask

# Test
from jarvis_ai_brain import ask
result = ask("tell me the news")
print(f"\nResult: {result[:80]}")
