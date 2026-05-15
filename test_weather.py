#!/usr/bin/env python3
"""
Test script for weather functionality in Jarvis AI
"""

import sys
sys.path.append('AI_Assistant')
from data_collector import get_weather

def test_weather_commands():
    """Test various weather command formats"""
    test_cases = [
        # Valid cases
        ("weather in london", "Current temperature in london:"),
        ("what's the temperature in paris", "Current temperature in paris:"),
        ("forecast for tokyo", "Current temperature in tokyo:"),
        ("weather in new york", "Current temperature in new york:"),

        # Edge cases
        ("weather", "Please specify a city name."),
        ("temperature", "Please specify a city name."),
        ("weather in", "Please specify a city name."),
    ]

    print("=== Testing Weather Commands ===")
    for command, expected_contains in test_cases:
        result = get_weather(command)
        status = "PASS" if expected_contains.lower() in result.lower() else "FAIL"
        print(f"{status}: '{command}' -> '{result}'")
        if expected_contains.lower() not in result.lower():
            print(f"      Expected to contain: '{expected_contains}'")

def test_integration():
    """Test integration with intent recognition"""
    print("\n=== Testing Integration ===")

    from jarvis_brain import JarvisBrain

    brain = JarvisBrain()

    test_commands = [
        "weather in london",
        "what's the temperature in paris",
        "forecast for tokyo",
        "weather in new york"
    ]

    for cmd in test_commands:
        intent = brain.analyze_intent(cmd)
        expected = "weather"
        status = "PASS" if intent == expected else "FAIL"
        print(f"{status}: '{cmd}' -> intent: {intent}")

if __name__ == "__main__":
    print("Starting thorough testing of weather functionality...\n")

    test_weather_commands()
    test_integration()

    print("\n=== Testing Complete ===")
    print("Weather functionality has been integrated into Jarvis AI.")
