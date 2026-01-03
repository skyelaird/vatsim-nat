# Migration Instructions: Add Current Position Tracking

## Overview
This migration adds real-time position tracking to the collector, enabling accurate conflict probing with fresh data.

## What Changed
- **Schema**: Added `last_update_time`, `current_lat`, `current_lon`, `current_fl`, `current_gs` columns
- **Collector**: Now updates current position every 5-minute poll cycle
- **Probe**: Uses `current_*` fields (< 15 min old) instead of stale entry positions

## Migration Steps

### 1. Stop the Collector
```powershell
Stop-ScheduledTask -TaskName "VATSIM NAT Traffic Collector"
```

### 2. Backup Database
```powershell
Copy-Item nat_traffic.db nat_traffic.db.backup
```

### 3. Run Migration SQL
```powershell
sqlite3 nat_traffic.db < migrate_add_current_position.sql
```

### 4. Restart Collector
```powershell
Start-ScheduledTask -TaskName "VATSIM NAT Traffic Collector"
```

### 5. Verify
After one poll cycle (5 minutes), check:
```sql
SELECT callsign, last_update_time, current_lat, current_lon 
FROM nat_crossings 
WHERE exit_time IS NULL 
LIMIT 5;
```

All active flights should have `last_update_time` populated.

## What to Expect

**Before Migration:**
- Probe showed 58-77 conflicts (mostly stale/ghost flights)
- Times jumping backwards on strips
- Flights not on radar appearing in conflicts

**After Migration:**
- Probe shows 5-15 real conflicts (only active flights with fresh positions)
- Times progress correctly W→E
- All conflicts are for flights actually online

## Rollback (if needed)
```powershell
Stop-ScheduledTask -TaskName "VATSIM NAT Traffic Collector"
Copy-Item nat_traffic.db.backup nat_traffic.db
Start-ScheduledTask -TaskName "VATSIM NAT Traffic Collector"
```

Note: Rollback returns to old collector behavior but won't remove new columns (harmless).
