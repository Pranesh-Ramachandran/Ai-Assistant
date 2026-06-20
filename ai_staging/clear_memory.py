#!/usr/bin/env python3
"""
Clear conversation memory
"""
import sys
import os

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import _MEMORY

print("Clearing conversation memory...")
_MEMORY.clear()
print("✓ Conversation memory cleared!")
