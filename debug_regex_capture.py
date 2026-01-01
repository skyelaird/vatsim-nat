"""
Debug what regex actually captures for each track
"""
import re
import requests
import certifi

session = requests.Session()
session.verify = certifi.where()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

url = "https://notams.aim.faa.gov/nat.html"
response = session.get(url, timeout=30)
html = response.text

# Strip HTML tags
text = re.sub(r'<[^>]+>', '', html)

print("=" * 80)
print("TRACK EXTRACTION TEST")
print("=" * 80)

for letter in ['V', 'W', 'X', 'Y', 'Z']:
    print(f"\nTrack {letter}:")
    pattern = rf'{letter} ([A-Z0-9/ \n]+?)(?:EAST LVLS|WEST LVLS)'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        captured = match.group(1)
        print(f"  Captured text: '{captured}'")
        
        # Split into waypoints
        waypoints = captured.split()
        print(f"  Waypoints: {waypoints}")
        print(f"  Entry: {waypoints[0] if waypoints else 'NONE'}")
    else:
        print(f"  ✗ NOT FOUND")
