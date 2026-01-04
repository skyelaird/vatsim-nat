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

# NAT entry points - COMPREHENSIVE lists
EASTBOUND_ENTRIES = [
    # Canadian entries (west side)
    'DOGAL', 'LIMRI', 'RESNO', 'ELSIR', 'RATKA', 'JOOPY',
    # US entries (west side)
    'TUDEP', 'ALLRY', 'NICSO', 'SUPRY', 'DINIM', 'PORTI',
    'KODIK', 'DIRGI', 'MUSVA'
]

WESTBOUND_ENTRIES = [
    # UK/Ireland exits (east side for westbound = entry points)
    'RIKAL', 'NEEKO', 'LOMSI', 'JANJO', 'PIKIL',
    'MALOT', 'GISTI', 'SOORY', 'BEDRA', 'NERTU',
    'BAKUR', 'LEKVA', 'NASBA', 'RENDL'
]

@app.route('/')
def index():
    """Serve main dashboard page"""
    return send_from_directory('.', 'index.html')

@app.route('/analytics')
def analytics():
    """Serve analytics/QA page"""
    return send_from_directory('.', 'analytics.html')

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
    # Validate entry_name format (prevent injection, allow any valid waypoint)
    # Accept:
    #   - Named waypoints: AGORI, SUNOT (4-6 alphanumeric, ARINC 424)
    #   - Full lat/lon: 57N050W, 5730N05000W
    #   - Short format: 50/20, 5730/50
    valid_format = re.match(r'^([A-Z0-9]{4,6}|\d{2,4}[NS]\d{3,5}[EW]|\d{2,4}/\d{2,3})$', entry_name)
    if not valid_format:
        # Log for pattern improvement - might be legitimate waypoint we missed
        print(f"⚠️  Blocked waypoint format: '{entry_name}' - check if legitimate")
        return jsonify({'error': f'Invalid waypoint format: {entry_name}'}), 400

    try:
        flights = get_active_crossings()
        trajectories = [build_trajectory(f) for f in flights]
        trajectories = [t for t in trajectories if t]
        conflicts = detect_conflicts(trajectories, flights)

        now = datetime.now(UTC)
        approaching = filter_approaching_flights(flights, trajectories, now, 60)

        # Filter for THIS entry point only from approaching flights
        entry_flights = [f for f in approaching if f.get('entry_fix') == entry_name]
        
        # Only show conflicts where BOTH flights are approaching this entry
        entry_conflicts = []
        for conflict in conflicts:
            if entry_name in conflict.get('waypoints', []):
                f1_callsign = conflict['flight1']
                f2_callsign = conflict['flight2']
                
                # Check if both flights are in our approaching list
                f1 = next((f for f in entry_flights if f['callsign'] == f1_callsign), None)
                f2 = next((f for f in entry_flights if f['callsign'] == f2_callsign), None)
                
                if f1 and f2:
                    entry_conflicts.append({
                        'waypoint': entry_name,
                        'separation': conflict['separation_min'],
                        'is_overtake': 'overtake' in conflict.get('type', '').lower(),
                        'flight1': format_flight_for_strip(f1),
                        'flight2': format_flight_for_strip(f2)
                    })
        
        all_flights = [format_flight_for_strip(f) for f in entry_flights]
        
        print(f"LOMSI: {len(entry_flights)} approaching flights, {len(entry_conflicts)} conflicts")
        
        return jsonify({
            'entry_name': entry_name,
            'conflicts': entry_conflicts,
            'all_flights': all_flights
        })
    except Exception as e:
        import traceback
        print(f"❌ Error processing entry point '{entry_name}': {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'entry_name': entry_name}), 500

def filter_approaching_flights(flights, trajectories, now, minutes_ahead):
    """Filter flights approaching NAT entry within specified minutes"""
    import re
    approaching = []
    
    for flight in flights:
        traj = next((t for t in trajectories if t and len(t) > 0 and t[0]['callsign'] == flight['callsign']), None)
        if not traj:
            continue
        
        entry_point = traj[0]
        entry_waypoint = entry_point['waypoint']
        entry_eta = entry_point['eta']
        time_to_entry = (entry_eta - now).total_seconds() / 60
        
        # Skip if "entry" is just a lat/lon coordinate (not a real entry fix)
        if re.match(r'^\d{2,4}[NS]\d{3,5}[EW]$', entry_waypoint):
            print(f"Skipping {flight['callsign']}: entering at coordinate {entry_waypoint} (not a named fix)")
            continue

        print(f"Flight {flight['callsign']}: entry={entry_waypoint}, ETA={entry_eta.strftime('%H%M')}, time={time_to_entry:.1f}min")
        
        if 0 <= time_to_entry <= minutes_ahead:
            flight['entry_fix'] = entry_waypoint
            flight['entry_eta'] = entry_eta.strftime('%H%M')
            flight['trajectory'] = traj
            approaching.append(flight)
    
    print(f"\nTotal approaching at named fixes: {len(approaching)} flights")
    return approaching

def process_entry_points(entry_list, approaching_flights, conflicts, direction):
    """Process entry points - count flights ENTERING at each fix"""
    result = []
    
    # Debug: Show all entry points being used
    all_entries = {}
    for f in approaching_flights:
        entry = f.get('entry_fix')
        all_entries[entry] = all_entries.get(entry, 0) + 1
    print(f"\n{direction} - All entries in use: {all_entries}")
    print(f"{direction} - Monitoring: {entry_list}")
    
    for entry in entry_list:
        # Flights entering at THIS specific entry point
        entry_flights = [f for f in approaching_flights if f.get('entry_fix') == entry]
        
        # Conflicts at this entry where both flights are entering here
        entry_callsigns = {f['callsign'] for f in entry_flights}
        entry_conflicts = []
        for c in conflicts:
            if entry in c.get('waypoints', []):
                if c['flight1'] in entry_callsigns and c['flight2'] in entry_callsigns:
                    entry_conflicts.append(c)
        
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
    
    # Extract aircraft type only (before first /)
    aircraft_full = flight.get('aircraft', '----')
    aircraft = aircraft_full.split('/')[0] if '/' in aircraft_full else aircraft_full
    
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

@app.route('/api/qa')
def qa_metrics():
    """
    QA/Sanity check endpoint - comprehensive data quality analysis
    Returns issues with trajectory building, speeds, positions, and data completeness
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Get all active crossings
        flights = get_active_crossings()

        # Initialize issue trackers
        trajectory_failures = []
        invalid_speeds = []
        stuck_flights = []
        coordinate_anomalies = []
        missing_fields = []
        prediction_errors = []

        total_flights = len(flights)
        successful_trajectories = 0

        # Check each flight for issues
        for flight in flights:
            callsign = flight['callsign']

            # 1. Trajectory build test
            try:
                traj = build_trajectory(flight)
                if traj and len(traj) > 0:
                    successful_trajectories += 1
                else:
                    trajectory_failures.append({
                        'callsign': callsign,
                        'route': flight.get('oceanic_route', 'NO ROUTE'),
                        'reason': 'Empty trajectory returned'
                    })
            except Exception as e:
                trajectory_failures.append({
                    'callsign': callsign,
                    'route': flight.get('oceanic_route', 'NO ROUTE'),
                    'reason': str(e)
                })

            # 2. Speed validation (100-600 kts reasonable for jets)
            gs = flight.get('gs', 0)
            if gs and (gs < 100 or gs > 600):
                invalid_speeds.append({
                    'callsign': callsign,
                    'gs': gs
                })

            # 3. Coordinate validation (NAT region bounds)
            lat = flight.get('lat', 0)
            lon = flight.get('lon', 0)
            if lat < 25 or lat > 75:
                coordinate_anomalies.append({
                    'callsign': callsign,
                    'reason': f'Latitude {lat}° outside NAT region (25-75°N)'
                })
            if lon > -10 or lon < -80:
                coordinate_anomalies.append({
                    'callsign': callsign,
                    'reason': f'Longitude {lon}° outside NAT region (80W-10W)'
                })

            # 4. Missing critical fields
            if not flight.get('oceanic_route'):
                missing_fields.append({
                    'callsign': callsign,
                    'field': 'oceanic_route'
                })
            if not flight.get('aircraft'):
                missing_fields.append({
                    'callsign': callsign,
                    'field': 'aircraft_type'
                })

        # 5. Stuck flights check (>12 hours in database with no exit)
        cursor.execute("""
            SELECT callsign,
                   CAST((julianday('now') - julianday(entry_time)) * 24 AS INTEGER) as hours_in_db
            FROM nat_crossings
            WHERE exit_time IS NULL
              AND entry_time < datetime('now', '-12 hours')
        """)
        for row in cursor.fetchall():
            stuck_flights.append({
                'callsign': row[0],
                'hours_in_db': row[1]
            })

        # 6. Position prediction errors (if prediction tracker is integrated)
        # TODO: Integrate with prediction_tracker.py when implemented
        # For now, check for position update staleness
        cursor.execute("""
            SELECT callsign,
                   CAST((julianday('now') - julianday(last_update_time)) * 1440 AS INTEGER) as minutes_stale
            FROM nat_crossings
            WHERE exit_time IS NULL
              AND last_update_time < datetime('now', '-15 minutes')
        """)
        for row in cursor.fetchall():
            prediction_errors.append({
                'callsign': row[0],
                'error_nm': 0,
                'time_span': row[1],
                'predicted_speed': 0,
                'actual_speed': 0,
                'reason': f'No position update for {row[1]} minutes (stale data)'
            })

        conn.close()

        # Calculate summary statistics
        trajectory_success_rate = round((successful_trajectories / total_flights * 100) if total_flights > 0 else 0, 1)
        total_issues = (len(trajectory_failures) + len(invalid_speeds) +
                       len(stuck_flights) + len(coordinate_anomalies) +
                       len(missing_fields) + len(prediction_errors))

        return jsonify({
            'timestamp': datetime.now(UTC).isoformat(),
            'summary': {
                'total_flights': total_flights,
                'trajectory_success_rate': trajectory_success_rate,
                'total_issues': total_issues
            },
            'issues': {
                'trajectory_failures': trajectory_failures,
                'invalid_speeds': invalid_speeds,
                'stuck_flights': stuck_flights,
                'coordinate_anomalies': coordinate_anomalies,
                'missing_fields': missing_fields,
                'prediction_errors': prediction_errors
            }
        })

    except Exception as e:
        import traceback
        print(f"❌ Error in QA metrics: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/qa/filtering')
def qa_filtering():
    """
    Flight filtering report - explains what's displayed vs filtered out
    Helps validate why certain flights appear or don't appear on main page
    """
    try:
        flights = get_active_crossings()
        trajectories = [build_trajectory(f) for f in flights]

        now = datetime.now(UTC)
        approaching = filter_approaching_flights(flights, trajectories, now, 60)

        # Track filtering reasons
        no_trajectory = []
        not_approaching = []
        invalid_entry = []
        displayed = []

        for i, flight in enumerate(flights):
            callsign = flight['callsign']
            traj = trajectories[i]

            if not traj or len(traj) == 0:
                no_trajectory.append(callsign)
            elif flight not in approaching:
                # Check why not approaching
                if traj:
                    entry_point = traj[0]
                    entry_eta = entry_point['eta']
                    time_to_entry = (entry_eta - now).total_seconds() / 60

                    if time_to_entry < 0:
                        not_approaching.append({
                            'callsign': callsign,
                            'reason': f'Already passed entry ({abs(int(time_to_entry))} min ago)'
                        })
                    elif time_to_entry > 60:
                        not_approaching.append({
                            'callsign': callsign,
                            'reason': f'Too far from entry ({int(time_to_entry)} min away)'
                        })
                    else:
                        # Check if entry is coordinate vs named fix
                        entry_waypoint = entry_point['waypoint']
                        if re.match(r'^\d{2,4}[NS]\d{3,5}[EW]$', entry_waypoint):
                            invalid_entry.append({
                                'callsign': callsign,
                                'entry': entry_waypoint,
                                'reason': 'Entry is coordinate, not named fix'
                            })
            else:
                displayed.append(callsign)

        # Group displayed flights by entry point
        entry_breakdown = {}
        for flight in approaching:
            entry = flight.get('entry_fix', 'UNKNOWN')
            if entry not in entry_breakdown:
                entry_breakdown[entry] = []
            entry_breakdown[entry].append(flight['callsign'])

        return jsonify({
            'timestamp': datetime.now(UTC).isoformat(),
            'summary': {
                'total_in_db': len(flights),
                'displayed_on_main': len(displayed),
                'filtered_out': len(flights) - len(displayed)
            },
            'filtering_reasons': {
                'no_trajectory': no_trajectory,
                'not_approaching': not_approaching,
                'invalid_entry_point': invalid_entry
            },
            'displayed_flights': displayed,
            'flights_per_entry': entry_breakdown
        })

    except Exception as e:
        import traceback
        print(f"❌ Error in filtering report: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/qa/flight/<callsign>')
def qa_flight_detail(callsign):
    """
    Detailed flight validation - compare raw DB data vs processed data
    Shows exactly what's happening with a specific flight
    """
    try:
        # Get raw data from database
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT callsign, aircraft_type, departure, destination,
                   oceanic_route, ots_track, filed_altitude, selcal,
                   entry_time, current_lat, current_lon, current_fl, current_gs,
                   last_update_time
            FROM nat_crossings
            WHERE callsign = ? AND exit_time IS NULL
            ORDER BY entry_time DESC
            LIMIT 1
        """, (callsign,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': f'Flight {callsign} not found in active crossings'}), 404

        raw_data = {
            'callsign': row[0],
            'aircraft_type': row[1],
            'departure': row[2],
            'destination': row[3],
            'oceanic_route': row[4],
            'ots_track': row[5],
            'filed_altitude': row[6],
            'selcal': row[7],
            'entry_time': row[8],
            'current_lat': row[9],
            'current_lon': row[10],
            'current_fl': row[11],
            'current_gs': row[12],
            'last_update_time': row[13]
        }

        # Build flight object for processing
        flight = {
            'callsign': row[0],
            'aircraft': row[1],
            'departure': row[2],
            'destination': row[3],
            'oceanic_route': row[4],
            'lat': row[9],
            'lon': row[10],
            'fl': row[11],
            'gs': row[12]
        }

        # Try to build trajectory
        trajectory_status = {
            'success': False,
            'error': None,
            'waypoints': []
        }

        try:
            traj = build_trajectory(flight)
            if traj and len(traj) > 0:
                trajectory_status['success'] = True
                trajectory_status['waypoints'] = [
                    {
                        'waypoint': wp['waypoint'],
                        'lat': wp['lat'],
                        'lon': wp['lon'],
                        'eta': wp['eta'].strftime('%H%MZ')
                    }
                    for wp in traj[:5]  # First 5 waypoints
                ]
            else:
                trajectory_status['error'] = 'Empty trajectory returned'
        except Exception as e:
            trajectory_status['error'] = str(e)

        # Check if approaching
        now = datetime.now(UTC)
        is_approaching = False
        entry_info = None

        if trajectory_status['success']:
            entry_point = traj[0]
            entry_eta = entry_point['eta']
            time_to_entry = (entry_eta - now).total_seconds() / 60

            entry_info = {
                'entry_fix': entry_point['waypoint'],
                'entry_eta': entry_eta.strftime('%H%MZ'),
                'minutes_to_entry': round(time_to_entry, 1),
                'is_approaching': 0 <= time_to_entry <= 60
            }
            is_approaching = entry_info['is_approaching']

        # Direction classification
        is_eastbound = flight['departure'][0] in 'KC'

        # Calculate how long in DB
        if raw_data['entry_time']:
            entry_dt = datetime.fromisoformat(raw_data['entry_time'].replace('Z', '+00:00'))
            minutes_in_db = (now - entry_dt).total_seconds() / 60
        else:
            minutes_in_db = 0

        # Calculate staleness
        if raw_data['last_update_time']:
            update_dt = datetime.fromisoformat(raw_data['last_update_time'].replace('Z', '+00:00'))
            minutes_stale = (now - update_dt).total_seconds() / 60
        else:
            minutes_stale = 999999

        return jsonify({
            'callsign': callsign,
            'raw_from_database': raw_data,
            'processed': {
                'direction': 'EASTBOUND' if is_eastbound else 'WESTBOUND',
                'trajectory_build': trajectory_status,
                'entry_point_info': entry_info,
                'is_approaching': is_approaching,
                'will_display_on_main': is_approaching and trajectory_status['success']
            },
            'data_quality': {
                'minutes_in_database': round(minutes_in_db, 1),
                'minutes_since_update': round(minutes_stale, 1),
                'is_stale': minutes_stale > 15,
                'has_oceanic_route': raw_data['oceanic_route'] is not None,
                'has_selcal': raw_data['selcal'] is not None
            },
            'issues': [
                'No oceanic route' if not raw_data['oceanic_route'] else None,
                f'Stale data ({int(minutes_stale)} min)' if minutes_stale > 15 else None,
                f'Stuck in DB ({int(minutes_in_db/60)} hours)' if minutes_in_db > 720 else None,
                'Trajectory build failed' if not trajectory_status['success'] else None
            ]
        })

    except Exception as e:
        import traceback
        print(f"❌ Error in flight detail: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("NAT Conflict Dashboard Server")
    print("=" * 70)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Dashboard: http://localhost:5000")
    print("\nPress Ctrl+C to stop")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
