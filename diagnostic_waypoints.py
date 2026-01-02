"""
Diagnostic - Check waypoint parsing
"""

import requests
from route_parser import extract_oceanic_route, is_nat_route
from nat_waypoints import get_waypoint
import re

def parse_waypoint_coords(waypoint_name):
    """Parse waypoint to lat/lon"""
    coords = get_waypoint(waypoint_name)
    if coords:
        return coords['lat'], coords['lon'], 'DB'
    
    # Skip OTS tracks
    if waypoint_name.startswith('NAT') and len(waypoint_name) == 4:
        return None, None, 'SKIP_OTS'
    
    # Degrees only: 59N050W
    match = re.match(r'(\d{2})N(\d{3})W', waypoint_name)
    if match:
        return int(match.group(1)), -int(match.group(2)), 'PARSED_DEG'
    
    # Degrees+minutes: 5830N02000W
    match = re.match(r'(\d{2})(\d{2})N(\d{3})(\d{2})W', waypoint_name)
    if match:
        lat = int(match.group(1)) + int(match.group(2)) / 60.0
        lon = -(int(match.group(3)) + int(match.group(4)) / 60.0)
        return lat, lon, 'PARSED_MIN'
    
    return None, None, 'FAILED'


# Fetch data
print("Fetching VATSIM data...")
status = requests.get("https://status.vatsim.net/status.json", timeout=10).json()
data = requests.get(status['data']['v3'][0], timeout=10).json()

# Check NAT flights
nat_count = 0
for pilot in data['pilots']:
    if not pilot.get('flight_plan'):
        continue
    
    fp = pilot['flight_plan']
    dep, dest = fp.get('departure', ''), fp.get('arrival', '')
    
    if not is_nat_route(dep, dest):
        continue
    
    lat, lon = pilot.get('latitude', 0), pilot.get('longitude', 0)
    if not (35 <= lat <= 65 and ((-80 <= lon <= -45) or (-25 <= lon <= 0))):
        continue
    
    route = fp.get('route', '')
    oceanic_route, entry, exit = extract_oceanic_route(route)
    
    if oceanic_route:
        nat_count += 1
        print(f"\n{'='*80}")
        print(f"{pilot['callsign']} - {dep}->{dest}")
        print(f"Oceanic route: {oceanic_route}")
        print(f"Waypoints parsed:")
        
        waypoint_count = 0
        for part in oceanic_route.split():
            if part == 'DCT':
                continue
            wpt_name = part.split('/')[0]
            lat, lon, source = parse_waypoint_coords(wpt_name)
            if lat and lon:
                waypoint_count += 1
                print(f"  {wpt_name:15s} -> {lat:6.2f}N {lon:7.2f}W  ({source})")
            else:
                print(f"  {wpt_name:15s} -> FAILED TO PARSE")
        
        print(f"Total waypoints found: {waypoint_count}")
        
        if nat_count >= 5:  # Show first 5
            break

print(f"\n\nTotal NAT flights: {nat_count}")
