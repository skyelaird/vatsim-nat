"""
Route parsing utilities for NAT traffic analysis
"""
import re

def extract_ots_track(route):
    """Extract OTS track letter from route (NAT[A-Z])"""
    match = re.search(r'NAT([A-Z])', route)
    return match.group(1) if match else None

def extract_selcal(remarks):
    """Extract SELCAL code from remarks (SEL/XXXX or SELCAL/XXXX)"""
    if not remarks:
        return None
    # Try SEL/ format first
    match = re.search(r'SEL/([A-Z]{4})', remarks, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Try SELCAL/ format
    match = re.search(r'SELCAL/([A-Z]{4})', remarks, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

def extract_pbn(remarks):
    """Extract PBN capability from remarks (PBN/...)"""
    if not remarks:
        return None
    match = re.search(r'PBN/([A-Z0-9]+)', remarks)
    return match.group(1) if match else None

def extract_com(remarks):
    """Extract COM capability from remarks (COM/...)"""
    if not remarks:
        return None
    match = re.search(r'COM/([A-Z0-9]+)', remarks)
    return match.group(1) if match else None

def extract_sur(remarks):
    """Extract SUR capability from remarks (SUR/...)"""
    if not remarks:
        return None
    match = re.search(r'SUR/([A-Z0-9]+)', remarks)
    return match.group(1) if match else None

def extract_operator(remarks):
    """Extract operator from remarks (OPR/XXX)"""
    if not remarks:
        return None
    match = re.search(r'OPR/([A-Z0-9]+)', remarks)
    return match.group(1) if match else None

def extract_registration(remarks):
    """Extract registration from remarks (REG/XXXXX)"""
    if not remarks:
        return None
    match = re.search(r'REG/([A-Z0-9]+)', remarks)
    return match.group(1) if match else None

def extract_oceanic_route(route):
    """
    Extract oceanic portion from full route.
    Oceanic segment = from entry fix to exit fix, stopping BEFORE domestic airways.
    
    Entry: First waypoint with /Mxxx (Mach number = oceanic entry)
    Exit: Last oceanic waypoint before entering European/domestic airspace
    
    Strategy: Stop at exit fix, don't include subsequent airways/fixes
    """
    if not route:
        return None, None, None
    
    # Find entry point (first Mach number filing)
    entry_match = re.search(r'(\w+)/M\d{3}', route)
    entry_fix = entry_match.group(1) if entry_match else None
    
    # Find all speed changes (both Mach and TAS)
    # Pattern matches: AVUTI/M085F390 or AGORI/N0472F390
    speed_changes = list(re.finditer(r'(\w+)/[MN]\d{3,4}', route))
    
    if not entry_match or len(speed_changes) < 2:
        return None, entry_fix, None
    
    # Exit is the LAST waypoint with speed change in oceanic segment
    # (usually changes from Mach back to TAS at oceanic boundary)
    exit_fix = speed_changes[-1].group(1)
    
    # Extract segment from entry to exit (inclusive)
    start = entry_match.start()
    end = speed_changes[-1].end()
    oceanic_segment = route[start:end]
    
    # Clean up: remove any subsequent airway names (L18, Y803, etc) that got included
    # Airways are typically: single letter + 1-3 digits (L18, Y803, UM605)
    # Stop at first airway AFTER the exit fix
    airway_match = re.search(r'/[MN]\d{3,4}[A-Z]?\s+(?:DCT\s+)?(\w+)\s+([A-Z]\d{1,3}|UM\d+)', oceanic_segment)
    if airway_match:
        # Trim everything after the exit fix + next waypoint before airway
        cut_point = airway_match.start(2)
        oceanic_segment = oceanic_segment[:cut_point].strip()
    
    return oceanic_segment, entry_fix, exit_fix

def extract_eet(remarks):
    """Extract EET string from remarks (EET/...)"""
    if not remarks:
        return None
    match = re.search(r'EET/([A-Z0-9/ ]+?)(?:\s+[A-Z]+/|$)', remarks)
    return match.group(1).strip() if match else None

def is_nat_route(departure, destination):
    """Check if route is transatlantic based on ICAO prefixes"""
    if not departure or not destination:
        return False
    
    # Western hemisphere
    west = ['C', 'K', 'T', 'M']
    # Eastern hemisphere (excluding Pacific)
    east = ['E', 'L', 'B', 'G', 'H', 'O', 'U']
    
    dep_west = departure[0] in west
    dep_east = departure[0] in east
    dest_west = destination[0] in west
    dest_east = destination[0] in east
    
    # One end must be Americas, other must be Eastern hemisphere
    return (dep_west and dest_east) or (dep_east and dest_west)

def determine_direction(departure, destination):
    """Determine if flight is eastbound or westbound"""
    if not departure or not destination:
        return None
    
    west = ['C', 'K', 'T', 'M']
    
    if departure[0] in west:
        return 'EAST'
    else:
        return 'WEST'
