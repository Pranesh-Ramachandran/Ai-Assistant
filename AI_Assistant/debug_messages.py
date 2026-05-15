#!/usr/bin/env python3
"""Debug messages sent to LLM."""
import os
os.environ["JARVIS_AI_MODE"] = "hybrid"

import jarvis_ai_brain as brain

# Monkey-patch _call_groq to see messages
original_call_groq = brain._call_groq
def debug_call_groq(messages, strict=False):
    print(f"[GROQ] Sending {len(messages)} messages")
    for i, msg in enumerate(messages[:3]):  # Show first 3 messages
        content_preview = (msg.get("content") or "")[:80]
        print(f"  [{i}] role={msg.get('role')}, content={repr(content_preview)}")
    result = original_call_groq(messages, strict)
    return result
brain._call_groq = debug_call_groq

# Test
from jarvis_ai_brain import ask
print("Testing: 'what is pi'\n")
result = ask("what is pi")
print(f"Result: {result[:100]}")
