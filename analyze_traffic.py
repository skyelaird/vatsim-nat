"""Quick analysis of NAT traffic collected so far"""
import sqlite3

conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("VATSIM NAT TRAFFIC ANALYSIS - FIRST 45 MINUTES")
print("=" * 80)
print()

# Total crossings
cursor.execute("SELECT COUNT(*) as total FROM nat_crossings")
total = cursor.fetchone()['total']
print(f"COMPLETED CROSSINGS: {total}")
print()

if total == 0:
    print("No completed crossings yet - all still in progress!")
    print("Check back in a few hours!")
    conn.close()
    exit()

# Direction breakdown
print("DIRECTION BREAKDOWN:")
print("-" * 40)
cursor.execute("""
    SELECT direction, COUNT(*) as count
    FROM nat_crossings
    GROUP BY direction
""")
for row in cursor.fetchall():
    print(f"  {row['direction']}: {row['count']} crossings")
print()

# OTS vs Random
print("OTS TRACK USAGE:")
print("-" * 40)
cursor.execute("""
    SELECT 
        COUNT(CASE WHEN ots_track IS NOT NULL THEN 1 END) as organized,
        COUNT(CASE WHEN ots_track IS NULL THEN 1 END) as random
    FROM nat_crossings
""")
row = cursor.fetchone()
organized = row['organized']
random = row['random']
pct_ots = round(100.0 * organized / total, 1) if total > 0 else 0
print(f"  Organized Tracks: {organized} ({pct_ots}%)")
print(f"  Random Routing:   {random} ({100-pct_ots}%)")
if organized > 0:
    cursor.execute("""
        SELECT ots_track, COUNT(*) as count
        FROM nat_crossings
        WHERE ots_track IS NOT NULL
        GROUP BY ots_track
        ORDER BY count DESC
    """)
    print("  Track distribution:")
    for row in cursor.fetchall():
        print(f"    NAT{row['ots_track']}: {row['count']}")
print()

# Top origin-destination pairs
print("TOP CITY PAIRS:")
print("-" * 40)
cursor.execute("""
    SELECT departure, destination, COUNT(*) as flights
    FROM nat_crossings
    GROUP BY departure, destination
    ORDER BY flights DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row['departure']} → {row['destination']}: {row['flights']}")
print()

# Aircraft types
print("AIRCRAFT TYPES:")
print("-" * 40)
cursor.execute("""
    SELECT aircraft_type, COUNT(*) as count
    FROM nat_crossings
    WHERE aircraft_type IS NOT NULL
    GROUP BY aircraft_type
    ORDER BY count DESC
""")
for row in cursor.fetchall():
    actype = row['aircraft_type'].split('/')[0] if row['aircraft_type'] else 'Unknown'
    print(f"  {actype}: {row['count']}")
print()

# SELCAL equipped
print("SELCAL EQUIPAGE:")
print("-" * 40)
cursor.execute("""
    SELECT 
        COUNT(CASE WHEN selcal IS NOT NULL THEN 1 END) as with_selcal,
        COUNT(CASE WHEN selcal IS NULL THEN 1 END) as without_selcal
    FROM nat_crossings
""")
row = cursor.fetchone()
with_sel = row['with_selcal']
pct_sel = round(100.0 * with_sel / total, 1) if total > 0 else 0
print(f"  With SELCAL:    {with_sel} ({pct_sel}%)")
print(f"  Without SELCAL: {row['without_selcal']} ({100-pct_sel}%)")
print()

# Flight level distribution
print("FLIGHT LEVEL DISTRIBUTION (Entry):")
print("-" * 40)
cursor.execute("""
    SELECT entry_fl, COUNT(*) as count
    FROM nat_crossings
    WHERE entry_fl IS NOT NULL
    GROUP BY entry_fl
    ORDER BY entry_fl DESC
""")
for row in cursor.fetchall():
    print(f"  FL{row['entry_fl']}: {row['count']}")
print()

# PBN capability
print("PBN EQUIPAGE:")
print("-" * 40)
cursor.execute("""
    SELECT 
        COUNT(CASE WHEN pbn_capability IS NOT NULL THEN 1 END) as with_pbn,
        COUNT(CASE WHEN pbn_capability IS NULL THEN 1 END) as without_pbn
    FROM nat_crossings
""")
row = cursor.fetchone()
print(f"  With PBN:    {row['with_pbn']}")
print(f"  Without PBN: {row['without_pbn']}")
print()

# Individual crossings with details
print("COMPLETED CROSSINGS (Detail):")
print("-" * 80)
cursor.execute("""
    SELECT callsign, aircraft_type, departure, destination, direction,
           ots_track, selcal, pbn_capability, operator,
           entry_fl, mid_fl, exit_fl, crossing_duration
    FROM nat_crossings
    ORDER BY rowid
""")
for row in cursor.fetchall():
    actype = row['aircraft_type'].split('/')[0] if row['aircraft_type'] else 'UNK'
    track = f"NAT{row['ots_track']}" if row['ots_track'] else 'RANDOM'
    selcal = row['selcal'] if row['selcal'] else 'NO'
    pbn = row['pbn_capability'] if row['pbn_capability'] else 'None'
    opr = row['operator'] if row['operator'] else '?'
    
    print(f"{row['callsign']:<10} {actype:<6} {row['departure']}->{row['destination']} [{row['direction']}]")
    print(f"  Route: {track:<10} SELCAL: {selcal:<6} PBN: {pbn:<15} Operator: {opr}")
    
    if row['entry_fl'] or row['mid_fl'] or row['exit_fl']:
        entry = f"FL{row['entry_fl']}" if row['entry_fl'] else "???"
        mid = f"FL{row['mid_fl']}" if row['mid_fl'] else "???"
        exit = f"FL{row['exit_fl']}" if row['exit_fl'] else "???"
        print(f"  Altitudes: Entry {entry} → Mid {mid} → Exit {exit}")
    
    print()

conn.close()
