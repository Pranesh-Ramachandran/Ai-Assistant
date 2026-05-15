#!/usr/bin/env python3
"""
Trace where the response is coming from
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

# Patch the ask function to add logging
import jarvis_ai_brain

original_ask = jarvis_ai_brain.ask
original_cache_get = jarvis_ai_brain.cache_get
original_call_groq = jarvis_ai_brain._call_groq
original_call_gemini = jarvis_ai_brain._call_gemini

def logged_cache_get(text):
    result = original_cache_get(text)
    if result:
        print(f"[TRACE] Cache HIT: {text[:50]}...")
    return result

def logged_call_groq(messages, strict):
    print(f"[TRACE] Calling Groq with {len(messages)} messages")
    result = original_call_groq(messages, strict)
    print(f"[TRACE] Groq returned: {result[:80]}...")
    return result

def logged_call_gemini(messages):
    print(f"[TRACE] Calling Gemini")
    result = original_call_gemini(messages)
    if result:
        print(f"[TRACE] Gemini returned: {result[:80]}...")
    else:
        print(f"[TRACE] Gemini returned None")
    return result

jarvis_ai_brain.cache_get = logged_cache_get
jarvis_ai_brain._call_groq = logged_call_groq
jarvis_ai_brain._call_gemini = logged_call_gemini

test_query = "what's the weather today in kerala"

print(f"Testing query: {test_query}\n")

response = original_ask(test_query)
print(f"\n[RESULT] Final response: {response}\n")
