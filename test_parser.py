"""
Test track parser with debug output
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

print("=" * 60)
print("CLEANED TEXT (first 1000 chars):")
print("=" * 60)
print(text[:1000])
print()

# Look for Track V
print("=" * 60)
print("SEARCHING FOR TRACK V:")
print("=" * 60)
pattern = r'V ([A-Z0-9/ ]+?)(?:EAST LVLS|WEST LVLS)'
match = re.search(pattern, text)
if match:
    print(f"✓ FOUND: {match.group(0)}")
    print(f"  Waypoints: {match.group(1)}")
else:
    print("✗ NOT FOUND")
    print()
    print("Looking for 'V SUPRY' in text:")
    if 'V SUPRY' in text:
        idx = text.index('V SUPRY')
        print(f"Found at position {idx}:")
        print(text[idx:idx+200])
    else:
        print("'V SUPRY' not found in text!")
