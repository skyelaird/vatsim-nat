-- NAT OTS Track Messages
-- Add this table to existing nat_traffic.db

CREATE TABLE IF NOT EXISTS nat_ots_tracks (
    track_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Track identification
    effective_date DATE NOT NULL,
    tmi TEXT NOT NULL,
    track_letter TEXT NOT NULL,
    
    -- Track waypoints (latitude in decimal degrees, longitude implicit in field name)
    entry_point TEXT,       -- "SUPRY", "RAFIN", "DOVEY"
    lat_60w REAL,          -- 42.0, 41.0 (or NULL if track doesn't start at 60W)
    lat_50w REAL,          -- 46.0, 45.0, 46.5
    lat_40w REAL,          -- 48.0, 47.0, 48.5
    lat_30w REAL,          -- 49.0, 48.0, 49.5
    lat_20w REAL,          -- 50.0, 49.0, 50.5
    lat_15w REAL,          -- 48.0, 47.0 (or NULL if track exits before 15W)
    lat_10w REAL,          -- NULL for most tracks
    boundary_point TEXT,   -- "SOMAX", "BEDRA", "OMOKO" (Shannon west boundary)
    exit_point TEXT,       -- "ATSUR", "NASBA", "GUNSO"
    
    -- Optional metadata
    nar_routes TEXT,       -- "N119B N97B" or NULL
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(effective_date, track_letter)
);

CREATE INDEX IF NOT EXISTS idx_track_date ON nat_ots_tracks(effective_date);
CREATE INDEX IF NOT EXISTS idx_track_letter ON nat_ots_tracks(track_letter);
