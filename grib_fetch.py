#!/usr/bin/env python3
"""
GRIB Wind Data Fetcher for NAT Conflict Probe
Downloads GFS winds from NOAA, caches for 6 hours, supports interpolation between models
"""
import urllib.request
import urllib.error
import ssl
from datetime import datetime, UTC, timedelta
from pathlib import Path
import json

# Cache settings
CACHE_DIR = Path('grib_cache')
CACHE_DURATION = timedelta(hours=6)

def get_gfs_run_times():
    """
    Get previous and current GFS run times for interpolation
    
    Returns:
        tuple: (previous_run_date, current_run_date)
    """
    now = datetime.now(UTC)
    
    # Find the most recent completed run (00Z, 06Z, 12Z, 18Z)
    # Assume run is available 3 hours after start time
    run_hour = (now.hour // 6) * 6
    current_run = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    
    # If less than 3 hours since run start, use previous run as current
    if (now - current_run).total_seconds() < 10800:  # 3 hours
        current_run -= timedelta(hours=6)
    
    # Previous run is 6 hours earlier
    previous_run = current_run - timedelta(hours=6)
    
    return previous_run, current_run

def build_gfs_url(run_date, forecast_hour=0):
    """
    Build NOAA GFS filter URL for NAT region winds
    
    Args:
        run_date: datetime of GFS model run (00Z, 06Z, 12Z, or 18Z)
        forecast_hour: 0 for analysis, 3/6/9 for forecasts
    
    Returns:
        str: Full URL for GRIB download
    """
    date_str = run_date.strftime('%Y%m%d')
    hour_str = f"{run_date.hour:02d}"
    
    # Analysis or forecast
    if forecast_hour == 0:
        file_name = f"gfs.t{hour_str}z.pgrb2.1p00.anl"
    else:
        file_name = f"gfs.t{hour_str}z.pgrb2.1p00.f{forecast_hour:03d}"
    
    # Build URL - exact format that works with NOAA
    base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl"
    
    params = [
        f"dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos",
        f"file={file_name}",
        "var_TMP=on",      # Temperature
        "var_UGRD=on",     # U-wind component
        "var_VGRD=on",     # V-wind component
        "lev_200_mb=on",   # ~FL390
        "lev_250_mb=on",   # ~FL340
        "lev_300_mb=on"    # ~FL300
    ]
    
    return base_url + "?" + "&".join(params)

def download_grib(url, output_path, timeout=120):
    """
    Download GRIB file from NOAA with proper SSL and headers
    
    Args:
        url: Full URL to download
        output_path: Path object where to save the file
        timeout: Request timeout in seconds
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"  Downloading from NOAA...")
    
    try:
        # Create request with browser-like headers
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        req.add_header('Accept', '*/*')
        req.add_header('Connection', 'keep-alive')
        
        # Create SSL context for HTTPS
        ssl_context = ssl.create_default_context()
        
        # Download with timeout
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            content = response.read()
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(content)
            
            size_mb = len(content) / (1024 * 1024)
            print(f"  ✓ Downloaded {size_mb:.2f} MB")
            return True
            
    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        if e.code == 500:
            print(f"    Server error - model run may not be ready yet")
        return False
        
    except urllib.error.URLError as e:
        print(f"  ✗ Connection error: {e.reason}")
        return False
        
    except Exception as e:
        print(f"  ✗ Error: {type(e).__name__}: {e}")
        return False

def get_cache_path(run_date, forecast_hour=0):
    """Get cache file path for a specific model run"""
    date_str = run_date.strftime('%Y%m%d')
    hour_str = f"{run_date.hour:02d}"
    
    if forecast_hour == 0:
        filename = f"gfs_{date_str}_{hour_str}Z.grib2"
    else:
        filename = f"gfs_{date_str}_{hour_str}Z_f{forecast_hour:03d}.grib2"
    
    return CACHE_DIR / filename

def is_cache_valid(cache_path):
    """Check if cached file exists and is not too old"""
    if not cache_path.exists():
        return False
    
    # Check age
    file_time = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC)
    age = datetime.now(UTC) - file_time
    
    return age < CACHE_DURATION

def fetch_model(run_date, forecast_hour=0, force_download=False):
    """
    Fetch a GFS model run, using cache if available
    
    Args:
        run_date: datetime of model run
        forecast_hour: 0 for analysis, 3/6/9 for forecast
        force_download: Force download even if cached
    
    Returns:
        Path: Path to GRIB file, or None if failed
    """
    cache_path = get_cache_path(run_date, forecast_hour)
    
    # Check cache
    if not force_download and is_cache_valid(cache_path):
        print(f"  ✓ Using cached file: {cache_path.name}")
        return cache_path
    
    # Download
    url = build_gfs_url(run_date, forecast_hour)
    
    # Ensure cache directory exists
    CACHE_DIR.mkdir(exist_ok=True)
    
    if download_grib(url, cache_path):
        return cache_path
    else:
        return None

def fetch_wind_models(force_download=False):
    """
    Fetch current GFS model. Previous model comes from cache (if available).
    
    Args:
        force_download: Force download even if cached
    
    Returns:
        dict: {'previous': Path, 'current': Path, 'previous_time': datetime, 'current_time': datetime}
              or None if current model fetch failed
    """
    print("=" * 70)
    print("Fetching GFS Wind Models")
    print("=" * 70)
    
    previous_run, current_run = get_gfs_run_times()
    
    # Check if previous model exists in cache (don't download)
    previous_path = get_cache_path(previous_run, forecast_hour=0)
    if previous_path.exists():
        print(f"\nPrevious model: {previous_run.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  ✓ Using cached file: {previous_path.name}")
    else:
        print(f"\nPrevious model: Not available (will be available after next fetch)")
        previous_path = None
        previous_run = None
    
    # Always fetch current model
    print(f"\nCurrent model: {current_run.strftime('%Y-%m-%d %H:%M UTC')}")
    current_path = fetch_model(current_run, forecast_hour=0, force_download=force_download)
    
    if not current_path:
        print("\n✗ Failed to fetch current model")
        return None
    
    print("\n" + "=" * 70)
    if previous_path:
        print("✓ Wind models ready (with interpolation)")
    else:
        print("✓ Current wind model ready (no interpolation)")
    print("=" * 70)
    
    return {
        'previous': previous_path,
        'current': current_path,
        'previous_time': previous_run,
        'current_time': current_run
    }

def cleanup_old_cache():
    """Remove GRIB files older than cache duration"""
    if not CACHE_DIR.exists():
        return
    
    cutoff = datetime.now(UTC) - CACHE_DURATION
    removed = 0
    
    for file in CACHE_DIR.glob("gfs_*.grib2"):
        file_time = datetime.fromtimestamp(file.stat().st_mtime, UTC)
        if file_time < cutoff:
            file.unlink()
            removed += 1
    
    if removed > 0:
        print(f"Cleaned up {removed} old GRIB file(s)")

if __name__ == "__main__":
    """Test fetcher"""
    import sys
    
    # Cleanup old files
    cleanup_old_cache()
    
    # Fetch models
    models = fetch_wind_models(force_download='--force' in sys.argv)
    
    if models:
        if models['previous']:
            print(f"\nPrevious model: {models['previous']}")
        print(f"Current model: {models['current']}")
        
        # Show file info
        if models['previous']:
            prev_size = models['previous'].stat().st_size / 1024
            print(f"\nPrevious model size: {prev_size:.1f} KB")
        
        current_size = models['current'].stat().st_size / 1024
        print(f"Current model size: {current_size:.1f} KB")
        
        sys.exit(0)
    else:
        print("\n✗ Failed to fetch wind models")
        sys.exit(1)
