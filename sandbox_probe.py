"""
NAT Conflict Probe - Proof of Concept (Sandbox)
================================================

Simple conflict detection using current VATSIM data
ATC-style display for professional review
NOW WITH OTS TRACK EXPANSION!
"""

import requests
import sqlite3
from datetime import datetime, timedelta, UTC
import math
import re
from nat_waypoints import NAT_WAYPOINTS, get_waypoint
from route_parser import extract_oceanic_route, is_nat_route

# Simple constants (no GRIB yet)
SPEED_OF_SOUND_FL370 = 573  # knots
DB_PATH = 'nat_traffic.db'


def haversine(lat1, lon1, lat2, lon2):
    """Calculate great circle distance in NM"""
    R = 3440.065
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def mach_to_tas_simple(mach, altitude_ft):
    """Mach to TAS using ISA"""
    temp_c = 15 - (altitude_ft / 1000 * 1.98) if altitude_ft <= 36089 else -56.5
    speed_of_sound = 38.967854 * math.sqrt(temp_c + 273.15)
    return mach * speed_of_sound


def expand_ots_track_inline(track_id):
    """Expand OTS track to waypoints (inline version)"""
    if not track_id.startswith('NAT') or len(track_id) != 4:
        return None
    
    track_letter = track_id[3]
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today = datetime.now(UTC).date() if hasattr(datetime, 'UTC') else datetime.utcnow().date()
        
        cursor.execute("""
            SELECT entry_point, lat_60w, lat_50w, lat_40w, lat_30w, lat_20w, lat_15w,
                   boundary_point, exit_point
            FROM nat_ots_tracks
            WHERE track_letter = ? AND effective_date = ?
        """, (track_letter, today))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        waypoints = []
        if row[0]:
            waypoints.append(row[0])
        
        coords = [(row[1], 60), (row[2], 50), (row[3], 40), (row[4], 30), (row[5], 20), (row[6], 15)]
        
        for lat, lon_deg in coords:
            if lat is not None:
                lat_int = int(lat)
                lat_min = int((lat - lat_int) * 60)
                wpt = f"{lat_int:02d}N{lon_deg:03d}W" if lat_min == 0 else f"{lat_int:02d}{lat_min:02d}N{lon_deg:03d}00W"
                waypoints.append(wpt)
        
        if row[7]:
            waypoints.append(row[7])
        if row[8]:
            waypoints.append(row[8])
        
        return waypoints
    except:
        return None


def expand_route_with_ots(oceanic_route):
    """Expand OTS tracks in route to actual waypoints"""
    ots_tracks = re.findall(r'\bNAT[A-Z]\b', oceanic_route)
    
    if not ots_tracks:
        return oceanic_route
    
    expanded = oceanic_route
    for ots_id in ots_tracks:
        waypoints = expand_ots_track_inline(ots_id)
        if waypoints:
            # Remove first/last (entry/exit fixes) - they're already in route
            # "SUPRY NATV ATSUR" -> "SUPRY 46N050W 48N040W 49N030W 50N020W ATSUR"
            # NOT "SUPRY SUPRY 46N050W ... ATSUR ATSUR"
            if len(waypoints) > 2:
                track_waypoints = waypoints[1:-1]  # Just middle coordinates
            else:
                track_waypoints = waypoints
            
            expanded = expanded.replace(ots_id, ' '.join(track_waypoints))
    
    return expanded


def parse_waypoint_coords(waypoint_name):
    """Parse waypoint to lat/lon - handles degrees and minutes"""
    coords = get_waypoint(waypoint_name)
    if coords:
        return coords['lat'], coords['lon']
    
    # Skip OTS identifiers (already expanded)
    if waypoint_name.startswith('NAT') and len(waypoint_name) == 4:
        return None, None
    
    # Degrees only: 59N050W
    match = re.match(r'(\d{2})N(\d{3})W', waypoint_name)
    if match:
        return int(match.group(1)), -int(match.group(2))
    
    # Degrees+minutes: 5830N02000W
    match = re.match(r'(\d{2})(\d{2})N(\d{3})(\d{2})W', waypoint_name)
    if match:
        lat = int(match.group(1)) + int(match.group(2)) / 60.0
        lon = -(int(match.group(3)) + int(match.group(4)) / 60.0)
        return lat, lon
    
    return None, None


def fetch_vatsim_data():
    """Fetch VATSIM pilot data"""
    print("Fetching VATSIM data...")
    status = requests.get("https://status.vatsim.net/status.json", timeout=10).json()
    data = requests.get(status['data']['v3'][0], timeout=10).json()
    print(f"✓ {len(data['pilots'])} pilots online\n")
    return data['pilots']


def identify_nat_flights(pilots):
    """Find NAT-bound flights"""
    nat_flights = []
    for pilot in pilots:
        if not pilot.get('flight_plan'):
            continue
        
        fp = pilot['flight_plan']
        dep, dest, route = fp.get('departure', ''), fp.get('arrival', ''), fp.get('route', '')
        
        if not is_nat_route(dep, dest):
            continue
        
        lat, lon = pilot.get('latitude', 0), pilot.get('longitude', 0)
        if not (35 <= lat <= 65 and ((-80 <= lon <= -45) or (-25 <= lon <= 0))):
            continue
        
        oceanic_route, entry_fix, exit_fix = extract_oceanic_route(route)
        if oceanic_route:
            nat_flights.append({
                'callsign': pilot['callsign'],
                'lat': lat, 'lon': lon,
                'altitude': pilot.get('altitude', 0),
                'groundspeed': pilot.get('groundspeed', 0),
                'departure': dep,
                'destination': dest,
                'oceanic_route': oceanic_route,
                'aircraft': fp.get('aircraft_short', 'UNKN'),
                'cruise_alt': fp.get('altitude', '0')
            })
    return nat_flights


def build_trajectory(flight):
    """Build trajectory from route WITH OTS EXPANSION"""
    # EXPAND OTS TRACKS FIRST!
    oceanic_route = expand_route_with_ots(flight['oceanic_route'])
    
    waypoints = []
    for part in oceanic_route.split():
        if part == 'DCT':
            continue
        wpt_name = part.split('/')[0]
        lat, lon = parse_waypoint_coords(wpt_name)
        if lat and lon:
            waypoints.append({'name': wpt_name, 'lat': lat, 'lon': lon})
    
    if len(waypoints) < 2:
        return None
    
    # Get filed Mach and FL
    mach_match = re.search(r'/M(\d{3})', flight['oceanic_route'])
    filed_mach = float(mach_match.group(1)) / 100 if mach_match else 0.85
    
    try:
        filed_fl = int(flight['cruise_alt'])
        filed_fl = filed_fl // 100 if filed_fl > 1000 else filed_fl
    except:
        filed_fl = flight['altitude'] // 100
    
    # Use groundspeed, but fallback to TAS if GS is 0 or unrealistic
    gs = flight['groundspeed']
    if gs < 100:  # Unrealistic groundspeed (aircraft not moving or bad data)
        tas = mach_to_tas_simple(filed_mach, filed_fl * 100)
        gs = tas  # Use TAS as fallback
    
    # Build ETAs
    trajectory = []
    current_lat, current_lon = flight['lat'], flight['lon']
    current_eta = datetime.now(UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
    
    for wpt in waypoints:
        distance = haversine(current_lat, current_lon, wpt['lat'], wpt['lon'])
        current_eta += timedelta(hours=distance / gs)
        trajectory.append({
            'waypoint': wpt['name'], 'lat': wpt['lat'], 'lon': wpt['lon'],
            'fl': filed_fl, 'eta': current_eta, 'callsign': flight['callsign']
        })
        current_lat, current_lon = wpt['lat'], wpt['lon']
    
    return trajectory


def detect_conflicts(all_trajectories):
    """Find conflicts - deduplicated"""
    conflicts = []
    seen_pairs = set()
    
    waypoint_groups = {}
    for traj in all_trajectories:
        if not traj:
            continue
        for point in traj:
            waypoint_groups.setdefault(point['waypoint'], []).append(point)
    
    for flights in waypoint_groups.values():
        if len(flights) < 2:
            continue
        
        for i in range(len(flights)):
            for j in range(i + 1, len(flights)):
                f1, f2 = flights[i], flights[j]
                
                if f1['fl'] != f2['fl']:
                    continue
                
                pair_key = tuple(sorted([f1['callsign'], f2['callsign']]))
                if pair_key in seen_pairs:
                    continue
                
                sep_min = abs((f1['eta'] - f2['eta']).total_seconds()) / 60
                
                if sep_min < 5:
                    seen_pairs.add(pair_key)
                    conflicts.append({
                        'waypoint': flights[i]['waypoint'],
                        'flight1': f1['callsign'], 'flight2': f2['callsign'],
                        'fl': f1['fl'], 'eta1': f1['eta'], 'eta2': f2['eta'],
                        'separation_min': sep_min,
                        'severity': 'HIGH' if sep_min < 3 else 'MEDIUM'
                    })
    
    return conflicts


def main():
    """Run probe"""
    print("=" * 100)
    print("NAT CONFLICT PROBE - SANDBOX (with OTS Track Expansion)")
    print("=" * 100 + "\n")
    
    pilots = fetch_vatsim_data()
    nat_flights = identify_nat_flights(pilots)
    print(f"✓ Found {len(nat_flights)} NAT-bound flights\n")
    
    if not nat_flights:
        print("No NAT flights approaching. Try again later!")
        return
    
    # Show flights
    print("NAT-bound flights:")
    print("-" * 100)
    for flight in nat_flights[:10]:
        print(f"{flight['callsign']:10s} {flight['aircraft']:6s} "
              f"{flight['departure']}->{flight['destination']} "
              f"FL{flight['altitude']//100:3d} "
              f"{flight['lat']:6.2f}°N {flight['lon']:7.2f}°")
    if len(nat_flights) > 10:
        print(f"... and {len(nat_flights) - 10} more\n")
    
    # Build trajectories
    print("Building trajectories (expanding OTS tracks)...")
    all_trajectories = [build_trajectory(f) for f in nat_flights]
    all_trajectories = [t for t in all_trajectories if t]
    print(f"✓ Built {len(all_trajectories)} trajectories\n")
    
    # Detect
    print("Detecting conflicts...")
    conflicts = detect_conflicts(all_trajectories)
    print(f"✓ Found {len(conflicts)} conflicts\n")
    
    # Display
    if conflicts:
        print("=" * 100)
        print("CONFLICTS DETECTED")
        print("=" * 100)
        
        for i, c in enumerate(conflicts, 1):
            icon = '🚨' if c['severity'] == 'HIGH' else '⚠️'
            print(f"\n{icon}  CONFLICT #{i} - {c['severity']}")
            print("-" * 100)
            print(f"Point: {c['waypoint']}    FL{c['fl']}    Separation: {c['separation_min']:.1f} min\n")
            
            for flight_call, eta in [(c['flight1'], c['eta1']), (c['flight2'], c['eta2'])]:
                flight = next((f for f in nat_flights if f['callsign'] == flight_call), None)
                if not flight:
                    continue
                
                mach_match = re.search(r'/M(\d{3})', flight['oceanic_route'])
                mach_str = f"M.{mach_match.group(1)[:2]}" if mach_match else "---"
                
                try:
                    fl = int(flight['cruise_alt'])
                    fl = fl // 100 if fl > 1000 else fl
                except:
                    fl = flight['altitude'] // 100
                
                tas = int(mach_to_tas_simple(float(mach_match.group(1))/100 if mach_match else 0.85, fl * 100))
                
                # Use same GS logic as trajectory builder
                gs = flight['groundspeed']
                if gs < 100:
                    gs = tas
                
                # Clean route
                route = re.sub(r'/[MN]\d{3,4}F?\d*', '', flight['oceanic_route'])
                route = ' '.join(route.replace('DCT', '').split())
                
                print(f"  {flight['callsign']:8s} | {flight['aircraft']:6s} | {flight['departure']}->{flight['destination']} | " +
                      f"{tas:3d}kt/{mach_str} | GS {gs:3d}kt")
                print(f"           | {route[:65]}")
                print(f"           | ETA {eta.strftime('%H%M')}Z\n")
            
            print("  Resolutions:")
            print(f"    → {c['flight1']} climb to FL{c['fl']+10} or FL{c['fl']+20}")
            print(f"    → {c['flight2']} descend to FL{c['fl']-10} or FL{c['fl']-20}")
    else:
        print("✅ No conflicts - adequate separation")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
