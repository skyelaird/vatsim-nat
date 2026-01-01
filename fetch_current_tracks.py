"""
Manually fetch current NAT tracks
Run: python fetch_current_tracks.py
"""
import sqlite3
from track_fetcher import NATTrackFetcher
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Connect to database
conn = sqlite3.connect('D:\\GitHub\\vatsim-nat\\nat_traffic.db')

# Create fetcher
fetcher = NATTrackFetcher(conn)

print("=" * 60)
print("Fetching current NAT tracks from FAA...")
print("=" * 60)
print()

# Fetch both eastbound and westbound
print("Fetching EASTBOUND tracks...")
if fetcher.fetch_and_store('eastbound'):
    print("✓ Eastbound tracks stored\n")
else:
    print("✗ Failed to fetch eastbound tracks\n")

print("Fetching WESTBOUND tracks...")
if fetcher.fetch_and_store('westbound'):
    print("✓ Westbound tracks stored\n")
else:
    print("✗ Failed to fetch westbound tracks\n")

# Show what we got
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM nat_ots_tracks")
count = cursor.fetchone()[0]

if count > 0:
    print("=" * 60)
    print(f"SUCCESS: {count} tracks stored in database")
    print("=" * 60)
    print()
    
    cursor.execute("""
        SELECT effective_date, tmi, track_letter, entry_point, exit_point
        FROM nat_ots_tracks
        ORDER BY track_letter
    """)
    
    print(f"{'Track':<8} {'Entry':<10} {'Exit':<10} {'Effective':<12} {'TMI':<5}")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"{row[2]:<8} {row[3]:<10} {row[4]:<10} {row[0]:<12} {row[1]:<5}")
else:
    print("No tracks found - check log for errors")

conn.close()
