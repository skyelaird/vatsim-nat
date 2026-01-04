# VATSIM NAT Traffic Analyzer

Comprehensive data collection and analysis of North Atlantic air traffic on the VATSIM network.

## Overview

**Production system tracking transatlantic flights** crossing the NAT region with:
- ✅ **Complete ocean crossings** (entry → midpoint → exit in single records)
- ✅ **OTS track correlation** (automated daily fetch from FAA)
- ✅ **High-precision waypoint database** (25,294 NAT region fixes)
- ✅ **Real-time traffic monitoring** (5-minute polling)
- ✅ **ATC Conflict Probe** (strategic detection with strip display - see [CONFLICT_PROBE.md](CONFLICT_PROBE.md))

---

## Quick Start

```powershell
# Start the collector
python collector_service.py

# Check what's being tracked
python show_sample_crossing.py

# View stored OTS tracks
python show_tracks.py

# Run sanity check
python sanity_check.py
```

**Data stored in `nat_traffic.db`** - one consolidated record per complete NAT crossing.

---

## Production Deployment

**Recommended: NSSM Windows Service** (auto-start, auto-restart, runs 24/7)

```cmd
# Install service (run as Administrator)
# See INSTALL_SERVICE.md for complete instructions
install_service_FINAL.bat

# Check status
check_service_status.bat

# Or use Windows service commands
sc query NATCollector
Get-Content nat_collector.log -Tail 50 -Wait
```

**Alternative: Task Scheduler** (see INSTALL_SERVICE.md for setup)

---

## System Components

### 1. Traffic Collector (`collector_service.py`)
**Real-time flight tracking with database-first architecture**

**Collects per crossing:**
- Flight identification (callsign, aircraft, origin, destination)
- Complete route with oceanic segment extraction
- OTS track filing (NAT A-Z or random)
- Equipage (SELCAL, PBN, COM, SUR capabilities)
- Three ocean checkpoints:
  - **Entry** (~50W): Time, position, FL, groundspeed
  - **Midpoint** (~30W): Time, position, FL, groundspeed
  - **Exit** (~15W): Time, position, FL, groundspeed
- Total crossing duration

**Sample crossing:**
```
AFR27 (KLAX→LFPG)
Aircraft: A359/H-SDE2E3GHIJ3J4J5LM1ORWXY/LB1D1
Filed: FL370 M.85
Route: AVUTI/M085F390 DCT 59N050W 60N040W 60N030W 59N020W DCT AGORI
OTS: RANDOM (not on organized track)

Entry:  2026-01-01 13:16:55 @ 56.99°N 59.95°W FL388 501kts
Mid:    2026-01-01 14:42:01 @ 60.08°N 33.29°W FL394 474kts
Exit:   2026-01-01 15:34:55 @ 55.54°N  9.89°W FL410 534kts
Duration: 137 minutes
```

**Geographic zones (fuzzy boundaries):**
- Entry: 55-45°W (western NAT boundary)
- Mid: 35-25°W (mid-ocean checkpoint)
- Exit: 20-10°W (eastern NAT boundary)

### 2. OTS Track Fetcher (`track_fetcher.py`)
**Automated daily collection of NAT Organized Track System messages**

**Fetches from FAA:**
- Source: https://notams.aim.faa.gov/nat.html
- Eastbound: 1430-1600 UTC (Gander tracks V-Z)
- Westbound: 2230-2400 UTC (Shanwick tracks A-U)
- Auto-retry every 5 minutes during window

**Database: `nat_ots_tracks`**
```sql
Stores: Track letter, effective date, TMI
Waypoints: Entry fix, lat at 60W/50W/40W/30W/20W/15W/10W
Exit: Boundary point, exit fix, NAR routes
```

**Example track:**
```
Track X (Eastbound, TMI 002, effective 2026-01-02)
Entry:     DOVEY
60W:       42.0°N
50W:       44.0°N
40W:       46.0°N
30W:       47.0°N
20W:       48.0°N
15W:       48.0°N
Boundary:  OMOKO
Exit:      GUNSO
```

**Analysis queries:**
```sql
-- Flights using Track X on Jan 2
SELECT callsign, entry_time, mid_lat, 
       ABS(mid_lat - nt.lat_30w) as deviation_degrees
FROM nat_crossings nc
JOIN nat_ots_tracks nt 
  ON nt.track_letter = 'X'
  AND nt.effective_date = DATE(nc.entry_time)
WHERE nc.ots_track = 'NATX';

-- Track popularity
SELECT track_letter, COUNT(*) as uses
FROM nat_crossings nc
JOIN nat_ots_tracks nt 
  ON nt.track_letter = SUBSTR(nc.ots_track, 4, 1)
  AND nt.effective_date = DATE(nc.entry_time)
GROUP BY track_letter
ORDER BY uses DESC;
```

### 3. NAT Waypoint Database
**25,294 waypoints from Navigraph AIRAC 2513 (25/DEC/2025 - 22/JAN/2026)**

**Coverage:**
- Bounding box: 35-75°N, 80°W-0°E
- Canadian approach fixes (OYSTR, CLAVY, MUSAK)
- NAT entry/exit points (AVUTI, SUPRY, AGORI, ATSUR)
- All lat/lon coordinates (59N050W, 60N040W, etc.)
- European approach fixes (RESNO, ETILO, SUNOT)

**Formats available:**
- `nat_waypoints.py` - Python dict for direct import
- `nat_waypoints.json` - Universal JSON format
- `nat_waypoints.csv` - Spreadsheet/analysis
- `nat_waypoints.sql` - Database import

**Usage:**
```python
from nat_waypoints import NAT_WAYPOINTS, get_waypoint

coords = get_waypoint('AVUTI')
# {'lat': 57.466667, 'lon': -58.0}
```

**AIRAC update process:**
```powershell
# Every 28 days when new AIRAC released
python generate_waypoints.py
git commit -m "Update waypoints for AIRAC XXXX"
```

### 4. Speed Calculations (`speed_calculations.py`)
**Accurate groundspeed and ETA calculations for conflict probe**

**Conversion chain:**
```
Filed Mach → TAS (using GRIB temps, not ISA)
         ↓
TAS + GRIB Winds → Groundspeed
         ↓
Distance / GS → ETA (±3 min accuracy)
```

**Why GRIB temps matter:**
```
Example: M.85 at FL370
ISA (-54.5°C):     488 kts TAS
Actual (-48°C):    493 kts TAS  (+5 kts)
Over NAT crossing: ±2-3 min ETA difference

Conflict probe tolerance: ±3 min
Temperature error would consume entire budget!
```

**Functions:**
- `mach_to_tas(mach, altitude, actual_temp_c)` - TAS from Mach
- `tas_to_gs(tas, wind_u, wind_v, heading)` - GS from TAS + winds
- `wind_component_along_track(u, v, heading)` - Head/tail component
- `validate_groundspeed(...)` - Compare predicted vs observed
- `calculate_eta(...)` - ETA at waypoint

---

## Database Schema

### nat_crossings (Main Table)
```sql
CREATE TABLE nat_crossings (
    crossing_id INTEGER PRIMARY KEY,
    
    -- Flight identification
    callsign TEXT NOT NULL,
    aircraft_type TEXT,
    departure TEXT,
    destination TEXT,
    
    -- Route information
    full_route TEXT,
    oceanic_route TEXT,
    entry_fix TEXT,
    exit_fix TEXT,
    ots_track TEXT,  -- 'NATA', 'NATB', ... or NULL for random
    
    -- Equipage
    selcal TEXT,
    pbn_capability TEXT,
    com_capability TEXT,
    sur_capability TEXT,
    
    -- Flight plan details
    filed_altitude INTEGER,
    cruise_tas INTEGER,
    filed_mach REAL,
    
    -- Entry point (~50W)
    entry_time DATETIME,
    entry_lat REAL,
    entry_lon REAL,
    entry_fl INTEGER,
    entry_gs INTEGER,
    
    -- Midpoint (~30W)
    mid_time DATETIME,
    mid_lat REAL,
    mid_lon REAL,
    mid_fl INTEGER,
    mid_gs INTEGER,
    
    -- Exit point (~15W)
    exit_time DATETIME,
    exit_lat REAL,
    exit_lon REAL,
    exit_fl INTEGER,
    exit_gs INTEGER,
    
    -- Crossing summary
    crossing_duration INTEGER,  -- minutes
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(callsign, entry_time)
);
```

### nat_ots_tracks (Track Messages)
```sql
CREATE TABLE nat_ots_tracks (
    track_id INTEGER PRIMARY KEY,
    effective_date DATE NOT NULL,
    tmi TEXT NOT NULL,
    track_letter TEXT NOT NULL,
    
    -- Track geometry (latitude at each longitude)
    entry_point TEXT,
    lat_60w REAL,
    lat_50w REAL,
    lat_40w REAL,
    lat_30w REAL,
    lat_20w REAL,
    lat_15w REAL,
    lat_10w REAL,
    boundary_point TEXT,
    exit_point TEXT,
    
    nar_routes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(effective_date, track_letter)
);
```

---

## Analysis Examples

### Traffic Volume
```sql
-- Daily crossings
SELECT DATE(entry_time), COUNT(*) as crossings
FROM nat_crossings 
GROUP BY DATE(entry_time)
ORDER BY DATE(entry_time) DESC;

-- Hourly distribution (UTC)
SELECT strftime('%H', entry_time) as hour_utc, COUNT(*)
FROM nat_crossings
GROUP BY hour_utc
ORDER BY hour_utc;
```

### OTS vs Random Routing
```sql
-- Overall usage
SELECT 
    CASE WHEN ots_track IS NOT NULL THEN 'OTS' ELSE 'Random' END as routing,
    COUNT(*) as flights,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM nat_crossings
GROUP BY routing;

-- Track popularity by date
SELECT 
    DATE(nc.entry_time) as date,
    nt.track_letter,
    COUNT(*) as uses
FROM nat_crossings nc
JOIN nat_ots_tracks nt 
  ON SUBSTR(nc.ots_track, 4, 1) = nt.track_letter
  AND DATE(nc.entry_time) = nt.effective_date
WHERE nc.ots_track IS NOT NULL
GROUP BY date, nt.track_letter
ORDER BY date DESC, uses DESC;
```

### Performance Analysis
```sql
-- Average crossing times by route
SELECT 
    departure, destination,
    COUNT(*) as crossings,
    ROUND(AVG(crossing_duration), 1) as avg_minutes,
    MIN(crossing_duration) as fastest,
    MAX(crossing_duration) as slowest
FROM nat_crossings
WHERE exit_time IS NOT NULL
GROUP BY departure, destination
HAVING COUNT(*) >= 5
ORDER BY avg_minutes;

-- Step climbs through NAT
SELECT 
    callsign,
    entry_fl,
    mid_fl,
    exit_fl,
    (exit_fl - entry_fl) as fl_change
FROM nat_crossings
WHERE exit_time IS NOT NULL
  AND (exit_fl - entry_fl) >= 20;  -- Climbed 2000+ ft
```

### Equipment Analysis
```sql
-- SELCAL equipped percentage
SELECT 
    COUNT(CASE WHEN selcal IS NOT NULL THEN 1 END) as with_selcal,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN selcal IS NOT NULL THEN 1 END) / COUNT(*), 1) as pct
FROM nat_crossings;

-- PBN capabilities
SELECT 
    pbn_capability,
    COUNT(*) as flights
FROM nat_crossings
WHERE pbn_capability IS NOT NULL
GROUP BY pbn_capability
ORDER BY flights DESC
LIMIT 10;
```

### Track Adherence
```sql
-- Deviation from published track centerline at 30W
SELECT 
    nc.callsign,
    nc.ots_track,
    nt.lat_30w as published_lat,
    nc.mid_lat as actual_lat,
    ROUND(ABS(nc.mid_lat - nt.lat_30w), 2) as deviation_deg,
    ROUND(ABS(nc.mid_lat - nt.lat_30w) * 60, 0) as deviation_nm
FROM nat_crossings nc
JOIN nat_ots_tracks nt 
  ON nt.track_letter = SUBSTR(nc.ots_track, 4, 1)
  AND nt.effective_date = DATE(nc.entry_time)
WHERE nc.ots_track IS NOT NULL
  AND nc.mid_lat IS NOT NULL
ORDER BY deviation_deg DESC;
```

---

## Utilities

### Diagnostic Scripts
- `sanity_check.py` - Database health check
- `show_sample_crossing.py` - Display complete crossing record
- `show_tracks.py` - View stored OTS tracks
- `fetch_current_tracks.py` - Manual track fetch

### Data Management
- `generate_waypoints.py` - Extract waypoints from Navigraph
- `add_tracks_table.py` - Database migration for tracks table

---

## Data Sources

- **VATSIM Network:** Real-time flight data (https://data.vatsim.net/)
- **FAA NAT Tracks:** Daily OTS messages (https://notams.aim.faa.gov/nat.html)
- **Navigraph:** AIRAC waypoint database (licensed data)

---

## Future Development

### NAT Conflict Probe (In Development)
**Strategic conflict detection 30 minutes before oceanic entry**

**Features:**
- ✅ GRIB wind/temperature integration (NOAA NOMADS)
- ✅ 4D trajectory prediction (lat/lon/FL/time)
- ✅ Progressive separation loss detection
- ✅ Overtake scenario identification
- 🚧 Resolution engine (vertical/speed/lateral)
- 🚧 Web dashboard
- 🚧 API endpoint

**Concept:**
```
30 min before OEP:
  Project entire NAT crossing
  Detect conflicts at all waypoints
  Identify degrading separation trends
  Provide resolutions BEFORE entry
  
Controller handles tactical in-flight
```

**Example conflict:**
```
🚨 PROGRESSIVE SEPARATION LOSS
BAW117 vs UAL42 (both FL370, eastbound)

Separation projection:
  50N030W: 5.0 min ⚠️  (marginal)
  51N020W: 4.0 min 🚨 (conflict)
  52N015W: 2.8 min 🚨 (critical)
  AGORI:   1.2 min ❌ (loss)

Resolution:
  ☑ UAL42 → FL380 NOW
  ☐ UAL42 → M.80
```

---

## File Structure

```
D:\GitHub\vatsim-nat\
├── collector_service.py      # Main collector (production)
├── track_fetcher.py          # OTS track automation
├── route_parser.py           # Flight plan parsing
├── speed_calculations.py     # Mach/TAS/GS conversions
├── schema.sql                # Database creation
├── schema_tracks.sql         # Track table schema
├── nat_waypoints.py          # Waypoint database (25K fixes)
├── nat_waypoints.json        # (JSON format)
├── nat_waypoints.csv         # (CSV format)
├── nat_waypoints.sql         # (SQL format)
├── generate_waypoints.py     # AIRAC extraction tool
├── sanity_check.py           # Database diagnostics
├── show_sample_crossing.py   # Display records
├── show_tracks.py            # Display OTS tracks
├── fetch_current_tracks.py   # Manual track fetch
├── Create-TaskScheduler.ps1  # Windows service installer
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── nat_traffic.db            # SQLite database (generated)
├── nat_collector.log         # Application log (generated)
├── NavData/                  # Navigraph AIRAC data
│   ├── wpNavFIX.txt         # (308K waypoints worldwide)
│   ├── wpNavRTE.txt         # (Airways)
│   └── cycle_info.txt       # (AIRAC cycle metadata)
└── Data-PMDG/               # PMDG navigation data
```

---

## Requirements

```
Python 3.8+
requests
certifi
sqlite3 (built-in)
```

Install:
```powershell
pip install -r requirements.txt
```

---

## Author

**Joel Tanner (VE1ATM)**  
Former NAV CANADA Air Traffic Controller  
Moncton/Gander FIRs (CZQM/CZQX)  
VATSIM CZQM/CZQX vACC - Sector File Maintainer

---

## Acknowledgments

- **VATSIM Network** - Real-time flight data API
- **NAV CANADA** - Gander/Shanwick operational experience
- **Navigraph** - AIRAC navigation database
- **NOAA NCEP** - NOMADS GRIB weather data

---

## License

Data collection for VATSIM network analysis and virtual ATC training purposes.

**Data Sources:**
- VATSIM data: Subject to VATSIM Terms of Service
- Navigraph data: Licensed for flight simulation use only
- Not for real-world navigation

---

## Change Log

### v3.1 (2026-01-04) - Critical Bug Fixes
- 🐛 **FIXED: Collector entry detection** - Flights now marked "entered" only at actual NAT boundaries
  - Updated NAT_LON_EAST from -10W to -15W (actual boundary)
  - Entry_time set to NULL initially, updated only when boundary crossed
  - Added `has_entered_nat()` and `update_entry()` functions
- ✅ **Database migration** - Preserved 421 historical crossings, fixed 82 incorrect entry times
- ✅ **NSSM service installation** - 24/7 operation with auto-restart
- ✅ **Entry point detection** - Added `detect_entry_point()` for accurate boundary waypoint identification
- ✅ **Dashboard fixes** - Corrected entry point geographical groupings

### v3.0 (2026-01-01)
- ✅ OTS track fetching automation
- ✅ NAT waypoint database (25K fixes)
- ✅ Improved oceanic segment parsing
- ✅ Speed calculation framework
- ✅ GRIB integration planning

### v2.0 (2025-12-XX)
- ✅ Database-first architecture
- ✅ Complete crossing records
- ✅ Three-checkpoint system

### v1.0 (Initial)
- ✅ Basic traffic collection
- ✅ SQLite storage
- ✅ Windows service deployment
