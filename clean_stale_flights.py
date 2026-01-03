"""
Clean stale NAT crossings from database
Marks flights as exited if they haven't been updated in >30 minutes
"""
import sqlite3
from datetime import datetime, UTC

DB_PATH = 'nat_traffic.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Find stale flights (no update in 30+ minutes)
cursor.execute("""
    SELECT crossing_id, callsign, 
           ROUND((julianday('now') - julianday(last_update_time)) * 24 * 60, 1) as min_ago
    FROM nat_crossings
    WHERE exit_time IS NULL
    AND last_update_time IS NOT NULL
    AND (julianday('now') - julianday(last_update_time)) * 24 * 60 > 30
    ORDER BY min_ago DESC
""")

stale = cursor.fetchall()

if not stale:
    print("✓ No stale flights found")
    conn.close()
    exit()

print(f"Found {len(stale)} stale flights (no update >30 min):")
print("-" * 60)
for crossing_id, callsign, min_ago in stale[:10]:
    hrs = int(min_ago / 60)
    mins = int(min_ago % 60)
    print(f"  {callsign:10s} - {hrs}h{mins:02d}m old")

if len(stale) > 10:
    print(f"  ... and {len(stale) - 10} more")

print("-" * 60)
response = input(f"\nMark all {len(stale)} flights as exited? (yes/no): ")

if response.lower() == 'yes':
    now = datetime.now(UTC).isoformat()
    
    for crossing_id, callsign, min_ago in stale:
        cursor.execute("""
            UPDATE nat_crossings
            SET exit_time = ?
            WHERE crossing_id = ?
        """, (now, crossing_id))
    
    conn.commit()
    print(f"✓ Marked {len(stale)} flights as exited")
else:
    print("Cancelled")

conn.close()
