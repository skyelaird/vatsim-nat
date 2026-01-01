"""
NAT OTS Track Message Fetcher
Fetches, parses, and stores daily NAT track messages from FAA
"""

import re
import requests
from datetime import datetime
import logging
import certifi

logger = logging.getLogger(__name__)

class NATTrackFetcher:
    """Handles fetching and parsing NAT track messages"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.url = "https://notams.aim.faa.gov/nat.html"
        
        # Configure session for better Windows compatibility
        self.session = requests.Session()
        self.session.verify = certifi.where()  # Use certifi certificates
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def should_fetch_eastbound(self):
        """Check if we should fetch eastbound tracks (1430-1600 UTC)"""
        now = datetime.utcnow()
        today = now.date()
        
        # Check time window
        if not (14 <= now.hour < 16):
            return False
        
        # Check if already fetched today (eastbound tracks are V-Z)
        self.cursor.execute("""
            SELECT COUNT(*) FROM nat_ots_tracks 
            WHERE effective_date = ? AND track_letter >= 'V'
        """, (today,))
        
        return self.cursor.fetchone()[0] == 0
    
    def should_fetch_westbound(self):
        """Check if we should fetch westbound tracks (2230-2400 UTC)"""
        now = datetime.utcnow()
        today = now.date()
        
        # Check time window
        if not (22 <= now.hour < 24):
            return False
        
        # Check if already fetched today (westbound tracks are A-U)
        self.cursor.execute("""
            SELECT COUNT(*) FROM nat_ots_tracks 
            WHERE effective_date = ? AND track_letter < 'V'
        """, (today,))
        
        return self.cursor.fetchone()[0] == 0
    
    def fetch_and_store(self, direction):
        """
        Fetch NAT track message and store in database.
        
        Args:
            direction: 'eastbound' or 'westbound'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Fetching {direction} NAT tracks from {self.url}")
            
            # Fetch HTML using requests session
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # Parse tracks
            tracks = self._parse_message(html, direction)
            
            if not tracks:
                logger.warning(f"No {direction} tracks found in message")
                return False
            
            # Store in database
            stored = self._store_tracks(tracks)
            
            logger.info(f"✓ Stored {stored} {direction} tracks (TMI {tracks[0]['tmi']}, effective {tracks[0]['effective_date']})")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Network error fetching {direction} tracks: {e}")
            return False
        except Exception as e:
            logger.error(f"Error fetching {direction} tracks: {e}", exc_info=True)
            return False
    
    def _parse_message(self, html, direction):
        """Parse NAT track message from HTML"""
        # Strip HTML tags to get clean text
        text = re.sub(r'<[^>]+>', '', html)
        
        # Extract TMI
        tmi_match = re.search(r'TMI IS (\d+)', text)
        if not tmi_match:
            logger.warning("TMI not found in track message")
            return None
        
        tmi = tmi_match.group(1)
        
        # Calculate effective date from TMI (Julian date)
        year = datetime.utcnow().year
        try:
            effective_date = datetime.strptime(f"{year}-{tmi}", "%Y-%j").date()
        except ValueError:
            logger.error(f"Invalid TMI: {tmi}")
            return None
        
        # Determine track letters to parse
        if direction == 'eastbound':
            track_letters = ['V', 'W', 'X', 'Y', 'Z']
        else:
            track_letters = list('ABCDEFGHIJKLMNOPQRSTU')
        
        tracks = []
        
        for letter in track_letters:
            track = self._parse_track(text, letter, effective_date, tmi)
            if track:
                tracks.append(track)
        
        return tracks if tracks else None
    
    def _parse_track(self, text, letter, effective_date, tmi):
        """Parse a single track from the message"""
        # Pattern: Match track letter at start of line or after dash
        # "- V SUPRY 46/50 48/40..." or newline then "V SUPRY..."
        # Ends at "EAST LVLS" or "WEST LVLS"
        pattern = rf'(?:^|\n|-)\s*{letter}\s+([A-Z0-9/ \n]+?)(?:EAST LVLS|WEST LVLS)'
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        
        if not match:
            return None
        
        route_str = match.group(1).strip()
        waypoints = route_str.split()
        
        if len(waypoints) < 2:
            return None
        
        track = {
            'effective_date': effective_date,
            'tmi': tmi,
            'track_letter': letter,
            'entry_point': waypoints[0],
            'lat_60w': None,
            'lat_50w': None,
            'lat_40w': None,
            'lat_30w': None,
            'lat_20w': None,
            'lat_15w': None,
            'lat_10w': None,
            'boundary_point': None,
            'exit_point': None,
            'nar_routes': None
        }
        
        # Parse waypoints
        named_waypoints = []
        for wp in waypoints[1:]:
            if '/' in wp:
                # Coordinate waypoint: "46/50" or "4630/40"
                try:
                    lat_str, lon_str = wp.split('/')
                    lat = self._parse_latitude(lat_str)
                    lon = int(lon_str) if len(lon_str) <= 2 else None
                    
                    if lat is not None and lon is not None:
                        lon_field = f'lat_{lon}w'
                        if lon_field in track:
                            track[lon_field] = lat
                except (ValueError, IndexError):
                    logger.warning(f"Invalid waypoint format: {wp}")
                    continue
            else:
                # Named waypoint (boundary or exit point)
                named_waypoints.append(wp)
        
        # Assign named waypoints (usually last 1-2 are boundary/exit)
        if len(named_waypoints) >= 2:
            track['boundary_point'] = named_waypoints[-2]
            track['exit_point'] = named_waypoints[-1]
        elif len(named_waypoints) == 1:
            track['exit_point'] = named_waypoints[0]
        
        # Extract NAR routes
        nar_pattern = rf'{letter}.*?NAR ([A-Z0-9 ]+?)(?:-|END OF PART)'
        nar_match = re.search(nar_pattern, text)
        if nar_match:
            nar_str = nar_match.group(1).strip()
            if nar_str and nar_str != 'NIL':
                track['nar_routes'] = nar_str
        
        return track
    
    def _parse_latitude(self, lat_str):
        """
        Parse NAT latitude format.
        
        Args:
            lat_str: "46" (whole degree) or "4630" (half degree)
            
        Returns:
            float: 46.0 or 46.5, or None if invalid
        """
        try:
            if len(lat_str) == 2:
                # Whole degrees
                return float(lat_str)
            elif len(lat_str) == 4:
                # Half degrees (should be XX30)
                degrees = int(lat_str[:2])
                minutes = int(lat_str[2:4])
                if minutes == 30:
                    return degrees + 0.5
                else:
                    logger.warning(f"Unexpected minutes in latitude: {lat_str}")
                    return degrees + (minutes / 60.0)
            else:
                logger.warning(f"Unexpected latitude format: {lat_str}")
                return None
        except ValueError:
            return None
    
    def _store_tracks(self, tracks):
        """Store parsed tracks in database"""
        stored_count = 0
        
        for track in tracks:
            try:
                self.cursor.execute("""
                    INSERT OR REPLACE INTO nat_ots_tracks
                    (effective_date, tmi, track_letter, entry_point,
                     lat_60w, lat_50w, lat_40w, lat_30w, lat_20w, lat_15w, lat_10w,
                     boundary_point, exit_point, nar_routes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    track['effective_date'], track['tmi'], track['track_letter'],
                    track['entry_point'], track['lat_60w'], track['lat_50w'],
                    track['lat_40w'], track['lat_30w'], track['lat_20w'],
                    track['lat_15w'], track['lat_10w'], track['boundary_point'],
                    track['exit_point'], track['nar_routes']
                ))
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing track {track['track_letter']}: {e}")
        
        self.conn.commit()
        return stored_count
