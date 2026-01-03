"""
Debug script to understand why probe finds 0 crossings
"""
import sqlite3
from datetime import datetime, UTC

DB_PATH = 'nat_traffic.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("PROBE FILTER DIAGNOSTICS")
print("=" * 80)
print()

# Total active crossings
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NULL")
total = cursor.fetchone()[0]
print(f"✓ Total active crossings (exit_time IS NULL): {total}")

# How many have last_update_time set?
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NULL AND last_update_time IS NOT NULL")
with_update = cursor.fetchone()[0]
print(f"✓ With last_update_time populated: {with_update}")

# How many have last_update_time within 15 minutes?
cursor.execute("""
    SELECT COUNT(*) FROM nat_crossings 
    WHERE exit_time IS NULL 
    AND last_update_time IS NOT NULL
    AND (julianday('now') - julianday(last_update_time)) * 24 * 60 < 15
""")
within_15min = cursor.fetchone()[0]
print(f"✓ Updated within last 15 minutes: {within_15min}")
print()

# Show sample of what's in the database
print("Sample of active crossings:")
print("-" * 80)
cursor.execute("""
    SELECT callsign, entry_time, last_update_time,
           ROUND((julianday('now') - julianday(last_update_time)) * 24 * 60, 1) as minutes_since_update,
           current_lat, current_lon
    FROM nat_crossings 
    WHERE exit_time IS NULL 
    ORDER BY last_update_time DESC
    LIMIT 10
""")

print(f"{'Callsign':<10} {'Entry Time':<20} {'Last Update':<20} {'Min Ago':<10} {'Current Pos'}")
print("-" * 80)
for row in cursor.fetchall():
    callsign, entry_time, last_update, min_ago, lat, lon = row
    last_update_str = last_update if last_update else "NULL"
    min_ago_str = f"{min_ago:.1f}" if min_ago else "N/A"
    pos_str = f"{lat:.2f},{lon:.2f}" if lat and lon else "NULL"
    print(f"{callsign:<10} {entry_time[:19]:<20} {last_update_str[:19]:<20} {min_ago_str:<10} {pos_str}")

print()
print("Current UTC time:", datetime.now(UTC).isoformat())
print()

# Show the exact SQL the probe is using
print("Probe SQL filter:")
print("-" * 80)
print("""
SELECT callsign, aircraft_type, departure, destination,
       oceanic_route, ots_track, filed_altitude, selcal,
       entry_lat, entry_lon, entry_fl, entry_gs,
       mid_lat, mid_lon, mid_fl, mid_gs, crossed_mid,
       current_lat, current_lon, current_fl, current_gs, last_update_time
FROM nat_crossings 
WHERE exit_time IS NULL
-- Only flights with recent position updates (within last 15 minutes)
AND last_update_time IS NOT NULL
AND (julianday('now') - julianday(last_update_time)) * 24 * 60 < 15
""")
print()

conn.close()
