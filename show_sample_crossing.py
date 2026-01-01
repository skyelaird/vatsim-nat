"""
Show complete details for one recent NAT crossing
"""
import sqlite3

conn = sqlite3.connect('D:\\GitHub\\vatsim-nat\\nat_traffic.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get most recent completed crossing with all data
cursor.execute("""
    SELECT *
    FROM nat_crossings
    WHERE exit_time IS NOT NULL
      AND mid_time IS NOT NULL
    ORDER BY entry_time DESC
    LIMIT 1
""")

row = cursor.fetchone()

if not row:
    print("No completed crossings found yet")
    conn.close()
    exit()

print("=" * 80)
print("COMPLETE NAT CROSSING RECORD - SAMPLE FOR OCEANIC DEMONSTRATION")
print("=" * 80)
print()

print("FLIGHT IDENTIFICATION")
print("-" * 80)
print(f"Callsign:              {row['callsign']}")
print(f"Aircraft Type:         {row['aircraft_type']}")
print(f"Departure:             {row['departure']}")
print(f"Destination:           {row['destination']}")
print(f"Operator:              {row['operator'] or 'N/A'}")
print(f"Registration:          {row['registration'] or 'N/A'}")
print()

print("FLIGHT PLAN DATA")
print("-" * 80)
filed_alt = row['filed_altitude']
if filed_alt:
    # Convert feet to flight level if needed
    if filed_alt >= 1000:
        fl = filed_alt // 100
        print(f"Filed Altitude:        FL{fl}")
    else:
        print(f"Filed Altitude:        FL{filed_alt}")
else:
    print(f"Filed Altitude:        N/A")
print(f"Cruise TAS:            {row['cruise_tas'] or 'N/A'} knots")
print(f"Departure Time:        {row['deptime'] or 'N/A'}Z")
print(f"Enroute Time:          {row['enroute_time'] or 'N/A'}")
print()

print("ROUTE")
print("-" * 80)
print(f"Full Route:")
print(f"  {row['full_route'][:150]}...")
print()
print(f"Oceanic Segment:       {row['oceanic_route'] or 'N/A'}")
print(f"Entry Fix:             {row['entry_fix'] or 'N/A'}")
print(f"Exit Fix:              {row['exit_fix'] or 'N/A'}")
print(f"OTS Track:             {row['ots_track'] or 'RANDOM (not on organized track)'}")
print()

print("EQUIPAGE / CAPABILITIES")
print("-" * 80)
print(f"SELCAL Code:           {row['selcal'] or 'None'}")
print(f"PBN Capability:        {row['pbn_capability'] or 'N/A'}")
print(f"COM Capability:        {row['com_capability'] or 'N/A'}")
print(f"SUR Capability:        {row['sur_capability'] or 'N/A'}")
print()

print("EET (Estimated Elapsed Times)")
print("-" * 80)
eet = row['eet_string'] or 'N/A'
if eet != 'N/A':
    print(f"  {eet}")
else:
    print(f"  {eet}")
print()

print("ACTUAL NAT CROSSING DATA")
print("-" * 80)
print(f"ENTRY (Western Boundary ~50W)")
print(f"  Time:     {row['entry_time']}")
print(f"  Position: {row['entry_lat']:.2f}°N, {row['entry_lon']:.2f}°W")
print(f"  Altitude: FL{row['entry_fl'] or 'N/A'}")
print(f"  Speed:    {row['entry_gs'] or 'N/A'} kts groundspeed")
print()

print(f"MIDPOINT (Mid-Atlantic ~30W)")
print(f"  Time:     {row['mid_time']}")
print(f"  Position: {row['mid_lat']:.2f}°N, {row['mid_lon']:.2f}°W")
print(f"  Altitude: FL{row['mid_fl'] or 'N/A'}")
print(f"  Speed:    {row['mid_gs'] or 'N/A'} kts groundspeed")
print()

print(f"EXIT (Eastern Boundary ~15W)")
print(f"  Time:     {row['exit_time']}")
print(f"  Position: {row['exit_lat']:.2f}°N, {row['exit_lon']:.2f}°W")
print(f"  Altitude: FL{row['exit_fl'] or 'N/A'}")
print(f"  Speed:    {row['exit_gs'] or 'N/A'} kts groundspeed")
print()

print(f"CROSSING DURATION:     {row['crossing_duration']} minutes ({row['crossing_duration']/60:.1f} hours)")
print()

print("=" * 80)
print("This is ONE database record - complete ocean crossing in a single row")
print("Collected automatically from VATSIM live data every 5 minutes")
print("=" * 80)

conn.close()
