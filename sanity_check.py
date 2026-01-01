"""
NAT Database Sanity Check
Run from: D:\GitHub\vatsim-nat\
"""
import sqlite3

conn = sqlite3.connect('D:\\GitHub\\vatsim-nat\\nat_traffic.db')
cursor = conn.cursor()

print("=" * 80)
print("NAT CROSSINGS DATABASE - SANITY CHECK")
print("=" * 80)

# Total records
cursor.execute("SELECT COUNT(*) FROM nat_crossings")
total = cursor.fetchone()[0]
print(f"\n📊 Total crossings: {total}")

# Completed vs incomplete
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NULL")
active = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NOT NULL")
completed = cursor.fetchone()[0]
print(f"   Active (in progress): {active}")
print(f"   Completed: {completed}")

# Quality breakdown
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NOT NULL AND mid_time IS NOT NULL")
high_quality = cursor.fetchone()[0]
print(f"   High quality (has midpoint): {high_quality}")

# Recent activity (last hour)
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE entry_time >= datetime('now', '-1 hour')")
recent_entries = cursor.fetchone()[0]
print(f"\n🕐 Last hour: {recent_entries} new entries")

# Top routes
print(f"\n🛫 Top 10 Routes:")
cursor.execute("""
    SELECT departure || '-' || destination as route, COUNT(*) as flights
    FROM nat_crossings
    GROUP BY route
    ORDER BY flights DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"   {row[0]:15s}: {row[1]:3d} flights")

# Aircraft types
print(f"\n✈️  Top 10 Aircraft Types:")
cursor.execute("""
    SELECT SUBSTR(aircraft_type, 1, INSTR(aircraft_type, '/') - 1) as type,
           COUNT(*) as flights
    FROM nat_crossings
    WHERE aircraft_type LIKE '%/%'
    GROUP BY type
    ORDER BY flights DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"   {row[0]:6s}: {row[1]:3d} flights")

# OTS usage
print(f"\n🗺️  OTS Track Usage:")
cursor.execute("""
    SELECT ots_track, COUNT(*) as uses
    FROM nat_crossings
    WHERE ots_track IS NOT NULL
    GROUP BY ots_track
    ORDER BY uses DESC
    LIMIT 10
""")
ots_results = cursor.fetchall()
if ots_results:
    for row in ots_results:
        print(f"   {row[0]:10s}: {row[1]:3d} uses")
else:
    print("   (None filed yet)")

# Sample recent crossing
print(f"\n📋 Sample Recent Crossing:")
cursor.execute("""
    SELECT callsign, departure, destination, aircraft_type,
           entry_time, mid_time, exit_time, crossing_duration,
           ots_track, selcal
    FROM nat_crossings
    WHERE exit_time IS NOT NULL
    ORDER BY entry_time DESC
    LIMIT 1
""")
row = cursor.fetchone()
if row:
    print(f"   Callsign: {row[0]}")
    print(f"   Route: {row[1]} → {row[2]}")
    print(f"   Aircraft: {row[3][:30]}...")
    print(f"   Entry: {row[4]}")
    print(f"   Mid: {row[5]}")
    print(f"   Exit: {row[6]}")
    print(f"   Duration: {row[7]} minutes")
    print(f"   OTS Track: {row[8] or 'Random'}")
    print(f"   SELCAL: {row[9] or 'None'}")

# Data completeness
print(f"\n✅ Data Completeness:")
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE selcal IS NOT NULL")
selcal_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE pbn_capability IS NOT NULL")
pbn_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE oceanic_route IS NOT NULL")
route_count = cursor.fetchone()[0]

print(f"   SELCAL codes: {selcal_count}/{total} ({selcal_count*100//total if total else 0}%)")
print(f"   PBN capability: {pbn_count}/{total} ({pbn_count*100//total if total else 0}%)")
print(f"   Oceanic routes: {route_count}/{total} ({route_count*100//total if total else 0}%)")

print("\n" + "=" * 80)
print("Sanity check complete!")
print("=" * 80)

conn.close()
