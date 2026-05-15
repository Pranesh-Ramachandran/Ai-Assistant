"""
Test script to verify novel/unknown query handling
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

from jarvis_ai_brain import ask

# Test novel queries that aren't covered by built-in tools
test_queries = [
    "what is machine learning",
    "how do solar panels work",
    "why is the sky blue",
    "what's the capital of france",
    "explain quantum computing",
    "what are the benefits of exercise",
    "how does photosynthesis work",
]

print("Testing novel/unknown query handling...")
print("=" * 70)

for query in test_queries:
    print(f"\n📝 Query: {query}")
    response = ask(query)
    print(f"📢 Response: {response}")
    
    # Check quality
    is_good = len(response) > 15 and any(p in response.lower() for p in ("because", "is", "can", "means", "through", "by"))
    status = "✓ Good answer" if is_good else "⚠ Short/vague answer"
    print(f"   {status}")
    print("-" * 70)
