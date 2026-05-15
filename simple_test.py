#!/usr/bin/env python3
import sys, os
print("[1] Starting", flush=True)
sys.path.insert(0, os.path.join(os.getcwd(), 'AI_Assistant'))
print("[2] Path added", flush=True)

from jarvis_ai_brain import ask
print("[3] Import complete", flush=True)

print("[4] Calling ask('test')...", flush=True)
result = ask("test")
print("[5] ask() returned:", result[:50], flush=True)
