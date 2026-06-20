#!/usr/bin/env python3
"""Clear cached Tamil responses."""
import os
import sys
import time

cache_file = os.path.abspath('jarvis_cache.db')
print(f"Target cache file: {cache_file}")

# Try multiple times with delays
for attempt in range(5):
    try:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"✓ Cache cleared on attempt {attempt + 1}")
            sys.exit(0)
        else:
            print("Cache file not found")
            sys.exit(0)
    except PermissionError:
        print(f"Attempt {attempt + 1}: File is locked, waiting...")
        time.sleep(2)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)

print("Failed to clear cache after multiple attempts")
sys.exit(1)
