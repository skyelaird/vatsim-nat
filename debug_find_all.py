"""
Find ALL occurrences of 'X ' and 'Y ' in the text
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
text = re.sub(r'<[^>]+>', '', html)

print("All occurrences of 'X ' in text:")
for match in re.finditer(r'X ', text):
    idx = match.start()
    print(f"  Position {idx}: ...{text[idx-20:idx+40]}...")

print()
print("All occurrences of 'Y ' in text:")
for match in re.finditer(r'Y ', text):
    idx = match.start()
    print(f"  Position {idx}: ...{text[idx-20:idx+40]}...")
