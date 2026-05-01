import os
from dotenv import load_dotenv
from flask import Flask
from routes.auth import auth_bp
from routes.assignments import assignments_bp
# from routes.assets import assets_bp       # add when Fares sends his file
# from routes.users import users_bp         # add when Alrasheed sends his file
# from routes.history import history_bp     # add when Albekairi sends his file

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

app.register_blueprint(auth_bp)
app.register_blueprint(assignments_bp)
# app.register_blueprint(assets_bp)
# app.register_blueprint(users_bp)
# app.register_blueprint(history_bp)

if __name__ == '__main__':
    app.run(debug=True)
