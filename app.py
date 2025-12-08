from flask import Flask, redirect, url_for, session
from database import load_users
from flask_cors import CORS
from config import Config
from routes.auth import auth_bp
from routes.main import main_bp
from routes.api import api_bp
from routes.crm import crm_bp

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)
app.register_blueprint(crm_bp)

# Context Processor to inject user into all templates
@app.context_processor
def inject_user():
    if 'user' in session:
        users = load_users()
        user = users.get(session['user'], {})
        return dict(user=user)
    return dict(user=None)

# Global error handlers or other app-level logic can go here

if __name__ == '__main__':
    app.run(debug=True, port=5000)
