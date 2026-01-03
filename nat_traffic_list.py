"""
NAT Traffic List - Reality check for conflict probe
Shows all active NAT crossings with key planning data
"""
import sqlite3
from datetime import datetime, UTC

DB_PATH = 'nat_traffic.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT callsign, departure, destination, ots_track, oceanic_route,
           entry_time, last_update_time,
           ROUND((julianday('now') - julianday(last_update_time)) * 24 * 60, 1) as min_ago,
           current_lat, current_lon, current_fl
    FROM nat_crossings
    WHERE exit_time IS NULL
    ORDER BY departure, ots_track, callsign
""")

flights = cursor.fetchall()
conn.close()

print("=" * 140)
print(f"NAT TRAFFIC LIST - {datetime.now(UTC).strftime('%H%MZ')} - {len(flights)} Active Crossings")
print("=" * 140)
print(f"{'Callsign':<10} {'Dir':<3} {'Track':<6} {'FL':<5} {'Position':<15} {'Updated':<10} {'Entry':<8} {'Route Summary':<60}")
print("-" * 140)

for row in flights:
    callsign, dep, dest, track, route, entry, last_upd, min_ago, lat, lon, fl = row
    
    # Determine direction
    direction = "EB" if dep and dep[0] in 'KC' else "WB"
    
    # Track
    track_str = track if track else "RND"
    
    # FL
    fl_str = f"FL{fl}" if fl else "---"
    
    # Position
    if lat and lon:
        pos_str = f"{lat:5.1f},{lon:6.1f}"
    else:
        pos_str = "Unknown"
    
    # Last update
    if min_ago is not None:
        if min_ago < 1:
            upd_str = "<1 min"
        elif min_ago < 60:
            upd_str = f"{int(min_ago)} min"
        else:
            upd_str = f"{int(min_ago/60)}h{int(min_ago%60):02d}m"
    else:
        upd_str = "Never"
    
    # Entry time
    if entry:
        entry_dt = datetime.fromisoformat(entry.replace('Z', '+00:00'))
        entry_str = entry_dt.strftime('%d/%H%M')
    else:
        entry_str = "---"
    
    # Route summary (first 3 and last 3 waypoints)
    route_parts = route.split() if route else []
    if len(route_parts) > 6:
        route_sum = ' '.join(route_parts[:3]) + ' ... ' + ' '.join(route_parts[-3:])
    else:
        route_sum = ' '.join(route_parts)
    route_sum = route_sum[:60]  # Truncate if too long
    
    print(f"{callsign:<10} {direction:<3} {track_str:<6} {fl_str:<5} {pos_str:<15} {upd_str:<10} {entry_str:<8} {route_sum:<60}")

print("-" * 140)
print(f"Total: {len(flights)} flights")
print("=" * 140)

# Write to file for analysis
with open('nat_traffic_list.txt', 'w') as f:
    f.write("=" * 140 + "\n")
    f.write(f"NAT TRAFFIC LIST - {datetime.now(UTC).strftime('%H%MZ')} - {len(flights)} Active Crossings\n")
    f.write("=" * 140 + "\n")
    f.write(f"{'Callsign':<10} {'Dir':<3} {'Track':<6} {'FL':<5} {'Position':<15} {'Updated':<10} {'Entry':<8} {'Route Summary':<60}\n")
    f.write("-" * 140 + "\n")
    
    cursor = sqlite3.connect(DB_PATH).cursor()
    cursor.execute("""
        SELECT callsign, departure, destination, ots_track, oceanic_route,
               entry_time, last_update_time,
               ROUND((julianday('now') - julianday(last_update_time)) * 24 * 60, 1) as min_ago,
               current_lat, current_lon, current_fl
        FROM nat_crossings
        WHERE exit_time IS NULL
        ORDER BY departure, ots_track, callsign
    """)
    
    for row in cursor.fetchall():
        callsign, dep, dest, track, route, entry, last_upd, min_ago, lat, lon, fl = row
        direction = "EB" if dep and dep[0] in 'KC' else "WB"
        track_str = track if track else "RND"
        fl_str = f"FL{fl}" if fl else "---"
        pos_str = f"{lat:5.1f},{lon:6.1f}" if lat and lon else "Unknown"
        
        if min_ago is not None:
            if min_ago < 1:
                upd_str = "<1 min"
            elif min_ago < 60:
                upd_str = f"{int(min_ago)} min"
            else:
                upd_str = f"{int(min_ago/60)}h{int(min_ago%60):02d}m"
        else:
            upd_str = "Never"
        
        if entry:
            entry_dt = datetime.fromisoformat(entry.replace('Z', '+00:00'))
            entry_str = entry_dt.strftime('%d/%H%M')
        else:
            entry_str = "---"
        
        route_parts = route.split() if route else []
        if len(route_parts) > 6:
            route_sum = ' '.join(route_parts[:3]) + ' ... ' + ' '.join(route_parts[-3:])
        else:
            route_sum = ' '.join(route_parts)
        route_sum = route_sum[:60]
        
        f.write(f"{callsign:<10} {direction:<3} {track_str:<6} {fl_str:<5} {pos_str:<15} {upd_str:<10} {entry_str:<8} {route_sum:<60}\n")
    
    f.write("-" * 140 + "\n")
    f.write(f"Total: {len(flights)} flights\n")
    f.write("=" * 140 + "\n")

print("\n✓ Saved to nat_traffic_list.txt")
