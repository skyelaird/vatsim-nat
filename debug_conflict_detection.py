"""
Debug conflict detection for VIR127B/D
"""
import sys
sys.path.insert(0, 'D:/GitHub/vatsim-nat')
from conflict_strip_atc import get_active_crossings, build_trajectory, detect_conflicts
from datetime import datetime, UTC

flights = get_active_crossings()
print(f"Active flights: {len(flights)}")

trajectories = [build_trajectory(f) for f in flights]
valid_traj = [t for t in trajectories if t]
print(f"Valid trajectories: {len(valid_traj)}")

# Check VIR127 trajectories
for traj in valid_traj:
    if traj and 'VIR127' in traj[0]['callsign']:
        print(f"\n{traj[0]['callsign']} trajectory:")
        for pt in traj:
            eta_str = pt['eta'].strftime('%H%M')
            future = "FUTURE" if pt['eta'] > datetime.now(UTC) else "PAST"
            print(f"  {pt['waypoint']:10s} FL{pt['fl']} ETA {eta_str} ({future})")

print("\n" + "="*60)
conflicts = detect_conflicts(trajectories, flights)
print(f"Conflicts detected: {len(conflicts)}")

if conflicts:
    for c in conflicts:
        print(f"\n{c['flight1']} vs {c['flight2']} at {c['waypoint']} FL{c['fl']}")
        print(f"  Waypoints: {c['waypoints']}")
        print(f"  Separation: {c['separation_min']:.1f} min")
else:
    print("\nNo conflicts detected!")
    
# Manual check - look for VIR127 at each waypoint
print("\n" + "="*60)
print("Manual waypoint check:")

waypoint_groups = {}
for traj in valid_traj:
    if not traj:
        continue
    for pt in traj:
        if pt['eta'] > datetime.now(UTC):  # Future only
            key = (pt['waypoint'], pt['fl'])
            if key not in waypoint_groups:
                waypoint_groups[key] = []
            waypoint_groups[key].append((pt['callsign'], pt['eta']))

for (wpt, fl), flights_at_wpt in waypoint_groups.items():
    if len(flights_at_wpt) > 1:
        # Check if VIR127 is in this group
        callsigns = [f[0] for f in flights_at_wpt]
        if any('VIR127' in cs for cs in callsigns):
            print(f"\n{wpt} FL{fl}:")
            for cs, eta in sorted(flights_at_wpt, key=lambda x: x[1]):
                print(f"  {cs:10s} {eta.strftime('%H%M')}")
