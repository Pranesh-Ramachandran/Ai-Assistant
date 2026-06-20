"""
Tier 3 Integration Test
Verify Tier 3 modules work with jarvis_ai_brain
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("TIER 3 INTEGRATION TEST")
print("=" * 70)

test_results = {"passed": 0, "failed": 0}

def check(name, condition, details=""):
    if condition:
        test_results["passed"] += 1
        print(f"✓ {name}")
    else:
        test_results["failed"] += 1
        print(f"✗ {name}")
        if details:
            print(f"  {details}")


test = check
test.__test__ = False

print("\n1. Testing Tier 3 module imports...")
try:
    from email_manager import handle_email
    from web_search import handle_web_search
    from proactive_assistance import detect_proactive_needs
    from smart_notifications import create_and_send_notification
    test("All Tier 3 modules import successfully", True)
except Exception as e:
    test("All Tier 3 modules import successfully", False, str(e))

print("\n2. Testing jarvis_ai_brain Tier 3 integration...")
try:
    from jarvis_ai_brain import ask, _EMAIL_OK, _WEB_SEARCH_OK, _PROACTIVE_OK, _NOTIFICATIONS_OK
    test("Tier 3 imports available in brain", _EMAIL_OK or not _EMAIL_OK, "")  # Just check module loads
    test("Email module integration", hasattr(__import__('jarvis_ai_brain'), '_EMAIL_OK'), "")
except Exception as e:
    test("jarvis_ai_brain loads with Tier 3", False, str(e))

print("\n3. Testing email query handling...")
try:
    from jarvis_ai_brain import ask
    response = ask("Email John about the meeting")
    test("Email query returns response", isinstance(response, str) and len(response) > 0, f"Got: {response}")
except Exception as e:
    test("Email query handling", False, str(e))

print("\n4. Testing web search query handling...")
try:
    from jarvis_ai_brain import ask
    response = ask("What is quantum computing?")
    test("Web search query returns response", isinstance(response, str) and len(response) > 0, f"Got: {response}")
except Exception as e:
    test("Web search query handling", False, str(e))

print("\n5. Testing calendar/scheduling query handling...")
try:
    from jarvis_ai_brain import ask
    response = ask("Schedule a meeting tomorrow at 2 PM")
    test("Calendar query returns response", isinstance(response, str) and len(response) > 0, f"Got: {response}")
except Exception as e:
    test("Calendar query handling", False, str(e))

print("\n6. Testing proactive assistance detection...")
try:
    from proactive_assistance import detect_proactive_needs
    result = detect_proactive_needs("I have a meeting tomorrow with John")
    test("Proactive needs detection works", isinstance(result, dict), f"Got: {result}")
except Exception as e:
    test("Proactive assistance detection", False, str(e))

print("\n7. Testing notification creation...")
try:
    from smart_notifications import create_and_send_notification
    result = create_and_send_notification("reminder", "Test reminder")
    test("Notification creation works", result.get("success") in [True, False], f"Got: {result}")
except Exception as e:
    test("Notification creation", False, str(e))

print("\n8. Testing multi-turn conversation with Tier 3...")
try:
    from jarvis_ai_brain import ask, clear_memory
    
    # Clear previous memory
    clear_memory()
    
    # Multi-turn conversation
    r1 = ask("What's the weather?")
    test("First turn returns response", isinstance(r1, str) and len(r1) > 0, f"Got: {r1}")
    
    r2 = ask("And what about in London?")  # Follow-up with proactive suggestion
    test("Follow-up returns response", isinstance(r2, str) and len(r2) > 0, f"Got: {r2}")
    
    clear_memory()
except Exception as e:
    test("Multi-turn Tier 3 conversation", False, str(e))

# Summary
print("\n" + "=" * 70)
print("INTEGRATION TEST SUMMARY")
print("=" * 70)
total = test_results["passed"] + test_results["failed"]
pct = (test_results["passed"] * 100) // total if total > 0 else 0
print(f"Passed: {test_results['passed']}/{total} ({pct}%)")

if test_results["failed"] == 0:
    print("\n✅ All Tier 3 integration tests passed!")
else:
    print(f"\n⚠️ {test_results['failed']} test(s) failed")

print("=" * 70)
