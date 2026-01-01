"""
Generate NAT waypoints directly to repo
"""
import json
import csv

# Parse Navigraph data
NAT_BOUNDS = {'lat_min': 35.0, 'lat_max': 75.0, 'lon_min': -80.0, 'lon_max': 0.0}
navdata_path = r'D:\GitHub\vatsim-nat\NavData\wpNavFIX.txt'
waypoints = {}

print("Parsing Navigraph AIRAC 2513...")

with open(navdata_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith(';') or len(line.strip()) < 24:
            continue
        
        fix_name = line[:24].strip()
        if fix_name.endswith('S'):
            continue
        
        parts = line[24:].strip().split()
        if len(parts) < 3:
            continue
        
        try:
            lat, lon = float(parts[1]), float(parts[2])
            if (lat >= 0 and NAT_BOUNDS['lat_min'] <= lat <= NAT_BOUNDS['lat_max'] and
                NAT_BOUNDS['lon_min'] <= lon <= NAT_BOUNDS['lon_max']):
                waypoints[fix_name] = {'lat': lat, 'lon': lon}
        except:
            continue

print(f"Found {len(waypoints):,} waypoints\n")

# 1. Python module
print("Writing nat_waypoints.py...")
with open(r'D:\GitHub\vatsim-nat\nat_waypoints.py', 'w') as f:
    f.write('"""\nNAT Region Waypoints\nNavigraph AIRAC 2513 (25/DEC/2025 - 22/JAN/2026)\n')
    f.write(f'Total waypoints: {len(waypoints):,}\n"""\n\n')
    f.write('NAT_WAYPOINTS = {\n')
    for name in sorted(waypoints.keys()):
        c = waypoints[name]
        f.write(f"    '{name}': {{'lat': {c['lat']:.6f}, 'lon': {c['lon']:.6f}}},\n")
    f.write('}\n\n')
    f.write('def get_waypoint(name):\n    """Get waypoint coords by name"""\n    return NAT_WAYPOINTS.get(name)\n')

# 2. JSON
print("Writing nat_waypoints.json...")
with open(r'D:\GitHub\vatsim-nat\nat_waypoints.json', 'w') as f:
    json.dump(waypoints, f, indent=2)

# 3. CSV
print("Writing nat_waypoints.csv...")
with open(r'D:\GitHub\vatsim-nat\nat_waypoints.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['fix_name', 'latitude', 'longitude'])
    for name in sorted(waypoints.keys()):
        writer.writerow([name, waypoints[name]['lat'], waypoints[name]['lon']])

# 4. SQL
print("Writing nat_waypoints.sql...")
with open(r'D:\GitHub\vatsim-nat\nat_waypoints.sql', 'w') as f:
    f.write('CREATE TABLE IF NOT EXISTS nat_waypoints (\n')
    f.write('    fix_name TEXT PRIMARY KEY,\n')
    f.write('    latitude REAL NOT NULL,\n')
    f.write('    longitude REAL NOT NULL\n')
    f.write(');\n\n')
    for name in sorted(waypoints.keys()):
        c = waypoints[name]
        f.write(f"INSERT OR REPLACE INTO nat_waypoints VALUES ('{name}', {c['lat']}, {c['lon']});\n")

print(f"\n✓ All files generated! ({len(waypoints):,} waypoints)")

# Show known NAT fixes
print("\nKnown NAT fixes:")
known = ['AVUTI', 'SUPRY', 'RAFIN', 'AGORI', 'ATSUR', 'NASBA']
for fix in known:
    if fix in waypoints:
        c = waypoints[fix]
        print(f"  {fix}: {c['lat']:.3f}°N, {c['lon']:.3f}°")
