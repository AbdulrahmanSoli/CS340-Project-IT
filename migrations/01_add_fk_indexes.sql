-- Foreign-key indexes added in Phase 5.
-- The base schema (schema.sql / Phase 3-4 of the report) already declares the
-- foreign keys; Postgres does not auto-index FKs, so joins on these columns
-- (dashboard "recent assignments", users-with-most-assignments, history page)
-- were doing sequential scans. These indexes turn them into index scans.
--
-- Apply once in Supabase SQL editor or psql.

CREATE INDEX IF NOT EXISTS idx_aa_asset      ON asset_assignment(assetID);
CREATE INDEX IF NOT EXISTS idx_aa_user       ON asset_assignment(userID);
CREATE INDEX IF NOT EXISTS idx_aa_by         ON asset_assignment(assignedBy);
CREATE INDEX IF NOT EXISTS idx_ash_asset     ON asset_status_history(assetID);
CREATE INDEX IF NOT EXISTS idx_ash_by        ON asset_status_history(changedBy);
