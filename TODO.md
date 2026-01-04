# NAT DASHBOARD TODO

## 🔴🔴🔴 CRITICAL - CODE REVIEW FINDINGS (2026-01-04)

### SYNTAX ERROR - App Won't Run!
- [ ] **FILE**: dashboard/app.py
- [ ] **LINE 151**: Unterminated string literal - missing closing quote/parenthesis
- [ ] **LINE 151-258**: Duplicate code - `filter_approaching_flights()` function appears TWICE
- [ ] **IMPACT**: Python cannot compile app.py - dashboard is completely broken
- [ ] **FIX IMMEDIATELY**: Remove duplicate function, fix regex pattern on line 151
- [ ] **ERROR**:
  ```
  File "dashboard\app.py", line 151
    if re.match(r'^\d{2,4}[NS]\d{3,5}[EW]
                ^
  SyntaxError: unterminated string literal
  ```

### XSS Security Vulnerability
- [ ] **RISK**: Cross-Site Scripting (XSS) via innerHTML
- [ ] **LOCATION**: dashboard/script.js, dashboard/strip_helper.js, dashboard/analytics.js
- [ ] **ISSUE**: Flight data (callsign, aircraft type) inserted via innerHTML without sanitization
- [ ] **ATTACK**: Malicious VATSIM user could set callsign to `<script>alert('xss')</script>`
- [ ] **FIX**: Use textContent instead of innerHTML, or sanitize with DOMPurify library
- [ ] **FILES AFFECTED**:
  - script.js: lines 189, 277 (tombstone HTML)
  - strip_helper.js: lines 11, 58
  - analytics.js: all chart rendering

### JavaScript Function Conflict
- [ ] **FILE CONFLICT**: dashboard/script.js vs dashboard/strip_helper.js
- [ ] **ISSUE**: Both files define `createATCStrip()` with different implementations
- [ ] **PROBLEM**: If both scripts loaded, one will override the other
- [ ] **FIX**: Rename one function or consolidate into single implementation
- [ ] **IMPACT**: Unknown which version is actually being used

### Prediction Tracker Logic Bug
- [ ] **FILE**: prediction_tracker.py
- [ ] **ISSUE**: `update()` method calculates prediction_error_nm but never stores it back into self.flights
- [ ] **LINE 56-63**: Error calculated and returned, but not persisted
- [ ] **LINE 87**: get_suspect_flights() tries to access data['prediction_error_nm'] but it was never saved
- [ ] **FIX**: Add `self.flights[callsign]['prediction_error_nm'] = error_nm` after line 62
- [ ] **FIX**: Also store time_since_prediction and other error metadata

---

## 🔴 CRITICAL - BLOCKING ISSUES

### Exclude Already-Engaged Flights
- [ ] **SYMPTOM**: WJA1 (already exiting NAT) shows as "approaching AGORI"
- [ ] **ROOT CAUSE**: Flight entered NAT hours ago, now near exit point AGORI
- [ ] **PROBLEM**: build_trajectory finds AGORI as closest waypoint, flight passes time filter
- [ ] **FIX**: Check `entry_time` from database in filter_approaching_flights()
  ```python
  # Get entry times from DB
  cursor.execute("""SELECT callsign, minutes_since_entry FROM nat_crossings 
                     WHERE exit_time IS NULL AND entry_time IS NOT NULL""")
  # Skip if already engaged >5 minutes
  if minutes_since_entry > 5: continue
  ```
- [ ] **TEST**: Verify WJA1 no longer appears in approaching list

### NAT Region Filter
- [x] **COMPLETED**: Changed longitude from -80W/-10W to -60W/-10W
- [x] **REASON**: Exclude coastal waypoints (RABIK -72.6W, PEMLU -80W, MUSVA -63W)
- [x] **FILE**: conflict_strip_atc.py line 173
- [ ] **TEST**: Verify RABIK/PEMLU/MUSVA no longer appear in trajectories

### Westbound Cell Placement Formula
- [x] **COMPLETED**: WB waypoints fill from right (cell 8)
- [x] **FORMULA**: `cellIndex = 9 - flight.waypoints.length + i`
- [x] **FILE**: dashboard/script.js lines 215, 246
- [ ] **TEST**: Verify SUNOT appears in cell 8 for WB flights
- [ ] **VERIFY**: Formula might be backwards - check with live data!

### Route Display Still Broken
- [ ] **SYMPTOM**: `EDDF - SUNOT 58N020W ... - MMUN` instead of `SUNOT 58N020W ... DORYY`
- [ ] **ROOT CAUSE**: Origin/destination still appearing despite filters
- [ ] **INVESTIGATION NEEDED**: Where are EDDF/MMUN coming from?
- [ ] Debug: Print route at each transformation step
- [ ] Check: oceanic_route field in database

### Flight Count Mismatch  
- [ ] **SYMPTOM**: Header shows "SUNOT - 1 Flights" but displays 2 flights
- [ ] **CAUSE**: Entry card uses stale count, modal fetches fresh data
- [ ] **FIX**: Ensure both use same data source or invalidate cache

### Trajectory Build Failures
- [ ] **SYMPTOM**: 7 flights showing "null" instead of error reason
- [ ] **FIX**: Capture exception/reason when build fails
- [ ] Return: `{'success': False, 'reason': 'description'}`
- [ ] Display actual failure reasons in QA metrics

---

## 🟠 HIGH PRIORITY - DATA QUALITY

### Path Traversal Security Risk
- [ ] **FILE**: dashboard/app.py
- [ ] **ROUTES**: `@app.route('/<path:path>')` on line 48
- [ ] **ISSUE**: send_from_directory() with user-controlled path parameter
- [ ] **RISK**: Attacker could request `../../etc/passwd` or other files
- [ ] **FIX**: Validate path parameter, restrict to allowed file types
- [ ] **MITIGATION**: Flask's send_from_directory() has some built-in protection, but explicit validation is safer

### Missing Input Validation
- [ ] **FILE**: dashboard/app.py
- [ ] **ROUTE**: `/api/entry-strips/<entry_name>` (line 85)
- [ ] **ISSUE**: No validation that entry_name is a valid entry point
- [ ] **RISK**: Could cause errors, information disclosure, or DoS
- [ ] **FIX**: Validate entry_name against EASTBOUND_ENTRIES + WESTBOUND_ENTRIES lists
- [ ] **RESPONSE**: Return 404 for invalid entry points

### Closest Waypoint Logic Error
- [ ] **FILE**: conflict_strip_atc.py
- [ ] **LINES**: 204-213 (build_trajectory function)
- [ ] **ISSUE**: Uses CLOSEST waypoint as start_idx, not NEXT waypoint ahead
- [ ] **PROBLEM**: If aircraft passes a waypoint, it might pick the one behind it
- [ ] **FIX**: Need to determine forward direction and pick next waypoint AHEAD
- [ ] **RELATED**: Might be contributing to "already-engaged flights" issue

### Prediction Tracker Integration
- [x] **CREATED**: prediction_tracker.py with in-memory position tracking
- [x] **FEATURES**: Error detection (>30nm threshold), auto-cleanup, haversine calc
- [ ] **TODO**: Add rebuild_prediction_tracker() call on startup
- [ ] **TODO**: Load recent positions from nat_crossings DB to populate tracker
- [ ] **TODO**: Test prediction error detection with live data
- [ ] **PURPOSE**: Sanity check - flag flights with bad speed/position data

### Database Housekeeping
- [x] **COMPLETED**: cleanup_stuck_flights() function
- [x] **RUNS**: On startup + every hour via background thread
- [x] **REMOVES**: Flights stuck >24 hours (exit_time IS NULL)
- [x] **LOGS**: Cleanup actions to console
- [x] **FILE**: dashboard/app.py lines 48-73

### Missing Oceanic Routes
- [ ] **7 flights missing oceanic_route field** - investigate collector
- [ ] Check: Are these flights not filing oceanic clearance?
- [ ] Check: Is route parsing failing in collector?
- [ ] Decision: Skip these flights or handle gracefully?

### Better Error Messages
- [ ] Trajectory failures: Show WHY it failed (no waypoints, bad coordinates, parse error)
- [ ] Missing fields: Show WHICH flight, WHICH field
- [ ] Invalid speeds: Show actual GS value, not just "invalid"
- [ ] Add structured logging for debugging

### Additional Data Quality Checks (Ideas)
- [ ] **Speed consistency**: Track speed changes >100kts/5min
- [ ] **Position jumps**: Detect >500nm position jumps between updates
- [ ] **FL changes**: Flag unexpected altitude changes in oceanic airspace
- [ ] **Route deviations**: Compare actual track vs filed route
- [ ] **Stale data**: Flag flights without position updates >15 minutes
- [ ] **Duplicate callsigns**: Detect same callsign at multiple positions
- [ ] **Invalid coordinates**: Check lat/lon within reasonable bounds
- [ ] **Mach/speed correlation**: Verify GS matches Mach for FL
- [ ] **Time anomalies**: ETAs in the past, unrealistic time-to-waypoint
- [ ] **Waypoint sequence**: Validate waypoint order makes geographic sense

---

## 🟡 MEDIUM PRIORITY - ANALYTICS ENHANCEMENTS

### Traffic Flow Chart Improvements
- [ ] Color-code bars: Eastbound = green, Westbound = red
- [ ] Show EB/WB breakdown in each hour
- [ ] Stacked bar chart or side-by-side bars

### Flight Levels Chart Improvements  
- [ ] Color-code distribution: EB = green, WB = red
- [ ] Show odd/even FL compliance per direction
- [ ] Highlight wrong-way FLs in orange

### Entry Points Display
- [ ] Sort entry points by latitude (north to south)
- [ ] Group by geographic region
- [ ] Show on map?

### Aggregation Period Selector
- [ ] Add dropdown: 6h / 12h / 24h / 48h
- [ ] Default: 24h
- [ ] Update all analytics charts based on selection
- [ ] Store selection in localStorage

---

## 🟡 MEDIUM PRIORITY - PERFORMANCE & CODE QUALITY

### Database Connection Management
- [ ] **FILE**: conflict_strip_atc.py
- [ ] **ISSUE**: Opens new database connection in every function (lines 32, 102)
- [ ] **PERFORMANCE**: Expensive overhead for each call
- [ ] **FIX**: Pass connection as parameter or use connection pooling
- [ ] **ALTERNATIVE**: Use context manager for automatic connection cleanup

### API Response Caching
- [ ] **FILE**: dashboard/app.py
- [ ] **ISSUE**: No caching on expensive operations
- [ ] **IMPACT**: Trajectory building runs on EVERY request
- [ ] **FIX**: Add caching with 30-60 second TTL on /api/entry-conflicts
- [ ] **LIBRARY**: flask-caching or simple in-memory dict with timestamps

### Conflict Detection Optimization
- [ ] **FILE**: conflict_strip_atc.py
- [ ] **LINES**: 250-350 (detect_conflicts function)
- [ ] **ISSUE**: Nested loops O(n²) complexity for waypoint matching
- [ ] **IMPROVEMENT**: Use spatial indexing (R-tree) or dictionary grouping
- [ ] **NOTE**: Current implementation works, only optimize if performance issue observed

### Inconsistent Database Timeouts
- [ ] **FILES**: collector_service.py, conflict_strip_atc.py
- [ ] **ISSUE**: Some connections use timeout=30.0, others use no timeout
- [ ] **LOCATIONS**:
  - collector_service.py line 55: timeout=30.0
  - conflict_strip_atc.py line 32: no timeout
- [ ] **FIX**: Standardize timeout value (30 seconds recommended)
- [ ] **ADD**: Retry logic for timeout errors

### Prediction Tracker Cleanup Never Called
- [ ] **FILE**: prediction_tracker.py
- [ ] **ISSUE**: cleanup() method defined but never invoked anywhere
- [ ] **LINE**: 94-100 (cleanup function exists)
- [ ] **FIX**: Call tracker.cleanup() periodically (every 30 min) in main loop
- [ ] **OR**: Add to database housekeeping thread

### Hard-Coded Configuration Values
- [ ] **ISSUE**: Constants scattered across multiple files
- [ ] **EXAMPLES**:
  - NAT region boundaries: conflict_strip_atc.py line 174-175
  - Refresh intervals: script.js line 5, analytics.js line 8
  - Error thresholds: prediction_tracker.py line 22
  - Time windows: collector_service.py lines 41-46
- [ ] **FIX**: Centralize in config.py or environment variables
- [ ] **BENEFIT**: Easier to adjust without hunting through code

### Missing API Features
- [ ] **NO HEALTH CHECK ENDPOINT**: Add /api/health for monitoring
- [ ] **NO RATE LIMITING**: API vulnerable to abuse/DoS
- [ ] **NO CORS HEADERS**: Might need for future deployments
- [ ] **NO API VERSIONING**: Consider /api/v1/ prefix for future-proofing
- [ ] **NO ERROR STANDARDS**: Inconsistent error response formats

---

## 🟡 MEDIUM PRIORITY - UI/UX

### Clock Display
- [ ] Add live UTC clock near page title
- [ ] Update every second
- [ ] Format: HH:MM:SSZ

### Westbound Fix Labels
- [x] Right-justify waypoint names in WB strips
- [x] Right-justify times in WB strips
- [x] Makes common waypoints align vertically for visual scanning

### API Data Viewer Page
- [ ] New route: `/data-viewer`
- [ ] Show scrollable table of all crossings
- [ ] Columns: ACID, Origin, Dest, Waypoints, ETAs, Last Pos, Last Time
- [ ] Purpose: Manual validation of data quality
- [ ] Export to CSV option?

---

## 🟢 LOW PRIORITY - NICE TO HAVE

### Data Validation Page
- [ ] Comprehensive flight-by-flight validation
- [ ] Show: Route parsing steps
- [ ] Show: Trajectory calculation details
- [ ] Show: Current vs filed FL
- [ ] Show: Speed calculations

### Overtake Detection Validation
- [ ] Test with real conflicts
- [ ] Verify separation_closing calculation
- [ ] Verify CRITICAL severity assignment

### Track Evolution Page
- [ ] `/tracks` - real implementation (not "coming soon")
- [ ] Show OTS track timeline
- [ ] Track-by-track usage stats
- [ ] Conflict rate per track

---

## 📊 CODE REVIEW SUMMARY (2026-01-04)

**Total Issues Found: 20+**

**By Severity:**
- 🔴 **CRITICAL**: 5 (1 syntax error, 2 security, 2 logic bugs)
- 🟠 **HIGH**: 4 (validation, error handling, waypoint logic)
- 🟡 **MEDIUM**: 11 (performance, code quality, API features)

**Top Priorities (Fix Immediately):**
1. ✅ dashboard/app.py syntax error (line 151) - **BLOCKS ALL FUNCTIONALITY**
2. ✅ dashboard/app.py duplicate code (lines 151-258) - **BLOCKS ALL FUNCTIONALITY**
3. ⚠️ XSS vulnerability in innerHTML usage - **SECURITY RISK**
4. ⚠️ Prediction tracker logic bug - **FEATURE BROKEN**
5. ⚠️ JavaScript function conflict (createATCStrip) - **UNKNOWN IMPACT**

**Security Issues:**
- XSS via innerHTML (multiple files)
- Path traversal risk in send_from_directory()
- Missing input validation on API routes
- SQL injection: ✅ **SAFE** (all queries use parameterized statements)

**Performance Notes:**
- Database connections inefficient but functional
- No caching on expensive operations
- Conflict detection could be optimized (not urgent)

**Code Quality:**
- Good: Parameterized SQL queries throughout
- Good: Comprehensive error logging in collector
- Needs: Configuration file for constants
- Needs: API standards (health checks, versioning)

**Files Reviewed:**
- ✅ conflict_strip_atc.py (517 lines)
- ✅ dashboard/app.py (341 lines) - **HAS SYNTAX ERROR**
- ✅ dashboard/script.js (304 lines)
- ✅ dashboard/analytics.js (229 lines)
- ✅ dashboard/strip_helper.js (75 lines)
- ✅ prediction_tracker.py (113 lines)
- ✅ collector_service.py (420 lines)
- ✅ route_parser.py (140 lines)

---

## ✅ COMPLETED

- [x] Dynamic entry point classification by coordinates
- [x] Enhanced overtake detection with separation tracking
- [x] QA/Sanity check API endpoint (`/api/qa`)
- [x] Analytics page with 4 tabs
- [x] Planned FL from route (not current FL)
- [x] 3-column ATC strip layout
- [x] Waypoint/time geographic sorting (W→E)
- [x] Issue tracking checklist created
- [x] Time/position calculation fix (skip past waypoints)
- [x] In-memory prediction tracker
- [x] Position prediction accuracy monitoring
- [x] Prediction errors in QA metrics
- [x] Database housekeeping (auto-cleanup stuck flights)
- [x] NAT longitude filter changed to 60W-10W
- [x] Westbound cell placement formula (right-align from cell 8)
- [x] Route statements all left-justified
- [x] Comprehensive session documentation

---

## 📚 DOCUMENTATION & REFERENCES

### Session Summaries
- **2026-01-03**: NAT filter, WB cell placement, prediction tracker - `/SESSION_SUMMARY_2026-01-03.md`
- See `journal.txt` in `/mnt/transcripts` for transcript catalog

### Key Files & Their Purposes
- **conflict_strip_atc.py**: Trajectory building, conflict detection, NAT waypoint filtering
- **prediction_tracker.py**: In-memory position tracking, prediction error detection
- **dashboard/app.py**: Flask server, API endpoints, data formatting
- **dashboard/script.js**: Frontend UI, ATC strip rendering, cell placement logic
- **dashboard/analytics.js**: QA metrics, traffic flow, FL distribution charts
- **nat_traffic.db**: SQLite database with nat_crossings table
- **nat_waypoints.py**: Waypoint coordinate lookup dictionary

### Database Schema (nat_crossings table)
```sql
callsign, aircraft_type, departure, destination,
oceanic_route, ots_track, filed_altitude, selcal,
entry_time, entry_lat, entry_lon, entry_fl, entry_gs,
mid_time, mid_lat, mid_lon, mid_fl, mid_gs, crossed_mid,
exit_time, exit_lat, exit_lon, exit_fl, exit_gs,
current_lat, current_lon, current_fl, current_gs,
last_update_time
```

### NAT Region Boundaries
- **Latitude**: 45°N to 65°N
- **Longitude**: 60°W to 10°W (changed from 80°W on 2026-01-03)
- **Purpose**: Filter oceanic waypoints, exclude coastal/domestic airspace

### Common Issues & Solutions
1. **File corruption**: Use Claude Code for multi-file edits
2. **Already-engaged flights**: Check entry_time in filter_approaching_flights()
3. **Route display**: Truncate after last oceanic waypoint
4. **Cell placement**: WB formula = 9 - length + i
5. **Prediction errors**: Track >30nm deviations over 5+ minutes

### Testing Checklist
- [ ] Run Flask server: `python dashboard/app.py`
- [ ] Check dashboard: http://localhost:5000
- [ ] Check analytics: http://localhost:5000/analytics
- [ ] Verify entry points populate
- [ ] Click entry point, check strips display
- [ ] Verify WB waypoints right-aligned
- [ ] Check console for errors/warnings
- [ ] Test with multiple simultaneous flights

### Git Workflow
```bash
git status                    # Check changes
git add <files>              # Stage files
git commit -m "message"      # Commit
git push                     # Push to GitHub
git log --oneline -10        # Recent commits
git checkout HEAD -- <file>  # Restore file
```

---

## 📝 NOTES

**Priority Order:**
1. Fix time calculation (CRITICAL - breaks everything)
2. Fix route display (CRITICAL - user-facing)
3. Database cleanup (HIGH - prevents data bloat)
4. Better error messages (HIGH - debugging)
5. Analytics improvements (MEDIUM - polish)
6. UI enhancements (MEDIUM - UX)

**Testing Strategy:**
- Fix time calc, test with VIR14/RESNO example
- Fix route display, test with multiple airports
- Run cleanup, verify DB size reduction
- Check analytics with real traffic data

**Git Commits:**
- Commit after each CRITICAL fix
- Commit analytics improvements as batch
- Tag releases: v1.0 = MVP, v1.1 = polish
