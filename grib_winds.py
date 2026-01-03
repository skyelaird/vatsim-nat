"""
GRIB Wind Data Fetcher for NAT Region
Downloads GFS winds from NOAA NOMADS, caches for 6 hours
Provides wind interpolation at any lat/lon/FL
"""
import xarray as xr
import numpy as np
from datetime import datetime, UTC, timedelta
from pathlib import Path
import urllib.request
import urllib.error

# NAT region bounds (CZQX/EGGX focus)
NAT_LAT_MIN, NAT_LAT_MAX = 44, 62
NAT_LON_MIN, NAT_LON_MAX = -60, -10

# Pressure levels (mb) - FL300 to FL390
PRESSURE_LEVELS = [200, 225, 250, 275, 300]  # 200mb = ~FL390, 300mb = ~FL300

# Cache settings
CACHE_DIR = Path('grib_cache')
CACHE_DURATION = timedelta(hours=6)

def mb_to_fl(mb):
    """Convert pressure (mb) to approximate flight level"""
    # Standard atmosphere approximation
    return int((1 - (mb / 1013.25) ** 0.190284) * 145366.45 / 100)

def fl_to_mb(fl):
    """Convert flight level to approximate pressure (mb)"""
    alt_ft = fl * 100
    return 1013.25 * (1 - alt_ft / 145366.45) ** (1 / 0.190284)

def build_grib_url(forecast_hour=0):
    """Build NOAA GFS filter URL for NAT region winds"""
    # Get latest GFS run (00Z, 06Z, 12Z, 18Z)
    now = datetime.now(UTC)
    run_hour = (now.hour // 6) * 6
    run_date = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    
    # Try previous run if current might not be ready yet
    if (now - run_date).total_seconds() < 7200:  # Less than 2 hours old
        run_date -= timedelta(hours=6)
        run_hour = run_date.hour
    
    date_str = run_date.strftime('%Y%m%d')
    hour_str = f"{run_hour:02d}"
    
    # Use analysis (anl) instead of forecast for current conditions
    if forecast_hour == 0:
        file_name = f"gfs.t{hour_str}z.pgrb2.1p00.anl"
    else:
        fhr_str = f"{forecast_hour:03d}"
        file_name = f"gfs.t{hour_str}z.pgrb2.1p00.f{fhr_str}"
    
    # Build filter URL matching the working format
    params = [
        f"file={file_name}",
        "lev_200_mb=on",
        "lev_225_mb=on",
        "lev_250_mb=on",
        "lev_275_mb=on",
        "lev_300_mb=on",
        "var_TMP=on",   # Temperature - essential for TAS calculation
        "var_UGRD=on",
        "var_VGRD=on",
        f"leftlon={NAT_LON_MIN}",
        f"rightlon={NAT_LON_MAX}",
        f"toplat={NAT_LAT_MAX}",
        f"bottomlat={NAT_LAT_MIN}",
        f"dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    ]
    
    url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl?" + "&".join(params)
    
    print(f"GFS run: {run_date.strftime('%Y-%m-%d %HZ')}")
    return url, run_date

def download_grib(url, cache_path):
    """Download GRIB file from NOAA with proper headers"""
    print(f"Downloading GFS winds from NOAA...")
    print(f"URL: {url[:100]}...")  # Show first 100 chars
    try:
        # Add headers to mimic browser request
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(cache_path, 'wb') as f:
                f.write(response.read())
        
        print(f"✓ Downloaded to {cache_path}")
        return True
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        print(f"Full URL: {url}")
        return False
    except urllib.error.URLError as e:
        print(f"✗ Download failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def load_winds(force_download=False):
    """Load wind data from cache or download if needed"""
    CACHE_DIR.mkdir(exist_ok=True)
    
    # Check for cached file
    url, run_date = build_grib_url()
    cache_file = CACHE_DIR / f"gfs_{run_date.strftime('%Y%m%d_%H')}Z.grib2"
    
    # Download if cache missing, expired, or forced
    if force_download or not cache_file.exists() or \
       (datetime.now(UTC) - datetime.fromtimestamp(cache_file.stat().st_mtime, UTC) > CACHE_DURATION):
        if not download_grib(url, cache_file):
            # Try to use existing cache if download fails
            if cache_file.exists():
                print(f"⚠ Using stale cache: {cache_file}")
            else:
                raise RuntimeError("No wind data available")
    
    # Load GRIB with xarray/cfgrib
    print(f"Loading winds from {cache_file}...")
    ds = xr.open_dataset(cache_file, engine='cfgrib')
    print(f"✓ Loaded winds for {len(PRESSURE_LEVELS)} levels")
    
    return ds

def get_wind(ds, lat, lon, fl):
    """Interpolate wind at specific lat/lon/FL
    Returns: (u_wind, v_wind) in knots
    """
    # Convert FL to pressure
    target_mb = fl_to_mb(fl)
    
    # Convert longitude to 0-360 range (GRIB uses 0-360)
    if lon < 0:
        lon = lon + 360
    
    # Interpolate
    try:
        u_wind = ds['u'].interp(latitude=lat, longitude=lon, isobaricInhPa=target_mb).values
        v_wind = ds['v'].interp(latitude=lat, longitude=lon, isobaricInhPa=target_mb).values
        
        # Convert m/s to knots
        u_wind_kt = float(u_wind) * 1.94384
        v_wind_kt = float(v_wind) * 1.94384
        
        return u_wind_kt, v_wind_kt
    except Exception as e:
        print(f"⚠ Wind interpolation failed for {lat},{lon} FL{fl}: {e}")
        return 0.0, 0.0

if __name__ == "__main__":
    # Test
    print("Testing GRIB wind fetcher...")
    ds = load_winds()
    
    # Test point: 54N 30W FL380
    u, v = get_wind(ds, 54, -30, 380)
    print(f"\nTest: 54N 30W FL380")
    print(f"U-wind: {u:.1f} kt")
    print(f"V-wind: {v:.1f} kt")
    print(f"Speed: {np.sqrt(u**2 + v**2):.1f} kt")
    print(f"Direction: {(270 - np.degrees(np.arctan2(v, u))) % 360:.0f}°")
