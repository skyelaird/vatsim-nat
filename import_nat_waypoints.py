"""
Import NAT region waypoints from Navigraph data
Extract all waypoints in expanded NAT region for conflict probe
"""

# Bounding box for NAT + approach regions
NAT_BOUNDS = {
    'lat_min': 35.0,   # Southern limit (includes Azores approaches)
    'lat_max': 75.0,   # Northern limit (includes Iceland/Greenland)
    'lon_min': -80.0,  # Western limit (includes Canadian feeds)
    'lon_max': 0.0     # Eastern limit (includes UK/Ireland)
}

print("Importing NAT Region Waypoints from Navigraph AIRAC 2513")
print("=" * 80)
print(f"Bounding box:")
print(f"  Latitude:  {NAT_BOUNDS['lat_min']}°N to {NAT_BOUNDS['lat_max']}°N")
print(f"  Longitude: {NAT_BOUNDS['lon_min']}°W to {NAT_BOUNDS['lon_max']}°E")
print("=" * 80)

navdata_path = r'D:\GitHub\vatsim-nat\NavData\wpNavFIX.txt'
waypoints = {}

with open(navdata_path, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        # Skip comments
        if line.startswith(';'):
            continue
        
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        
        # Parse format: NAME IDENT-LAT LON
        # Example: AVUTI AVUTI-57.000000 -50.000000
        fix_name = parts[0]
        
        # Second part contains IDENT-LAT
        coord_part = parts[1]
        lon_str = parts[2]
        
        try:
            # Extract latitude from IDENT-LAT
            if '-' in coord_part:
                lat_str = coord_part.split('-')[-1]  # Get everything after last dash
                lat = float(lat_str)
            else:
                continue
            
            lon = float(lon_str)
            
            # Check if in NAT region
            if (NAT_BOUNDS['lat_min'] <= lat <= NAT_BOUNDS['lat_max'] and
                NAT_BOUNDS['lon_min'] <= lon <= NAT_BOUNDS['lon_max']):
                
                waypoints[fix_name] = {
                    'lat': lat,
                    'lon': lon
                }
        
        except (ValueError, IndexError):
            # Skip malformed records
            continue

print(f"\n✓ Processed {line_num:,} total waypoints")
print(f"✓ Found {len(waypoints):,} waypoints in NAT region")

# Show some samples
print("\n" + "=" * 80)
print("Sample waypoints extracted:")
print("=" * 80)

# Show by longitude bands
lon_bands = [
    (-80, -60, "Canadian Approach"),
    (-60, -40, "Western NAT"),
    (-40, -20, "Central NAT"),
    (-20, 0, "Eastern NAT/European Approach")
]

for lon_min, lon_max, region_name in lon_bands:
    region_wpts = {
        name: coords for name, coords in waypoints.items()
        if lon_min <= coords['lon'] < lon_max
    }
    
    print(f"\n{region_name} ({lon_min}°W to {lon_max}°W): {len(region_wpts)} waypoints")
    
    # Show first 5 from this region
    for i, (name, coords) in enumerate(list(region_wpts.items())[:5]):
        print(f"  {name:10s}: {coords['lat']:7.3f}°N, {coords['lon']:8.3f}°W")
    
    if len(region_wpts) > 5:
        print(f"  ... and {len(region_wpts) - 5} more")

# Save to Python module
output_path = r'D:\GitHub\vatsim-nat\nat_waypoints.py'
with open(output_path, 'w') as f:
    f.write('"""\n')
    f.write('NAT Region Waypoints\n')
    f.write('Extracted from Navigraph AIRAC 2513 (25/DEC/2025 - 22/JAN/2026)\n')
    f.write('\n')
    f.write('Bounding box:\n')
    f.write(f'  Latitude:  {NAT_BOUNDS["lat_min"]}°N to {NAT_BOUNDS["lat_max"]}°N\n')
    f.write(f'  Longitude: {NAT_BOUNDS["lon_min"]}°W to {NAT_BOUNDS["lon_max"]}°E\n')
    f.write(f'\n')
    f.write(f'Total waypoints: {len(waypoints):,}\n')
    f.write('"""\n\n')
    
    f.write('NAT_WAYPOINTS = {\n')
    for name in sorted(waypoints.keys()):
        coords = waypoints[name]
        f.write(f"    '{name}': {{'lat': {coords['lat']:.6f}, 'lon': {coords['lon']:.6f}}},\n")
    f.write('}\n\n')
    
    # Add helper function
    f.write('''
def get_waypoint_coords(fix_name):
    """
    Get coordinates for a waypoint
    
    Args:
        fix_name: Waypoint identifier (e.g., 'AVUTI', '59N050W')
    
    Returns:
        dict with 'lat' and 'lon', or None if not found
    """
    return NAT_WAYPOINTS.get(fix_name)


def is_nat_waypoint(fix_name):
    """Check if waypoint exists in NAT region database"""
    return fix_name in NAT_WAYPOINTS
''')

print("\n" + "=" * 80)
print(f"✓ Saved to: {output_path}")
print(f"  Total waypoints: {len(waypoints):,}")
print("=" * 80)

# Show some known NAT waypoints if found
print("\nKnown NAT waypoints found:")
known_fixes = [
    'AVUTI', 'SUPRY', 'RAFIN', 'DOVEY', 'JOBOC', 'SELIM',  # EB entries
    'AGORI', 'ATSUR', 'NASBA', 'GUNSO', 'REGHI', 'LAPEX',  # EB exits
    'RESNO', 'ETILO', 'SUNOT',  # WB entries
    'OYSTR', 'CLAVY', 'MUSAK',  # WB exits
]

found_known = []
for fix in known_fixes:
    if fix in waypoints:
        coords = waypoints[fix]
        found_known.append(f"  {fix:10s}: {coords['lat']:7.3f}°N, {coords['lon']:8.3f}°W")

if found_known:
    for line in found_known:
        print(line)
else:
    print("  (None found - check data)")
