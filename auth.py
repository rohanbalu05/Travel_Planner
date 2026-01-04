from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import db, User

def register_user(username, email, password):
    """
    Registers a new user with a hashed password.
    Returns (success_boolean, message_string).
    """
    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        return False, "Username already taken."
    if User.query.filter_by(email=email).first():
        return False, "Email already registered."

    # Hash the password for secure storage
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return True, "Registration successful! Please log in."

def login_user(username, password):
    """
    Authenticates a user and establishes a session.
    Returns (success_boolean, message_string).
    """
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return True, "Logged in successfully!"
    return False, "Invalid username or password."

def logout_user():
    """
    Clears the user session, effectively logging them out.
    """
    session.pop('user_id', None)
    session.pop('username', None)
    flash("You have been logged out.", "info")

def login_required(f):
    """
    Decorator to restrict access to routes to logged-in users only.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """
    Retrieves the current logged-in user object from the database.
    """
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None