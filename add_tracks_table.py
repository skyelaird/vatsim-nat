"""
Add NAT OTS tracks table to existing database
Run once: python add_tracks_table.py
"""
import sqlite3

conn = sqlite3.connect('D:\\GitHub\\vatsim-nat\\nat_traffic.db')
cursor = conn.cursor()

# Read and execute schema
with open('D:\\GitHub\\vatsim-nat\\schema_tracks.sql', 'r') as f:
    cursor.executescript(f.read())

conn.commit()

# Verify table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nat_ots_tracks'")
if cursor.fetchone():
    print("✓ Table nat_ots_tracks created successfully")
    
    # Show schema
    cursor.execute("PRAGMA table_info(nat_ots_tracks)")
    print("\nTable schema:")
    for row in cursor.fetchall():
        print(f"  {row[1]:20s} {row[2]}")
else:
    print("✗ Table creation failed")

conn.close()
