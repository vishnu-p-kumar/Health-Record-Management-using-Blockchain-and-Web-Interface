from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'doctor' or 'patient'
    
    # Additional fields for both doctors and patients
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))

    # Fields specific to patients
    date_of_birth = db.Column(db.Date, nullable=True)
    blood_group = db.Column(db.String(5), nullable=True)
    address = db.Column(db.String(200), nullable=True)

    # Fields specific to doctors
    specialization = db.Column(db.String(100), nullable=True)
    license_number = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'

class HealthRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id], backref='patient_records')
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref='doctor_records')
