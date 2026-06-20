#!/usr/bin/env python3
"""
Debug script - Test each component individually
"""
import sys
import os

print("[1] Python version:", sys.version)
print("[2] Working directory:", os.getcwd())

print("\n[3] Adding to path...")
sys.path.insert(0, os.path.join(os.getcwd(), 'AI_Assistant'))
print("    ✅ Path updated")

print("\n[4] Importing jarvis_ai_brain...")
try:
    from jarvis_ai_brain import ask
    print("    ✅ Import successful")
except Exception as e:
    print(f"    ❌ Import failed: {e}")
    sys.exit(1)

print("\n[5] Testing ask() function...")
print("    Calling ask('hi')...")
import time
start = time.time()

# This should timeout or return quickly
result = ask("hi")

elapsed = time.time() - start
print(f"    ✅ Response received in {elapsed:.2f}s")
print(f"    Result: {result[:100]}")
