"""
Authentication module
User login and role management
"""

import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash
from src.database import get_session
from src.models import Base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime


class User(Base):
    """User model"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='user')
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed


def create_user(username, password, role='user'):
    """Create a new user"""
    session_db = get_session()
    try:
        # Check if user exists
        existing = session_db.query(User).filter(User.username == username).first()
        if existing:
            return False

        # Create user
        hashed = hash_password(password)
        user = User(username=username, password_hash=hashed, role=role)
        session_db.add(user)
        session_db.commit()
        return True
    finally:
        session_db.close()


def authenticate_user(username, password):
    """Authenticate user and return user data"""
    session_db = get_session()
    try:
        user = session_db.query(User).filter(User.username == username).first()

        if not user:
            return None

        if verify_password(password, user.password_hash):
            return {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }

        return None
    finally:
        session_db.close()


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))

        if session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function


def init_default_users():
    """Initialize default admin and user accounts"""
    from src.database import engine

    # Create users table
    Base.metadata.create_all(engine)

    # Create default admin (username: admin, password: admin123)
    if create_user('admin', 'admin123', 'admin'):
        print('Default admin created: admin/admin123')

    # Create default user (username: user, password: user123)
    if create_user('user', 'user123', 'user'):
        print('Default user created: user/user123')
