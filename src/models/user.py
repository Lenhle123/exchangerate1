from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Create db instance that will be initialized in main.py
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # User preferences
    preferred_currency_pairs = db.Column(db.Text)  # JSON string of preferred pairs
    notification_preferences = db.Column(db.Text)  # JSON string of notification settings
    dashboard_layout = db.Column(db.Text)  # JSON string of dashboard configuration
    
    def __init__(self, username, email, password=None):
        self.username = username
        self.email = email
        if password:
            self.set_password(password)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class Watchlist(db.Model):
    __tablename__ = 'watchlists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    currency_pair = db.Column(db.String(10), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency_pair': self.currency_pair,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<Watchlist {self.currency_pair}>'


class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    currency_pair = db.Column(db.String(10), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # 'above', 'below', 'change'
    threshold_value = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    triggered_at = db.Column(db.DateTime)
    message = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency_pair': self.currency_pair,
            'alert_type': self.alert_type,
            'threshold_value': self.threshold_value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'message': self.message
        }
    
    def __repr__(self):
        return f'<Alert {self.currency_pair} {self.alert_type} {self.threshold_value}>'
