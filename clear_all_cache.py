#!/usr/bin/env python3
"""
Clear all cache entries to force fresh LLM responses
"""
import sys
import os
import sqlite3

# Add AI_Assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

db_path = os.path.join(os.path.dirname(__file__), 'AI_Assistant', 'jarvis_cache.db')

if not os.path.exists(db_path):
    print(f"Cache file not found: {db_path}")
    sys.exit(1)

print(f"Opening cache database: {db_path}")

try:
    conn = sqlite3.connect(db_path, timeout=10.0)
    cursor = conn.cursor()
    
    # Get count of all entries
    cursor.execute("SELECT COUNT(*) FROM cache")
    count = cursor.fetchone()[0]
    
    # Delete all entries
    cursor.execute("DELETE FROM cache")
    conn.commit()
    
    print(f"✓ Deleted {count} cache entries")
    print("✓ Cache cleared successfully!")
    print("\nNext time you ask a query, you'll get a fresh response from the LLM.")
    
    conn.close()
    
except sqlite3.OperationalError as e:
    print(f"Error (file locked): {e}")
    print("Please close any other Python processes and try again.")
except Exception as e:
    print(f"Error: {e}")
