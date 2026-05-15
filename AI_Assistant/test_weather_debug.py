#!/usr/bin/env python3
"""Debug weather query issue."""
import sys
import os

# Test offline first
os.environ["JARVIS_AI_MODE"] = "offline"

from jarvis_ai_brain import ask, _offline_reply, _execute_tool_locally

print("=" * 60)
print("Testing offline weather path")
print("=" * 60)

# Test local execution
local_result = _execute_tool_locally('weather today')
print(f"_execute_tool_locally('weather today'): {repr(local_result)}")

# Test offline reply directly
offline = _offline_reply('weather today')
print(f"_offline_reply('weather today'): {repr(offline)}")

# Test through ask
result = ask('weather today')
print(f"ask('weather today'): {repr(result)}")

print("\n" + "=" * 60)
print("Testing direct tool execution")
print("=" * 60)

from data_collector import get_weather
weather = get_weather('weather in Tamil Nadu')
print(f"get_weather('weather in Tamil Nadu'): {repr(weather)}")

from jarvis_ai_brain import _execute_tool
tool_result = _execute_tool("get_weather", {"location": "Tamil Nadu"})
print(f"_execute_tool('get_weather', {{'location': 'Tamil Nadu'}}): {repr(tool_result)}")
