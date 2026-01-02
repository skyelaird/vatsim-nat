"""
Expand OTS track identifiers to waypoints
NATV -> actual track waypoints from database
"""

import sqlite3
from datetime import datetime

def expand_ots_track(track_identifier, db_path='nat_traffic.db'):
    """
    Expand OTS track (e.g., NATV) to waypoints
    Returns list of waypoint names or None if not found
    
    Example: NATV -> ['SUPRY', '46N050W', '48N040W', '49N030W', '50N020W', 'SOMAX']
    """
    if not track_identifier.startswith('NAT'):
        return None
    
    if len(track_identifier) != 4:
        return None
    
    track_letter = track_identifier[3]  # NATV -> V
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get today's track
        today = datetime.now(datetime.UTC).date() if hasattr(datetime, 'UTC') else datetime.utcnow().date()
        
        cursor.execute("""
            SELECT entry_point, lat_60w, lat_50w, lat_40w, lat_30w, lat_20w, lat_15w, 
                   boundary_point, exit_point
            FROM nat_ots_tracks
            WHERE track_letter = ? 
              AND effective_date = ?
        """, (track_letter, today))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print(f"WARNING: Track {track_letter} not found for {today}")
            return None
        
        # Build waypoint list
        waypoints = []
        
        # Entry point
        if row[0]:
            waypoints.append(row[0])
        
        # Lat/lon coordinates at each longitude
        # Convert to coordinate format: 46.0 @ 60W -> 46N060W
        coords = [
            (row[1], 60),   # lat_60w
            (row[2], 50),   # lat_50w
            (row[3], 40),   # lat_40w
            (row[4], 30),   # lat_30w
            (row[5], 20),   # lat_20w
            (row[6], 15)    # lat_15w
        ]
        
        for lat, lon_deg in coords:
            if lat is not None:
                lat_int = int(lat)
                lat_min = int((lat - lat_int) * 60)
                
                if lat_min == 0:
                    # Format: 46N060W
                    wpt = f"{lat_int:02d}N{lon_deg:03d}W"
                else:
                    # Format: 4630N06000W (with minutes)
                    wpt = f"{lat_int:02d}{lat_min:02d}N{lon_deg:03d}00W"
                
                waypoints.append(wpt)
        
        # Boundary/exit points
        if row[7]:
            waypoints.append(row[7])
        if row[8]:
            waypoints.append(row[8])
        
        return waypoints
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


# Test it
if __name__ == "__main__":
    import sys
    
    db_path = 'D:/GitHub/vatsim-nat/nat_traffic.db'
    
    # Try a few tracks
    for track in ['NATV', 'NATW', 'NATX', 'NATY', 'NATZ']:
        waypoints = expand_ots_track(track, db_path)
        if waypoints:
            print(f"{track}: {' '.join(waypoints)}")
        else:
            print(f"{track}: Not found")
