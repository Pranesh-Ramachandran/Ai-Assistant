#!/usr/bin/env python3
"""
Debug the exact response format and test pattern matching
"""
import sys
import os
import re

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

test_query = "what's the weather today in kerala"

print(f"Testing query: {test_query}\n")

response = ask(test_query)
print(f"Raw response: {repr(response)}")
print(f"Response length: {len(response)}")
print(f"Response str: '{response}'")

# Test the pattern
pattern = r'^([a-z_]+)\s*(\{.+\})$'
match = re.match(pattern, response)

print(f"\nPattern: {pattern}")
print(f"Match result: {match}")

if match:
    print(f"Function name: {match.group(1)}")
    print(f"JSON string: {match.group(2)}")
else:
    print("No match")
    
    # Try simpler patterns to debug
    print("\n--- Testing simpler patterns ---")
    print(f"Starts with 'get_': {response.startswith('get_')}")
    print(f"Contains '{{': {'{' in response}")
    print(f"Ends with '}}': {response.endswith('}')}")
    
    # Try to find where the pattern breaks
    import json
    try:
        # Try to extract JSON from end
        start_idx = response.find('{')
        if start_idx >= 0:
            json_str = response[start_idx:]
            print(f"\nExtracted JSON: {json_str}")
            parsed = json.loads(json_str)
            print(f"Parsed JSON: {parsed}")
    except Exception as e:
        print(f"JSON parsing error: {e}")
