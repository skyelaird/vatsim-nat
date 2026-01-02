"""
NAT Conflict Probe - Database-Driven Version
=============================================

Analyzes active NAT crossings from database (not live VATSIM)
Runs every 5-15 minutes alongside collector
"""

import sqlite3
from datetime import datetime, timedelta, UTC
import math
import re
from nat_waypoints import get_waypoint
from route_parser import extract_oceanic_route

# Constants
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
    """Expand OTS track to waypoints"""
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
        if waypoints and len(waypoints) > 2:
            # Remove entry/exit (already in route)
            track_waypoints = waypoints[1:-1]
            expanded = expanded.replace(ots_id, ' '.join(track_waypoints))
    
    return expanded


def parse_waypoint_coords(waypoint_name):
    """Parse waypoint to lat/lon"""
    coords = get_waypoint(waypoint_name)
    if coords:
        return coords['lat'], coords['lon']
    
    if waypoint_name.startswith('NAT') and len(waypoint_name) == 4:
        return None, None
    
    # Degrees: 59N050W
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


def get_active_crossings():
    """Get all active NAT crossings from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            callsign, aircraft_type, departure, destination,
            oceanic_route, ots_track, filed_altitude,
            entry_time, entry_lat, entry_lon, entry_fl, entry_gs,
            mid_time, mid_lat, mid_lon, mid_fl, mid_gs,
            crossed_mid
        FROM nat_crossings
        WHERE exit_time IS NULL
        ORDER BY entry_time DESC
    """)
    
    flights = []
    for row in cursor.fetchall():
        # Determine current position and speed
        if row[17]:  # crossed_mid
            lat, lon = row[13], row[14]  # mid position
            gs = row[16] if row[16] and row[16] > 100 else None
            fl = row[15]
        else:
            lat, lon = row[8], row[9]  # entry position
            gs = row[11] if row[11] and row[11] > 100 else None
            fl = row[10]
        
        flights.append({
            'callsign': row[0],
            'aircraft': row[1],
            'departure': row[2],
            'destination': row[3],
            'oceanic_route': row[4],
            'ots_track': row[5],
            'filed_altitude': row[6],
            'lat': lat,
            'lon': lon,
            'fl': fl,
            'groundspeed': gs,
            'entry_time': row[7]
        })
    
    conn.close()
    return flights


def build_trajectory(flight):
    """Build trajectory from database flight"""
    if not flight['oceanic_route']:
        return None
    
    # Expand OTS tracks
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
    
    # Extract Mach from route
    mach_match = re.search(r'/M(\d{3})', flight['oceanic_route'])
    filed_mach = float(mach_match.group(1)) / 100 if mach_match else 0.85
    
    # Get FL
    try:
        filed_fl = int(flight['filed_altitude']) if flight['filed_altitude'] else flight['fl']
        if filed_fl > 1000:
            filed_fl = filed_fl // 100
    except:
        filed_fl = flight['fl'] if flight['fl'] else 370
    
    # Calculate groundspeed
    tas = mach_to_tas_simple(filed_mach, filed_fl * 100)
    gs = flight['groundspeed'] if flight['groundspeed'] else tas
    
    # Build trajectory
    trajectory = []
    current_lat, current_lon = flight['lat'], flight['lon']
    current_eta = datetime.now(UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
    
    for wpt in waypoints:
        distance = haversine(current_lat, current_lon, wpt['lat'], wpt['lon'])
        current_eta += timedelta(hours=distance / gs)
        trajectory.append({
            'waypoint': wpt['name'],
            'lat': wpt['lat'],
            'lon': wpt['lon'],
            'fl': filed_fl,
            'eta': current_eta,
            'callsign': flight['callsign']
        })
        current_lat, current_lon = wpt['lat'], wpt['lon']
    
    return trajectory


def validate_resolution(callsign, new_fl, all_trajectories, original_conflicts):
    """Check if changing a flight's FL creates new conflicts"""
    # Create modified trajectory with new FL
    modified_trajectories = []
    for traj in all_trajectories:
        if not traj:
            continue
        
        if traj[0]['callsign'] == callsign:
            # Modify this trajectory's FL
            modified_traj = []
            for point in traj:
                new_point = point.copy()
                new_point['fl'] = new_fl
                modified_traj.append(new_point)
            modified_trajectories.append(modified_traj)
        else:
            modified_trajectories.append(traj)
    
    # Detect conflicts with modified trajectory
    new_conflicts = detect_conflicts(modified_trajectories)
    
    # Check if this creates NEW conflicts (not in original list)
    original_pairs = {tuple(sorted([c['flight1'], c['flight2']])) for c in original_conflicts}
    
    for conflict in new_conflicts:
        pair = tuple(sorted([conflict['flight1'], conflict['flight2']]))
        if pair not in original_pairs:
            # New conflict created!
            return False, conflict
    
    return True, None


def suggest_resolutions(conflict, all_trajectories, all_conflicts, flights):
    """Suggest single best conflict-free resolution per aircraft"""
    current_fl = conflict['fl']
    
    # Determine flight directions
    f1 = next((f for f in flights if f['callsign'] == conflict['flight1']), None)
    f2 = next((f for f in flights if f['callsign'] == conflict['flight2']), None)
    
    if not f1 or not f2:
        return []
    
    # Eastbound = US/Canada departure (K/C), Westbound = European departure (E/L/U/G)
    f1_eb = f1['departure'][0] in 'KC'
    f2_eb = f2['departure'][0] in 'KC'
    
    # Preferred altitudes by direction
    # EB: Odd (FL350, 370, 390, 410)
    # WB: Even (FL340, 360, 380, 400)
    def get_preferred_fls(is_eastbound, current):
        if is_eastbound:
            # Odd altitudes
            options = [current + 20, current + 40, current - 20, current - 40, 
                      current + 10, current + 30, current - 10, current - 30]
        else:
            # Even altitudes
            options = [current + 20, current + 40, current - 20, current - 40,
                      current + 10, current + 30, current - 10, current - 30]
        
        # Filter for NAT range and correct odd/even
        valid = []
        for fl in options:
            if 290 <= fl <= 410:
                if is_eastbound and fl % 2 == 1:  # Odd for EB (e.g., 37 in FL370)
                    valid.append(fl)
                elif not is_eastbound and fl % 2 == 0:  # Even for WB
                    valid.append(fl)
        
        return valid
    
    resolutions = []
    
    # Try to find ONE clear resolution for each aircraft
    for callsign, is_eb in [(conflict['flight1'], f1_eb), (conflict['flight2'], f2_eb)]:
        preferred_fls = get_preferred_fls(is_eb, current_fl)
        
        for new_fl in preferred_fls:
            is_clear, new_conflict = validate_resolution(callsign, new_fl, all_trajectories, all_conflicts)
            
            if is_clear:
                resolutions.append({
                    'callsign': callsign,
                    'action': f"FL{new_fl}",
                    'change': f"{'+' if new_fl > current_fl else ''}{(new_fl - current_fl) * 100}ft",
                    'direction': 'EB' if is_eb else 'WB',
                    'status': 'CLEAR'
                })
                break  # Only need ONE per aircraft
    
    return resolutions


def detect_conflicts(all_trajectories):
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
                        'flight1': f1['callsign'],
                        'flight2': f2['callsign'],
                        'fl': f1['fl'],
                        'eta1': f1['eta'],
                        'eta2': f2['eta'],
                        'separation_min': sep_min,
                        'severity': 'HIGH' if sep_min < 3 else 'MEDIUM'
                    })
    
    return conflicts


def main():
    """Run database-driven conflict probe"""
    print("=" * 100)
    print("NAT CONFLICT PROBE - Database Analysis")
    print("=" * 100 + "\n")
    
    # Get active crossings from database
    print("Loading active NAT crossings from database...")
    flights = get_active_crossings()
    print(f"✓ Found {len(flights)} active crossings\n")
    
    if not flights:
        print("No active NAT crossings in database.")
        print("(Collector must be running to populate database)")
        return
    
    # Show active crossings
    print("Active NAT crossings:")
    print("-" * 100)
    for flight in flights[:10]:
        ots = f"[{flight['ots_track']}]" if flight['ots_track'] else "[RANDOM]"
        print(f"{flight['callsign']:10s} {flight['aircraft']:6s} "
              f"{flight['departure']}->{flight['destination']} "
              f"FL{flight['fl']:3d} {ots:10s} "
              f"{flight['lat']:6.2f}°N {flight['lon']:7.2f}°")
    if len(flights) > 10:
        print(f"... and {len(flights) - 10} more\n")
    
    # Build trajectories
    print("Building trajectories (expanding OTS tracks)...")
    all_trajectories = [build_trajectory(f) for f in flights]
    all_trajectories = [t for t in all_trajectories if t]
    print(f"✓ Built {len(all_trajectories)} trajectories\n")
    
    # Detect conflicts
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
                flight = next((f for f in flights if f['callsign'] == flight_call), None)
                if not flight:
                    continue
                
                mach_match = re.search(r'/M(\d{3})', flight['oceanic_route'])
                mach_str = f"M.{mach_match.group(1)[:2]}" if mach_match else "---"
                
                try:
                    fl = int(flight['filed_altitude']) if flight['filed_altitude'] else flight['fl']
                    if fl > 1000:
                        fl = fl // 100
                except:
                    fl = flight['fl']
                
                tas = int(mach_to_tas_simple(float(mach_match.group(1))/100 if mach_match else 0.85, fl * 100))
                gs = flight['groundspeed'] if flight['groundspeed'] else tas
                
                # Clean route
                route = re.sub(r'/[MN]\d{3,4}F?\d*', '', flight['oceanic_route'])
                route = ' '.join(route.replace('DCT', '').split())
                
                ots = f"[{flight['ots_track']}]" if flight['ots_track'] else "[RND]"
                
                print(f"  {flight['callsign']:8s} | {flight['aircraft']:6s} | {flight['departure']}->{flight['destination']} | " +
                      f"{tas:3d}kt/{mach_str} | GS {gs:3d}kt {ots}")
                print(f"           | {route[:60]}")
                print(f"           | ETA {eta.strftime('%H%M')}Z\n")
            
            # Display resolutions - ONE per aircraft, direction-aligned
            resolutions = suggest_resolutions(c, all_trajectories, conflicts, flights)
            
            if resolutions:
                print("  Resolutions:")
                for res in resolutions:
                    dir_label = f"({res['direction']})" if res.get('direction') else ""
                    print(f"    ✓ {res['callsign']} → {res['action']} {res['change']} {dir_label}")
            else:
                print("  Resolutions:")
                print("    ⚠️  No conflict-free vertical separation available")
                print("    → Consider speed adjustment or lateral offset")
    else:
        print("✅ No conflicts - adequate separation")
    
    print("\n" + "=" * 100)
    print(f"Analysis complete at {datetime.now(UTC).strftime('%H:%M:%S')}Z" if hasattr(datetime, 'UTC') else f"Analysis complete at {datetime.utcnow().strftime('%H:%M:%S')}Z")
    print("=" * 100)


if __name__ == "__main__":
    main()
