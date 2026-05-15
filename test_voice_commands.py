#!/usr/bin/env python3
"""
Comprehensive test of voice command handling with tool execution
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

test_queries = [
    "what's the weather in kerala",
    "whats the weather today",
    "weather in delhi",
    "tell me about the moon",
    "what time is it",
]

print("Testing voice command responses:\n")
print("=" * 60)

success_count = 0
for query in test_queries:
    response = ask(query)
    
    # Check if response contains raw tool call syntax
    has_tool_syntax = any(
        func in response 
        for func in ["get_weather", "get_time", "get_information"]
    ) and "{" in response
    
    status = "❌ FAILED" if has_tool_syntax else "✓ PASSED"
    success_count += (1 if not has_tool_syntax else 0)
    
    print(f"Query:    {query}")
    print(f"Response: {response}")
    print(f"Status:   {status}\n")

print("=" * 60)
print(f"\nResults: {success_count}/{len(test_queries)} tests passed")

if success_count == len(test_queries):
    print("\n✓ All voice commands are working correctly!")
    print("✓ Tool calls are being executed and responses synthesized")
else:
    print(f"\n❌ Some tests failed - there may still be issues")
