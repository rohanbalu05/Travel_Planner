from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """
    SQLAlchemy model for storing user information.
    Includes username, email, and a securely hashed password.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Relationship to trips, allowing access to user.trips
    trips = db.relationship('Trip', backref='user', lazy=True)

    def __repr__(self):
        return f'&lt;User {self.username}&gt;'

class Trip(db.Model):
    """
    SQLAlchemy model for storing user-generated trip details.
    Links to a User and contains basic trip parameters.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.String(50)) # Stored as string for flexibility (e.g., "20000 INR")
    days = db.Column(db.Integer, nullable=False)
    trip_type = db.Column(db.String(50))
    num_people = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Relationship to itinerary days, allowing access to trip.itinerary_days
    itinerary_days = db.relationship('ItineraryDay', backref='trip', lazy=True, order_by='ItineraryDay.day_number')

    def __repr__(self):
        return f'&lt;Trip {self.destination} for User {self.user_id}&gt;'

class ItineraryDay(db.Model):
    """
    SQLAlchemy model for storing individual days of an itinerary.
    Links to a Trip and holds the detailed description for that day.
    """
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False) # Full text for the day's plan

    def __repr__(self):
        return f'&lt;ItineraryDay Day {self.day_number} for Trip {self.trip_id}&gt;'

def init_db(app):
    """
    Initializes the SQLAlchemy database with the Flask app.
    Configures SQLite as the database.
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///novatrip.db' # Using SQLite for simplicity
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress warning
    db.init_app(app)
    with app.app_context():
        db.create_all() # Create tables if they don't exist