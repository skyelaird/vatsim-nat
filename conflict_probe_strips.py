"""
NAT Conflict Probe - ATC Strip Display Version
===============================================

Database-driven with visual strip-style presentation
"""

import sqlite3
from datetime import datetime, timedelta, UTC
import math
import re
from nat_waypoints import get_waypoint
from route_parser import extract_oceanic_route

# Constants
SPEED_OF_SOUND_FL370 = 573
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
    """Expand OTS tracks in route"""
    ots_tracks = re.findall(r'\bNAT[A-Z]\b', oceanic_route)
    
    if not ots_tracks:
        return oceanic_route
    
    expanded = oceanic_route
    for ots_id in ots_tracks:
        waypoints = expand_ots_track_inline(ots_id)
        if waypoints and len(waypoints) > 2:
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
    
    match = re.match(r'(\d{2})N(\d{3})W', waypoint_name)
    if match:
        return int(match.group(1)), -int(match.group(2))
    
    match = re.match(r'(\d{2})(\d{2})N(\d{3})(\d{2})W', waypoint_name)
    if match:
        lat = int(match.group(1)) + int(match.group(2)) / 60.0
        lon = -(int(match.group(3)) + int(match.group(4)) / 60.0)
        return lat, lon
    
    return None, None


def extract_waypoints_from_route(route):
    """Extract clean waypoint list from route"""
    clean = re.sub(r'/[MN]\d{3,4}F?\d*', '', route)
    parts = clean.split()
    waypoints = [p for p in parts if p != 'DCT' and not p.startswith('NAT')]
    return waypoints


def get_active_crossings():
    """Get active crossings from database"""
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
        if row[17]:  # crossed_mid
            lat, lon = row[13], row[14]
            gs = row[16] if row[16] and row[16] > 100 else None
            fl = row[15]
        else:
            lat, lon = row[8], row[9]
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
    """Build trajectory from flight"""
    if not flight['oceanic_route']:
        return None
    
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
    
    mach_match = re.search(r'/M(\d{3})', flight['oceanic_route'])
    filed_mach = float(mach_match.group(1)) / 100 if mach_match else 0.85
    
    try:
        filed_fl = int(flight['filed_altitude']) if flight['filed_altitude'] else flight['fl']
        if filed_fl > 1000:
            filed_fl = filed_fl // 100
    except:
        filed_fl = flight['fl'] if flight['fl'] else 370
    
    tas = mach_to_tas_simple(filed_mach, filed_fl * 100)
    gs = flight['groundspeed'] if flight['groundspeed'] else tas
    
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


def detect_conflicts(all_trajectories):
    """Find conflicts"""
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


def print_strip_eb_eb(conflict, f1, f2, f1_wpts, f2_wpts):
    """Both eastbound - tombstone right"""
    print(f"┌{'─' * 116}┐")
    
    # Flight 1
    wpt_line = "│ "
    for wpt in f1_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (100 - len(wpt_line)) + f"{f1['callsign']:8s} │"
    print(wpt_line)
    
    ots = f"[{f1['ots_track']}]" if f1['ots_track'] else "[RND]"
    info_line = f"│ {f1['departure']}→{f1['destination']:4s}  {ots:8s}"
    info_line += " " * (90 - len(info_line)) + f"{f1['aircraft'][:10]:10s} │"
    print(info_line)
    
    eta_line = f"│ ETA {conflict['eta1'].strftime('%H%M')}Z"
    eta_line += " " * (100 - len(eta_line)) + f"FL{f1['fl']:3d}    │"
    print(eta_line)
    
    print(f"├{'─' * 116}┤")
    
    # Flight 2
    wpt_line = "│ "
    for wpt in f2_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (100 - len(wpt_line)) + f"{f2['callsign']:8s} │"
    print(wpt_line)
    
    ots = f"[{f2['ots_track']}]" if f2['ots_track'] else "[RND]"
    info_line = f"│ {f2['departure']}→{f2['destination']:4s}  {ots:8s}"
    info_line += " " * (90 - len(info_line)) + f"{f2['aircraft'][:10]:10s} │"
    print(info_line)
    
    eta_line = f"│ ETA {conflict['eta2'].strftime('%H%M')}Z"
    eta_line += " " * (100 - len(eta_line)) + f"FL{f2['fl']:3d}    │"
    print(eta_line)
    
    print(f"└{'─' * 116}┘")


def print_strip_wb_wb(conflict, f1, f2, f1_wpts, f2_wpts):
    """Both westbound - tombstone left"""
    print(f"┌{'─' * 116}┐")
    
    # Flight 1
    wpt_line = f"│ {f1['callsign']:8s}  "
    for wpt in f1_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (117 - len(wpt_line)) + "│"
    print(wpt_line)
    
    ots = f"[{f1['ots_track']}]" if f1['ots_track'] else "[RND]"
    info_line = f"│ {f1['aircraft'][:10]:10s}  {f1['departure']}→{f1['destination']:4s}  {ots:8s}"
    info_line += " " * (117 - len(info_line)) + "│"
    print(info_line)
    
    eta_line = f"│ FL{f1['fl']:3d}     ETA {conflict['eta1'].strftime('%H%M')}Z"
    eta_line += " " * (117 - len(eta_line)) + "│"
    print(eta_line)
    
    print(f"├{'─' * 116}┤")
    
    # Flight 2
    wpt_line = f"│ {f2['callsign']:8s}  "
    for wpt in f2_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (117 - len(wpt_line)) + "│"
    print(wpt_line)
    
    ots = f"[{f2['ots_track']}]" if f2['ots_track'] else "[RND]"
    info_line = f"│ {f2['aircraft'][:10]:10s}  {f2['departure']}→{f2['destination']:4s}  {ots:8s}"
    info_line += " " * (117 - len(info_line)) + "│"
    print(info_line)
    
    eta_line = f"│ FL{f2['fl']:3d}     ETA {conflict['eta2'].strftime('%H%M')}Z"
    eta_line += " " * (117 - len(eta_line)) + "│"
    print(eta_line)
    
    print(f"└{'─' * 116}┘")


def print_strip_wb_eb(conflict, wb, eb, wb_wpts, eb_wpts):
    """Opposite directions"""
    print(f"┌{'─' * 116}┐")
    
    # WB - tombstone left
    wpt_line = f"│ {wb['callsign']:8s}  "
    for wpt in wb_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (117 - len(wpt_line)) + "│"
    print(wpt_line)
    
    ots = f"[{wb['ots_track']}]" if wb['ots_track'] else "[RND]"
    info_line = f"│ {wb['aircraft'][:10]:10s}  {wb['departure']}→{wb['destination']:4s}  {ots:8s}  FL{wb['fl']:3d}  ETA {conflict['eta1'].strftime('%H%M')}Z"
    info_line += " " * (117 - len(info_line)) + "│"
    print(info_line)
    
    print(f"├{'─' * 116}┤")
    
    # EB - tombstone right
    wpt_line = "│ "
    for wpt in eb_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (100 - len(wpt_line)) + f"{eb['callsign']:8s} │"
    print(wpt_line)
    
    ots = f"[{eb['ots_track']}]" if eb['ots_track'] else "[RND]"
    info_line = f"│ ETA {conflict['eta2'].strftime('%H%M')}Z  FL{eb['fl']:3d}  {ots:8s}  {eb['departure']}→{eb['destination']:4s}"
    info_line += " " * (90 - len(info_line)) + f"{eb['aircraft'][:10]:10s} │"
    print(info_line)
    
    print(f"└{'─' * 116}┘")


def display_conflict_strip(conflict, flights):
    """Display conflict as ATC strip"""
    f1 = next((f for f in flights if f['callsign'] == conflict['flight1']), None)
    f2 = next((f for f in flights if f['callsign'] == conflict['flight2']), None)
    
    if not f1 or not f2:
        return
    
    # Determine directions
    f1_wb = f1['departure'][0] in 'EGLU'
    f2_wb = f2['departure'][0] in 'EGLU'
    
    # Extract waypoints
    f1_wpts = extract_waypoints_from_route(f1['oceanic_route'])
    f2_wpts = extract_waypoints_from_route(f2['oceanic_route'])
    
    # Print header
    icon = '🚨' if conflict['severity'] == 'HIGH' else '⚠️'
    print(f"\n{icon}  CONFLICT at {conflict['waypoint']} FL{conflict['fl']} - Separation: {conflict['separation_min']:.1f} min")
    
    # Print appropriate strip
    if f1_wb and f2_wb:
        print_strip_wb_wb(conflict, f1, f2, f1_wpts, f2_wpts)
    elif not f1_wb and not f2_wb:
        print_strip_eb_eb(conflict, f1, f2, f1_wpts, f2_wpts)
    else:
        if f1_wb:
            print_strip_wb_eb(conflict, f1, f2, f1_wpts, f2_wpts)
        else:
            print_strip_wb_eb(conflict, f2, f1, f2_wpts, f1_wpts)


def main():
    """Run probe with strip display"""
    print("=" * 120)
    print("NAT CONFLICT PROBE - ATC Strip Display")
    print("=" * 120 + "\n")
    
    print("Loading active crossings from database...")
    flights = get_active_crossings()
    print(f"✓ {len(flights)} active crossings\n")
    
    if not flights:
        print("No active crossings in database")
        return
    
    print("Building trajectories...")
    all_trajectories = [build_trajectory(f) for f in flights]
    all_trajectories = [t for t in all_trajectories if t]
    print(f"✓ {len(all_trajectories)} trajectories\n")
    
    print("Detecting conflicts...")
    conflicts = detect_conflicts(all_trajectories)
    print(f"✓ {len(conflicts)} conflicts found\n")
    
    if conflicts:
        print("=" * 120)
        print("CONFLICTS DETECTED")
        print("=" * 120)
        
        for conflict in conflicts:
            display_conflict_strip(conflict, flights)
        
        print("\n" + "=" * 120)
    else:
        print("✅ No conflicts - adequate separation\n")
        print("=" * 120)


if __name__ == "__main__":
    main()
