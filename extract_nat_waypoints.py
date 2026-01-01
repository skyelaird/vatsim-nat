"""
Extract NAT waypoints from Navigraph data
"""
import os

# NAT entry/exit fixes we care about
NAT_FIXES = [
    # Eastbound entries
    'AVUTI', 'SUPRY', 'RAFIN', 'DOVEY', 'JOBOC', 'SELIM',
    # Eastbound exits  
    'AGORI', 'ATSUR', 'NASBA', 'GUNSO', 'REGHI', 'LAPEX',
    # Boundary points
    'SOMAX', 'BEDRA', 'SEPAL', 'OMOKO', 'ETIKI',
    # Additional common NAT fixes
    'RESNO', 'ETILO', 'SUNOT', 'OYSTR', 'CLAVY', 'MUSAK',
    'MALOT', 'RIKAL', 'DINIM', 'RONPO', 'NEEKO', 'JANJO'
]

print("Extracting NAT waypoints from Navigraph data...")
print("=" * 60)

navdata_path = r'D:\GitHub\vatsim-nat\NavData\wpNavFIX.txt'

if not os.path.exists(navdata_path):
    print(f"ERROR: File not found: {navdata_path}")
    exit(1)

nat_waypoints = {}

with open(navdata_path, 'r', encoding='utf-8') as f:
    for line in f:
        # Skip comments
        if line.startswith(';'):
            continue
        
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        
        fix_name = parts[0]
        
        # Check if this is a NAT fix
        if fix_name in NAT_FIXES:
            # Parse coordinates
            # Format: FIXNAME IDENT-LAT LON
            # Example: AVUTI AVUTI-57.000000 -50.000000
            coord_part = parts[1]
            if '-' in coord_part:
                coord_str = coord_part.split('-', 1)[1]  # Remove ident prefix
                coords = coord_str.split()
                if len(coords) == 2:
                    lat = float(coords[0])
                    lon = float(coords[1])
                    nat_waypoints[fix_name] = {'lat': lat, 'lon': lon}

print(f"\nFound {len(nat_waypoints)} NAT waypoints:")
print("-" * 60)

for fix_name in sorted(nat_waypoints.keys()):
    coords = nat_waypoints[fix_name]
    print(f"{fix_name:10s}: {coords['lat']:8.4f}°N, {coords['lon']:9.4f}°W")

# Save to Python module
output_path = r'D:\GitHub\vatsim-nat\nat_waypoints.py'
with open(output_path, 'w') as f:
    f.write('"""\n')
    f.write('NAT Waypoint Coordinates\n')
    f.write('Extracted from Navigraph AIRAC 2513 (25/DEC/2025 - 22/JAN/2026)\n')
    f.write('"""\n\n')
    f.write('NAT_WAYPOINTS = {\n')
    for fix_name in sorted(nat_waypoints.keys()):
        coords = nat_waypoints[fix_name]
        f.write(f"    '{fix_name}': {{'lat': {coords['lat']:.6f}, 'lon': {coords['lon']:.6f}}},\n")
    f.write('}\n')

print(f"\n✓ Saved to: {output_path}")
print(f"  Total waypoints: {len(nat_waypoints)}")
