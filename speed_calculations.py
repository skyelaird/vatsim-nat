"""
NAT Wind and Speed Calculations
Mach → TAS → Groundspeed conversions for conflict probe
"""

import math

def mach_to_tas(mach, altitude_ft, actual_temp_c=None):
    """
    Convert Mach number to True Airspeed (TAS)
    
    Args:
        mach: Mach number (e.g., 0.85 for M.85)
        altitude_ft: Altitude in feet
        actual_temp_c: Actual temperature in °C from GRIB (if available)
                      If None, uses ISA standard atmosphere
    
    Returns:
        TAS in knots
    
    Example:
        >>> mach_to_tas(0.85, 37000, actual_temp_c=-52)  # Using GRIB temp
        493.2  # knots TAS at FL370 with actual temp
        >>> mach_to_tas(0.85, 37000)  # Using ISA
        488.5  # knots TAS at FL370 ISA standard
    """
    if actual_temp_c is not None:
        # Use actual temperature from GRIB
        temp_c = actual_temp_c
    else:
        # Fall back to ISA standard atmosphere
        if altitude_ft <= 36089:  # Troposphere
            # Standard temp: 15°C at sea level, -2°C per 1000ft
            temp_c = 15 - (altitude_ft / 1000 * 1.98)
        else:  # Lower stratosphere
            temp_c = -56.5  # Constant at tropopause
    
    temp_k = temp_c + 273.15
    
    # Speed of sound: a = 38.967854 × √T(K)
    speed_of_sound_kts = 38.967854 * math.sqrt(temp_k)
    
    # TAS = Mach × speed of sound
    tas = mach * speed_of_sound_kts
    
    return round(tas, 1)


def tas_to_gs(tas, wind_u, wind_v, heading_deg):
    """
    Convert TAS to Groundspeed using wind components
    
    Args:
        tas: True airspeed in knots
        wind_u: U-component (east-west) in knots (+ = eastward)
        wind_v: V-component (north-south) in knots (+ = northward)
        heading_deg: True heading in degrees (0-360)
    
    Returns:
        Groundspeed in knots
    
    Note:
        Uses vector addition: GS_vector = TAS_vector + Wind_vector
    """
    # Convert heading to radians
    heading_rad = math.radians(heading_deg)
    
    # TAS vector components (aircraft velocity relative to air)
    tas_east = tas * math.sin(heading_rad)
    tas_north = tas * math.cos(heading_rad)
    
    # Add wind (ground velocity = air velocity + wind velocity)
    gs_east = tas_east + wind_u
    gs_north = tas_north + wind_v
    
    # Calculate groundspeed magnitude
    gs = math.sqrt(gs_east**2 + gs_north**2)
    
    return round(gs, 1)


def wind_component_along_track(wind_u, wind_v, heading_deg):
    """
    Calculate headwind/tailwind component along track
    
    Args:
        wind_u: U-component (E-W) in knots
        wind_v: V-component (N-S) in knots  
        heading_deg: Track heading in degrees
    
    Returns:
        Wind component in knots (positive = tailwind, negative = headwind)
    """
    # Calculate wind speed and direction
    wind_speed = math.sqrt(wind_u**2 + wind_v**2)
    wind_dir_deg = (math.degrees(math.atan2(wind_u, wind_v)) + 360) % 360
    
    # Angle between wind direction and aircraft heading
    angle_diff = abs(heading_deg - wind_dir_deg)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    # Component along track
    component = wind_speed * math.cos(math.radians(angle_diff))
    
    # Determine if headwind or tailwind
    if abs(heading_deg - wind_dir_deg) < 90 or abs(heading_deg - wind_dir_deg) > 270:
        return component  # Tailwind (positive)
    else:
        return -component  # Headwind (negative)


def validate_groundspeed(filed_mach, filed_tas, current_gs, altitude_ft, wind_u, wind_v, heading_deg):
    """
    Validate current groundspeed against filed speeds with winds
    
    Args:
        filed_mach: Filed Mach number (e.g., 0.85)
        filed_tas: Filed TAS from flight plan (knots)
        current_gs: Current observed groundspeed (knots)
        altitude_ft: Current altitude
        wind_u, wind_v: Wind components at position
        heading_deg: Track heading
    
    Returns:
        dict with validation results
    """
    # Calculate expected TAS from filed Mach
    expected_tas_from_mach = mach_to_tas(filed_mach, altitude_ft)
    
    # Calculate expected GS from TAS + winds
    expected_gs = tas_to_gs(expected_tas_from_mach, wind_u, wind_v, heading_deg)
    
    # Validation
    tas_diff = abs(expected_tas_from_mach - filed_tas) if filed_tas else None
    gs_diff = abs(expected_gs - current_gs)
    
    wind_component = wind_component_along_track(wind_u, wind_v, heading_deg)
    
    return {
        'filed_mach': filed_mach,
        'filed_tas': filed_tas,
        'expected_tas': expected_tas_from_mach,
        'tas_match': tas_diff < 10 if tas_diff else None,  # Within 10 knots
        'expected_gs': expected_gs,
        'current_gs': current_gs,
        'gs_diff': gs_diff,
        'gs_match': gs_diff < 20,  # Within 20 knots tolerance
        'wind_component': wind_component,
        'status': 'OK' if gs_diff < 20 else 'CHECK'
    }


def calculate_eta(waypoint_lat, waypoint_lon, current_lat, current_lon, 
                  filed_mach, altitude_ft, wind_u, wind_v, temp_c=None):
    """
    Calculate ETA at waypoint using Mach → TAS → GS calculation
    
    Args:
        waypoint_lat, waypoint_lon: Destination waypoint
        current_lat, current_lon: Current position
        filed_mach: Filed Mach number
        altitude_ft: Cruise altitude
        wind_u, wind_v: Wind components (interpolated along route)
        temp_c: Actual temperature from GRIB (optional)
    
    Returns:
        (eta_seconds, groundspeed_kts, distance_nm)
    """
    from datetime import timedelta
    
    # Calculate distance (great circle)
    distance_nm = haversine(current_lat, current_lon, waypoint_lat, waypoint_lon)
    
    # Calculate heading to waypoint
    heading = calculate_bearing(current_lat, current_lon, waypoint_lat, waypoint_lon)
    
    # Mach → TAS (using actual temp if available)
    tas = mach_to_tas(filed_mach, altitude_ft, actual_temp_c=temp_c)
    
    # TAS + winds → GS
    gs = tas_to_gs(tas, wind_u, wind_v, heading)
    
    # Time = Distance / Speed
    time_hours = distance_nm / gs
    time_seconds = time_hours * 3600
    
    return time_seconds, gs, distance_nm


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate great circle distance between two points
    
    Returns:
        Distance in nautical miles
    """
    R = 3440.065  # Earth radius in nautical miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate initial bearing between two points
    
    Returns:
        Bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    
    x = math.sin(dlon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))
    
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


# Example usage and validation
if __name__ == "__main__":
    print("NAT Speed Calculations - Test Cases")
    print("=" * 60)
    
    # Test 1: Mach → TAS conversion
    print("\nTest 1: Mach to TAS")
    print("-" * 60)
    mach = 0.85
    alt = 37000
    tas = mach_to_tas(mach, alt)
    print(f"M.{int(mach*100):02d} at FL{alt//100} = {tas} kts TAS")
    
    # Test 2: TAS → GS with typical NAT westerly winds
    print("\nTest 2: TAS to Groundspeed (Westerly winds)")
    print("-" * 60)
    wind_u = 80  # 80 kt from west (tailwind for eastbound)
    wind_v = 10  # 10 kt from south
    heading = 90  # Eastbound
    gs = tas_to_gs(tas, wind_u, wind_v, heading)
    print(f"TAS: {tas} kts")
    print(f"Wind: {wind_u}U {wind_v}V")
    print(f"Heading: {heading}°")
    print(f"GS: {gs} kts")
    
    # Test 3: Validation
    print("\nTest 3: Groundspeed Validation")
    print("-" * 60)
    filed_mach = 0.85
    filed_tas = 488
    current_gs = 568  # Observed
    result = validate_groundspeed(
        filed_mach, filed_tas, current_gs, 
        alt, wind_u, wind_v, heading
    )
    print(f"Filed: M.85 / {filed_tas} kts TAS")
    print(f"Expected GS: {result['expected_gs']} kts")
    print(f"Current GS: {current_gs} kts")
    print(f"Difference: {result['gs_diff']} kts")
    print(f"Status: {result['status']}")
    
    # Test 4: Headwind case (westbound)
    print("\nTest 4: Westbound with Headwinds")
    print("-" * 60)
    heading_wb = 270  # Westbound
    gs_wb = tas_to_gs(tas, wind_u, wind_v, heading_wb)
    component = wind_component_along_track(wind_u, wind_v, heading_wb)
    print(f"TAS: {tas} kts")
    print(f"Wind component: {component:.1f} kts (headwind)")
    print(f"GS: {gs_wb} kts")
