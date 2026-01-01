"""
Show all NAT track records from database
"""
import sqlite3

conn = sqlite3.connect('D:\\GitHub\\vatsim-nat\\nat_traffic.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

rows = cursor.execute('SELECT * FROM nat_ots_tracks ORDER BY track_letter').fetchall()

print("=" * 80)
print(f"NAT TRACKS DATABASE - {len(rows)} tracks found")
print("=" * 80)

for r in rows:
    print(f"\nTrack {r['track_letter']}:")
    print(f"  Effective: {r['effective_date']} (TMI {r['tmi']})")
    print(f"  Entry:     {r['entry_point']}")
    print(f"  60W:       {r['lat_60w']}")
    print(f"  50W:       {r['lat_50w']}")
    print(f"  40W:       {r['lat_40w']}")
    print(f"  30W:       {r['lat_30w']}")
    print(f"  20W:       {r['lat_20w']}")
    print(f"  15W:       {r['lat_15w']}")
    print(f"  Boundary:  {r['boundary_point']}")
    print(f"  Exit:      {r['exit_point']}")
    print(f"  NARs:      {r['nar_routes']}")

conn.close()
