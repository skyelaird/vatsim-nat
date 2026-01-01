"""
Debug waypoint parsing
"""

def parse_latitude(lat_str):
    try:
        if len(lat_str) == 2:
            return float(lat_str)
        elif len(lat_str) == 4:
            degrees = int(lat_str[:2])
            minutes = int(lat_str[2:4])
            if minutes == 30:
                return degrees + 0.5
            else:
                return degrees + (minutes / 60.0)
        else:
            return None
    except ValueError:
        return None

# Test Track V waypoints
waypoints = ['SUPRY', '46/50', '48/40', '49/30', '50/20', 'SOMAX', 'ATSUR']

track = {
    'entry_point': waypoints[0],
    'lat_60w': None,
    'lat_50w': None,
    'lat_40w': None,
    'lat_30w': None,
    'lat_20w': None,
    'lat_15w': None,
}

print(f"Entry point: {track['entry_point']}")
print()

for wp in waypoints[1:]:
    print(f"Processing: {wp}")
    if '/' in wp:
        lat_str, lon_str = wp.split('/')
        print(f"  Split: lat_str='{lat_str}', lon_str='{lon_str}'")
        
        lat = parse_latitude(lat_str)
        print(f"  Parsed lat: {lat}")
        
        lon = int(lon_str) if len(lon_str) <= 2 else None
        print(f"  Parsed lon: {lon}")
        
        if lat is not None and lon is not None:
            lon_field = f'lat_{lon}w'
            print(f"  Field name: {lon_field}")
            
            if lon_field in track:
                track[lon_field] = lat
                print(f"  ✓ Set {lon_field} = {lat}")
            else:
                print(f"  ✗ Field {lon_field} not in track dict!")
    else:
        print(f"  Named waypoint (skip)")
    print()

print("Final track:")
for k, v in track.items():
    print(f"  {k}: {v}")
