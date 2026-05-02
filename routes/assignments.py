import psycopg2
from flask import Blueprint, flash, render_template, request, redirect, session
from db import query, tx

assignments_bp = Blueprint('assignments', __name__)

ASSIGNMENT_SELECT = '''
    SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
           aa.assetID, aa.userID, aa.assignedBy,
           a.assetName, u.userFullName
    FROM asset_assignment aa
    JOIN asset a ON aa.assetID = a.assetID
    JOIN users u ON aa.userID = u.userID
'''

def admin_required():
    return 'user_id' not in session or session.get('user_type') != 'Admin'

def _form_options():
    """Available assets + all employees, for the assign-asset dropdowns.
    Only fetched when an admin is viewing the page."""
    if session.get('user_type') != 'Admin':
        return {}
    available_assets = query('''
        SELECT assetID, assetName, category
        FROM asset
        WHERE status = 'Available'
        ORDER BY assetID
    ''') or []
    employees = query('''
        SELECT u.userID, u.userFullName, u.department
        FROM employee e
        JOIN users u ON e.userID = u.userID
        ORDER BY u.userID
    ''') or []
    return {'available_assets': available_assets, 'employees': employees}

def _assignment_rows(where_sql='', params=(), order_sql='aa.assignedDate DESC, aa.assignmentID DESC'):
    sql = ASSIGNMENT_SELECT
    if where_sql:
        sql += f'\nWHERE {where_sql}'
    sql += f'\nORDER BY {order_sql}'
    return query(sql, params) or []

def _render_with_error(msg):
    rows = _assignment_rows('aa.returnDate IS NULL')
    return render_template('assignments.html', assignments=rows, error=msg, **_form_options())

# Query 1 - show all active assignments
@assignments_bp.route('/assignments')
def list_assignments():
    if admin_required():
        return redirect('/login')
    rows = _assignment_rows('aa.returnDate IS NULL')
    return render_template('assignments.html', assignments=rows, **_form_options())

# Query 2 - show returned assignments
@assignments_bp.route('/assignments/returned')
def returned_assignments():
    if admin_required():
        return redirect('/login')
    rows = _assignment_rows('aa.returnDate IS NOT NULL', order_sql='aa.returnDate DESC, aa.assignmentID DESC')
    return render_template('assignments.html', assignments=rows, **_form_options())

# Query 3 - assign an asset (admin only)
@assignments_bp.route('/assignments/add', methods=['POST'])
def assign_asset():
    if admin_required():
        return redirect('/login')

    asset_id = request.form.get('asset_id', '').strip()
    user_id = request.form.get('user_id', '').strip()
    if not asset_id.isdigit() or not user_id.isdigit():
        return _render_with_error('Asset ID and Employee ID must be numbers.')

    asset_rows = query('SELECT status FROM asset WHERE assetID = %s', (asset_id,))
    if not asset_rows:
        return _render_with_error(f'Asset {asset_id} does not exist.')
    current_status = asset_rows[0][0]
    if current_status != 'Available':
        return _render_with_error(f'Asset {asset_id} is not available for assignment.')

    if not query('SELECT 1 FROM employee WHERE userID = %s', (user_id,)):
        return _render_with_error(f'Employee {user_id} does not exist.')

    next_assignment = query('SELECT COALESCE(MAX(assignmentID), 0) + 1 FROM asset_assignment')[0][0]
    next_history = query('SELECT COALESCE(MAX(historyID), 0) + 1 FROM asset_status_history')[0][0]
    admin_id = session['user_id']

    statements = [
        ('INSERT INTO asset_assignment (assignmentID, assignedDate, assetID, userID, assignedBy) VALUES (%s, CURRENT_DATE, %s, %s, %s)',
         (next_assignment, asset_id, user_id, admin_id)),
    ]
    if current_status != 'Assigned':
        statements.append(('UPDATE asset SET status = %s WHERE assetID = %s', ('Assigned', asset_id)))
        statements.append(('INSERT INTO asset_status_history (historyID, previousStatus, newStatus, changeDate, assetID, changedBy) VALUES (%s, %s, %s, CURRENT_DATE, %s, %s)',
                           (next_history, current_status, 'Assigned', asset_id, admin_id)))

    try:
        tx(statements)
    except psycopg2.errors.UniqueViolation:
        return _render_with_error(f'Asset {asset_id} is already actively assigned.')
    except psycopg2.errors.ForeignKeyViolation:
        return _render_with_error('Foreign key violation — check asset and employee IDs.')
    except Exception as e:
        return _render_with_error(f'Database error: {e}')

    flash(f'Asset {asset_id} assigned successfully.')
    return redirect('/assignments')

# Query 4 - mark returned (admin only)
@assignments_bp.route('/assignments/return/<int:assignment_id>', methods=['POST'])
def return_asset(assignment_id):
    if admin_required():
        return redirect('/login')

    rows = query('''
        SELECT aa.assetID, a.status, aa.returnDate
        FROM asset_assignment aa
        JOIN asset a ON aa.assetID = a.assetID
        WHERE aa.assignmentID = %s
    ''', (assignment_id,))
    if not rows:
        return _render_with_error(f'Assignment {assignment_id} not found.')
    asset_id, current_status, already_returned = rows[0]
    if already_returned is not None:
        return redirect('/assignments')

    next_history = query('SELECT COALESCE(MAX(historyID), 0) + 1 FROM asset_status_history')[0][0]
    admin_id = session['user_id']

    statements = [
        ('UPDATE asset_assignment SET returnDate = CURRENT_DATE WHERE assignmentID = %s', (assignment_id,)),
    ]
    if current_status != 'Available':
        statements.append(('UPDATE asset SET status = %s WHERE assetID = %s', ('Available', asset_id)))
        statements.append(('INSERT INTO asset_status_history (historyID, previousStatus, newStatus, changeDate, assetID, changedBy) VALUES (%s, %s, %s, CURRENT_DATE, %s, %s)',
                           (next_history, current_status, 'Available', asset_id, admin_id)))

    try:
        tx(statements)
    except Exception as e:
        return _render_with_error(f'Return failed: {e}')

    flash(f'Assignment {assignment_id} marked returned.')
    return redirect('/assignments')

# Query 5 - employee's own assignments
@assignments_bp.route('/assignments/employee/<int:user_id>')
def employee_assignments(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_type') != 'Admin' and session.get('user_id') != user_id:
        return redirect('/dashboard')
    rows = _assignment_rows('aa.userID = %s', (user_id,))
    return render_template('assignments.html', assignments=rows, **_form_options())

# Query 6 - active assignments with asset + employee names (fixed: returns same shape as SELECT *)
@assignments_bp.route('/assignments/details')
def assignment_details():
    if admin_required():
        return redirect('/login')
    rows = _assignment_rows('aa.returnDate IS NULL')
    return render_template('assignments.html', assignments=rows, **_form_options())

# Query 7 - average days an asset was kept
@assignments_bp.route('/assignments/avg-days')
def avg_days():
    if admin_required():
        return redirect('/login')
    rows = query('SELECT ROUND(AVG(returnDate - assignedDate), 1) FROM asset_assignment WHERE returnDate IS NOT NULL')
    avg = rows[0][0] if rows and rows[0][0] is not None else 0
    return render_template('assignments.html', assignments=[], avg_days=avg, **_form_options())

# Query 8 - most assigned user
@assignments_bp.route('/assignments/top-users')
def top_users():
    if admin_required():
        return redirect('/login')
    rows = query('SELECT userID, COUNT(*) AS total FROM asset_assignment GROUP BY userID ORDER BY total DESC')
    return render_template('assignments.html', assignments=[], top_users=rows, **_form_options())

# Query 9 - returned within 7 days
@assignments_bp.route('/assignments/quick-returns')
def quick_returns():
    if admin_required():
        return redirect('/login')
    rows = _assignment_rows('aa.returnDate IS NOT NULL AND (aa.returnDate - aa.assignedDate) <= 7',
                            order_sql='aa.returnDate DESC, aa.assignmentID DESC')
    return render_template('assignments.html', assignments=rows, **_form_options())

# Query 10 - assets assigned more than once
@assignments_bp.route('/assignments/repeated-assets')
def repeated_assets():
    if admin_required():
        return redirect('/login')
    rows = query('SELECT assetID, COUNT(*) AS total FROM asset_assignment GROUP BY assetID HAVING COUNT(*) > 1 ORDER BY total DESC')
    return render_template('assignments.html', assignments=[], repeated=rows, **_form_options())
