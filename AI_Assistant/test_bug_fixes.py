"""
Full integration test — verify all 5 bug fixes.
"""
import sys, time
sys.path.insert(0, '.')

# ── Bug 2: Intent classifier no longer over-clarifies ─────────────────────────
print("=" * 60)
print("BUG 2 — Intent classifier clarification check")
print("=" * 60)
from intent_classifier import classify_query

cases = {
    "tell me a joke":               False,
    "play some music":              False,
    "who is Elon Musk":             False,
    "what time is it":              False,
    "set an alarm for 7am":         False,
    "turn on the lights":           False,
    "how are you":                  False,
    "what is the weather in Delhi": False,
    "X":                            True,   # genuinely ambiguous single char
}

all_pass = True
for q, expect_clarify in cases.items():
    r = classify_query(q)
    got = r["requires_clarification"]
    status = "PASS" if got == expect_clarify else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] '{q}' → clarify={got} (expected {expect_clarify}), intent={r['intent']}")

print("Result:", "ALL PASS ✓" if all_pass else "SOME FAILED ✗")
print()

# ── Bug 3: _pending_schedule module-level init ─────────────────────────────────
print("=" * 60)
print("BUG 3 — _pending_schedule module-level init")
print("=" * 60)
import jarvis_ai_brain as brain
try:
    val = brain._pending_schedule
    print(f"  [PASS] _pending_schedule = {val}")
except AttributeError:
    print("  [FAIL] _pending_schedule not defined at module level")
print()

# ── Bug 1 + 4 + 5: Full ask() integration test ────────────────────────────────
print("=" * 60)
print("BUGS 1,4,5 — Full ask() integration test")
print("=" * 60)
tests = [
    ("hello",                            lambda r: "jarvis" in r.lower() or "hello" in r.lower() or "what do you need" in r.lower()),
    ("what time is it",                  lambda r: ":" in r or "am" in r.lower() or "pm" in r.lower()),
    ("tell me a joke",                   lambda r: "function=" not in r.lower() and len(r) > 5),
    ("what is artificial intelligence",  lambda r: "function=" not in r.lower() and len(r) > 20),
    ("what is the weather in Chennai",   lambda r: "function=" not in r.lower()),
]

for q, check in tests:
    t0 = time.perf_counter()
    r = brain.ask(q)
    elapsed = time.perf_counter() - t0
    ok = check(r)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] ({elapsed:.2f}s) Q: {q}")
    print(f"         A: {r[:100]}")
    print()
