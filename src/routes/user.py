from flask import Blueprint, request, jsonify, session
from datetime import datetime
import json
import re

# Create blueprint - db and models will be imported from main.py
user_bp = Blueprint('user', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_currency_pair(pair):
    """Validate currency pair format"""
    valid_pairs = [
        'USD/EUR', 'USD/GBP', 'USD/JPY', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY',
        'USD/CAD', 'USD/AUD', 'USD/CHF', 'EUR/CAD', 'EUR/AUD', 'EUR/CHF',
        'GBP/CAD', 'GBP/AUD', 'GBP/CHF', 'AUD/CAD', 'AUD/JPY', 'CAD/JPY'
    ]
    return pair in valid_pairs

@user_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        # Import here to avoid circular imports
        from src.models.user import db, User
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Validation
        if not username or len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400
        
        if not email or not validate_email(email):
            return jsonify({'error': 'Valid email address is required'}), 400
        
        if not password or len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create new user
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        try:
            from src.models.user import db
            db.session.rollback()
        except:
            pass
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@user_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user login"""
    try:
        from src.models.user import User
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username_or_email or not password:
            return jsonify({'error': 'Username/email and password are required'}), 400
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email.lower())
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Update last login
        from src.models.user import db
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Store user session
        session['user_id'] = user.id
        session['username'] = user.username
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@user_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        from src.models.user import User
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict(),
            'preferences': {
                'currency_pairs': json.loads(user.preferred_currency_pairs) if user.preferred_currency_pairs else [],
                'notifications': json.loads(user.notification_preferences) if user.notification_preferences else {},
                'dashboard': json.loads(user.dashboard_layout) if user.dashboard_layout else {}
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@user_bp.route('/health', methods=['GET'])
def user_health():
    """User service health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'user_service',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
