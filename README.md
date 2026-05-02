# IT Asset Management System

A web app for tracking IT assets (laptops, monitors, peripherals), assigning them to employees, and logging status history. Built for **CS 340 — Introduction to Database Systems** (Section 361, Semester 252, Dr. Omar Alomeir).

**Team Atlas Data:** Abdulrahman Solimanie · Abdullah Alrasheed · Mohammed Almuaigel · Abdullah Albekairi · Fares Hassan

## Live demo

<https://cs340-project-it.onrender.com>

> First request after idle is slow (~30s) — Render's free tier sleeps after 15 minutes of inactivity.

### Demo credentials

| Email | Password | Role |
|---|---|---|
| abdulrahman@atlas.com | `hash_1` | Admin |
| alrasheed@atlas.com | `hash_2` | Admin |
| mohammed@atlas.com | `hash_3` | Employee |
| fares@atlas.com | `hash_5` | Employee |

(All ten seeded users follow the pattern `hash_<userID>`.)

## Tech stack

- **Backend:** Flask (Python)
- **Database:** PostgreSQL (Supabase)
- **Frontend:** HTML + Jinja2 templates
- **Hosting:** Render (free tier) with `gunicorn`
- **No ORM** — every route uses raw SQL through small helpers in [db.py](db.py)

## Features

- Login with role-based access (Admin / Employee), passwords stored as `werkzeug` scrypt hashes
- **Assets:** add, update, delete, filter by status / category / serial number
- **Assignments:** assign assets to employees, mark returned, prevent double-assignment via partial unique index
- **Status history:** every status change logged to `asset_status_history` inside a transaction
- **Users:** add, update department, delete (with referential-integrity safeguards)
- **Analytics queries:** assets-per-user, top user, assets by category, frequently assigned, etc.
- **Employee view:** `/assets/my` shows only the logged-in employee's currently assigned assets

## Project structure

```
.
├── app.py                       # Flask app factory + blueprint registration
├── db.py                        # query() / tx() helpers, per-request connection on flask.g
├── schema.sql                   # DDL (mirrors the report's Phase 3-4 schema)
├── routes/
│   ├── auth.py                  # /login, /logout, /dashboard
│   ├── assets.py                # /assets CRUD + filters + analytics
│   ├── assignments.py           # /assignments workflow
│   ├── users.py                 # /users CRUD + analytics
│   └── history.py               # /history (placeholder)
├── templates/                   # Jinja2 templates
├── migrations/
│   └── 01_add_fk_indexes.sql    # Additive migrations applied in Supabase
├── scripts/
│   └── hash_existing_passwords.py
├── Procfile                     # Render: gunicorn app:app --bind 0.0.0.0:$PORT
└── requirements.txt
```

## Running locally

```bash
git clone https://github.com/AbdulrahmanSoli/CS340-Project-IT.git
cd CS340-Project-IT
pip install -r requirements.txt
cp .env.example .env
# Fill in DATABASE_URL and SECRET_KEY in .env
python app.py
```

Then open <http://localhost:5000>.

### First-time database setup

1. Create a Postgres database (Supabase free tier works).
2. In the Supabase SQL editor, run the contents of [schema.sql](schema.sql) to create tables and seed sample data.
3. Run the FK-index migration:
   ```bash
   # paste migrations/01_add_fk_indexes.sql into the Supabase SQL editor
   ```
4. Hash the seeded placeholder passwords:
   ```bash
   python scripts/hash_existing_passwords.py
   ```
   After this, the seeded users log in with `hash_1`, `hash_2`, … as their passwords.

## Project phases

The accompanying report covers Phase 0 (planning) through Phase 5 (full-stack app — this repo). Schema design is documented in Phase 3 & 4 of the report; the SQL is reproduced verbatim in [schema.sql](schema.sql).
