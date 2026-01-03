"""
Debug why VIR127B/D not showing in conflict
"""
import sys
sys.path.insert(0, 'D:/GitHub/vatsim-nat')
from conflict_strip_atc import get_active_crossings, build_trajectory

flights = get_active_crossings()
print(f"Total flights from get_active_crossings(): {len(flights)}")

# Find VIR127 flights
vir_flights = [f for f in flights if 'VIR127' in f['callsign']]
print(f"\nVIR127 flights found: {len(vir_flights)}")

for f in vir_flights:
    print(f"\n{f['callsign']}:")
    print(f"  oceanic_route: {f['oceanic_route']}")
    print(f"  current FL: {f['fl']}")
    print(f"  lat/lon: {f['lat']:.2f}, {f['lon']:.2f}")
    print(f"  gs: {f['gs']}")
    
    # Try building trajectory
    traj = build_trajectory(f)
    if traj:
        print(f"  ✓ Trajectory built: {len(traj)} waypoints")
        print(f"  Waypoints: {[t['waypoint'] for t in traj]}")
        print(f"  FLs: {set([t['fl'] for t in traj])}")
    else:
        print(f"  ✗ Trajectory build FAILED")
