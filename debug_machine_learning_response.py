"""
Debug script to trace why "what is machine learning" returns wrong answer
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import _try_rule, _offline_reply, ask

query = "what is machine learning"
print(f"Testing query: '{query}'")
print("=" * 70)

# Test 1: Check simple rules
print("\n[1] Simple rule matching:")
rule_result = _try_rule(query)
if rule_result:
    print(f"    ✗ MATCHED RULE: {rule_result}")
else:
    print(f"    ✓ No simple rule matched (good)")

# Test 2: Check offline fallback
print("\n[2] Offline fallback:")
offline_result = _offline_reply(query)
print(f"    Result: {offline_result}")

# Test 3: Full ask()
print("\n[3] Full ask() response:")
response = ask(query)
print(f"    Result: {response}")
print(f"    Length: {len(response)} chars")
print(f"    Has 'machine learning'? {('machine' in response.lower())}")
print(f"    Has 'bro'? {('bro' in response.lower())}")
print(f"    Has 'What do you need'? {('What do you need' in response)}")

print("\n" + "=" * 70)
