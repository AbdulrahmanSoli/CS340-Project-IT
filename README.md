# IT Asset Management System

A Flask and PostgreSQL web app for tracking IT assets, assigning them to employees, and logging asset status changes. Built for CS 340, Introduction to Database Systems, Section 361, Semester 252, Dr. Omar Alomeir.

Team Atlas Data: Abdulrahman Solimanie, Abdullah Alrasheed, Mohammed Almuaigel, Abdullah Albekairi, Fares Hassan.

## Live Demo

<https://cs340-project-it.onrender.com>

First request after idle can be slow, around 30 seconds, because Render's free tier sleeps after 15 minutes of inactivity.

### Demo Credentials

| Email | Password | Role |
|---|---|---|
| abdulrahman@atlas.com | `hash_1` | Admin |
| alrasheed@atlas.com | `hash_2` | Admin |
| mohammed@atlas.com | `hash_3` | Employee |
| fares@atlas.com | `hash_5` | Employee |

All ten seeded users follow the pattern `hash_<userID>`.

## Tech Stack

- Backend: Flask
- Database: PostgreSQL, hosted on Supabase
- Frontend: HTML and Jinja2 templates
- Hosting: Render with `gunicorn`
- Database access: raw SQL through small helpers in [db.py](db.py)

## Features

- Login with role-based access for Admin and Employee users.
- Passwords stored as `werkzeug` scrypt hashes.
- CSRF protection for POST forms.
- Admin asset management: add, update, delete, filter, and review analytics.
- Assignment workflow: assign available assets, mark assets returned, and prevent double-assignment with a partial unique index.
- Assignment tables show asset and employee names with IDs.
- Status history is written inside transactions when asset status changes.
- Admin user management: add users, update departments, delete safe users, and review analytics.
- Employee views: `/assets/my` and `/assignments/employee/<user_id>`.
- Success messages after create, update, delete, assign, and return actions.

## Project Structure

```text
.
|-- app.py                       # Flask app setup and blueprint registration
|-- db.py                        # query() and tx() helpers
|-- schema.sql                   # DDL matching the submitted report schema
|-- routes/
|   |-- auth.py                  # /login, /logout, /dashboard
|   |-- assets.py                # /assets CRUD, filters, analytics
|   |-- assignments.py           # /assignments workflow and analytics
|   |-- users.py                 # /users CRUD and analytics
|   `-- history.py               # placeholder, waiting for teammate implementation
|-- templates/                   # Jinja2 templates
|-- migrations/
|   `-- 01_add_fk_indexes.sql    # additive FK indexes for Supabase
|-- scripts/
|   `-- hash_existing_passwords.py
|-- tests/
|   `-- test_routes.py
|-- Procfile                     # Render command
`-- requirements.txt
```

## Running Locally

```bash
git clone https://github.com/AbdulrahmanSoli/CS340-Project-IT.git
cd CS340-Project-IT
pip install -r requirements.txt
```

Create `.env` from the example file.

macOS or Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Fill in `.env`:

```env
DATABASE_URL=postgresql://...
SECRET_KEY=...
FLASK_DEBUG=1
```

Run the app:

```bash
python app.py
```

Then open <http://localhost:5000>.

## First-Time Database Setup

1. Create a PostgreSQL database. Supabase free tier works.
2. Run [schema.sql](schema.sql) in the Supabase SQL editor to create the tables.
3. Load the project seed data if your database is not already seeded.
4. Run the FK index migration:

   ```sql
   -- paste migrations/01_add_fk_indexes.sql into the Supabase SQL editor
   ```

5. Hash seeded placeholder passwords:

   ```bash
   python scripts/hash_existing_passwords.py
   ```

After hashing, seeded users log in with `hash_1`, `hash_2`, and so on as their passwords.

## Testing

Run the local checks:

```bash
python -m compileall app.py db.py routes scripts tests
python -m unittest discover -s tests -v
```

The test suite mocks database calls, so it does not modify Supabase data.

## History Page Status

The History page is owned by a teammate and is intentionally still a placeholder. `history_bp` is not registered in [app.py](app.py) yet. Add it only after `routes/history.py` is delivered.

## Deployment

Render runs the app with:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Render reads `DATABASE_URL` and `SECRET_KEY` from its environment variables panel. Pushing to `main` triggers an auto-deploy.

Use `python app.py` for local development on Windows. `gunicorn` is for Render/Linux deployment.

## Project Notes

The submitted report covers Phase 0 through Phase 5. The schema in [schema.sql](schema.sql) mirrors the report, so avoid schema changes unless the report is updated too. Prefer additive migrations under [migrations/](migrations/) when possible.
