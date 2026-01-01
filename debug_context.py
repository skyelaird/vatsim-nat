"""
Show the actual text around tracks X and Y
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

# Find track X
if 'X DOVEY' in text:
    idx = text.index('X DOVEY')
    print("Context around 'X DOVEY':")
    print(text[idx-100:idx+300])
    print()

# Find track Y  
if 'Y JOBOC' in text:
    idx = text.index('Y JOBOC')
    print("Context around 'Y JOBOC':")
    print(text[idx-100:idx+300])
else:
    print("'Y JOBOC' not found in text!")
