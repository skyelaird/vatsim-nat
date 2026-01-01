"""
Debug: Save NAT track HTML to file
"""
import requests
import certifi

session = requests.Session()
session.verify = certifi.where()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

url = "https://notams.aim.faa.gov/nat.html"
response = session.get(url, timeout=30)

with open('nat_debug.html', 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"Saved {len(response.text)} bytes to nat_debug.html")
print()
print("First 500 chars:")
print(response.text[:500])
print()
print("Search for 'TMI':")
if 'TMI' in response.text:
    idx = response.text.index('TMI')
    print(response.text[idx:idx+200])
else:
    print("TMI not found!")
