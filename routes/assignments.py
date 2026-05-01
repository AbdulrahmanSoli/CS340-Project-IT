from flask import Blueprint, render_template, request, redirect, session
from db import query

assignments_bp = Blueprint('assignments', __name__)

def admin_required():
    return 'user_id' not in session or session.get('user_type') != 'Admin'

# Query 1 - show all active assignments
@assignments_bp.route('/assignments')
def list_assignments():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('SELECT * FROM asset_assignment WHERE returnDate IS NULL')
    return render_template('assignments.html', assignments=rows)

# Query 2 - show returned assignments
@assignments_bp.route('/assignments/returned')
def returned_assignments():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('SELECT * FROM asset_assignment WHERE returnDate IS NOT NULL')
    return render_template('assignments.html', assignments=rows)

# Query 3 - assign an asset (admin only)
@assignments_bp.route('/assignments/add', methods=['POST'])
def assign_asset():
    if admin_required():
        return redirect('/login')
    next_id_rows = query('SELECT COALESCE(MAX(assignmentID), 0) + 1 FROM asset_assignment')
    if not next_id_rows:
        rows = query('SELECT * FROM asset_assignment WHERE returnDate IS NULL')
        return render_template('assignments.html', assignments=rows, error='Database error.')
    data = (next_id_rows[0][0], request.form['asset_id'], request.form['user_id'], session['user_id'])
    result = query('INSERT INTO asset_assignment (assignmentID, assignedDate, assetID, userID, assignedBy) VALUES (%s, CURRENT_DATE, %s, %s, %s)', data)
    if result is None:
        rows = query('SELECT * FROM asset_assignment WHERE returnDate IS NULL')
        return render_template('assignments.html', assignments=rows, error='Assignment failed: asset ID or employee ID does not exist, or asset is already assigned.')
    return redirect('/assignments')

# Query 4 - mark returned (admin only)
@assignments_bp.route('/assignments/return/<int:assignment_id>', methods=['POST'])
def return_asset(assignment_id):
    if admin_required():
        return redirect('/login')
    query('UPDATE asset_assignment SET returnDate = CURRENT_DATE WHERE assignmentID = %s', (assignment_id,))
    return redirect('/assignments')

# Query 5 - employee's own assignments
@assignments_bp.route('/assignments/employee/<int:user_id>')
def employee_assignments(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_type') != 'Admin' and session.get('user_id') != user_id:
        return redirect('/dashboard')
    rows = query('SELECT * FROM asset_assignment WHERE userID = %s', (user_id,))
    return render_template('assignments.html', assignments=rows)

# Query 6 - active assignments with asset + employee names (fixed: returns same shape as SELECT *)
@assignments_bp.route('/assignments/details')
def assignment_details():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('''
        SELECT aa.assignmentID, aa.assignedDate, aa.returnDate,
               aa.assetID, aa.userID, aa.assignedBy
        FROM asset_assignment aa
        JOIN asset a ON aa.assetID = a.assetID
        JOIN users u ON aa.userID = u.userID
        WHERE aa.returnDate IS NULL
    ''')
    return render_template('assignments.html', assignments=rows)

# Query 7 - average days an asset was kept
@assignments_bp.route('/assignments/avg-days')
def avg_days():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('SELECT ROUND(AVG(returnDate - assignedDate), 1) FROM asset_assignment WHERE returnDate IS NOT NULL')
    avg = rows[0][0] if rows else 0
    return render_template('assignments.html', assignments=[], avg_days=avg)

# Query 8 - most assigned user
@assignments_bp.route('/assignments/top-users')
def top_users():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('SELECT userID, COUNT(*) AS total FROM asset_assignment GROUP BY userID ORDER BY total DESC')
    return render_template('assignments.html', assignments=[], top_users=rows)

# Query 9 - returned within 7 days
@assignments_bp.route('/assignments/quick-returns')
def quick_returns():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('SELECT * FROM asset_assignment WHERE returnDate IS NOT NULL AND (returnDate - assignedDate) <= 7')
    return render_template('assignments.html', assignments=rows)

# Query 10 - assets assigned more than once
@assignments_bp.route('/assignments/repeated-assets')
def repeated_assets():
    if 'user_id' not in session:
        return redirect('/login')
    rows = query('SELECT assetID, COUNT(*) AS total FROM asset_assignment GROUP BY assetID HAVING COUNT(*) > 1 ORDER BY total DESC')
    return render_template('assignments.html', assignments=[], repeated=rows)
