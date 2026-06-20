#!/usr/bin/env python3
"""Test cleaning function directly."""
import os
os.environ['JARVIS_AI_MODE'] = 'hybrid'

from jarvis_ai_brain import _clean_response

test_cases = [
    'get_news>{"category": "world"}',
    'I am fine. get_information>{"query": "photosynthesis"}',
    'I am okay. <function=get_time></function>',
    'Top news: get_information>{"query": "latest news"}',
]

for test in test_cases:
    result = _clean_response(test)
    print(f'Input:  {repr(test[:60])}')
    print(f'Output: {repr(result[:60])}')
    print(f'Match: {"✓" if result != test else "✗"}')
    print()
