import psycopg2
from flask import Blueprint, render_template, request, redirect, session
from db import query
from routes.guards import admin_redirect, admin_required

history_bp = Blueprint('history', __name__)

VALID_STATUSES = ('Available', 'Assigned', 'Damaged')


def _history_rows():
    return query('SELECT * FROM asset_status_history ORDER BY changeDate DESC, historyID DESC') or []


def _render_with_error(message):
    return render_template('history.html', history=_history_rows(), error=message)


# Query 1 - show all history
@history_bp.route('/history')
def list_history():
    if admin_required():
        return admin_redirect()
    rows = _history_rows()
    return render_template('history.html', history=rows)


# Query 2 - show history for one specific asset
@history_bp.route('/history/asset')
def asset_history_lookup():
    if admin_required():
        return admin_redirect()

    asset_id = request.args.get('asset_id', '').strip()
    if not asset_id.isdigit():
        return _render_with_error('Asset ID must be a number.')
    return redirect(f'/history/asset/{asset_id}')


@history_bp.route('/history/asset/<int:asset_id>')
def asset_history(asset_id):
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT *
        FROM asset_status_history
        WHERE assetID = %s
        ORDER BY changeDate DESC, historyID DESC
    ''', (asset_id,)) or []
    return render_template('history.html', history=rows)


# Query 3 - log a new status change
@history_bp.route('/history/add', methods=['POST'])
def add_history():
    if admin_required():
        return admin_redirect()

    history_id = request.form.get('history_id', '').strip()
    asset_id = request.form.get('asset_id', '').strip()
    prev_status = request.form.get('prev_status', '').strip()
    new_status = request.form.get('new_status', '').strip()

    if not history_id.isdigit() or not asset_id.isdigit():
        return _render_with_error('History ID and Asset ID must be numbers.')
    if prev_status not in VALID_STATUSES or new_status not in VALID_STATUSES:
        return _render_with_error('Status must be Available, Assigned, or Damaged.')
    if prev_status == new_status:
        return _render_with_error('Previous and new status must be different.')

    data = (history_id, prev_status, new_status, asset_id, session['user_id'])
    try:
        query('''
            INSERT INTO asset_status_history
                (historyID, previousStatus, newStatus, changeDate, assetID, changedBy)
            VALUES (%s, %s, %s, CURRENT_DATE, %s, %s)
        ''', data)
    except psycopg2.errors.UniqueViolation:
        return _render_with_error(f'History ID {history_id} already exists.')
    except psycopg2.errors.ForeignKeyViolation:
        return _render_with_error('Foreign key violation - check asset and admin IDs.')
    except Exception as e:
        return _render_with_error(f'Database error: {e}')

    return redirect('/history')


# Query 4 - filter by new status
@history_bp.route('/history/filter')
def filter_history():
    if admin_required():
        return admin_redirect()

    status = request.args.get('status', '').strip()
    if status not in VALID_STATUSES:
        return _render_with_error('Invalid status filter.')

    rows = query('''
        SELECT *
        FROM asset_status_history
        WHERE newStatus = %s
        ORDER BY changeDate DESC, historyID DESC
    ''', (status,)) or []
    return render_template('history.html', history=rows, selected_status=status)


# Query 5 - filter by date range
@history_bp.route('/history/dates', methods=['POST'])
def filter_by_date():
    if admin_required():
        return admin_redirect()

    from_date = request.form.get('from_date', '').strip()
    to_date = request.form.get('to_date', '').strip()
    if not from_date or not to_date:
        return _render_with_error('Both dates are required.')
    if from_date > to_date:
        return _render_with_error('From date must be before or equal to to date.')

    data = (from_date, to_date)
    rows = query('''
        SELECT *
        FROM asset_status_history
        WHERE changeDate BETWEEN %s AND %s
        ORDER BY changeDate DESC, historyID DESC
    ''', data) or []
    return render_template('history.html',
                           history=rows,
                           from_date=data[0],
                           to_date=data[1])


# Query 6 - show asset name with its history
@history_bp.route('/history/with-assets')
def history_with_assets():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT a.assetName, h.previousStatus, h.newStatus, h.changeDate
        FROM asset_status_history h
        JOIN asset a ON h.assetID = a.assetID
        ORDER BY h.changeDate DESC, h.historyID DESC
    ''') or []
    return render_template('history.html', history=[], named_history=rows)


# Query 7 - how many status changes per asset
@history_bp.route('/history/count-by-asset')
def count_by_asset():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT assetID, COUNT(*) AS total
        FROM asset_status_history
        GROUP BY assetID
        ORDER BY total DESC, assetID
    ''') or []
    return render_template('history.html', history=[], asset_counts=rows)


# Query 8 - assets that were ever damaged
@history_bp.route('/history/damaged')
def damaged_assets():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT DISTINCT assetID
        FROM asset_status_history
        WHERE newStatus = 'Damaged'
        ORDER BY assetID
    ''') or []
    return render_template('history.html', history=[], damaged_assets=rows)


# Query 9 - latest status recorded for each asset
@history_bp.route('/history/latest')
def latest_statuses():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT DISTINCT ON (assetID) assetID, newStatus, changeDate
        FROM asset_status_history
        ORDER BY assetID, changeDate DESC, historyID DESC
    ''') or []
    return render_template('history.html', history=[], latest_statuses=rows)


# Query 10 - assets with 3 or more status changes
@history_bp.route('/history/frequent')
def frequent_status_changes():
    if admin_required():
        return admin_redirect()
    rows = query('''
        SELECT assetID, COUNT(*) AS total
        FROM asset_status_history
        GROUP BY assetID
        HAVING COUNT(*) >= 3
        ORDER BY total DESC, assetID
    ''') or []
    return render_template('history.html', history=[], frequent_assets=rows)
