# NAT DASHBOARD TODO

## 🔴 CRITICAL - BLOCKING ISSUES

### Time/Position Calculation Bug
- [x] **ROOT CAUSE**: build_trajectory() was starting at `datetime.now()` and calculating through ALL waypoints
- [x] **PROBLEM**: If current position was PAST some waypoints, ETAs went backwards
- [x] **FIX**: Find closest waypoint to current position, build trajectory forward from there
- [x] **IMPLEMENTATION**: 
  - Get current lat/lon and time
  - Find closest waypoint (start_idx)
  - Calculate ETAs from current position to all waypoints[start_idx:]
  - Only return future waypoints
- [ ] **TEST**: Verify VIR14/RESNO times are now correct

### Route Display Still Broken
- [ ] **SYMPTOM**: `EGLL - LIMRI 53N020W ... KEWR` instead of just `LIMRI 53N020W ...`
- [ ] **TRIED**: Filtering departure/destination from route_parts (3 times)
- [ ] **STILL FAILING**: They keep appearing in final output
- [ ] **FIX NEEDED**: Root cause analysis - WHERE are EGLL/KEWR coming from?
- [ ] Debug: Print route_filed, route_clean, route_parts, route_display at each step
- [ ] Check: Is oceanic_route field in DB corrupted?

### Trajectory Build Failures
- [ ] **SYMPTOM**: 7 flights showing "null" instead of error reason
- [ ] **FIX**: Capture actual exception/reason when trajectory build fails
- [ ] Return dict with: `{'success': False, 'reason': 'No waypoints found', 'route': route_text}`
- [ ] Update QA display to show actual failure reasons

---

## 🟠 HIGH PRIORITY - DATA QUALITY

### Database Housekeeping
- [x] **Create cleanup job** to remove flights stuck >24 hours
- [x] Schedule: Run on startup + every hour in background thread
- [x] SQL: `DELETE FROM nat_crossings WHERE exit_time IS NULL AND hours > 24`
- [x] Log cleanup actions to console

### Missing Oceanic Routes
- [ ] **7 flights missing oceanic_route field** - investigate collector
- [ ] Check: Are these flights not filing oceanic clearance?
- [ ] Check: Is route parsing failing in collector?
- [ ] Decision: Skip these flights or handle gracefully?

### Better Error Messages
- [ ] Trajectory failures: Show WHY it failed (no waypoints, bad coordinates, parse error)
- [ ] Missing fields: Show WHICH flight, WHICH field
- [ ] Invalid speeds: Show actual GS value, not just "invalid"

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
