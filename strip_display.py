"""
NAT Conflict Probe - ATC Strip Display
=======================================

Visual strip-style conflict presentation
"""

def format_conflict_strip(conflict, flight1_data, flight2_data):
    """
    Format conflict as ATC-style strip
    
    Westbound: Left side (tombstone left)
    Eastbound: Right side (tombstone right)
    """
    
    # Determine direction
    f1_wb = flight1_data['departure'][0] in 'EGLU'  # European departure = WB
    f2_wb = flight2_data['departure'][0] in 'EGLU'
    
    # Extract waypoints from oceanic route
    def extract_waypoints(route):
        import re
        # Remove speed/alt annotations
        clean = re.sub(r'/[MN]\d{3,4}F?\d*', '', route)
        parts = clean.split()
        waypoints = [p for p in parts if p != 'DCT' and not p.startswith('NAT')]
        return waypoints
    
    f1_wpts = extract_waypoints(flight1_data['oceanic_route'])
    f2_wpts = extract_waypoints(flight2_data['oceanic_route'])
    
    # Build strip
    print("=" * 120)
    print(f"🚨 CONFLICT at {conflict['waypoint']} FL{conflict['fl']} - Separation: {conflict['separation_min']:.1f} min")
    print("=" * 120)
    
    # Header
    if f1_wb and f2_wb:
        # Both westbound
        print_strip_wb_wb(conflict, flight1_data, flight2_data, f1_wpts, f2_wpts)
    elif not f1_wb and not f2_wb:
        # Both eastbound
        print_strip_eb_eb(conflict, flight1_data, flight2_data, f1_wpts, f2_wpts)
    else:
        # Opposite directions
        if f1_wb:
            print_strip_wb_eb(conflict, flight1_data, flight2_data, f1_wpts, f2_wpts)
        else:
            print_strip_wb_eb(conflict, flight2_data, flight1_data, f2_wpts, f1_wpts)


def print_strip_eb_eb(conflict, f1, f2, f1_wpts, f2_wpts):
    """Both eastbound - tombstone on right"""
    
    # Flight 1 strip
    print(f"┌{'─' * 116}┐")
    
    # Waypoint progression (left to right for EB)
    wpt_line = "│ "
    for wpt in f1_wpts[:8]:  # Show first 8 waypoints
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (100 - len(wpt_line)) + f"{f1['callsign']:8s} │"
    print(wpt_line)
    
    # Aircraft/route info
    info_line = f"│ {f1['departure']}→{f1['destination']:4s}  "
    ots = f"[{f1['ots_track']}]" if f1['ots_track'] else "[RND]"
    info_line += f"{ots:8s}  "
    info_line += " " * (90 - len(info_line))
    info_line += f"{f1['aircraft']:6s} │"
    print(info_line)
    
    # ETA line
    eta_line = f"│ ETA {conflict['eta1'].strftime('%H%M')}Z"
    eta_line += " " * (100 - len(eta_line))
    eta_line += f"FL{f1['fl']:3d}    │"
    print(eta_line)
    
    print(f"├{'─' * 116}┤")
    
    # Flight 2 strip
    wpt_line = "│ "
    for wpt in f2_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (100 - len(wpt_line)) + f"{f2['callsign']:8s} │"
    print(wpt_line)
    
    info_line = f"│ {f2['departure']}→{f2['destination']:4s}  "
    ots = f"[{f2['ots_track']}]" if f2['ots_track'] else "[RND]"
    info_line += f"{ots:8s}  "
    info_line += " " * (90 - len(info_line))
    info_line += f"{f2['aircraft']:6s} │"
    print(info_line)
    
    eta_line = f"│ ETA {conflict['eta2'].strftime('%H%M')}Z"
    eta_line += " " * (100 - len(eta_line))
    eta_line += f"FL{f2['fl']:3d}    │"
    print(eta_line)
    
    print(f"└{'─' * 116}┘")


def print_strip_wb_wb(conflict, f1, f2, f1_wpts, f2_wpts):
    """Both westbound - tombstone on left"""
    
    # Flight 1 strip
    print(f"┌{'─' * 116}┐")
    
    # Tombstone first (left side for WB)
    wpt_line = f"│ {f1['callsign']:8s}  "
    # Waypoint progression (right to left for WB, but display left to right)
    for wpt in f1_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (117 - len(wpt_line)) + "│"
    print(wpt_line)
    
    info_line = f"│ {f1['aircraft']:6s}  "
    info_line += f"{f1['departure']}→{f1['destination']:4s}  "
    ots = f"[{f1['ots_track']}]" if f1['ots_track'] else "[RND]"
    info_line += f"{ots:8s}"
    info_line += " " * (117 - len(info_line)) + "│"
    print(info_line)
    
    eta_line = f"│ FL{f1['fl']:3d}     ETA {conflict['eta1'].strftime('%H%M')}Z"
    eta_line += " " * (117 - len(eta_line)) + "│"
    print(eta_line)
    
    print(f"├{'─' * 116}┤")
    
    # Flight 2 strip
    wpt_line = f"│ {f2['callsign']:8s}  "
    for wpt in f2_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (117 - len(wpt_line)) + "│"
    print(wpt_line)
    
    info_line = f"│ {f2['aircraft']:6s}  "
    info_line += f"{f2['departure']}→{f2['destination']:4s}  "
    ots = f"[{f2['ots_track']}]" if f2['ots_track'] else "[RND]"
    info_line += f"{ots:8s}"
    info_line += " " * (117 - len(info_line)) + "│"
    print(info_line)
    
    eta_line = f"│ FL{f2['fl']:3d}     ETA {conflict['eta2'].strftime('%H%M')}Z"
    eta_line += " " * (117 - len(eta_line)) + "│"
    print(eta_line)
    
    print(f"└{'─' * 116}┘")


def print_strip_wb_eb(conflict, wb_flight, eb_flight, wb_wpts, eb_wpts):
    """One westbound, one eastbound - tombstones on opposite sides"""
    
    print(f"┌{'─' * 116}┐")
    
    # WB flight - tombstone left
    wpt_line = f"│ {wb_flight['callsign']:8s}  "
    for wpt in wb_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (117 - len(wpt_line)) + "│"
    print(wpt_line)
    
    info_line = f"│ {wb_flight['aircraft']:6s}  {wb_flight['departure']}→{wb_flight['destination']:4s}  "
    ots = f"[{wb_flight['ots_track']}]" if wb_flight['ots_track'] else "[RND]"
    info_line += f"{ots:8s}  FL{wb_flight['fl']:3d}  ETA {conflict['eta1'].strftime('%H%M')}Z"
    info_line += " " * (117 - len(info_line)) + "│"
    print(info_line)
    
    print(f"├{'─' * 116}┤")
    
    # EB flight - tombstone right
    wpt_line = "│ "
    for wpt in eb_wpts[:8]:
        wpt_line += f"{wpt:9s} "
    wpt_line += " " * (100 - len(wpt_line)) + f"{eb_flight['callsign']:8s} │"
    print(wpt_line)
    
    info_line = f"│ ETA {conflict['eta2'].strftime('%H%M')}Z  FL{eb_flight['fl']:3d}  "
    ots = f"[{eb_flight['ots_track']}]" if eb_flight['ots_track'] else "[RND]"
    info_line += f"{ots:8s}  {eb_flight['departure']}→{eb_flight['destination']:4s}"
    info_line += " " * (90 - len(info_line)) + f"{eb_flight['aircraft']:6s} │"
    print(info_line)
    
    print(f"└{'─' * 116}┘")
    print()


# Test with sample data
if __name__ == "__main__":
    from datetime import datetime, UTC
    
    conflict = {
        'waypoint': '57N050W',
        'fl': 370,
        'separation_min': 2.3,
        'eta1': datetime.now(UTC),
        'eta2': datetime.now(UTC)
    }
    
    # Eastbound flight
    f1 = {
        'callsign': 'UAL877',
        'aircraft': 'B77W/H',
        'departure': 'KJFK',
        'destination': 'EGLL',
        'oceanic_route': 'HOIST/M082F370 DCT 57N050W 58N040W 58N030W 56N020W DCT GOMUP',
        'ots_track': None,
        'fl': 370
    }
    
    # Another eastbound
    f2 = {
        'callsign': 'VIR75L',
        'aircraft': 'B744/H',
        'departure': 'KJFK',
        'destination': 'EGLL',
        'oceanic_route': 'HOIST/M082F370 DCT 57N050W 59N040W 60N030W 59N020W DCT GOMUP',
        'ots_track': None,
        'fl': 370
    }
    
    format_conflict_strip(conflict, f1, f2)
