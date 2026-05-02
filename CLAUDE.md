# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IT Asset Management System - a Flask + PostgreSQL (Supabase) web app for tracking assets, assignments, and users across Admin/Employee roles. CS340 (Intro to Database Systems, Section 361, Semester 252, instructor Dr. Omar Alomeir). Team "Atlas Data": Abdulrahman Solimanie (lead), Abdullah Alrasheed, Mohammed Almuaigel, Abdullah Albekairi, Fares Hassan. Phase 5 (Full Stack App) is the deliverable - the report (Phases 0–5) is finalized and the GitHub repo is what gets graded.

**Important:** the DDL in [schema.sql](schema.sql) is reproduced verbatim in the submitted report. Schema changes mean editing the report too - prefer additive migrations under [migrations/](migrations/) (see deployment section).

## Running the App

```bash
python app.py
```

Runs on `http://localhost:5000`. Debug mode is gated by `FLASK_DEBUG=1`. Requires a `.env` file with:
```
DATABASE_URL=postgresql://...
SECRET_KEY=...
FLASK_DEBUG=1   # optional, dev only
```
See [.env.example](.env.example).

## Installing Dependencies

```bash
pip install -r requirements.txt
```

## Architecture

### Entry Point

[app.py](app.py) - Creates the Flask app, loads `SECRET_KEY` from env, and registers four blueprints: `auth_bp`, `assignments_bp`, `assets_bp`, `users_bp`. `history_bp` is commented out pending implementation.

### Database Layer

[db.py](db.py) - utilities used everywhere:
- `get_connection()` - opens a fresh psycopg2 connection from `DATABASE_URL`. Use from scripts/migrations.
- `query(sql, params)` - executes a single statement, auto-commits, returns rows. **Raises on error** (no `raise_errors` flag).
- `tx(list_of_(sql, params))` - executes multiple statements atomically; rolls back on any error.
- Inside a Flask request, both helpers reuse a single connection stored on `flask.g`, closed by `app.teardown_appcontext`. Outside a request (e.g., the migration script) each call opens and closes its own connection.

All routes use raw SQL via these helpers - no ORM.

### Routes (Blueprints) and Module Ownership

| File | Prefix | Owner | Responsibility |
|------|--------|-------|----------------|
| [routes/auth.py](routes/auth.py) | `/` | Solimanie | Login, logout, dashboard |
| [routes/assets.py](routes/assets.py) | `/assets` | Hassan | Asset CRUD, filters (`status`/`category`/`serial`), employee `/assets/my`, analytics |
| [routes/assignments.py](routes/assignments.py) | `/assignments` | Almuaigel | Assignment workflow + analytics |
| [routes/users.py](routes/users.py) | `/users` | Alrasheed | User CRUD + analytics |
| [routes/history.py](routes/history.py) | `/history` | Albekairi | **Owned by teammate - placeholder.** Don't implement here; `history_bp` is commented out in [app.py](app.py) until the file lands. |

### Auth Pattern

- `login_required()` - checks `session['user_id']`
- `admin_required()` - checks `session['user_type'] == 'Admin'`
- Session stores: `user_id`, `user_type`, `user_name`

### Password Storage

Passwords are stored as `werkzeug.security` hashes (scrypt-prefixed) in `users.passwordHash`:
- Insert: `generate_password_hash(password)` ([routes/users.py](routes/users.py))
- Login: `check_password_hash(row[passwordHash], password)` ([routes/auth.py](routes/auth.py))

Never compare raw input against `passwordHash`. The seeded users from the report DDL had placeholder strings like `hash_1`, `hash_2`; [scripts/hash_existing_passwords.py](scripts/hash_existing_passwords.py) one-shot-hashes any rows that don't already start with a known werkzeug prefix (idempotent). After running it once, the seeded users log in with the literal strings (`hash_1`, `hash_2`, …) as their passwords.

### ID Generation

IDs are generated manually with `COALESCE(MAX(id), 0) + 1` - not `SERIAL`/auto-increment. Match this pattern when adding new inserts.

### Multi-step Operations

Any operation that touches multiple tables (e.g., assign asset → update `asset` status → insert `asset_status_history`) uses `tx()` for atomicity.

### Error Rendering

Routes use a `_render_with_error(error_msg, template, data...)` pattern - re-fetches data and re-renders the template with an error message rather than redirecting.

## Database Schema

Tables (inferred from queries):

- **users**: `userID`, `userFullName`, `email`, `department`, `passwordHash`, `userType` (`Admin`/`Employee`)
- **admin**: `userID` (FK → users)
- **employee**: `userID` (FK → users)
- **asset**: `assetID`, `assetName`, `category`, `status` (`Available`/`Assigned`/`Damaged`), `serialNum`, `purchaseDate`, `condition`, `notes`
- **asset_assignment**: `assignmentID`, `assignedDate`, `returnDate`, `assetID` (FK), `userID` (FK), `assignedBy` (FK → users)
- **asset_status_history**: `historyID`, `previousStatus`, `newStatus`, `changeDate`, `assetID` (FK), `changedBy` (FK → users)

Valid asset statuses: `Available`, `Assigned`, `Damaged`  
Valid user types: `Admin`, `Employee`

## Templates

Jinja2 templates in [templates/](templates/) extend [templates/base.html](templates/base.html). Nav links: Dashboard, Assets, My Assets (Employee only), Assignments, History, Users, Logout. Templates currently use positional row indexing (`{{ a[0] }}`, `{{ u[1] }}` …) - psycopg2 default cursor returns tuples. If switching to `RealDictCursor` later, every template needs updating too.

[templates/history.html](templates/history.html) is an empty placeholder until Albekairi delivers `routes/history.py`.

## Migrations and Scripts

- [migrations/](migrations/) - additive SQL applied in the Supabase SQL editor (e.g., [01_add_fk_indexes.sql](migrations/01_add_fk_indexes.sql)). Keeps [schema.sql](schema.sql) aligned with the submitted report.
- [scripts/](scripts/) - one-off Python utilities. Run from project root: `python scripts/<name>.py`. They use `get_connection()` directly (no Flask context).

## Deployment (Render)

Production runs on Render's free tier via [Procfile](Procfile) → `gunicorn app:app --bind 0.0.0.0:$PORT`. Render reads the `DATABASE_URL` and `SECRET_KEY` from its env-vars panel, not from `.env`. Free tier sleeps after 15 min idle (~30s cold start). Pushing to `main` triggers an auto-redeploy.

`gunicorn` doesn't run on Windows - local dev still uses `python app.py`. Don't try to start gunicorn from a Windows shell.
