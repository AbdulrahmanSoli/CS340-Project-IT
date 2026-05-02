import psycopg2
from flask import Blueprint, flash, render_template, request, redirect, session
from werkzeug.security import generate_password_hash
from db import query, tx
from routes.guards import admin_redirect, admin_required

users_bp = Blueprint('users', __name__)

VALID_TYPES = ('Admin', 'Employee')

def _render(users=None, **extra):
    return render_template('users.html', users=users or [], **extra)

def _render_with_error(msg):
    rows = query('SELECT * FROM users ORDER BY userType, userID') or []
    return render_template('users.html', users=rows, error=msg)


# Query 1 - show all users
@users_bp.route('/users')
def list_users():
    if admin_required():
        return admin_redirect()
    rows = query('SELECT * FROM users ORDER BY userType, userID') or []
    return _render(users=rows)

# Query 2 - filter by role
@users_bp.route('/users/filter')
def filter_users():
    if admin_required():
        return admin_redirect()
    usertype = request.args.get('type', '')
    if usertype not in VALID_TYPES:
        return _render_with_error('Invalid user type filter.')
    rows = query('SELECT * FROM users WHERE userType = %s ORDER BY userID', (usertype,)) or []
    return _render(users=rows)

# Query 3 - add a new user (admin only)
@users_bp.route('/users/add', methods=['POST'])
def add_user():
    if admin_required():
        return admin_redirect()

    user_id = request.form.get('user_id', '').strip()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    dept = request.form.get('dept', '').strip() or None
    password = request.form.get('password', '').strip()
    usertype = request.form.get('type', '').strip()

    if not user_id.isdigit():
        return _render_with_error('User ID must be a number.')
    if not name or not email or not password:
        return _render_with_error('Name, email, and password are required.')
    if usertype not in VALID_TYPES:
        return _render_with_error('User type must be Admin or Employee.')

    role_table = 'admin' if usertype == 'Admin' else 'employee'
    statements = [
        ('''INSERT INTO users (userID, userFullName, email, department, passwordHash, userType)
            VALUES (%s, %s, %s, %s, %s, %s)''',
         (user_id, name, email, dept, generate_password_hash(password), usertype)),
        (f'INSERT INTO {role_table} (userID) VALUES (%s)', (user_id,)),
    ]
    try:
        tx(statements)
    except psycopg2.errors.UniqueViolation:
        return _render_with_error(f'User {user_id} or email {email} already exists.')
    except Exception as e:
        return _render_with_error(f'Database error: {e}')

    flash(f'User {name} added successfully.')
    return redirect('/users')

# Query 4 - update department (admin only)
@users_bp.route('/users/update', methods=['POST'])
def update_user():
    if admin_required():
        return admin_redirect()

    user_id = request.form.get('user_id', '').strip()
    dept = request.form.get('dept', '').strip() or None

    if not user_id.isdigit():
        return _render_with_error('User ID must be a number.')
    if not query('SELECT 1 FROM users WHERE userID = %s', (user_id,)):
        return _render_with_error(f'User {user_id} does not exist.')

    try:
        query('UPDATE users SET department = %s WHERE userID = %s',
              (dept, user_id))
    except Exception as e:
        return _render_with_error(f'Update failed: {e}')

    flash(f'User {user_id} department updated.')
    return redirect('/users')

# Query 5 - delete a user (admin only, POST)
@users_bp.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if admin_required():
        return admin_redirect()
    if user_id == session.get('user_id'):
        return _render_with_error('You cannot delete your own account.')

    rows = query('SELECT userType FROM users WHERE userID = %s', (user_id,))
    if not rows:
        return _render_with_error(f'User {user_id} does not exist.')
    usertype = rows[0][0]

    has_assignments, has_assigned_by, has_status_changes = query('''
        SELECT EXISTS(SELECT 1 FROM asset_assignment       WHERE userID = %s),
               EXISTS(SELECT 1 FROM asset_assignment       WHERE assignedBy = %s),
               EXISTS(SELECT 1 FROM asset_status_history   WHERE changedBy = %s)
    ''', (user_id, user_id, user_id))[0]
    if has_assignments:
        return _render_with_error(f'User {user_id} has assignment history and cannot be deleted.')
    if has_assigned_by:
        return _render_with_error(f'User {user_id} has assigned assets to others and cannot be deleted.')
    if has_status_changes:
        return _render_with_error(f'User {user_id} has logged status changes and cannot be deleted.')

    role_table = 'admin' if usertype == 'Admin' else 'employee'
    statements = [
        (f'DELETE FROM {role_table} WHERE userID = %s', (user_id,)),
        ('DELETE FROM users WHERE userID = %s', (user_id,)),
    ]
    try:
        tx(statements)
    except psycopg2.errors.ForeignKeyViolation:
        return _render_with_error(f'User {user_id} is referenced elsewhere and cannot be deleted.')
    except Exception as e:
        return _render_with_error(f'Delete failed: {e}')

    flash(f'User {user_id} deleted.')
    return redirect('/users')

# Query 6 - each user + how many assets they have
@users_bp.route('/users/assets-count')
def users_assets_count():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT u.userFullName, COUNT(aa.assignmentID) AS total
        FROM users u
        LEFT JOIN asset_assignment aa ON u.userID = aa.userID
        GROUP BY u.userID, u.userFullName
        ORDER BY total DESC, u.userID
    ''') or []
    return _render(asset_counts=rows)

# Query 7 - employees with no active asset
@users_bp.route('/users/no-active-asset')
def no_active_asset():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT u.* FROM users u
        WHERE u.userType = 'Employee'
          AND NOT EXISTS (
            SELECT 1 FROM asset_assignment aa
            WHERE aa.userID = u.userID AND aa.returnDate IS NULL
          )
        ORDER BY u.userID
    ''') or []
    return _render(users=rows)

# Query 8 - count users per department
@users_bp.route('/users/department-count')
def department_count():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT COALESCE(department, '(none)') AS department, COUNT(*) AS total
        FROM users
        GROUP BY department
        ORDER BY total DESC
    ''') or []
    return _render(dept_counts=rows)

# Query 9 - who has the most assignments ever
@users_bp.route('/users/most-assignments')
def most_assignments():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT u.userID, u.userFullName, COUNT(*) AS total
        FROM asset_assignment aa
        JOIN users u ON aa.userID = u.userID
        GROUP BY u.userID, u.userFullName
        ORDER BY total DESC, u.userID
        LIMIT 1
    ''') or []
    return _render(top_user=rows)

# Query 10 - count admins vs employees
@users_bp.route('/users/type-count')
def type_count():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT userType, COUNT(*) AS total
        FROM users
        GROUP BY userType
        ORDER BY total DESC
    ''') or []
    return _render(type_counts=rows)
