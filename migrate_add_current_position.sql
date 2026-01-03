-- Migration: Add current position tracking for active crossings
-- Run this once to add columns to existing database

ALTER TABLE nat_crossings ADD COLUMN last_update_time TEXT;
ALTER TABLE nat_crossings ADD COLUMN current_lat REAL;
ALTER TABLE nat_crossings ADD COLUMN current_lon REAL;
ALTER TABLE nat_crossings ADD COLUMN current_fl INTEGER;
ALTER TABLE nat_crossings ADD COLUMN current_gs INTEGER;

CREATE INDEX IF NOT EXISTS idx_last_update ON nat_crossings(last_update_time);
