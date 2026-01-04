"""
VATSIM NAT Traffic Collector - Production Service v3
Database-first model with fuzzy zone boundaries
Extended to 25N for Caribbean/South Atlantic traffic
"""
import urllib.request
import json
import sqlite3
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, UTC
from route_parser import *
from track_fetcher import NATTrackFetcher

# Configure logging with rotation
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Rotating file handler (10MB max, 5 backups)
file_handler = RotatingFileHandler(
    'nat_collector.log',
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# NAT geographic boundaries (extended to capture Caribbean/South Atlantic)
NAT_LAT_MIN = 25  # Down to Caribbean
NAT_LAT_MAX = 66  # Up to Polar routes
NAT_LON_WEST = -60  # Western boundary (Canada/US coast)
NAT_LON_EAST = -15  # Eastern boundary (Europe/UK coast) - actual NAT boundary

# Fuzzy zone boundaries (approximate, not strict lines)
ENTRY_ZONE_WEST = -55  # Western boundary area
ENTRY_ZONE_EAST = -45
MID_ZONE_WEST = -35    # Mid-Atlantic area
MID_ZONE_EAST = -25
EXIT_ZONE_WEST = -20   # Eastern boundary area
EXIT_ZONE_EAST = -15   # Match NAT eastern boundary

# Error tracking
consecutive_errors = 0
MAX_CONSECUTIVE_ERRORS = 5

def init_database():
    """Initialize database with schema"""
    try:
        conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        logger.info("Database initialized")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def is_in_nat_region(lat, lon):
    """Check if position is in NAT region"""
    return (NAT_LAT_MIN <= lat <= NAT_LAT_MAX) and (NAT_LON_WEST <= lon <= NAT_LON_EAST)

def is_in_entry_zone(lon):
    """Check if in western entry zone (55W-45W)"""
    return ENTRY_ZONE_WEST <= lon <= ENTRY_ZONE_EAST

def is_in_mid_zone(lon):
    """Check if in mid-Atlantic zone (35W-25W)"""
    return MID_ZONE_WEST <= lon <= MID_ZONE_EAST

def is_in_exit_zone(lon):
    """Check if in eastern exit zone (20W-10W)"""
    return EXIT_ZONE_WEST <= lon <= EXIT_ZONE_EAST

def has_entered_nat(lat, lon, prev_lat, prev_lon, is_eastbound):
    """
    Check if flight has crossed the NAT entry boundary.

    For eastbound: Crosses from east to west of -52W (typical western entry)
    For westbound: Crosses from west to east of -15W (eastern boundary)

    Args:
        lat, lon: Current position
        prev_lat, prev_lon: Previous position (can be None for first check)
        is_eastbound: Flight direction

    Returns:
        True if flight just crossed the entry boundary
    """
    if prev_lat is None or prev_lon is None:
        # First position check - verify we're inside the boundary
        if is_eastbound:
            return lon <= -45  # Inside western entry zone
        else:
            return lon <= -15  # At or inside eastern boundary

    # Check if boundary was crossed between previous and current position
    if is_eastbound:
        # Eastbound crosses from east (-45W) to west (-52W or beyond)
        return prev_lon > -45 and lon <= -45
    else:
        # Westbound crosses from west (-20W) to east (-15W)
        return prev_lon < -15 and lon >= -15

def get_vatsim_data():
    """Fetch current VATSIM data"""
    try:
        url = "https://data.vatsim.net/v3/vatsim-data.json"
        response = urllib.request.urlopen(url, timeout=10)
        data = json.loads(response.read())
        return data['pilots']
    except Exception as e:
        logger.error(f"Error fetching VATSIM data: {e}")
        return []

def get_active_crossing(conn, callsign):
    """Check if callsign has an active (incomplete) crossing in database"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT crossing_id, crossed_mid, entry_time, current_lat, current_lon
        FROM nat_crossings
        WHERE callsign = ? AND exit_time IS NULL
        ORDER BY COALESCE(entry_time, last_update_time) DESC
        LIMIT 1
    """, (callsign,))
    row = cursor.fetchone()
    if row:
        return {
            'crossing_id': row[0],
            'crossed_mid': row[1] == 1,
            'entry_time': row[2],
            'current_lat': row[3],
            'current_lon': row[4]
        }
    return None

def create_crossing(conn, pilot, route_data, remarks_data, flight_plan):
    """Create new crossing record in database"""
    cursor = conn.cursor()
    
    now = datetime.now(UTC).isoformat()
    lat = pilot['latitude']
    lon = pilot['longitude']
    alt = pilot['altitude']
    gs = pilot['groundspeed']
    fl = int(alt / 100) if alt else None
    
    cursor.execute("""
        INSERT INTO nat_crossings (
            callsign, aircraft_type, departure, destination,
            cruise_tas, filed_altitude, deptime, enroute_time,
            full_route, oceanic_route, entry_fix, exit_fix, ots_track, eet_string,
            selcal, pbn_capability, com_capability, sur_capability, operator, registration,
            entry_time, entry_lat, entry_lon, entry_fl, entry_gs,
            last_update_time, current_lat, current_lon, current_fl, current_gs,
            crossed_mid
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        pilot['callsign'],
        route_data['aircraft_type'],
        route_data['departure'],
        route_data['destination'],
        flight_plan.get('cruise_tas'),
        flight_plan.get('altitude'),
        flight_plan.get('deptime'),
        flight_plan.get('enroute_time'),
        route_data['full_route'],
        route_data['oceanic_route'],
        route_data['entry_fix'],
        route_data['exit_fix'],
        route_data['ots_track'],
        remarks_data['eet_string'],
        remarks_data['selcal'],
        remarks_data['pbn'],
        remarks_data['com'],
        remarks_data['sur'],
        remarks_data['operator'],
        remarks_data['registration'],
        None, None, None, None, None,  # Entry data - set when boundary is crossed
        now, lat, lon, fl, gs  # Initialize current position
    ))
    
    conn.commit()
    crossing_id = cursor.lastrowid
    
    logger.info(f"New NAT crossing: {pilot['callsign']} {route_data['departure']}-{route_data['destination']}")
    
    return crossing_id

def update_midpoint(conn, crossing_id, pilot):
    """Update crossing with midpoint zone data"""
    cursor = conn.cursor()
    
    now = datetime.now(UTC).isoformat()
    lat = pilot['latitude']
    lon = pilot['longitude']
    alt = pilot['altitude']
    gs = pilot['groundspeed']
    fl = int(alt / 100) if alt else None
    
    cursor.execute("""
        UPDATE nat_crossings
        SET mid_time = ?, mid_lat = ?, mid_lon = ?, mid_fl = ?, mid_gs = ?,
            crossed_mid = 1
        WHERE crossing_id = ?
    """, (now, lat, lon, fl, gs, crossing_id))
    
    conn.commit()
    logger.info(f"{pilot['callsign']} in mid-Atlantic zone")

def update_current_position(conn, crossing_id, pilot):
    """Update current position for active crossing (called every poll cycle)"""
    cursor = conn.cursor()
    
    now = datetime.now(UTC).isoformat()
    lat = pilot['latitude']
    lon = pilot['longitude']
    alt = pilot['altitude']
    gs = pilot['groundspeed']
    fl = int(alt / 100) if alt else None
    
    cursor.execute("""
        UPDATE nat_crossings
        SET last_update_time = ?, current_lat = ?, current_lon = ?, current_fl = ?, current_gs = ?
        WHERE crossing_id = ?
    """, (now, lat, lon, fl, gs, crossing_id))

    conn.commit()

def update_entry(conn, crossing_id, pilot):
    """Set entry data when flight crosses NAT boundary"""
    cursor = conn.cursor()

    now = datetime.now(UTC).isoformat()
    lat = pilot['latitude']
    lon = pilot['longitude']
    alt = pilot['altitude']
    gs = pilot['groundspeed']
    fl = int(alt / 100) if alt else None

    cursor.execute("""
        UPDATE nat_crossings
        SET entry_time = ?, entry_lat = ?, entry_lon = ?, entry_fl = ?, entry_gs = ?
        WHERE crossing_id = ?
    """, (now, lat, lon, fl, gs, crossing_id))

    conn.commit()
    logger.info(f"{pilot['callsign']} entered NAT at {lat:.2f}N {lon:.2f}W FL{fl}")

def complete_crossing(conn, crossing_id, pilot):
    """Mark crossing as complete with exit data"""
    cursor = conn.cursor()
    
    now = datetime.now(UTC).isoformat()
    lat = pilot['latitude']
    lon = pilot['longitude']
    alt = pilot['altitude']
    gs = pilot['groundspeed']
    fl = int(alt / 100) if alt else None
    
    # Calculate duration
    cursor.execute("""
        SELECT entry_time FROM nat_crossings WHERE crossing_id = ?
    """, (crossing_id,))
    row = cursor.fetchone()
    duration = None
    if row and row[0]:
        entry = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
        exit = datetime.fromisoformat(now.replace('Z', '+00:00'))
        duration = int((exit - entry).total_seconds() / 60)
    
    cursor.execute("""
        UPDATE nat_crossings
        SET exit_time = ?, exit_lat = ?, exit_lon = ?, exit_fl = ?, exit_gs = ?,
            crossing_duration = ?
        WHERE crossing_id = ?
    """, (now, lat, lon, fl, gs, duration, crossing_id))
    
    conn.commit()
    logger.info(f"Completed crossing: {pilot['callsign']} ({duration} min)")

def process_flight(conn, pilot):
    """Process a single flight"""
    try:
        callsign = pilot['callsign']
        lat = pilot['latitude']
        lon = pilot['longitude']
        
        flight_plan = pilot.get('flight_plan')
        if not flight_plan:
            return
        
        departure = flight_plan.get('departure', '')
        destination = flight_plan.get('arrival', '')
        route = flight_plan.get('route', '')
        remarks = flight_plan.get('remarks', '')
        # Use full ICAO aircraft string (not FAA)
        aircraft_type = flight_plan.get('aircraft', '')
        
        # Check if this is a NAT route
        if not is_nat_route(departure, destination):
            return
        
        # Check if we're tracking this crossing
        active = get_active_crossing(conn, callsign)
        
        # Aircraft is OUTSIDE NAT region
        if not is_in_nat_region(lat, lon):
            if active:
                # Exiting NAT - complete the crossing
                complete_crossing(conn, active['crossing_id'], pilot)
            return
        
        # Aircraft is INSIDE NAT region
        if not active:
            # New crossing - create database record
            oceanic_route, entry_fix, exit_fix = extract_oceanic_route(route)
            
            route_data = {
                'aircraft_type': aircraft_type,
                'departure': departure,
                'destination': destination,
                'full_route': route,
                'oceanic_route': oceanic_route,
                'entry_fix': entry_fix,
                'exit_fix': exit_fix,
                'ots_track': extract_ots_track(route)
            }
            
            remarks_data = {
                'eet_string': extract_eet(remarks),
                'selcal': extract_selcal(remarks),
                'pbn': extract_pbn(remarks),
                'com': extract_com(remarks),
                'sur': extract_sur(remarks),
                'operator': extract_operator(remarks),
                'registration': extract_registration(remarks)
            }
            
            create_crossing(conn, pilot, route_data, remarks_data, flight_plan)
        
        else:
            # Update existing crossing
            # Always update current position for active crossings
            update_current_position(conn, active['crossing_id'], pilot)

            # Check if flight has entered NAT (if not already marked as entered)
            if active['entry_time'] is None:
                is_eastbound = departure[0] in 'KC'
                prev_lat = active.get('current_lat')
                prev_lon = active.get('current_lon')

                if has_entered_nat(lat, lon, prev_lat, prev_lon, is_eastbound):
                    update_entry(conn, active['crossing_id'], pilot)

            # Check for midpoint zone crossing
            if not active['crossed_mid'] and is_in_mid_zone(lon):
                update_midpoint(conn, active['crossing_id'], pilot)
            
    except Exception as e:
        logger.error(f"Error processing flight {pilot.get('callsign', 'UNKNOWN')}: {e}")

def main():
    """Main collection loop with auto-recovery"""
    global consecutive_errors
    
    logger.info("=" * 60)
    logger.info("VATSIM NAT Traffic Collector - Production Service v3")
    logger.info("Region: 25N-66N, 60W-15W (includes Caribbean)")
    logger.info("Database-first model (crash-resistant)")
    logger.info("NAT track fetching: 1430 UTC (EB), 2230 UTC (WB)")
    logger.info("=" * 60)
    
    if not init_database():
        logger.error("Failed to initialize database - exiting")
        return 1
    
    # Initialize track fetcher
    conn_init = sqlite3.connect('nat_traffic.db', timeout=30.0)
    track_fetcher = NATTrackFetcher(conn_init)
    conn_init.close()
    
    poll_interval = 300  # 5 minutes
    
    while True:
        try:
            # Open database connection for this poll cycle
            conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
            
            # Update track fetcher connection
            track_fetcher.conn = conn
            track_fetcher.cursor = conn.cursor()
            
            # Check and fetch NAT tracks if in time window
            if track_fetcher.should_fetch_eastbound():
                logger.info("→ Time window for eastbound tracks (1430-1600 UTC)")
                track_fetcher.fetch_and_store('eastbound')
            
            if track_fetcher.should_fetch_westbound():
                logger.info("→ Time window for westbound tracks (2230-2400 UTC)")
                track_fetcher.fetch_and_store('westbound')
            
            # Count active crossings
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM nat_crossings WHERE exit_time IS NULL")
            active_count = cursor.fetchone()[0]
            
            logger.info(f"Polling VATSIM... (tracking {active_count} crossings)")
            
            pilots = get_vatsim_data()
            
            if pilots:
                logger.info(f"Found {len(pilots)} pilots online")
                consecutive_errors = 0  # Reset on success
                
                for pilot in pilots:
                    process_flight(conn, pilot)
            else:
                consecutive_errors += 1
                logger.warning(f"No data received ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")
            
            conn.close()
            
            # Check for too many errors
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.error("Too many consecutive errors - attempting recovery")
                time.sleep(60)
                consecutive_errors = 0
            
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            logger.info("Shutdown requested - saving in-progress crossings...")
            
            # Mark all active crossings with current position as exit data
            try:
                conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
                cursor = conn.cursor()
                
                # Get all incomplete crossings
                cursor.execute("""
                    SELECT crossing_id, callsign 
                    FROM nat_crossings 
                    WHERE exit_time IS NULL
                """)
                active = cursor.fetchall()
                
                if active:
                    logger.info(f"Marking {len(active)} in-progress crossings as incomplete...")
                    
                    # Mark them with a note that they're incomplete (could add a status field)
                    # For now, just log them - they'll remain in DB with exit_time = NULL
                    for crossing_id, callsign in active:
                        logger.info(f"  {callsign} - incomplete (will resume if still in NAT)")
                
                conn.close()
                logger.info("All data safely stored in database")
                
            except Exception as e:
                logger.error(f"Error during graceful shutdown: {e}")
            
            return 0
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error in main loop ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {e}")
            time.sleep(60)

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        exit(1)
