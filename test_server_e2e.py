#!/usr/bin/env python3
"""
End-to-end test of JARVIS server with Tier 1 + Tier 2 features
Tests by directly calling the ask() function from jarvis_ai_brain
"""

import sys
sys.path.insert(0, 'd:/ai/AI_Assistant')

from jarvis_ai_brain import ask

# Color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def test_query(description, query):
    """Test a query through the server"""
    print(f"\n{YELLOW}[USER]{RESET} {description}")
    print(f"  Query: \"{query}\"")
    response = ask(query)
    print(f"{BLUE}[JARVIS]{RESET}")
    if response:
        # Print first 200 chars for readability
        print(f"  Response: {response[:200]}{'...' if len(response) > 200 else ''}")
    else:
        print(f"  Response: (empty)")
    return response

print(f"\n{BLUE}{'='*70}")
print(f"  END-TO-END SERVER TEST: Tier 1 + Tier 2 Features")
print(f"{'='*70}{RESET}\n")

# ─────────────────────────────────────────────────────────────────────────────
print(f"{BLUE}Scenario 1: Simple greeting with personalization{RESET}")
test_query("User introduces themselves", "Hi, my name is Alex")
test_query("Follow-up greeting", "How are you?")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 2: Time-aware execution{RESET}")
test_query("Time-aware request", "Set a reminder in 5 minutes to check email")
test_query("Scheduled action", "Book a meeting tomorrow at 2 PM")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 3: Intent classification{RESET}")
test_query("Question intent", "What is the capital of India?")
test_query("Request intent", "Play some relaxing music")
test_query("Information intent", "Tell me about Python programming")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 4: Follow-up handling{RESET}")
test_query("Initial location query", "What's the weather in Chennai?")
test_query("Follow-up with continuation", "And in Bangalore?")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 5: Query rephrasing{RESET}")
test_query("Ambiguous query", "How much?")
test_query("Vague reference", "Is it good?")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 6: Multi-turn conversation{RESET}")
test_query("First question", "What's trending today?")
test_query("Follow-up question", "Can you tell me more?")
test_query("Third turn", "Are these reliable?")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 7: Location preference{RESET}")
test_query("Provide location", "I'm from Kerala")
test_query("Location-based query", "What's the weather here?")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLUE}Scenario 8: Error handling{RESET}")
test_query("Handle unknown query", "Zibberish qwerty asdf xyz")
test_query("Handle empty response", "")

print(f"\n{BLUE}{'='*70}")
print(f"  ✓ End-to-end server test complete")
print(f"{'='*70}{RESET}\n")
