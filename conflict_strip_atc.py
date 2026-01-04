"""
NAT Conflict Probe - ATC Strip Format
Three-column layout with proper tombstone placement and SELCAL
"""

import sqlite3
from datetime import datetime, timedelta, UTC
import math
import re
from pathlib import Path
from nat_waypoints import get_waypoint

DB_PATH = Path(__file__).parent / 'nat_traffic.db'

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
               mid_lat, mid_lon, mid_fl, mid_gs, crossed_mid,
               current_lat, current_lon, current_fl, current_gs, last_update_time
        FROM nat_crossings 
        WHERE exit_time IS NULL
        -- Only flights with recent position updates (within last 15 minutes)
        AND last_update_time IS NOT NULL
        AND (julianday('now') - julianday(last_update_time)) * 24 * 60 < 15
    """)
    
    flights = []
    for row in cursor.fetchall():
        # Prioritize current position (most recent collector update)
        # Fallback: mid position if crossed midpoint, otherwise entry position
        if row[17] and row[18]:  # current_lat, current_lon exist
            lat, lon = row[17], row[18]
            fl = row[19]
            gs = row[20]
        elif row[16]:  # crossed_mid = True
            lat, lon = row[12], row[13]
            fl = row[14]
            gs = row[15]
        else:  # use entry
            lat, lon = row[8], row[9]
            fl = row[10]
            gs = row[11]
        
        gs = gs if gs and gs > 100 else None
        
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
            # Filter NAT region only: 45N-65N, 60W-10W
            if 45 <= lat <= 65 and -60 <= lon <= -10:
                waypoints.append({'name': name, 'lat': lat, 'lon': lon})
    
    if len(waypoints) < 2:
        return None
    
    # Get Mach from oceanic route
    mach_m = re.search(r'/M(\d{3})', flight['oceanic_route'])
    filed_mach = float(mach_m.group(1)) / 100 if mach_m else 0.85
    
    # Get FL from oceanic route (e.g., MALOT/M082F360 → FL360)
    fl_match = re.search(r'F(\d{3})', flight['oceanic_route'])
    if fl_match:
        fl = int(fl_match.group(1))  # Oceanic cruise level
    else:
        try:
            fl = int(flight['filed_altitude']) if flight['filed_altitude'] else 370
            if fl > 1000: fl //= 100
        except:
            fl = 370
    
    tas = mach_to_tas(filed_mach, fl)
    gs = flight['gs'] if flight['gs'] and flight['gs'] > 100 else tas
    
    # Current aircraft position
    current_lat = flight['lat']
    current_lon = flight['lon']
    current_time = datetime.now(UTC)
    
    # Find first waypoint AHEAD of current position
    # Simple approach: find closest waypoint, assume we're heading toward remaining waypoints
    min_dist = float('inf')
    start_idx = 0
    
    for i, wpt in enumerate(waypoints):
        dist = haversine(current_lat, current_lon, wpt['lat'], wpt['lon'])
        if dist < min_dist:
            min_dist = dist
            start_idx = i
    
    # Build trajectory from current position to all FUTURE waypoints
    trajectory = []
    cur_lat, cur_lon = current_lat, current_lon
    cur_eta = current_time
    
    for wpt in waypoints[start_idx:]:
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
    
    return trajectory if len(trajectory) > 0 else None

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
                if f1['eta'] < current_time or f2['eta'] < current_time:
                    continue
                
                pair = tuple(sorted([f1['callsign'], f2['callsign']]))
                
                # Calculate time separation
                time_diff = (f2['eta'] - f1['eta']).total_seconds()
                sep_min = abs(time_diff) / 60
                
                if sep_min < 5:
                    # First conflict for this pair? Create new conflict entry
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        
                        conflict_counts[f1['callsign']] = conflict_counts.get(f1['callsign'], 0) + 1
                        conflict_counts[f2['callsign']] = conflict_counts.get(f2['callsign'], 0) + 1
                        
                        conflicts.append({
                            'waypoint': waypoint,
                            'waypoints': [waypoint],  # List of all conflicted waypoints
                            'separations': [sep_min],  # Track separation at each waypoint
                            'flight1': f1['callsign'],
                            'flight2': f2['callsign'],
                            'fl': f1['fl'],
                            'eta1': f1['eta'],
                            'eta2': f2['eta'],
                            'mach1': f1['mach'],
                            'mach2': f2['mach'],
                            'separation_min': sep_min,
                            'severity': 'HIGH' if sep_min < 3 else 'MEDIUM',
                            'is_overtake': False
                        })
                    else:
                        # Add this waypoint to existing conflict
                        for conflict in conflicts:
                            if conflict['flight1'] in pair and conflict['flight2'] in pair:
                                conflict['waypoints'].append(waypoint)
                                conflict['separations'].append(sep_min)
                                # Update to minimum separation
                                if sep_min < conflict['separation_min']:
                                    conflict['separation_min'] = sep_min
                                    conflict['waypoint'] = waypoint  # Primary conflict point
                                    conflict['severity'] = 'HIGH' if sep_min < 3 else 'MEDIUM'
                                break
    
    # Analyze overtakes: check separation trend across waypoints
    for conflict in conflicts:
        if len(conflict['separations']) >= 2:
            first_sep = conflict['separations'][0]
            last_sep = conflict['separations'][-1]
            
            # Separation closing by >1 minute = overtake
            if first_sep - last_sep > 1.0:
                conflict['is_overtake'] = True
                conflict['separation_closing'] = first_sep - last_sep
                conflict['severity'] = 'CRITICAL'  # Overtakes are always critical
                conflict['type'] = 'OVERTAKE'
            else:
                conflict['type'] = 'LEVEL'
    
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
    """Print ATC strip with 4-line layout: waypoints, times, mach/gs/route, FL"""
    
    # Determine directions
    f1_eb = f1['departure'][0] in 'KC'
    f2_eb = f2['departure'][0] in 'KC'
    head_on = " (HEAD-ON)" if f1_eb != f2_eb else ""
    
    # Detect overtake: same direction but separation closing
    overtake = ""
    if f1_eb == f2_eb and len(conflict['waypoints']) > 1:
        # Get first and last conflicted waypoints in trajectory order
        # Check separation trend across the conflict
        first_wpt_times = []
        last_wpt_times = []
        
        for wpt, t in f1_traj:
            if wpt == conflict['waypoints'][0]:
                first_wpt_times.append(t)
            if wpt == conflict['waypoints'][-1]:
                last_wpt_times.append(t)
        
        for wpt, t in f2_traj:
            if wpt == conflict['waypoints'][0]:
                first_wpt_times.append(t)
            if wpt == conflict['waypoints'][-1]:
                last_wpt_times.append(t)
        
        if len(first_wpt_times) == 2 and len(last_wpt_times) == 2:
            first_sep = abs((first_wpt_times[0] - first_wpt_times[1]).total_seconds() / 60)
            last_sep = abs((last_wpt_times[0] - last_wpt_times[1]).total_seconds() / 60)
            
            if first_sep > last_sep + 1:  # Separation decreasing
                overtake = " 🔴 OVERTAKE - CLOSING"
    
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
    print(f"\n{icon}  CONFLICT at {conflict['waypoint']} FL{conflict['fl']} - Separation: {sep_int} min{head_on}{overtake}{culprit}")
    
    print("┌" + "─" * 118 + "┐")
    
    # Flight 1
    print_flight_strip(f1, f1_traj, conflict['fl'], conflict['eta1'], conflict['mach1'], f1_eb, conflict['waypoints'])
    
    print("├" + "─" * 118 + "┤")
    
    # Flight 2
    print_flight_strip(f2, f2_traj, conflict['fl'], conflict['eta2'], conflict['mach2'], f2_eb, conflict['waypoints'])
    
    print("└" + "─" * 118 + "┘")

def print_flight_strip(flight, trajectory, fl, eta, mach, is_eastbound, conflict_waypoints):
    """Print single flight strip: waypoints / times / mach+gs+route / FL
    conflict_waypoints is a list of all waypoints in conflict
    """
    
    ac_type = simplify_aircraft_type(flight['aircraft'])
    selcal = flight['selcal'] if flight['selcal'] else ""
    route_summary = get_route_summary(flight['oceanic_route'])
    gs = flight.get('gs', 0)
    
    # Build waypoint and time columns - each gets exactly 9 chars
    wpt_parts = []
    time_parts = []
    for wpt, time in trajectory:
        marker = "*" if wpt in conflict_waypoints else " "
        wpt_short = format_waypoint_short(wpt)
        wpt_parts.append(f"{marker}{wpt_short:6s}  ")
        time_parts.append(f"{time.strftime('%H%M'):^9s}")
    
    wpt_line = "".join(wpt_parts).rstrip()
    time_line = "".join(time_parts)
    
    # Mach and groundspeed line
    mach_gs = f"M.{int(mach*100):02d} G{int(gs):03d}" if gs else f"M.{int(mach*100):02d}"
    
    # Show current FL in brackets if different from filed
    current_fl = flight.get('fl', fl)
    fl_display = f"FL{fl}" if current_fl == fl else f"FL{fl} ({current_fl})"
    
    if is_eastbound:
        # EB: Tombstone on right
        print(f"│           {wpt_line:<88s}{flight['callsign']:>8s} │")
        print(f"│  {selcal:8s} {time_line:<88s}{ac_type:>8s} │")
        print(f"│  {mach_gs:10s} {'':97s} │")
        print(f"│  {fl_display:<12s} {route_summary:<92s} │")
    else:
        # WB: Tombstone on left
        print(f"│{flight['callsign']:^10s} {wpt_line:<89s}{selcal:>8s} │")
        print(f"│{ac_type:^10s} {time_line:<97s} │")
        print(f"│{mach_gs:^10s} {'':97s} │")
        print(f"│{fl_display:<14s} {route_summary:<93s} │")

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
        current_time = datetime.now(UTC).strftime('%H%MZ')
        print("=" * 120)
        print(f"CONFLICTS - {current_time}")
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
