"""
Debug conflict detection to see why no conflicts found
"""
import sqlite3
from datetime import datetime, UTC
import sys
sys.path.insert(0, 'D:/GitHub/vatsim-nat')
from conflict_strip_atc import get_active_crossings, build_trajectory, detect_conflicts

flights = get_active_crossings()
print(f"Active crossings: {len(flights)}")

trajectories = [build_trajectory(f) for f in flights]
trajectories = [t for t in trajectories if t]
print(f"Valid trajectories: {len(trajectories)}")

# Check for VIR127B and VIR127D specifically
vir_flights = [f for f in flights if 'VIR127' in f['callsign']]
print(f"\nVIR127 flights found: {len(vir_flights)}")
for f in vir_flights:
    print(f"  {f['callsign']}: FL{f['fl']} - {f['oceanic_route'][:50]}")
    traj = build_trajectory(f)
    if traj:
        print(f"    Trajectory: {len(traj)} waypoints")
        print(f"    Waypoints: {[t['waypoint'] for t in traj[:5]]}")
        print(f"    FLs: {[t['fl'] for t in traj[:5]]}")

conflicts = detect_conflicts(trajectories, flights)
print(f"\nConflicts detected: {len(conflicts)}")
