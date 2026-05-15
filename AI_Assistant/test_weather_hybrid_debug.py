#!/usr/bin/env python3
"""Debug weather in hybrid mode with detailed traces."""
import sys
import os
os.environ["JARVIS_AI_MODE"] = "hybrid"

import jarvis_ai_brain as brain

# Monkey-patch _clean_response to see what's being cleaned
original_clean = brain._clean_response
def debug_clean(text):
    print(f"[DEBUG] _clean_response INPUT: {repr(text[:200] if text else text)}")
    result = original_clean(text)
    print(f"[DEBUG] _clean_response OUTPUT: {repr(result[:200] if result else result)}")
    return result
brain._clean_response = debug_clean

# Monkey patch _call_groq to see raw response
original_call_groq = brain._call_groq
def debug_call_groq(messages, strict=False):
    print(f"[DEBUG] _call_groq called with {len(messages)} messages")
    result = original_call_groq(messages, strict)
    print(f"[DEBUG] _call_groq returned: {repr(result[:200] if result else result)}")
    return result
brain._call_groq = debug_call_groq

print("Testing: 'what is the weather'")
result = brain.ask('what is the weather')
print(f"\nFinal result: {repr(result)}")
