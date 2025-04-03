from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from blockchain import Blockchain
import json
from datetime import datetime
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Initialize blockchain
blockchain = Blockchain()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health_records.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
CORS(app)

# Database Models
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

    def get_id(self):
        return str(self.id)

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

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Get common fields
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            full_name=request.form['full_name'],
            email=request.form['email'],
            phone=request.form['phone']
        )

        # Add role-specific fields
        if role == 'patient':
            user.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d') if request.form['date_of_birth'] else None
            user.blood_group = request.form['blood_group']
            user.address = request.form['address']
        else:  # doctor
            user.specialization = request.form['specialization']
            user.license_number = request.form['license_number']

        db.session.add(user)
        try:
            db.session.commit()
            flash('Registration successful')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_record', methods=['POST'])
@login_required
def add_record():
    if current_user.role != 'doctor':
        return jsonify({'error': 'Only doctors can add records'}), 403
    
    data = request.get_json()
    patient = User.query.filter_by(username=data['patient_id']).first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    try:
        # Add record to SQL database
        record = HealthRecord(
            patient_id=patient.id,
            doctor_id=current_user.id,
            diagnosis=data['diagnosis'],
            treatment=data['treatment'],
            notes=data.get('notes', ''),
            created_at=datetime.now()
        )
        db.session.add(record)
        db.session.commit()

        # Add record to blockchain
        blockchain.add_transaction(
            sender=current_user.username,
            recipient=patient.username,
            data={
                'diagnosis': data['diagnosis'],
                'treatment': data['treatment'],
                'notes': data.get('notes', ''),
                'date': datetime.now().isoformat()
            }
        )
        # Mine the block
        block = blockchain.mine_pending_transactions(current_user.username)

        return jsonify({
            'message': 'Record added successfully',
            'block_hash': block.hash
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/get_records/<username>')
@login_required
def get_records(username):
    try:
        patient = User.query.filter_by(username=username).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404

        # Check permissions
        if current_user.role != 'doctor' and current_user.username != username:
            return jsonify({'error': 'Unauthorized access'}), 403

        # Get records from blockchain
        records = blockchain.get_patient_records(username)
        
        # Format and return records
        formatted_records = []
        for record in records:
            formatted_records.append({
                'doctor': record['sender'],
                'diagnosis': record['data']['diagnosis'],
                'treatment': record['data']['treatment'],
                'notes': record['data']['notes'],
                'date': record['data']['date']
            })

        return jsonify(formatted_records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'doctor':
        return render_template('doctor_dashboard.html')
    else:
        return render_template('patient_dashboard.html')

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()  # Initialize database tables
    app.run(debug=True)
