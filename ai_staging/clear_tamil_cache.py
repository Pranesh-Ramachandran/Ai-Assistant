#!/usr/bin/env python3
"""
Clear cached responses that are in Tamil language to fix stale data.
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
    
    # Get all cached responses
    cursor.execute("SELECT rowid, response FROM cache")
    rows = cursor.fetchall()
    
    tamil_rows = []
    for rowid, response in rows:
        # Check if response contains Tamil characters
        has_tamil = any('\u0b80' <= char <= '\u0bff' for char in response)
        if has_tamil:
            tamil_rows.append(rowid)
    
    print(f"\nFound {len(tamil_rows)} cached responses in Tamil.")
    print("Deleting Tamil-language responses...")
    
    for rowid in tamil_rows:
        cursor.execute("DELETE FROM cache WHERE rowid = ?", (rowid,))
    
    conn.commit()
    print(f"✓ Deleted {len(tamil_rows)} Tamil cache entries")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM cache")
    remaining = cursor.fetchone()[0]
    print(f"✓ Remaining cache entries: {remaining}")
    
    conn.close()
    print("✓ Cache cleaned successfully!")
    
except sqlite3.OperationalError as e:
    print(f"Error (file locked): {e}")
    print("Please close any other Python processes and try again.")
except Exception as e:
    print(f"Error: {e}")
