#!/usr/bin/env python3
"""Debug Groq fallback handler."""
import os
os.environ["JARVIS_AI_MODE"] = "hybrid"

import jarvis_ai_brain as brain

# Monkey-patch _call_groq to add logging
original_call_groq = brain._call_groq
def debug_call_groq(messages, strict=False):
    print(f"[DEBUG_GROQ] Called")
    result = original_call_groq(messages, strict)
    print(f"[DEBUG_GROQ] Raw result: {repr(result[:100] if result else result)}")
    return result
brain._call_groq = debug_call_groq

# Test
from jarvis_ai_brain import ask
result = ask("tell me the news")
print(f"\nFinal result: {repr(result[:100])}")
