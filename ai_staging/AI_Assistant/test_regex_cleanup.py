#!/usr/bin/env python3
"""Debug cleaning function."""
import re

test_strings = [
    'get_news>{"category": "world"}',
    '<function=get_time></function>',
    'I\'m okay. <function=get_time></function>',
    'Tell me about photosynthesis via get_information>{"query": "photosynthesis"}',
]

def debug_clean(text):
    """Test pattern against string."""
    print(f"Original: {repr(text)}")
    
    # Test 1: function_name>json pattern
    result = re.sub(r'\b(?:get_weather|get_information|get_news|get_time|set_alarm|control_light|call_sms|play_game)\s*>\s*\{[^}]*\}', 'REMOVED', text, flags=re.IGNORECASE)
    print(f"After pattern 1: {repr(result)}")
    
    # Test 2: Simpler pattern without word boundary
    result2 = re.sub(r'(?:get_weather|get_information|get_news|get_time|set_alarm|control_light|call_sms|play_game)\s*>\s*\{[^}]*\}', 'REMOVED', text, flags=re.IGNORECASE)
    print(f"After pattern 2 (no \\b): {repr(result2)}")
    
    print()

for s in test_strings:
    debug_clean(s)
