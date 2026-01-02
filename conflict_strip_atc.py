"""
NAT Conflict Probe - ATC Strip Format
Three-column layout with proper tombstone placement and SELCAL
"""

import sqlite3
from datetime import datetime, timedelta, UTC
import math
import re
from nat_waypoints import get_waypoint

DB_PATH = 'nat_traffic.db'

def haversine(lat1, lon1, lat2, lon2):
    R = 3440.065
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def mach_to_tas(mach, fl):
    alt_ft = fl * 100
    temp_c = 15 - (alt_ft / 1000 * 1.98) if alt_ft <= 36089 else -56.5
    speed_of_sound = 38.967854 * math.sqrt(temp_c + 273.15)
    return mach * speed_of_sound

def expand_ots_track(track_id):
    if not track_id.startswith('NAT') or len(track_id) != 4:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now(UTC).date()
    
    cursor.execute("""
        SELECT entry_point, lat_60w, lat_50w, lat_40w, lat_30w, lat_20w, lat_15w,
               boundary_point, exit_point
        FROM nat_ots_tracks WHERE track_letter = ? AND effective_date = ?
    """, (track_id[3], today))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    waypoints = []
    if row[0]: waypoints.append(row[0])
    
    for lat, lon in [(row[1],60), (row[2],50), (row[3],40), (row[4],30), (row[5],20), (row[6],15)]:
        if lat:
            lat_int = int(lat)
            lat_min = int((lat - lat_int) * 60)
            wpt = f"{lat_int:02d}N{lon:03d}W" if lat_min == 0 else f"{lat_int:02d}{lat_min:02d}N{lon:03d}00W"
            waypoints.append(wpt)
    
    if row[7]: waypoints.append(row[7])
    if row[8]: waypoints.append(row[8])
    
    return waypoints[1:-1] if len(waypoints) > 2 else []

def parse_waypoint(name):
    coords = get_waypoint(name)
    if coords:
        return coords['lat'], coords['lon']
    
    m = re.match(r'(\d{2})N(\d{3})W', name)
    if m:
        return int(m.group(1)), -int(m.group(2))
    
    m = re.match(r'(\d{2})(\d{2})N(\d{3})(\d{2})W', name)
    if m:
        return int(m.group(1)) + int(m.group(2))/60.0, -(int(m.group(3)) + int(m.group(4))/60.0)
    
    return None, None

def format_waypoint_short(name):
    """Format waypoint as 57/50 style"""
    # Named waypoints stay as-is
    if len(name) <= 5 and not any(c.isdigit() for c in name):
        return name
    
    # 57N050W -> 57/50
    m = re.match(r'(\d{2})N(\d{3})W', name)
    if m:
        return f"{m.group(1)}/{m.group(2)[1:]}"  # 57/50
    
    # 5730N05000W -> 5730/50
    m = re.match(r'(\d{4})N(\d{3})\d{2}W', name)
    if m:
        return f"{m.group(1)}/{m.group(2)[1:]}"
    
    return name

def simplify_aircraft_type(full_type):
    """B77W/H-SDE1E2... -> B77W/H"""
    match = re.match(r'([^/]+/[A-Z])', full_type)
    return match.group(1) if match else full_type.split('-')[0]

def get_active_crossings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT callsign, aircraft_type, departure, destination,
               oceanic_route, ots_track, filed_altitude, selcal,
               entry_lat, entry_lon, entry_fl, entry_gs,
               mid_lat, mid_lon, mid_fl, mid_gs, crossed_mid
        FROM nat_crossings WHERE exit_time IS NULL
    """)
    
    flights = []
    for row in cursor.fetchall():
        lat, lon = (row[12], row[13]) if row[16] else (row[8], row[9])
        gs = (row[15] if row[16] else row[11]) or None
        fl = row[14] if row[16] else row[10]
        
        flights.append({
            'callsign': row[0],
            'aircraft': row[1],
            'departure': row[2],
            'destination': row[3],
            'oceanic_route': row[4],
            'ots_track': row[5],
            'filed_altitude': row[6],
            'selcal': row[7],
            'lat': lat, 'lon': lon, 'fl': fl, 'gs': gs
        })
    
    conn.close()
    return flights

def build_trajectory(flight):
    if not flight['oceanic_route']:
        return None
    
    # Expand OTS
    route = flight['oceanic_route']
    for nat in re.findall(r'\bNAT[A-Z]\b', route):
        wpts = expand_ots_track(nat)
        if wpts:
            route = route.replace(nat, ' '.join(wpts))
    
    # Parse waypoints
    waypoints = []
    for part in route.split():
        if part in ['DCT'] or part.startswith('NAT'):
            continue
        name = part.split('/')[0]
        # Skip 3-letter non-coordinate waypoints
        if len(name) == 3 and not any(c.isdigit() for c in name):
            continue
        lat, lon = parse_waypoint(name)
        if lat and lon:
            waypoints.append({'name': name, 'lat': lat, 'lon': lon})
    
    if len(waypoints) < 2:
        return None
    
    # Get Mach from oceanic route
    mach_m = re.search(r'/M(\d{3})', flight['oceanic_route'])
    filed_mach = float(mach_m.group(1)) / 100 if mach_m else 0.85
    
    # Get FL from oceanic route (e.g., MALOT/M082F360 → FL360)
    fl_match = re.search(r'F(\d{3})', flight['oceanic_route'])
    if fl_match:
        fl = int(fl_match.group(1))
    else:
        try:
            fl = int(flight['filed_altitude']) if flight['filed_altitude'] else flight['fl']
            if fl > 1000: fl //= 100
        except:
            fl = flight['fl'] or 370
    
    tas = mach_to_tas(filed_mach, fl)
    gs = flight['gs'] if flight['gs'] and flight['gs'] > 100 else tas
    
    # Build trajectory with ETAs
    trajectory = []
    cur_lat, cur_lon = flight['lat'], flight['lon']
    cur_eta = datetime.now(UTC)
    
    for wpt in waypoints:
        dist = haversine(cur_lat, cur_lon, wpt['lat'], wpt['lon'])
        cur_eta += timedelta(hours=dist / gs)
        trajectory.append({
            'waypoint': wpt['name'],
            'lat': wpt['lat'],
            'lon': wpt['lon'],
            'fl': fl,
            'eta': cur_eta,
            'callsign': flight['callsign'],
            'mach': filed_mach
        })
        cur_lat, cur_lon = wpt['lat'], wpt['lon']
    
    return trajectory

def is_wrong_way(callsign, fl, flights):
    """Check if flight is on wrong odd/even for direction"""
    flight = next((f for f in flights if f['callsign'] == callsign), None)
    if not flight:
        return False
    
    is_eb = flight['departure'][0] in 'KC'
    
    # EB should be odd, WB should be even
    if is_eb:
        return fl % 2 == 0  # Wrong if even
    else:
        return fl % 2 == 1  # Wrong if odd

def detect_conflicts(trajectories, flights):
    """Detect conflicts only at ACTUAL shared waypoints AND only for future encounters"""
    conflicts = []
    conflict_counts = {}
    
    # Group flights by actual waypoint NAME
    waypoint_groups = {}
    for traj in trajectories:
        if not traj:
            continue
        for pt in traj:
            waypoint_groups.setdefault(pt['waypoint'], []).append(pt)
    
    seen_pairs = set()
    current_time = datetime.now(UTC)
    
    for waypoint, wpt_flights in waypoint_groups.items():
        if len(wpt_flights) < 2:
            continue
        
        for i in range(len(wpt_flights)):
            for j in range(i + 1, len(wpt_flights)):
                f1, f2 = wpt_flights[i], wpt_flights[j]
                
                # Same callsign = self-conflict bug, skip
                if f1['callsign'] == f2['callsign']:
                    continue
                
                # Must be at same FL
                if f1['fl'] != f2['fl']:
                    continue
                
                # CRITICAL: Only flag FUTURE conflicts
                # If ETA is in the past, they've already passed this waypoint (or stale data)
                if f1['eta'] < current_time or f2['eta'] < current_time:
                    continue
                
                pair = tuple(sorted([f1['callsign'], f2['callsign']]))
                
                # Already found a conflict for this pair?
                if pair in seen_pairs:
                    continue
                
                # Calculate time separation
                time_diff = (f2['eta'] - f1['eta']).total_seconds()
                sep_min = abs(time_diff) / 60
                
                if sep_min < 5:
                    seen_pairs.add(pair)
                    
                    conflict_counts[f1['callsign']] = conflict_counts.get(f1['callsign'], 0) + 1
                    conflict_counts[f2['callsign']] = conflict_counts.get(f2['callsign'], 0) + 1
                    
                    conflicts.append({
                        'waypoint': waypoint,
                        'flight1': f1['callsign'],
                        'flight2': f2['callsign'],
                        'fl': f1['fl'],
                        'eta1': f1['eta'],
                        'eta2': f2['eta'],
                        'mach1': f1['mach'],
                        'mach2': f2['mach'],
                        'separation_min': sep_min,
                        'severity': 'HIGH' if sep_min < 3 else 'MEDIUM'
                    })
    
    # Add metadata
    for conflict in conflicts:
        conflict['f1_count'] = conflict_counts.get(conflict['flight1'], 0)
        conflict['f2_count'] = conflict_counts.get(conflict['flight2'], 0)
        conflict['f1_wrong_way'] = is_wrong_way(conflict['flight1'], conflict['fl'], flights)
        conflict['f2_wrong_way'] = is_wrong_way(conflict['flight2'], conflict['fl'], flights)
    
    return conflicts

def get_trajectory_with_times(flight, trajectories):
    """Get trajectory points with ETAs, sorted W to E by longitude"""
    traj = next((t for t in trajectories if t and t[0]['callsign'] == flight['callsign']), None)
    if not traj:
        return []
    
    # Sort by longitude (west to east = more negative to less negative)
    sorted_traj = sorted(traj, key=lambda pt: pt['lon'])
    
    return [(pt['waypoint'], pt['eta']) for pt in sorted_traj[:8]]

def get_route_summary(route):
    """Extract origin, key waypoints, destination from oceanic route"""
    # Remove speed/alt annotations
    clean = re.sub(r'/[MN]\d{3,4}F?\d*', '', route)
    parts = [p for p in clean.split() if p != 'DCT']
    
    # Return space-separated, no ellipses
    return ' '.join(parts) if len(parts) <= 8 else ' '.join(parts[:3] + parts[-3:])

def print_atc_strip(conflict, f1, f2, f1_traj, f2_traj):
    """Print ATC strip with 3-column layout"""
    
    # Determine directions
    f1_eb = f1['departure'][0] in 'KC'
    f2_eb = f2['departure'][0] in 'KC'
    head_on = " (HEAD-ON)" if f1_eb != f2_eb else ""
    
    # Wrong-way warnings
    culprit = ""
    if conflict['f1_wrong_way'] and conflict['f1_count'] >= 3:
        culprit = f" [WRONG-WAY: {conflict['flight1']}]"
    elif conflict['f2_wrong_way'] and conflict['f2_count'] >= 3:
        culprit = f" [WRONG-WAY: {conflict['flight2']}]"
    elif conflict['f1_wrong_way']:
        culprit = f" [{conflict['flight1']} wrong FL]"
    elif conflict['f2_wrong_way']:
        culprit = f" [{conflict['flight2']} wrong FL]"
    
    # Header
    icon = '⚠️' if conflict['severity'] == 'MEDIUM' else '🚨'
    sep_int = int(conflict['separation_min'])
    print(f"\n{icon}  CONFLICT at {conflict['waypoint']} FL{conflict['fl']} - Separation: {sep_int} min{head_on}{culprit}")
    
    print("┌" + "─" * 118 + "┐")
    
    # Flight 1
    print_flight_strip(f1, f1_traj, conflict['fl'], conflict['eta1'], conflict['mach1'], f1_eb, conflict['waypoint'])
    
    print("├" + "─" * 118 + "┤")
    
    # Flight 2
    print_flight_strip(f2, f2_traj, conflict['fl'], conflict['eta2'], conflict['mach2'], f2_eb, conflict['waypoint'])
    
    print("└" + "─" * 118 + "┘")

def print_flight_strip(flight, trajectory, fl, eta, mach, is_eastbound, conflict_waypoint):
    """Print single flight strip with conflict waypoint highlighted"""
    
    TOMB_WIDTH = 12
    DATA_WIDTH = 94
    
    ac_type = simplify_aircraft_type(flight['aircraft'])
    selcal = flight['selcal'] if flight['selcal'] else ""
    route_summary = get_route_summary(flight['oceanic_route'])
    
    if is_eastbound:
        # EB: Empty left | Data center | Tombstone right
        
        # TOP: Waypoints W→E with conflict highlighted
        wpt_line = "│" + " " * TOMB_WIDTH + " "
        for wpt, _ in trajectory:
            marker = "*" if wpt == conflict_waypoint else " "
            wpt_line += f"{marker}{format_waypoint_short(wpt):6s} "
        wpt_line += " " * (DATA_WIDTH - len(wpt_line) + TOMB_WIDTH + 3)
        wpt_line += f"{flight['callsign']:8s} │"
        print(wpt_line)
        
        # MIDDLE: Times + SELCAL in left column
        time_line = f"│{selcal:^{TOMB_WIDTH}s} "
        for _, time in trajectory:
            time_line += f"{time.strftime('%H%M'):7s} "
        time_line += " " * (DATA_WIDTH - len(time_line) + TOMB_WIDTH + 3)
        time_line += f"{ac_type:8s} │"
        print(time_line)
        
        # BOTTOM: Route
        route_line = "│" + " " * TOMB_WIDTH + f" {route_summary}"
        route_line += " " * (DATA_WIDTH - len(route_line) + TOMB_WIDTH + 3)
        route_line += f"FL{fl:3d}    │"
        print(route_line)
        
    else:
        # WB: Tombstone left | Data center | Empty right
        
        # TOP: Waypoints W→E with conflict highlighted
        wpt_line = f"│{flight['callsign']:^{TOMB_WIDTH}s} "
        for wpt, _ in trajectory:
            marker = "*" if wpt == conflict_waypoint else " "
            wpt_line += f"{marker}{format_waypoint_short(wpt):6s} "
        wpt_line += " " * (120 - len(wpt_line)) + "│"
        print(wpt_line)
        
        # MIDDLE: Times + SELCAL in right column
        time_line = f"│{ac_type:^{TOMB_WIDTH}s} "
        for _, time in trajectory:
            time_line += f"{time.strftime('%H%M'):7s} "
        time_line += " " * (106 - len(time_line))
        time_line += f"{selcal:>10s} │"
        print(time_line)
        
        # BOTTOM: Route
        route_line = f"│FL{fl:3d}       {route_summary}"
        route_line += " " * (120 - len(route_line)) + "│"
        print(route_line)

def main():
    print("=" * 120)
    print("NAT CONFLICT PROBE - ATC Strip Format")
    print("=" * 120 + "\n")
    
    flights = get_active_crossings()
    print(f"✓ {len(flights)} active crossings\n")
    
    if not flights:
        print("No active crossings")
        return
    
    trajectories = [build_trajectory(f) for f in flights]
    trajectories = [t for t in trajectories if t]
    print(f"✓ {len(trajectories)} trajectories\n")
    
    conflicts = detect_conflicts(trajectories, flights)
    print(f"✓ {len(conflicts)} conflicts\n")
    
    if conflicts:
        print("=" * 120)
        print("CONFLICTS")
        print("=" * 120)
        
        for c in conflicts:
            f1 = next((f for f in flights if f['callsign'] == c['flight1']), None)
            f2 = next((f for f in flights if f['callsign'] == c['flight2']), None)
            
            if f1 and f2:
                f1_traj = get_trajectory_with_times(f1, trajectories)
                f2_traj = get_trajectory_with_times(f2, trajectories)
                print_atc_strip(c, f1, f2, f1_traj, f2_traj)
        
        print("\n" + "=" * 120)
    else:
        print("✅ No conflicts\n" + "=" * 120)

if __name__ == "__main__":
    main()
