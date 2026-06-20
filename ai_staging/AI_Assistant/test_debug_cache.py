#!/usr/bin/env python3
"""Debug where response is coming from."""
import os
os.environ["JARVIS_AI_MODE"] = "hybrid"

import jarvis_ai_brain as brain

# Monkey-patch cache
original_cache_get = brain.cache_get
def debug_cache_get(key):
    result = original_cache_get(key)
    if result:
        print(f"[CACHE_HIT] {repr(key[:40])}: {repr(result[:50])}")
    return result
brain.cache_get = debug_cache_get

# Monkey-patch ask
original_ask = brain.ask
def debug_ask(text, **kw):
    print(f"\n[ASK] Query: {repr(text)}")
    result = original_ask(text, **kw)
    print(f"[ASK] Result: {repr(result[:80])}")
    return result
brain.ask = debug_ask

# Test
from jarvis_ai_brain import ask
ask("tell me the news")
