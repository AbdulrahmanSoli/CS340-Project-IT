-- Indexes that match the ORDER BY clauses used by the hot pages.
-- Postgres can read these indexes in order and skip the sort step entirely,
-- which matters once the tables grow past a few hundred rows.
--
-- Apply once in Supabase SQL editor or psql.

-- History page: every default + filter view sorts by (changeDate DESC, historyID DESC).
-- Used by: /history, /history/asset/<id>, /history/filter, /history/dates, /history/with-assets
CREATE INDEX IF NOT EXISTS idx_ash_changedate_desc
  ON asset_status_history (changeDate DESC, historyID DESC);

-- Active assignments listing + dashboard recent. Partial index keeps it small
-- because we only ever read this ordering for rows where returnDate IS NULL.
-- Used by: /dashboard (admin recent), /assignments, /assignments/employee/<id>
CREATE INDEX IF NOT EXISTS idx_aa_active_recent
  ON asset_assignment (assignedDate DESC, assignmentID DESC)
  WHERE returnDate IS NULL;

-- Returned-assignments tab + quick-returns sort by returnDate DESC.
-- Used by: /assignments/returned, /assignments/quick-returns
CREATE INDEX IF NOT EXISTS idx_aa_returned_recent
  ON asset_assignment (returnDate DESC, assignmentID DESC)
  WHERE returnDate IS NOT NULL;

-- Default asset listing sorts by (status, assetName, assetID).
-- Used by: /assets, error re-renders
CREATE INDEX IF NOT EXISTS idx_asset_status_name
  ON asset (status, assetName, assetID);

-- Default users listing sorts by (userType, userFullName, userID).
-- Used by: /users, error re-renders
CREATE INDEX IF NOT EXISTS idx_users_type_name
  ON users (userType, userFullName, userID);
