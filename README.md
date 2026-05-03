# IT Asset Management System

A Flask and PostgreSQL web app for tracking IT assets, assigning them to employees, and logging asset status changes. Built for CS 340, Introduction to Database Systems, Section 361, Semester 252, Dr. Omar Alomeir.

Team Atlas Data: Abdulrahman Solimanie, Abdullah Alrasheed, Mohammed Almuaigel, Abdullah Albekairi, Fares Hassan.

## Contributors

- [@AbdulrahmanSoli](https://github.com/AbdulrahmanSoli) — Abdulrahman Solimanie (Lead): Flask app setup, blueprint registration, `.env` loading, database helpers, CSRF protection, login/session handling, dashboard integration, tests, and Render deployment.
- [@wolf69-9](https://github.com/wolf69-9) — Abdullah Alrasheed: User management page (CRUD, role inserts into `admin`/`employee`, and user analytics).
- [@asus3020](https://github.com/asus3020) — Mohammed Almuaigel: Assignment workflow (assign/return with transactional status-history writes) and assignment analytics.
- [@AAlbekairi](https://github.com/AAlbekairi) — Abdullah Albekairi: Asset status history page (filters, manual log form, and history analytics).
- [@Fares1Albadry](https://github.com/Fares1Albadry) — Fares Hassan: Asset management page (CRUD, multi-filter search by status/category/serial, and asset analytics).

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
- Status history page: view history, filter by status/date, log new history rows, and run status-history analytics.
- Admin user management: add users, update departments, delete safe users, and review analytics.
- Employee views: `/assets/my` and `/assignments/employee/<user_id>`.
- Success messages after create, update, delete, assign, and return actions.

## Team Query Ownership

`%s` marks values passed safely through parameterized `psycopg2` queries. Some write actions also run validation queries before the final insert, update, or delete.

### Abdullah Albekairi: Asset Status History Page

Basic queries:

1. Show all status history.

   ```sql
   SELECT *
   FROM asset_status_history
   ORDER BY changeDate DESC, historyID DESC;
   ```

2. Show history for one asset.

   ```sql
   SELECT *
   FROM asset_status_history
   WHERE assetID = %s
   ORDER BY changeDate DESC, historyID DESC;
   ```

3. Log a new status change.

   ```sql
   INSERT INTO asset_status_history
       (historyID, previousStatus, newStatus, changeDate, assetID, changedBy)
   VALUES (%s, %s, %s, CURRENT_DATE, %s, %s);
   ```

4. Filter history by new status.

   ```sql
   SELECT *
   FROM asset_status_history
   WHERE newStatus = %s
   ORDER BY changeDate DESC, historyID DESC;
   ```

5. Filter history by date range.

   ```sql
   SELECT *
   FROM asset_status_history
   WHERE changeDate BETWEEN %s AND %s
   ORDER BY changeDate DESC, historyID DESC;
   ```

Advanced queries:

1. Show asset names with history rows.

   ```sql
   SELECT a.assetName, h.previousStatus, h.newStatus, h.changeDate
   FROM asset_status_history h
   JOIN asset a ON h.assetID = a.assetID
   ORDER BY h.changeDate DESC, h.historyID DESC;
   ```

2. Count status changes per asset.

   ```sql
   SELECT assetID, COUNT(*) AS total
   FROM asset_status_history
   GROUP BY assetID
   ORDER BY total DESC, assetID;
   ```

3. Show assets that were ever damaged.

   ```sql
   SELECT DISTINCT assetID
   FROM asset_status_history
   WHERE newStatus = 'Damaged'
   ORDER BY assetID;
   ```

4. Show the latest recorded status for each asset.

   ```sql
   SELECT DISTINCT ON (assetID) assetID, newStatus, changeDate
   FROM asset_status_history
   ORDER BY assetID, changeDate DESC, historyID DESC;
   ```

5. Show assets with three or more status changes.

   ```sql
   SELECT assetID, COUNT(*) AS total
   FROM asset_status_history
   GROUP BY assetID
   HAVING COUNT(*) >= 3
   ORDER BY total DESC, assetID;
   ```

### Abdullah Alrasheed: User Management Page

Basic queries:

1. Show all users.

   ```sql
   SELECT *
   FROM users
   ORDER BY userType, userFullName, userID;
   ```

2. Filter users by role.

   ```sql
   SELECT *
   FROM users
   WHERE userType = %s
   ORDER BY userFullName, userID;
   ```

3. Add a new user and role record.

   ```sql
   INSERT INTO users (userID, userFullName, email, department, passwordHash, userType)
   VALUES (%s, %s, %s, %s, %s, %s);

   INSERT INTO admin (userID) VALUES (%s);
   ```

   Employee users use the same second insert with `employee` instead of `admin`.

4. Update a user's department.

   ```sql
   UPDATE users
   SET department = %s
   WHERE userID = %s;
   ```

5. Delete a user after checking references.

   ```sql
   DELETE FROM admin
   WHERE userID = %s;

   DELETE FROM users
   WHERE userID = %s;
   ```

   Employee users use `employee` instead of `admin`. The route first checks assignment and history references.

Advanced queries:

1. Show each user with the number of assigned assets.

   ```sql
   SELECT u.userFullName, COUNT(aa.assignmentID) AS total
   FROM users u
   LEFT JOIN asset_assignment aa ON u.userID = aa.userID
   GROUP BY u.userID, u.userFullName
   ORDER BY total DESC, u.userFullName;
   ```

2. Show employees with no active asset.

   ```sql
   SELECT *
   FROM users
   WHERE userType = 'Employee'
     AND userID NOT IN (
       SELECT userID FROM asset_assignment WHERE returnDate IS NULL
     )
   ORDER BY userID;
   ```

3. Count users per department.

   ```sql
   SELECT COALESCE(department, '(none)') AS department, COUNT(*) AS total
   FROM users
   GROUP BY department
   ORDER BY total DESC;
   ```

4. Show the user with the most assignments ever.

   ```sql
   SELECT u.userID, u.userFullName, COUNT(*) AS total
   FROM asset_assignment aa
   JOIN users u ON aa.userID = u.userID
   GROUP BY u.userID, u.userFullName
   ORDER BY total DESC
   LIMIT 1;
   ```

5. Count admins and employees.

   ```sql
   SELECT userType, COUNT(*) AS total
   FROM users
   GROUP BY userType
   ORDER BY total DESC;
   ```

### Fares Hassan: Asset Management Page

Basic queries:

1. Show all assets.

   ```sql
   SELECT *
   FROM asset
   ORDER BY status, assetName, assetID;
   ```

2. Filter assets by status, category, and serial number.

   ```sql
   SELECT *
   FROM asset
   WHERE status = %s
     AND category ILIKE %s
     AND serialNum ILIKE %s
   ORDER BY assetID;
   ```

   The route builds the `WHERE` clause only for filters the user provides.

3. Add a new asset.

   ```sql
   INSERT INTO asset (assetID, assetName, category, status, serialNum)
   VALUES (%s, %s, %s, %s, %s);
   ```

4. Update asset status and record the history row.

   ```sql
   UPDATE asset
   SET status = %s
   WHERE assetID = %s;

   INSERT INTO asset_status_history
       (historyID, previousStatus, newStatus, changeDate, assetID, changedBy)
   VALUES (%s, %s, %s, CURRENT_DATE, %s, %s);
   ```

5. Delete an asset after checking it has no active assignment.

   ```sql
   DELETE FROM asset
   WHERE assetID = %s;
   ```

Advanced queries:

1. Show each active asset with its current holder.

   ```sql
   SELECT a.assetName, u.userFullName
   FROM asset a
   JOIN asset_assignment aa ON a.assetID = aa.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NULL
   ORDER BY a.assetName;
   ```

2. Show assets that have never been assigned.

   ```sql
   SELECT *
   FROM asset
   WHERE assetID NOT IN (SELECT assetID FROM asset_assignment)
   ORDER BY assetID;
   ```

3. Count assets by category.

   ```sql
   SELECT category, COUNT(*) AS total
   FROM asset
   GROUP BY category
   ORDER BY total DESC;
   ```

4. Show assets assigned more than once.

   ```sql
   SELECT assetID, COUNT(*) AS total
   FROM asset_assignment
   GROUP BY assetID
   HAVING COUNT(*) > 1
   ORDER BY total DESC;
   ```

5. Show assets purchased this year.

   ```sql
   SELECT *
   FROM asset
   WHERE EXTRACT(YEAR FROM purchaseDate) = EXTRACT(YEAR FROM CURRENT_DATE)
   ORDER BY assetID;
   ```

### Mohammed Almuaigel: Asset Assignment Page

Basic queries:

1. Show all active assignments.

   ```sql
   SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
          aa.assetID, aa.userID, aa.assignedBy,
          a.assetName, u.userFullName
   FROM asset_assignment aa
   JOIN asset a ON aa.assetID = a.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NULL
   ORDER BY aa.assignedDate DESC, aa.assignmentID DESC;
   ```

2. Show returned assignments.

   ```sql
   SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
          aa.assetID, aa.userID, aa.assignedBy,
          a.assetName, u.userFullName
   FROM asset_assignment aa
   JOIN asset a ON aa.assetID = a.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NOT NULL
   ORDER BY aa.returnDate DESC, aa.assignmentID DESC;
   ```

3. Assign an asset and update its status history.

   ```sql
   INSERT INTO asset_assignment (assignmentID, assignedDate, assetID, userID, assignedBy)
   VALUES (%s, CURRENT_DATE, %s, %s, %s);

   UPDATE asset
   SET status = %s
   WHERE assetID = %s;

   INSERT INTO asset_status_history
       (historyID, previousStatus, newStatus, changeDate, assetID, changedBy)
   VALUES (%s, %s, %s, CURRENT_DATE, %s, %s);
   ```

4. Mark an assignment returned and update asset status.

   ```sql
   UPDATE asset_assignment
   SET returnDate = CURRENT_DATE
   WHERE assignmentID = %s;

   UPDATE asset
   SET status = %s
   WHERE assetID = %s;
   ```

5. Show an employee's own assignments.

   ```sql
   SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
          aa.assetID, aa.userID, aa.assignedBy,
          a.assetName, u.userFullName
   FROM asset_assignment aa
   JOIN asset a ON aa.assetID = a.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.userID = %s
   ORDER BY aa.assignedDate DESC, aa.assignmentID DESC;
   ```

Advanced queries:

1. Show active assignments with asset and employee names.

   ```sql
   SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
          aa.assetID, aa.userID, aa.assignedBy,
          a.assetName, u.userFullName
   FROM asset_assignment aa
   JOIN asset a ON aa.assetID = a.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NULL
   ORDER BY aa.assignedDate DESC, aa.assignmentID DESC;
   ```

2. Show the average number of days assets were kept.

   ```sql
   SELECT ROUND(AVG(returnDate - assignedDate), 1)
   FROM asset_assignment
   WHERE returnDate IS NOT NULL;
   ```

3. Show users with the most assignments.

   ```sql
   SELECT userID, COUNT(*) AS total
   FROM asset_assignment
   GROUP BY userID
   ORDER BY total DESC;
   ```

4. Show assignments returned within seven days.

   ```sql
   SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
          aa.assetID, aa.userID, aa.assignedBy,
          a.assetName, u.userFullName
   FROM asset_assignment aa
   JOIN asset a ON aa.assetID = a.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NOT NULL
     AND (aa.returnDate - aa.assignedDate) <= 7
   ORDER BY aa.returnDate DESC, aa.assignmentID DESC;
   ```

5. Show assets assigned more than once.

   ```sql
   SELECT assetID, COUNT(*) AS total
   FROM asset_assignment
   GROUP BY assetID
   HAVING COUNT(*) > 1
   ORDER BY total DESC;
   ```

### Abdulrahman Solimanie: Leader, Setup, Login, Dashboard, and Integration

This work connects the whole application instead of owning one separate ten-query CRUD page. It includes Flask app setup, blueprint registration, `.env` loading, database helpers, CSRF protection, login/session handling, dashboard integration, tests, deployment setup, and final route compatibility.

Basic queries:

1. Login: find user by email and password.

   ```sql
   SELECT *
   FROM users
   WHERE email = %s AND passwordHash = %s;
   ```

   The implemented app improves this by selecting the password hash by email, then checking it with `check_password_hash()` in Python.

2. Count assets by status.

   ```sql
   SELECT status, COUNT(*) AS total
   FROM asset
   GROUP BY status;
   ```

3. Show total number of assets.

   ```sql
   SELECT COUNT(*) AS total
   FROM asset;
   ```

4. Show most recently assigned assets.

   ```sql
   SELECT *
   FROM asset_assignment
   ORDER BY assignedDate DESC
   LIMIT 5;
   ```

5. Show all damaged assets.

   ```sql
   SELECT *
   FROM asset
   WHERE status = 'Damaged';
   ```

Advanced queries:

1. Dashboard summary: assigned, available, and damaged assets.

   ```sql
   SELECT
       SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) AS available,
       SUM(CASE WHEN status='Assigned'  THEN 1 ELSE 0 END) AS assigned,
       SUM(CASE WHEN status='Damaged'   THEN 1 ELSE 0 END) AS damaged
   FROM asset;
   ```

2. Show recent assignments with asset and employee name.

   ```sql
   SELECT a.assetName, u.userFullName, aa.assignedDate
   FROM asset_assignment aa
   JOIN asset a ON aa.assetID = a.assetID
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NULL
   ORDER BY aa.assignedDate DESC
   LIMIT 5;
   ```

3. Show which department has the most active assignments.

   ```sql
   SELECT u.department, COUNT(*) AS total
   FROM asset_assignment aa
   JOIN users u ON aa.userID = u.userID
   WHERE aa.returnDate IS NULL
   GROUP BY u.department
   ORDER BY total DESC;
   ```

4. Show employees who currently have no asset.

   ```sql
   SELECT *
   FROM users
   WHERE userType = 'Employee'
     AND userID NOT IN (
       SELECT userID
       FROM asset_assignment
       WHERE returnDate IS NULL
     );
   ```

5. Full overview of all active assignments with details.

   ```sql
   SELECT u.userFullName, u.department, a.assetName, a.category, aa.assignedDate
   FROM asset_assignment aa
   JOIN users u ON aa.userID = u.userID
   JOIN asset a ON aa.assetID = a.assetID
   WHERE aa.returnDate IS NULL
   ORDER BY aa.assignedDate DESC;
   ```

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
|   `-- history.py               # /history status-history page
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

## Deployment

Render runs the app with:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Render reads `DATABASE_URL` and `SECRET_KEY` from its environment variables panel. Pushing to `main` triggers an auto-deploy.

Use `python app.py` for local development on Windows. `gunicorn` is for Render/Linux deployment.

## Project Notes

The submitted report covers Phase 0 through Phase 5. The schema in [schema.sql](schema.sql) mirrors the report, so avoid schema changes unless the report is updated too. Prefer additive migrations under [migrations/](migrations/) when possible.
