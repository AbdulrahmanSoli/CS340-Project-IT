from flask import Blueprint, render_template, request, redirect, session
from werkzeug.security import check_password_hash
from db import query

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        rows = query('SELECT userID, userFullName, passwordHash, userType '
                     'FROM users WHERE email = %s', (email,))
        if rows and check_password_hash(rows[0][2], password):
            session['user_id'] = rows[0][0]
            session['user_name'] = rows[0][1]
            session['user_type'] = rows[0][3]
            return redirect('/dashboard')
        return render_template('login.html', error='Wrong email or password')
    return render_template('login.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect('/dashboard')
        return redirect('/login')
    session.clear()
    return redirect('/login')

@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    if session.get('user_type') == 'Employee':
        total = query('''
            SELECT COUNT(*)
            FROM asset_assignment
            WHERE userID = %s AND returnDate IS NULL
        ''', (session['user_id'],))[0][0]

        recent = query('''
            SELECT a.assetName, aa.assignedDate
            FROM asset_assignment aa
            JOIN asset a ON aa.assetID = a.assetID
            WHERE aa.userID = %s
            ORDER BY aa.assignedDate DESC, aa.assignmentID DESC
            LIMIT 5
        ''', (session['user_id'],))

        return render_template('dashboard.html',
                               employee_dashboard=True,
                               total=total,
                               recent=recent)

    status_rows = query('''
        SELECT
            SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) AS available,
            SUM(CASE WHEN status='Assigned'  THEN 1 ELSE 0 END) AS assigned,
            SUM(CASE WHEN status='Damaged'   THEN 1 ELSE 0 END) AS damaged
        FROM asset
    ''')
    available = status_rows[0][0] or 0
    assigned  = status_rows[0][1] or 0
    damaged   = status_rows[0][2] or 0
    total     = available + assigned + damaged

    recent = query('''
        SELECT a.assetName, u.userFullName, aa.assignedDate
        FROM asset_assignment aa
        JOIN asset a ON aa.assetID = a.assetID
        JOIN users u ON aa.userID = u.userID
        WHERE aa.returnDate IS NULL
        ORDER BY aa.assignedDate DESC, aa.assignmentID DESC
        LIMIT 5
    ''')

    return render_template('dashboard.html',
                           total=total,
                           available=available,
                           assigned=assigned,
                           damaged=damaged,
                           recent=recent)
