import sqlite3
from collections import defaultdict

conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        departure,
        destination,
        aircraft_type,
        COUNT(*) as crossings
    FROM nat_crossings
    WHERE aircraft_type IS NOT NULL
      AND departure IS NOT NULL
      AND destination IS NOT NULL
    GROUP BY departure, destination, aircraft_type
    ORDER BY departure, destination, crossings DESC
""")

results = cursor.fetchall()

if not results:
    print("No data yet!")
    conn.close()
    exit()

city_pairs = defaultdict(lambda: {'total': 0, 'aircraft': {}})

for row in results:
    pair = f"{row['departure']}-{row['destination']}"
    actype = row['aircraft_type'].split('/')[0] if row['aircraft_type'] else 'UNKNOWN'
    count = row['crossings']
    
    city_pairs[pair]['total'] += count
    city_pairs[pair]['aircraft'][actype] = count

sorted_pairs = sorted(city_pairs.items(), key=lambda x: x[1]['total'], reverse=True)

print("=" * 80)
print("NAT TRAFFIC: Aircraft Types by City Pair")
print("=" * 80)
print()

for i, (pair, data) in enumerate(sorted_pairs[:20], 1):
    print(f"{i:2d}. {pair:13s} - {data['total']:3d} crossings")
    sorted_aircraft = sorted(data['aircraft'].items(), key=lambda x: x[1], reverse=True)
    for actype, count in sorted_aircraft[:5]:
        pct = (count / data['total']) * 100
        print(f"    {actype:6s}: {count:3d} ({pct:5.1f}%)")
    if len(sorted_aircraft) > 5:
        other = sum(c for ac, c in sorted_aircraft[5:])
        print(f"    Others: {other:3d} ({(other/data['total'])*100:5.1f}%)")
    print()

conn.close()
