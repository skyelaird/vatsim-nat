-- VATSIM NAT Traffic Analyzer Database Schema v2

CREATE TABLE IF NOT EXISTS nat_crossings (
    crossing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Flight identification
    callsign TEXT NOT NULL,
    aircraft_type TEXT,  -- Full ICAO (B789/H-SDE1E2E3FGHIJ2J3J4J5M1RWXY/LB1D1)
    departure TEXT,      -- ICAO code
    destination TEXT,    -- ICAO code
    
    -- Filed flight plan data
    cruise_tas TEXT,     -- Filed TAS (e.g., "481")
    filed_altitude TEXT, -- Filed altitude (e.g., "36000")
    deptime TEXT,        -- Departure time (e.g., "0930")
    enroute_time TEXT,   -- Filed enroute time (e.g., "1821" = 18h21m)
    
    -- Route information
    full_route TEXT,     -- Complete filed route
    oceanic_route TEXT,  -- Just NAT portion
    entry_fix TEXT,      -- First oceanic waypoint
    exit_fix TEXT,       -- Last oceanic waypoint
    ots_track TEXT,      -- 'A', 'B', 'C', etc or NULL for random
    eet_string TEXT,     -- EET/... from remarks (future FIR analysis)
    
    -- Equipage from remarks
    selcal TEXT,
    pbn_capability TEXT,
    com_capability TEXT,
    sur_capability TEXT,
    operator TEXT,
    registration TEXT,
    
    -- Entry zone (55W-45W western boundary area)
    entry_time TEXT,
    entry_lat REAL,
    entry_lon REAL,
    entry_fl INTEGER,
    entry_gs INTEGER,
    
    -- Midpoint zone (35W-25W mid-Atlantic area)
    mid_time TEXT,
    mid_lat REAL,
    mid_lon REAL,
    mid_fl INTEGER,
    mid_gs INTEGER,
    
    -- Exit zone (20W-10W eastern boundary area)
    exit_time TEXT,
    exit_lat REAL,
    exit_lon REAL,
    exit_fl INTEGER,
    exit_gs INTEGER,
    
    -- Derived data
    crossing_duration INTEGER,  -- minutes
    inferred_fir TEXT,          -- CZQX, EGGX, BIRD, KZNY based on route/position
    crossed_mid INTEGER DEFAULT 0,  -- Boolean flag for midpoint zone
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entry_time ON nat_crossings(entry_time);
CREATE INDEX IF NOT EXISTS idx_ots_track ON nat_crossings(ots_track);
CREATE INDEX IF NOT EXISTS idx_aircraft_type ON nat_crossings(aircraft_type);
CREATE INDEX IF NOT EXISTS idx_departure ON nat_crossings(departure);
CREATE INDEX IF NOT EXISTS idx_destination ON nat_crossings(destination);
CREATE INDEX IF NOT EXISTS idx_exit_time ON nat_crossings(exit_time);
