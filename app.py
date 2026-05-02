import os
from dotenv import load_dotenv
from secrets import token_urlsafe
from flask import Flask, abort, request, session
from db import close_connection
from routes.auth import auth_bp
from routes.assignments import assignments_bp
from routes.assets import assets_bp
from routes.users import users_bp
from routes.history import history_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    raise RuntimeError('SECRET_KEY is not set')
app.teardown_appcontext(close_connection)

def csrf_token():
    token = session.get('csrf_token')
    if token is None:
        token = token_urlsafe(32)
        session['csrf_token'] = token
    return token

@app.context_processor
def inject_csrf_token():
    return {'csrf_token': csrf_token}

@app.before_request
def protect_post_requests():
    if request.method == 'POST':
        expected = session.get('csrf_token')
        actual = request.form.get('csrf_token')
        if not expected or expected != actual:
            abort(400)

app.register_blueprint(auth_bp)
app.register_blueprint(assignments_bp)
app.register_blueprint(assets_bp)
app.register_blueprint(users_bp)
app.register_blueprint(history_bp)

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1')
