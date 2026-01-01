"""Quick lookup of a specific flight"""
import sqlite3

conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

callsign = 'BAW29G'

cursor.execute("""
    SELECT * FROM nat_crossings WHERE callsign = ? ORDER BY entry_time DESC LIMIT 1
""", (callsign,))

flight = cursor.fetchone()

if not flight:
    print(f"No data found for {callsign}")
else:
    print("=" * 80)
    print(f"FLIGHT STORY: {callsign}")
    print("=" * 80)
    print()
    
    # Flight info
    print(f"Aircraft (full): {flight['aircraft_type']}")
    actype = flight['aircraft_type'].split('/')[0] if flight['aircraft_type'] else 'UNK'
    print(f"Aircraft (short): {actype}")
    print(f"Route: {flight['departure']} → {flight['destination']}")
    print(f"Filed: FL{flight['filed_altitude'][:-2] if flight['filed_altitude'] else '???'}, {flight['cruise_tas']}kt TAS")
    print(f"Departure: {flight['deptime']}Z, Enroute: {flight['enroute_time']}")
    print()
    
    # OTS track
    if flight['ots_track']:
        print(f"Track: NAT{flight['ots_track']}")
    else:
        print("Track: RANDOM")
    print()
    
    # Equipage
    print("Equipage:")
    if flight['selcal']:
        print(f"  SELCAL: {flight['selcal']}")
    if flight['pbn_capability']:
        print(f"  PBN: {flight['pbn_capability']}")
    if flight['com_capability']:
        print(f"  COM: {flight['com_capability']}")
    if flight['sur_capability']:
        print(f"  SUR: {flight['sur_capability']}")
    if flight['operator']:
        print(f"  Operator: {flight['operator']}")
    if flight['registration']:
        print(f"  Registration: {flight['registration']}")
    print()
    
    # EET
    if flight['eet_string']:
        print(f"EET: {flight['eet_string']}")
        print()
    
    # Journey so far
    print("Journey:")
    print(f"  Entry: {flight['entry_time']} at {flight['entry_lat']:.2f}N {abs(flight['entry_lon']):.2f}W FL{flight['entry_fl']} {flight['entry_gs']}kt")
    
    if flight['mid_time']:
        print(f"  Mid:   {flight['mid_time']} at {flight['mid_lat']:.2f}N {abs(flight['mid_lon']):.2f}W FL{flight['mid_fl']} {flight['mid_gs']}kt")
    else:
        print(f"  Mid:   Not yet reached")
    
    if flight['exit_time']:
        print(f"  Exit:  {flight['exit_time']} at {flight['exit_lat']:.2f}N {abs(flight['exit_lon']):.2f}W FL{flight['exit_fl']} {flight['exit_gs']}kt")
        print(f"  Duration: {flight['crossing_duration']} minutes")
    else:
        print(f"  Exit:  Still crossing...")
    
    print()
    
    # Route
    if flight['oceanic_route']:
        print(f"Oceanic Route:")
        print(f"  {flight['oceanic_route'][:100]}...")
    
    print()
    print(f"Status: {'COMPLETE' if flight['exit_time'] else 'IN PROGRESS'}")

conn.close()
