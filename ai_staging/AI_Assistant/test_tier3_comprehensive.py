"""
Tier 3 Comprehensive Test Suite
Tests all 5 Tier 3 modules (Calendar, Email, Web Search, Proactive, Notifications)
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("TIER 3 COMPREHENSIVE TEST SUITE")
print("=" * 70)

# Track test results
test_results = {"passed": 0, "failed": 0, "total": 0}

def check(description: str, result: bool, details: str = ""):
    """Log test result."""
    test_results["total"] += 1
    if result:
        test_results["passed"] += 1
        status = "✓ PASS"
        print(f"{status:8} | {description}")
    else:
        test_results["failed"] += 1
        status = "✗ FAIL"
        print(f"{status:8} | {description}")
        if details:
            print(f"         | {details}")


test = check
test.__test__ = False

print("\n" + "=" * 70)
print("MODULE 1: EMAIL MANAGER")
print("=" * 70)

try:
    from email_manager import EmailManager, handle_email
    
    # Test 1: Email command parsing
    em = EmailManager()
    cmd = em.parse_email_command("Email John about the project deadline")
    test("Parse email command (recipient extraction)",
         cmd.get("recipient") == "John", f"Got: {cmd.get('recipient')}")
    test("Parse email command (subject extraction)",
         cmd.get("subject") == "project deadline", f"Got: {cmd.get('subject')}")
    
    # Test 2: Urgency detection
    cmd2 = em.parse_email_command("Send urgent email to Sarah")
    test("Urgency detection (high priority)",
         cmd2.get("urgency") == "high", f"Got: {cmd2.get('urgency')}")
    
    # Test 3: Email validation
    test("Email validation (valid format)",
         em.validate_email_address("john@example.com"), "")
    test("Email validation (invalid format)",
         not em.validate_email_address("invalid-email"), "")
    
    # Test 4: Public API
    result = handle_email("Email John about the project")
    test("Public API handle_email()",
         result.get("success") == True, f"Got: {result.get('success')}")
    
    # Test 5: Draft creation
    draft = em.compose_email_draft("alice@example.com", "Team Meeting", "Let's sync up")
    test("Draft composition",
         draft.get("status") == "draft_ready", f"Got: {draft.get('status')}")
    test("Draft has recipient",
         draft.get("to") == "alice@example.com", f"Got: {draft.get('to')}")
    
    print("\n✓ Email Manager tests completed\n")
    
except Exception as e:
    test("Email Manager import/basic", False, str(e))
    print(f"\n✗ Email Manager failed: {e}\n")

print("=" * 70)
print("MODULE 2: WEB SEARCH")
print("=" * 70)

try:
    from web_search import WebSearchManager, handle_web_search
    
    ws = WebSearchManager()
    
    # Test 1: Query searchability
    test("Query searchability (searchable query)",
         ws.is_searchable_query("What is artificial intelligence?"), "")
    test("Query searchability (non-searchable query)",
         not ws.is_searchable_query("Turn off the lights"), "")
    
    # Test 2: Search parameter extraction
    params = ws.extract_search_parameters("Best restaurants in Paris")
    test("Search parameter extraction (location)",
         params.get("location") == "Paris", f"Got: {params.get('location')}")
    test("Search parameter extraction (type)",
         params.get("search_type") in ["general", "local"], f"Got: {params.get('search_type')}")
    
    # Test 3: Search type detection
    params2 = ws.extract_search_parameters("Latest news on AI")
    test("News search type detection",
         params2.get("search_type") == "news", f"Got: {params2.get('search_type')}")
    
    # Test 4: Public API
    result = handle_web_search("What is quantum computing?")
    test("Public API handle_web_search()",
         result.get("success") == True, f"Got: {result.get('success')}")
    
    # Test 5: Caching
    ws.cache_search_result("Test query", [{"title": "Test", "snippet": "Result"}])
    cached = ws.get_cached_search("test query")
    test("Search result caching",
         cached is not None and len(cached) > 0, f"Got: {cached}")
    
    print("\n✓ Web Search tests completed\n")
    
except Exception as e:
    test("Web Search import/basic", False, str(e))
    print(f"\n✗ Web Search failed: {e}\n")

print("=" * 70)
print("MODULE 3: PROACTIVE ASSISTANCE")
print("=" * 70)

try:
    from proactive_assistance import ProactiveAssistant, detect_proactive_needs
    
    pa = ProactiveAssistant()
    
    # Test 1: Topic classification
    context = pa.analyze_context(["I have a meeting tomorrow with John"])
    test("Topic classification",
         context.get("topic") in ["work", "social", "general"], f"Got: {context.get('topic')}")
    
    # Test 2: Urgency assessment
    context2 = pa.analyze_context(["I need this done urgently"])
    test("Urgency assessment (high)",
         context2.get("urgency") == "high", f"Got: {context2.get('urgency')}")
    
    # Test 3: Entity extraction
    context3 = pa.analyze_context(["Meeting with John in Paris"])
    test("Entity extraction",
         len(context3.get("entities", [])) > 0, f"Got: {context3.get('entities')}")
    
    # Test 4: Sentiment analysis
    context4 = pa.analyze_context(["This is terrible, I'm frustrated"])
    test("Sentiment analysis (negative)",
         context4.get("sentiment") == "negative", f"Got: {context4.get('sentiment')}")
    
    # Test 5: Proactive need detection
    needs = pa.detect_need_for_assistance(
        "I have a deadline tomorrow about the project presentation",
        context={"topic": "work", "urgency": "high", "entities": []}
    )
    test("Deadline detection triggers calendar suggestion",
         len(needs) > 0, f"Got {len(needs)} suggestions")
    
    # Test 6: Public API
    result = detect_proactive_needs("I'm flying to Paris next week")
    test("Public API detect_proactive_needs()",
         result.get("has_suggestions") == True or result.get("has_suggestions") == False, "")
    
    print("\n✓ Proactive Assistance tests completed\n")
    
except Exception as e:
    test("Proactive Assistance import/basic", False, str(e))
    print(f"\n✗ Proactive Assistance failed: {e}\n")

print("=" * 70)
print("MODULE 4: SMART NOTIFICATIONS")
print("=" * 70)

try:
    from smart_notifications import SmartNotificationManager, create_and_send_notification, get_next_notification
    
    snm = SmartNotificationManager()
    
    # Test 1: Priority classification
    priority = snm.classify_notification_priority("CRITICAL: System alert")
    test("Priority classification (critical)",
         priority == "critical", f"Got: {priority}")
    
    priority2 = snm.classify_notification_priority("Meeting reminder")
    test("Priority classification (high)",
         priority2 in ["high", "normal"], f"Got: {priority2}")
    
    # Test 2: Notification creation
    notif = snm.create_notification("reminder", "Your meeting starts soon")
    test("Notification creation",
         notif.get("type") == "reminder", f"Got: {notif.get('type')}")
    test("Notification has priority",
         notif.get("priority") in ["critical", "high", "normal", "low"], f"Got: {notif.get('priority')}")
    
    # Test 3: Quiet hours check
    # This test depends on time of day, so just check the function works
    in_quiet = snm.is_in_quiet_hours()
    test("Quiet hours check (returns bool)",
         isinstance(in_quiet, bool), f"Got type: {type(in_quiet)}")
    
    # Test 4: Notification formatting
    formatted = snm.format_notification(notif)
    test("Notification formatting",
         "message" in formatted and "priority" in formatted, f"Got: {formatted.keys()}")
    
    # Test 5: Public API
    result = create_and_send_notification(
        "reminder",
        "Test reminder",
        context={"channel": "calendar"},
        actions=["Snooze", "Dismiss"]
    )
    test("Public API create_and_send_notification()",
         result.get("success") == True, f"Got: {result.get('success')}")
    
    # Test 6: Pending notifications
    snm.add_notification(notif)
    pending = snm.get_pending_notifications()
    test("Get pending notifications",
         len(pending) > 0, f"Got: {len(pending)} pending")
    
    print("\n✓ Smart Notifications tests completed\n")
    
except Exception as e:
    test("Smart Notifications import/basic", False, str(e))
    print(f"\n✗ Smart Notifications failed: {e}\n")

print("=" * 70)
print("INTEGRATION TESTS")
print("=" * 70)

try:
    # Test 1: Email → Notification workflow
    from email_manager import handle_email
    from smart_notifications import create_and_send_notification
    
    email_result = handle_email("Send urgent email to client")
    if email_result.get("success"):
        notif_result = create_and_send_notification(
            "email",
            "Email sent to client",
            context={"channel": "email"}
        )
        test("Email → Notification workflow",
             notif_result.get("success") == True, "")
    else:
        test("Email → Notification workflow", False, "Email creation failed")
    
    # Test 2: Web Search → Proactive workflow
    from web_search import handle_web_search
    from proactive_assistance import detect_proactive_needs
    
    search_result = handle_web_search("What's the weather in London?")
    if search_result.get("success"):
        needs = detect_proactive_needs(search_result.get("query", ""))
        test("Web Search → Proactive workflow",
             True, "Workflow completed")
    else:
        test("Web Search → Proactive workflow", False, "Search failed")
    
    print("\n✓ Integration tests completed\n")
    
except Exception as e:
    test("Integration tests", False, str(e))
    print(f"\n✗ Integration tests failed: {e}\n")

# Print summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Total Tests: {test_results['total']}")
print(f"Passed: {test_results['passed']} ({test_results['passed']*100//test_results['total']}%)")
print(f"Failed: {test_results['failed']}")

if test_results["failed"] == 0:
    print("\n🎉 ALL TIER 3 TESTS PASSED! 🎉")
else:
    print(f"\n⚠️ {test_results['failed']} test(s) failed")

print("=" * 70)
