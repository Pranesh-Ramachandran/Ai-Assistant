#!/usr/bin/env python3
"""
Test voice command weather query to verify the fix
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

test_query = "what's the weather today in kerala"

print(f"Testing query: {test_query}\n")

try:
    response = ask(test_query)
    print(f"Response: {response}\n")
    
    # Check if we got a proper response (not just the tool call)
    if "get_weather" in response and "{" in response:
        print("❌ FAILED - Still returning tool call syntax instead of actual weather")
    else:
        print("✓ SUCCESS - Got actual weather response (not tool syntax)")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
