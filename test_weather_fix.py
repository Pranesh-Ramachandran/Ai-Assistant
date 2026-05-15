"""
Test script to verify weather query fix
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

# Test weather queries
test_queries = [
    "what's weather today",
    "how is the weather",
    "what weather outside",
    "temperature now",
    "will it rain today",
    "weather forecast tomorrow",
]

print("Testing weather query fix...")
print("-" * 60)

for query in test_queries:
    print(f"\nQuery: {query}")
    response = ask(query)
    print(f"Response: {response}")
    
    # Check if response looks like weather data
    weather_keywords = ["temperature", "rain", "cloud", "wind", "sunny", "clear", "°", "partly", "weather", "celsius", "fahrenheit"]
    has_weather = any(kw in response.lower() for kw in weather_keywords)
    status = "✓ Weather data" if has_weather else "✗ Generic response"
    print(f"Status: {status}")
    print("-" * 60)
