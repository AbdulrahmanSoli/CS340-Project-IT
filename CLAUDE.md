# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IT Asset Management System — a Flask + PostgreSQL (Supabase) web app for tracking assets, assignments, and users across Admin/Employee roles. Built for CS340 (Oregon State DB course).

## Running the App

```bash
python app.py
```

Runs in debug mode on `http://localhost:5000`. Requires a `.env` file with:
```
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

## Installing Dependencies

```bash
pip install -r requirements.txt
```

## Architecture

### Entry Point

[app.py](app.py) — Creates the Flask app, loads `SECRET_KEY` from env, and registers four blueprints: `auth_bp`, `assignments_bp`, `assets_bp`, `users_bp`. `history_bp` is commented out pending implementation.

### Database Layer

[db.py](db.py) — Two core utilities used everywhere:
- `get_connection()` — opens a psycopg2 connection from `DATABASE_URL`
- `query(sql, params)` — executes a single statement, auto-commits, returns rows
- `tx(list_of_(sql, params))` — executes multiple statements atomically; rolls back on any error

All routes use raw SQL via these helpers — no ORM.

### Routes (Blueprints)

| File | Prefix | Responsibility |
|------|--------|----------------|
| [routes/auth.py](routes/auth.py) | `/` | Login, logout, dashboard |
| [routes/assets.py](routes/assets.py) | `/assets` | Asset CRUD + analytics |
| [routes/assignments.py](routes/assignments.py) | `/assignments` | Assignment workflow + analytics |
| [routes/users.py](routes/users.py) | `/users` | User CRUD + analytics |
| [routes/history.py](routes/history.py) | `/history` | Placeholder (not implemented) |

### Auth Pattern

- `login_required()` — checks `session['user_id']`
- `admin_required()` — checks `session['user_type'] == 'Admin'`
- Session stores: `user_id`, `user_type`, `user_name`

### ID Generation

IDs are generated manually with `COALESCE(MAX(id), 0) + 1` — not `SERIAL`/auto-increment. Match this pattern when adding new inserts.

### Multi-step Operations

Any operation that touches multiple tables (e.g., assign asset → update `asset` status → insert `asset_status_history`) uses `tx()` for atomicity.

### Error Rendering

Routes use a `_render_with_error(error_msg, template, data...)` pattern — re-fetches data and re-renders the template with an error message rather than redirecting.

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

Jinja2 templates in [templates/](templates/) extend [templates/base.html](templates/base.html). Nav links: Dashboard, Assets, Assignments, History, Users, Logout. [templates/history.html](templates/history.html) is an empty placeholder.
