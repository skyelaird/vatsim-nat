"""
Examine Navigraph data structure
"""

# Read sample records from each file
files = [
    ('wpNavFIX.txt', 'Waypoints/Fixes'),
    ('wpNavRTE.txt', 'Routes/Airways'),
    ('wpNavAID.txt', 'Navaids'),
    ('airports.dat', 'Airports')
]

for filename, description in files:
    filepath = f'D:\\GitHub\\vatsim-nat\\NavData\\{filename}'
    
    print("=" * 80)
    print(f"{description}: {filename}")
    print("=" * 80)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # Skip header comments
            data_lines = [l for l in lines if not l.startswith(';')]
            
            # Show first 10 data records
            print(f"\nFirst 10 data records:\n")
            for i, line in enumerate(data_lines[:10]):
                print(f"{i+1:3d}: {line.strip()}")
            
            # Show sample from middle (around NAT region)
            # Look for records with lat 40-70 and lon -70 to -10
            print(f"\n\nSample NAT region records (40-70N, 70-10W):\n")
            nat_samples = []
            for line in data_lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    # Try to extract coordinates
                    coord_str = parts[1] if len(parts) > 1 else parts[0]
                    if '-' in coord_str:
                        try:
                            # Format might be: NAME-LAT LON or NAME LAT-LON
                            coords = coord_str.split('-')[-1].split()
                            if len(coords) >= 2:
                                lat = float(coords[0])
                                lon = float(coords[1])
                                
                                # Check if in NAT region
                                if 40 <= lat <= 70 and -70 <= lon <= -10:
                                    nat_samples.append(line.strip())
                                    if len(nat_samples) >= 10:
                                        break
                        except:
                            pass
            
            for i, line in enumerate(nat_samples):
                print(f"{i+1:3d}: {line}")
            
            print(f"\nTotal lines: {len(lines)}")
            print(f"Data lines: {len(data_lines)}")
            
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n")
