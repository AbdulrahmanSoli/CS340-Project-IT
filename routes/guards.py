from flask import redirect, session


def login_required():
    return 'user_id' not in session


def admin_required():
    return login_required() or session.get('user_type') != 'Admin'


def admin_redirect():
    if login_required():
        return redirect('/login')
    return redirect('/dashboard')
