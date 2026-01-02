# NAT Conflict Probe

ATC-style conflict detection for North Atlantic traffic using VATSIM data.

## Overview

The conflict probe analyzes active NAT crossings from the database and identifies potential conflicts where aircraft will be at the same waypoint, same flight level, with less than 5 minutes separation.

## Features

- **ATC Strip Format**: Displays conflicts in familiar controller strip layout
- **Three-Column Layout**: WB tombstone left, data center, EB tombstone right
- **Geographic Waypoint Display**: W→E ordering with simplified coordinates (57/50 format)
- **Conflict Highlighting**: Asterisk marks conflict waypoints
- **Wrong-Way Detection**: Flags flights on improper odd/even FL for direction
- **Future-Only Probing**: Only shows conflicts that haven't occurred yet
- **SELCAL Display**: Shows SELCAL codes in empty tombstone column

## Usage

```bash
python conflict_strip_atc.py
```

## Output Format

```
🚨  CONFLICT at DOGAL FL360 - Separation: 2 min
┌──────────────────────────────────────────────────────────────────┐
│  TEF1039    JANJO   56/50   57/40   57/30   55/20  *DOGAL        │
│   A339/H    1822    1747    1704    1621    1535    1511         │
│FL360       DOGAL 55N020W 56N050W JANJO                           │
├──────────────────────────────────────────────────────────────────┤
│  KLM1748    NEEKO   54/50   55/40   55/30   54/20  *DOGAL        │
│   A339/H    2347    1810    1901    1951    2042    1513         │
│FL360       DOGAL NATB NEEKO                                      │
└──────────────────────────────────────────────────────────────────┘
```

### Strip Elements

**Top Line:**
- Callsign (WB: left, EB: right)
- Waypoints in W→E geographic order
- Conflict waypoint marked with `*`

**Middle Line:**
- Aircraft type/wake (simplified: A35K/H)
- Times at each waypoint (HHMM format)
- SELCAL in empty tombstone column

**Bottom Line:**
- Flight level
- Route as filed (origin waypoints destination)

## Conflict Detection Logic

### Filtering Criteria

1. **Shared Waypoint**: Both flights must pass through the exact same waypoint (not just similar coordinates)
2. **Same Flight Level**: Conflicts only detected at same FL
3. **Future Events Only**: ETA must be in the future (past = already handled safely)
4. **Separation Standard**: < 5 minutes = conflict (HIGH if < 3 min, MEDIUM if 3-5 min)
5. **One Conflict Per Pair**: Only reports first conflict point between any two aircraft

### Direction Rules

- **Eastbound (K/C departure)**: Should use ODD flight levels (FL350, 370, 390, 410)
- **Westbound (E/L/U/G departure)**: Should use EVEN flight levels (FL340, 360, 380, 400)
- Flights on wrong odd/even for direction are flagged as `[wrong FL]`
- Multiple wrong-way conflicts (3+) flagged as `[WRONG-WAY: callsign]`

### Head-On Detection

When eastbound and westbound flights meet at the same waypoint going opposite directions, conflict is marked `(HEAD-ON)`.

## Database Requirements

Requires active `nat_crossings` table with:
- `callsign`, `aircraft_type`, `departure`, `destination`
- `oceanic_route`, `ots_track`, `filed_altitude`, `selcal`
- Position data: `entry_lat/lon`, `mid_lat/lon`, current FL/GS
- `exit_time IS NULL` for active crossings

## Known Issues

### Stale Database Entries

The collector service doesn't currently update `exit_time` when flights:
- Disconnect from VATSIM
- Exit NAT region
- Complete crossing

This can result in "ghost" conflicts with flights that no longer exist. The probe correctly filters these out by checking if ETAs are in the past, but they still appear in the database as active.

**Future Enhancement**: Collector needs to implement exit detection and cleanup of stale entries.

## File Structure

```
conflict_strip_atc.py          # Main conflict probe (USE THIS)
nat_waypoints.py              # Waypoint coordinate lookup
route_parser.py               # Parse oceanic routes
track_fetcher.py              # Fetch OTS track definitions
nat_traffic.db                # Database with active crossings
```

## Dependencies

- Python 3.12+
- sqlite3
- datetime, math, re (standard library)

## Related Tools

- `collector_service.py` - Collects NAT traffic from VATSIM
- `show_tracks.py` - Display current OTS tracks
- `analyze_traffic.py` - Traffic flow analysis

## Future Enhancements

### Resolution Suggestions (Planned)

1. **Vertical**: ±1000ft, direction-proper preference
2. **Speed**: ±0.02 Mach adjustment calculations
3. **Lateral**: Adjacent OTS track or ±1° latitude offset

### Web Interface (Planned)

Move to web-based display for:
- Better formatting and styling
- Real-time updates
- Interactive conflict resolution
- Historical conflict analysis

## Version History

- **v3.0** (2026-01-02): ATC strip format with proper tombstone placement
- **v2.0**: Database-driven with OTS track integration
- **v1.0**: Initial live VATSIM API probe
