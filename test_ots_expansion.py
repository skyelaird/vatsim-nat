"""
OTS Track Expansion Integration Example

Shows how to integrate OTS track expansion into the probe
"""

from expand_ots_track import expand_ots_track
import re

def expand_route_with_ots(oceanic_route, db_path='nat_traffic.db'):
    """
    Expand any OTS tracks in the route to actual waypoints
    
    Example:
        Input:  "SUPRY/M083F340 NATV ATSUR/M082F350"
        Output: "SUPRY/M083F340 SUPRY 46N050W 48N040W 49N030W 50N020W SOMAX ATSUR ATSUR/M082F350"
    """
    # Find OTS track identifiers (NATV, NATW, etc.)
    ots_pattern = r'\bNAT[A-Z]\b'
    ots_tracks = re.findall(ots_pattern, oceanic_route)
    
    if not ots_tracks:
        return oceanic_route  # No OTS tracks, return as-is
    
    expanded_route = oceanic_route
    
    for ots_id in ots_tracks:
        # Get waypoints for this track
        waypoints = expand_ots_track(ots_id, db_path)
        
        if waypoints:
            # Replace NATV with "SUPRY 46N050W 48N040W..."
            waypoint_string = ' '.join(waypoints)
            expanded_route = expanded_route.replace(ots_id, waypoint_string)
            print(f"  Expanded {ots_id} -> {waypoint_string}")
        else:
            print(f"  WARNING: Could not expand {ots_id}")
    
    return expanded_route


# Test it
if __name__ == "__main__":
    test_routes = [
        "SUPRY/M083F340 NATV ATSUR/M082F350",
        "RAFIN/M081F370 NATW NASBA/N0456",
        "AVUTI/M085F390 DCT 59N050W 60N040W 60N030W DCT AGORI"  # Random route
    ]
    
    print("Testing OTS Track Expansion")
    print("=" * 80)
    
    for route in test_routes:
        print(f"\nOriginal: {route}")
        expanded = expand_route_with_ots(route, 'D:/GitHub/vatsim-nat/nat_traffic.db')
        print(f"Expanded: {expanded}")
