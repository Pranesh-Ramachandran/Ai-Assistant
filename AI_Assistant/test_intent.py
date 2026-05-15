import sys
sys.path.insert(0, '.')
from intent_classifier import classify_query

tests = [
    "tell me a joke",
    "play some music",
    "what is the weather in Chennai",
    "what time is it",
    "set an alarm for 7am",
    "turn on the lights",
    "who is Elon Musk",
    "how are you",
]

for q in tests:
    r = classify_query(q)
    clarify = r.get("requires_clarification", False)
    cqs = r.get("clarification_questions", [])
    print(f"Q: {q}")
    print(f"  intent={r['intent']}, confidence={r['confidence']:.2f}, clarify={clarify}")
    if cqs:
        print(f"  questions={cqs}")
    print()
