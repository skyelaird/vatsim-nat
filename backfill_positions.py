"""
Backfill current_* fields for existing active crossings
Sets current position = entry position for flights that entered before migration
"""
import sqlite3
from datetime import datetime, UTC

conn = sqlite3.connect('nat_traffic.db')
cursor = conn.cursor()

# Get all active crossings without current position set
cursor.execute("""
    SELECT crossing_id, entry_time, entry_lat, entry_lon, entry_fl, entry_gs
    FROM nat_crossings
    WHERE exit_time IS NULL
    AND last_update_time IS NULL
""")

flights = cursor.fetchall()
print(f"Found {len(flights)} flights needing backfill...")

for crossing_id, entry_time, lat, lon, fl, gs in flights:
    cursor.execute("""
        UPDATE nat_crossings
        SET last_update_time = ?, current_lat = ?, current_lon = ?, current_fl = ?, current_gs = ?
        WHERE crossing_id = ?
    """, (entry_time, lat, lon, fl, gs, crossing_id))

conn.commit()
print(f"✓ Backfilled {len(flights)} flights")

# Verify
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NULL AND last_update_time IS NOT NULL")
updated = cursor.fetchone()[0]
print(f"✓ Total active flights with positions: {updated}")

conn.close()
