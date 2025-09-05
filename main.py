import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
import threading
import time
import random
from datetime import datetime, timedelta
import json

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'exchange-forecast-secret-key-2025'

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# -----------------------------
# Database configuration (FIXED)
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # ✅ Fix for Render's Postgres URL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    print(f"Using PostgreSQL database")
else:
    # ✅ FIXED: Use writable directory for SQLite on cloud platforms
    if os.environ.get('RENDER') or os.environ.get('RAILWAY') or os.environ.get('HEROKU'):
        # Use temporary directory on cloud platforms
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), 'app.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        print(f"Using SQLite in temp directory: {db_path}")
    else:
        # Local development - ensure directory exists
        db_dir = os.path.join(os.path.dirname(__file__), 'database')
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, 'app.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        print(f"Using SQLite locally: {db_path}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# ✅ FIXED: Better error handling for model imports
try:
    from src.models.user import User, Watchlist, Alert
    from src.routes.user import user_bp
    
    # Register blueprints
    app.register_blueprint(user_bp, url_prefix='/api')
    print("User authentication modules loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import user modules: {e}")
    print("Running without user authentication features")
    
    # Create dummy models to prevent errors
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        
    class Watchlist(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        pair = db.Column(db.String(10), nullable=False)
        
    class Alert(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        pair = db.Column(db.String(10), nullable=False)
        target_rate = db.Column(db.Float, nullable=False)
    
    # Create a dummy blueprint to prevent errors
    from flask import Blueprint
    user_bp = Blueprint('user_dummy', __name__)

# -----------------------------
# Global variables for real-time data
# -----------------------------
current_rates = {
    'USD/EUR': {'rate': 1.0545, 'change': 0.0007, 'timestamp': datetime.utcnow().isoformat()},
    'USD/GBP': {'rate': 0.7823, 'change': -0.0012, 'timestamp': datetime.utcnow().isoformat()},
    'USD/JPY': {'rate': 149.85, 'change': 0.45, 'timestamp': datetime.utcnow().isoformat()},
    'EUR/GBP': {'rate': 0.8412, 'change': 0.0023, 'timestamp': datetime.utcnow().isoformat()},
}

# -----------------------------
# Real-time data simulation
# -----------------------------
def simulate_rate_updates():
    """Simulate real-time exchange rate updates"""
    while True:
        try:
            for pair in current_rates:
                current_rate = current_rates[pair]['rate']
                change = random.uniform(-0.005, 0.005)
                new_rate = current_rate + change
                
                current_rates[pair] = {
                    'rate': round(new_rate, 4),
                    'change': round(change, 4),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                socketio.emit('rate_update', {
                    'pair': pair,
                    'data': current_rates[pair]
                })
            
            time.sleep(5)
        except Exception as e:
            print(f"Error in rate simulation: {e}")
            time.sleep(10)

# Start background thread for rate updates
rate_thread = threading.Thread(target=simulate_rate_updates, daemon=True)
rate_thread.start()

# -----------------------------
# WebSocket events
# -----------------------------
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to Exchange Rate Server'})
    emit('initial_rates', current_rates)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('subscribe_pair')
def handle_subscribe(data):
    pair = data.get('pair')
    if pair in current_rates:
        emit('rate_update', {'pair': pair, 'data': current_rates[pair]})

# -----------------------------
# API Routes
# -----------------------------
@app.route('/api/health')
def health_check():
    # ✅ ADDED: Check database connection status
    db_status = 'connected'
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db.session.commit()
    except Exception as e:
        db_status = f'error: {str(e)[:50]}'
        print(f"Database health check failed: {e}")
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'api': 'running',
            'websocket': 'running',
            'database': db_status
        }
    })

@app.route('/api/rates')
def get_all_rates():
    return jsonify({
        'rates': current_rates,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/rates/<pair>')
def get_rate(pair):
    if pair in current_rates:
        history = []
        base_rate = current_rates[pair]['rate']
        for i in range(20):
            history.append({
                'rate': round(base_rate + random.uniform(-0.01, 0.01), 4),
                'timestamp': (datetime.utcnow() - timedelta(minutes=i*5)).isoformat()
            })
        
        return jsonify({
            'pair': pair,
            'current': current_rates[pair],
            'history': history[::-1],
            'statistics': {
                'min': round(min(h['rate'] for h in history), 4),
                'max': round(max(h['rate'] for h in history), 4),
                'avg': round(sum(h['rate'] for h in history) / len(history), 4),
                'volatility': round(random.uniform(0.005, 0.02), 4)
            }
        })
    else:
        return jsonify({'error': 'Currency pair not found'}), 404

# -----------------------------
# Serve React frontend
# -----------------------------
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return jsonify({
            'message': 'Exchange Rate Forecasting API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/api/health',
                'rates': '/api/rates',
                'forecast': '/api/forecast',
                'news': '/api/news/<pair>',
                'models': '/api/models/performance'
            }
        })

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return jsonify({
                'message': 'Exchange Rate Forecasting API',
                'version': '1.0.0',
                'endpoints': {
                    'health': '/api/health',
                    'rates': '/api/rates',
                    'forecast': '/api/forecast',
                    'news': '/api/news/<pair>',
                    'models': '/api/models/performance'
                }
            })

# -----------------------------
# ✅ FIXED: Initialize database tables with better error handling
# -----------------------------
def init_database():
    """Initialize database tables with proper error handling"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Test the connection
            db.session.execute('SELECT 1')
            db.session.commit()
            print("✅ Database connection verified")
            
            return True
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            print("⚠️  App will continue running but database features may not work")
            return False

# Initialize database on startup
init_database()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
