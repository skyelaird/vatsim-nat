#!/usr/bin/env python3
"""
NAT Conflict Dashboard Backend
Flask server providing conflict probe data via REST API
"""
from flask import Flask, jsonify, send_from_directory
from datetime import datetime, UTC, timedelta
import sqlite3
from pathlib import Path
import sys
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from conflict_strip_atc import get_active_crossings, build_trajectory, detect_conflicts

app = Flask(__name__, static_folder='.')
DB_PATH = str(Path(__file__).parent.parent / 'nat_traffic.db')

# Verify database exists
if not Path(DB_PATH).exists():
    print(f"ERROR: Database not found at {DB_PATH}")
    sys.exit(1)
else:
    print(f"Using database: {DB_PATH} ({Path(DB_PATH).stat().st_size} bytes)")

# NAT entry points
EASTBOUND_ENTRIES = ['TUDEP', 'ELSIR', 'ALLRY', 'NICSO', 'SUPRY', 'JOOPY']  # West side
WESTBOUND_ENTRIES = ['RIKAL', 'NEEKO', 'LOMSI', 'JANJO', 'PIKIL']  # East side

@app.route('/')
def index():
    """Serve main dashboard page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)

@app.route('/api/entry-conflicts')
def get_entry_conflicts():
    """Get conflict summary for all entry points"""
    try:
        flights = get_active_crossings()
        print(f"Loaded {len(flights)} active flights")
        
        trajectories = [build_trajectory(f) for f in flights]
        trajectories = [t for t in trajectories if t]
        print(f"Built {len(trajectories)} trajectories")
        
        conflicts = detect_conflicts(trajectories, flights)
        print(f"Detected {len(conflicts)} conflicts")
        
        now = datetime.now(UTC)
        approaching_flights = filter_approaching_flights(flights, trajectories, now, 60)
        print(f"Found {len(approaching_flights)} approaching flights")
        
        eastbound = process_entry_points(EASTBOUND_ENTRIES, approaching_flights, conflicts, 'EB')
        westbound = process_entry_points(WESTBOUND_ENTRIES, approaching_flights, conflicts, 'WB')
        
        return jsonify({
            'timestamp': now.isoformat(),
            'eastbound': eastbound,
            'westbound': westbound
        })
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/entry-strips/<entry_name>')
def get_entry_strips(entry_name):
    """Get detailed ATC strips for specific entry point"""
    try:
        flights = get_active_crossings()
        trajectories = [build_trajectory(f) for f in flights]
        trajectories = [t for t in trajectories if t]
        conflicts = detect_conflicts(trajectories, flights)
        
        now = datetime.now(UTC)
        approaching = filter_approaching_flights(flights, trajectories, now, 60)
        entry_flights = [f for f in approaching if f['entry_fix'] == entry_name]
        
        entry_conflicts = []
        for conflict in conflicts:
            if entry_name in conflict.get('waypoints', []):
                f1 = next((f for f in flights if f['callsign'] == conflict['flight1']), None)
                f2 = next((f for f in flights if f['callsign'] == conflict['flight2']), None)
                
                if f1 and f2:
                    entry_conflicts.append({
                        'waypoint': entry_name,
                        'separation': conflict['separation_min'],
                        'is_overtake': 'overtake' in conflict.get('type', '').lower(),
                        'flight1': format_flight_for_strip(f1),
                        'flight2': format_flight_for_strip(f2)
                    })
        
        all_flights = [format_flight_for_strip(f) for f in entry_flights]
        
        return jsonify({
            'entry_name': entry_name,
            'conflicts': entry_conflicts,
            'all_flights': all_flights
        })
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def filter_approaching_flights(flights, trajectories, now, minutes_ahead):
    """Filter flights approaching entry within specified minutes"""
    approaching = []
    for flight in flights:
        traj = next((t for t in trajectories if t and t[0]['callsign'] == flight['callsign']), None)
        if not traj:
            continue
        
        entry_point = traj[0]
        entry_eta = entry_point['eta']
        time_to_entry = (entry_eta - now).total_seconds() / 60
        
        if 0 <= time_to_entry <= minutes_ahead:
            flight['entry_fix'] = entry_point['waypoint']
            flight['entry_eta'] = entry_eta.strftime('%H%M')
            approaching.append(flight)
    return approaching

def process_entry_points(entry_list, approaching_flights, conflicts, direction):
    """Process entry points and determine conflict status"""
    result = []
    for entry in entry_list:
        entry_flights = [f for f in approaching_flights if f.get('entry_fix') == entry]
        entry_conflicts = [c for c in conflicts if entry in c.get('waypoints', [])]
        
        status = 'clear'
        if entry_conflicts:
            critical = any(
                c.get('separation_min', 999) < 3 or 'overtake' in c.get('type', '').lower()
                for c in entry_conflicts
            )
            status = 'critical' if critical else 'warning'
        
        result.append({
            'name': entry,
            'flight_count': len(entry_flights),
            'conflict_count': len(entry_conflicts),
            'status': status
        })
    result.sort(key=lambda x: x['flight_count'], reverse=True)
    return result

def format_flight_for_strip(flight):
    """Format flight data for ATC strip display"""
    route = flight.get('oceanic_route', '')
    waypoints = []
    for part in route.split():
        if '/' in part:
            waypoints.append(part.split('/')[0])
        elif re.match(r'^\d{2}N\d{3}W', part):
            waypoints.append(part)
    
    callsign = flight['callsign']
    aircraft = flight.get('aircraft', '----')
    fl = flight.get('fl', '---')
    entry_eta = flight.get('entry_eta', '----')
    waypoint_str = ' '.join(waypoints[:6]) if waypoints else route[:40]
    strip_text = f"{callsign:8s}  {aircraft:8s}  {waypoint_str:50s}  FL{fl}  ETA {entry_eta}"
    
    return {
        'callsign': callsign,
        'aircraft': aircraft,
        'fl': fl,
        'entry_eta': entry_eta,
        'route': route,
        'strip_text': strip_text
    }

if __name__ == '__main__':
    print("=" * 70)
    print("NAT Conflict Dashboard Server")
    print("=" * 70)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Dashboard: http://localhost:5000")
    print("\nPress Ctrl+C to stop")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
