#!/usr/bin/env python3
"""
Direct LLM Testing - Bypass server, test ask() directly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask
import time

print("=" * 60)
print("JARVIS LLM Direct Test")
print("=" * 60)

# Test 1: Simple greeting
print("\n[TEST 1] Simple greeting...")
start = time.time()
try:
    result = ask("hello")
    elapsed = time.time() - start
    print(f"✅ Response ({elapsed:.2f}s):")
    print(f"   {result[:100]}...")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Question
print("\n[TEST 2] Simple question...")
start = time.time()
try:
    result = ask("what is 2+2?")
    elapsed = time.time() - start
    print(f"✅ Response ({elapsed:.2f}s):")
    print(f"   {result[:100]}...")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test completed")
