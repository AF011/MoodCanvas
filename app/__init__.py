# app/__init__.py
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
    
    # Register blueprints
    from app.routes import auth_bp, initial_session_bp, dashboard_bp, mood_canvas_bp, profile_bp
    from app.routes import smart_diary_bp
    from app.whatsapp_integration import whatsapp_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(initial_session_bp, url_prefix='/initial-session')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(mood_canvas_bp, url_prefix='/mood-canvas')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(smart_diary_bp, url_prefix='/diary')
    app.register_blueprint(whatsapp_bp, url_prefix='/whatsapp')
    
    # Add a root route
    @app.route('/')
    def index():
        return redirect(url_for('auth.index'))
    
    return app