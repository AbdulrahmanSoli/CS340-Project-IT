import psycopg2
from flask import Blueprint, flash, render_template, request, redirect, session
from db import query, tx

assets_bp = Blueprint('assets', __name__)

def login_required():
    return 'user_id' not in session

def admin_required():
    return 'user_id' not in session or session.get('user_type') != 'Admin'

def _render(assets=None, **extra):
    return render_template('assets.html', assets=assets or [], **extra)

def _render_with_error(msg):
    rows = query('SELECT * FROM asset ORDER BY status, assetName, assetID') or []
    return render_template('assets.html', assets=rows, error=msg)


# --- BASIC QUERIES (1-5) ---

# 1. Show all assets
@assets_bp.route('/assets')
def list_assets():
    if admin_required():
        return redirect('/login')
    rows = query('SELECT * FROM asset ORDER BY status, assetName, assetID') or []
    return _render(assets=rows)

# 2. Filter by status, category, and/or serial number
@assets_bp.route('/assets/filter')
def filter_assets():
    if admin_required():
        return redirect('/login')

    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    serial = request.args.get('serial', '').strip()

    clauses = []
    params = []
    if status:
        if status not in ('Available', 'Assigned', 'Damaged'):
            return _render_with_error('Invalid status filter.')
        clauses.append('status = %s')
        params.append(status)
    if category:
        clauses.append('category ILIKE %s')
        params.append(f'%{category}%')
    if serial:
        clauses.append('serialNum ILIKE %s')
        params.append(f'%{serial}%')

    if not clauses:
        return _render_with_error('Provide at least one of: status, category, serial.')

    sql = 'SELECT * FROM asset WHERE ' + ' AND '.join(clauses) + ' ORDER BY assetID'
    rows = query(sql, tuple(params)) or []
    return _render(assets=rows, filters={
        'status': status,
        'category': category,
        'serial': serial,
    })

# 3. Add a new asset (admin only)
@assets_bp.route('/assets/add', methods=['POST'])
def add_asset():
    if admin_required():
        return redirect('/login')

    asset_id = request.form.get('asset_id', '').strip()
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    serial = request.form.get('serial', '').strip()
    status = request.form.get('status', '').strip()

    if not asset_id.isdigit():
        return _render_with_error('Asset ID must be a number.')
    if not name or not category or not serial:
        return _render_with_error('Name, category, and serial are required.')
    if status not in ('Available', 'Damaged'):
        return _render_with_error('New assets can only be Available or Damaged.')

    try:
        query('''
            INSERT INTO asset (assetID, assetName, category, status, serialNum)
            VALUES (%s, %s, %s, %s, %s)
        ''', (asset_id, name, category, status, serial))
    except psycopg2.errors.UniqueViolation:
        return _render_with_error(f'Asset {asset_id} (or its serial) already exists.')
    except Exception as e:
        return _render_with_error(f'Database error: {e}')

    flash('Asset added successfully.')
    return redirect('/assets')

# 4. Update an asset's status (admin only)
@assets_bp.route('/assets/update', methods=['POST'])
def update_asset():
    if admin_required():
        return redirect('/login')

    asset_id = request.form.get('asset_id', '').strip()
    new_status = request.form.get('status', '').strip()

    if not asset_id.isdigit():
        return _render_with_error('Asset ID must be a number.')
    if new_status not in ('Available', 'Damaged'):
        return _render_with_error('Manual update can only set Available or Damaged. Use the assignments page to assign.')

    rows = query('SELECT status FROM asset WHERE assetID = %s', (asset_id,))
    if not rows:
        return _render_with_error(f'Asset {asset_id} does not exist.')
    current_status = rows[0][0]
    if current_status == new_status:
        return redirect('/assets')
    if current_status == 'Assigned':
        return _render_with_error(f'Asset {asset_id} is currently assigned. Return it before changing status.')

    next_history = query('SELECT COALESCE(MAX(historyID), 0) + 1 FROM asset_status_history')[0][0]
    admin_id = session['user_id']

    statements = [
        ('UPDATE asset SET status = %s WHERE assetID = %s', (new_status, asset_id)),
        ('''INSERT INTO asset_status_history
            (historyID, previousStatus, newStatus, changeDate, assetID, changedBy)
            VALUES (%s, %s, %s, CURRENT_DATE, %s, %s)''',
         (next_history, current_status, new_status, asset_id, admin_id)),
    ]
    try:
        tx(statements)
    except Exception as e:
        return _render_with_error(f'Update failed: {e}')

    flash(f'Asset {asset_id} marked {new_status}.')
    return redirect('/assets')

# 5. Delete an asset (admin only, POST)
@assets_bp.route('/assets/delete/<int:asset_id>', methods=['POST'])
def delete_asset(asset_id):
    if admin_required():
        return redirect('/login')

    if not query('SELECT 1 FROM asset WHERE assetID = %s', (asset_id,)):
        return _render_with_error(f'Asset {asset_id} does not exist.')

    active = query(
        'SELECT 1 FROM asset_assignment WHERE assetID = %s AND returnDate IS NULL',
        (asset_id,)
    )
    if active:
        return _render_with_error(f'Asset {asset_id} has an active assignment. Return it first.')

    try:
        query('DELETE FROM asset WHERE assetID = %s', (asset_id,))
    except psycopg2.errors.ForeignKeyViolation:
        return _render_with_error(f'Asset {asset_id} is referenced elsewhere and cannot be deleted.')
    except Exception as e:
        return _render_with_error(f'Delete failed: {e}')

    flash(f'Asset {asset_id} deleted.')
    return redirect('/assets')


# --- ADVANCED QUERIES (6-10) ---

# 6. Show each asset with who currently has it
@assets_bp.route('/assets/assignments')
def current_assignments():
    if admin_required():
        return redirect('/login')
    rows = query('''
        SELECT a.assetName, u.userFullName
        FROM asset a
        JOIN asset_assignment aa ON a.assetID = aa.assetID
        JOIN users u ON aa.userID = u.userID
        WHERE aa.returnDate IS NULL
        ORDER BY a.assetName
    ''') or []
    return _render(current_holders=rows)

# 7. Assets that have never been assigned
@assets_bp.route('/assets/unassigned')
def unassigned_assets():
    if admin_required():
        return redirect('/login')
    rows = query('''
        SELECT * FROM asset
        WHERE assetID NOT IN (SELECT assetID FROM asset_assignment)
        ORDER BY assetID
    ''') or []
    return _render(assets=rows)

# 8. Count assets by category
@assets_bp.route('/assets/count-by-category')
def count_categories():
    if admin_required():
        return redirect('/login')
    rows = query('''
        SELECT category, COUNT(*) AS total
        FROM asset
        GROUP BY category
        ORDER BY total DESC
    ''') or []
    return _render(category_counts=rows)

# 9. Assets assigned more than once
@assets_bp.route('/assets/frequent-assignments')
def frequent_assets():
    if admin_required():
        return redirect('/login')
    rows = query('''
        SELECT assetID, COUNT(*) AS total
        FROM asset_assignment
        GROUP BY assetID
        HAVING COUNT(*) > 1
        ORDER BY total DESC
    ''') or []
    return _render(frequent=rows)

# Employee view: only assets currently assigned to the logged-in user
@assets_bp.route('/assets/my')
def my_assets():
    if login_required():
        return redirect('/login')
    rows = query('''
        SELECT a.*
        FROM asset a
        JOIN asset_assignment aa ON a.assetID = aa.assetID
        WHERE aa.userID = %s AND aa.returnDate IS NULL
        ORDER BY a.assetID
    ''', (session['user_id'],)) or []
    return _render(assets=rows)

# 10. Assets purchased this year (requires purchaseDate column)
@assets_bp.route('/assets/new-purchases')
def recent_purchases():
    if admin_required():
        return redirect('/login')
    rows = query('''
        SELECT * FROM asset
        WHERE EXTRACT(YEAR FROM purchaseDate) = EXTRACT(YEAR FROM CURRENT_DATE)
        ORDER BY assetID
    ''') or []
    return _render(assets=rows)
