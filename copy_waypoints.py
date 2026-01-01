"""
Copy waypoint files from outputs to repo
Run this after generating waypoints
"""
import shutil

files = [
    'nat_waypoints.py',
    'nat_waypoints.json', 
    'nat_waypoints.csv',
    'nat_waypoints.sql'
]

for filename in files:
    src = f'/mnt/user-data/outputs/{filename}'
    dst = f'D:\\GitHub\\vatsim-nat\\{filename}'
    
    try:
        shutil.copy(src, dst)
        print(f"✓ Copied {filename}")
    except Exception as e:
        print(f"✗ Failed to copy {filename}: {e}")

print("\nDone! Waypoint files ready in repo.")
