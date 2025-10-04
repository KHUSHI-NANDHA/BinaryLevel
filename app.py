from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import os
import re
import requests
import base64
import json
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('local_link.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL,  -- 'student' or 'local'
            full_name TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Local guides table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS local_guides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            university TEXT,
            employment TEXT,
            bio TEXT,
            hourly_rate DECIMAL(10,2),
            is_verified BOOLEAN DEFAULT 0,
            verification_status TEXT DEFAULT 'pending',
            home_country TEXT,
            field_of_study TEXT,
            languages TEXT,
            dietary_preferences TEXT,
            cultural_background TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            local_id INTEGER NOT NULL,
            session_type TEXT NOT NULL,
            duration INTEGER NOT NULL,
            total_cost DECIMAL(10,2) NOT NULL,
            status TEXT DEFAULT 'pending',
            scheduled_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (local_id) REFERENCES local_guides (id)
        )
    ''')
    
    # Reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            local_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (local_id) REFERENCES local_guides (id)
        )
    ''')
    
    # Student preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            home_country TEXT NOT NULL,
            field_of_study TEXT,
            languages TEXT,
            dietary_preferences TEXT,
            budget_range TEXT,
            preferred_session_types TEXT,
            cultural_adaptation_needs TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    
    # Matching results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matching_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            local_id INTEGER NOT NULL,
            fit_score DECIMAL(5,2) NOT NULL,
            cultural_distance_score DECIMAL(5,2),
            language_match_score DECIMAL(5,2),
            field_match_score DECIMAL(5,2),
            dietary_match_score DECIMAL(5,2),
            budget_match_score DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (local_id) REFERENCES local_guides (id)
        )
    ''')
    
    # Add demo data if tables are empty
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # Add demo local guides
        demo_locals = [
            ('local_demo', 'local@demo.com', hash_password('DemoPass123!'), 'local', 'Arjun Sharma', '+420123456789'),
            ('local_demo2', 'priya@demo.com', hash_password('DemoPass123!'), 'local', 'Priya Patel', '+36123456789'),
            ('local_demo3', 'rahul@demo.com', hash_password('DemoPass123!'), 'local', 'Rahul Kumar', '+48123456789')
        ]
        
        for local_data in demo_locals:
            cursor.execute('INSERT INTO users (username, email, password_hash, user_type, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)', local_data)
        
        # Add demo local guide profiles
        cursor.execute('SELECT id FROM users WHERE user_type = "local"')
        local_user_ids = [row[0] for row in cursor.fetchall()]
        
        demo_profiles = [
            (local_user_ids[0], 'Prague', 'Czech Republic', 'Charles University', None, 'Experienced guide helping students with housing, transport, and cultural adaptation in Prague.', 2.0, 1, 'approved', 'India', 'Computer Science', 'English, Hindi, Czech', 'vegetarian', 'From Mumbai, understands the challenges of adapting to European culture'),
            (local_user_ids[1], 'Budapest', 'Hungary', None, 'Google', 'Local expert specializing in student life, affordable shopping, and public transport tips.', 2.0, 1, 'approved', 'India', 'Engineering', 'English, Hindi, Hungarian', 'halal', 'Originally from Delhi, helps students with cultural integration and finding halal food'),
            (local_user_ids[2], 'Warsaw', 'Poland', 'Warsaw University', None, 'Helping students find affordable housing and navigate Polish bureaucracy with ease.', 2.0, 1, 'approved', 'India', 'Business', 'English, Hindi, Polish', 'vegetarian', 'From Bangalore, specializes in helping students with academic and professional development')
        ]
        
        for profile_data in demo_profiles:
            cursor.execute('INSERT INTO local_guides (user_id, city, country, university, employment, bio, hourly_rate, is_verified, verification_status, home_country, field_of_study, languages, dietary_preferences, cultural_background) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', profile_data)
        
        # Add demo student
        cursor.execute('INSERT INTO users (username, email, password_hash, user_type, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)', 
                      ('student_demo', 'student@demo.com', hash_password('DemoPass123!'), 'student', 'Demo Student', '+420987654321'))
        
        # Add demo student preferences
        cursor.execute('SELECT id FROM users WHERE username = "student_demo"')
        student_id = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO student_preferences 
            (student_id, home_country, field_of_study, languages, dietary_preferences, budget_range, preferred_session_types, cultural_adaptation_needs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, 'India', 'Computer Science', 'English, Hindi', 'vegetarian', 'low', 'housing,transport', 'housing,transport,banking'))
        
        # Add demo sessions
        cursor.execute('SELECT id FROM users WHERE user_type = "student"')
        student_id = cursor.fetchone()[0]
        
        demo_sessions = [
            (student_id, 1, 'housing', 2, 2.0, 'completed', '2024-01-15 10:00:00'),
            (student_id, 2, 'transport', 2, 2.0, 'completed', '2024-01-20 14:00:00')
        ]
        
        for session_data in demo_sessions:
            cursor.execute('INSERT INTO sessions (student_id, local_id, session_type, duration, total_cost, status, scheduled_at) VALUES (?, ?, ?, ?, ?, ?, ?)', session_data)
        
        # Add demo reviews
        demo_reviews = [
            (1, student_id, 1, 5, 'Arjun was amazing! Helped me find a great apartment in Prague.'),
            (2, student_id, 2, 5, 'Priya showed me the best transport routes and saved me so much money!')
        ]
        
        for review_data in demo_reviews:
            cursor.execute('INSERT INTO reviews (session_id, student_id, local_id, rating, comment) VALUES (?, ?, ?, ?, ?)', review_data)
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password_strength(password):
    """Validate password strength requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image(image_path):
    """Encodes an image file into base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def verify_document(document_path):
    """Verify document using IDAnalyzer API"""
    try:
        # Set up your data
        api_key = "NG6QRbcJnpdWPk4OeLqL4EEjykIbsfGP"
        profile_id = "your profile id"  # Replace with your actual profile ID
        api_url = "https://api2.idanalyzer.com/scan"

        # Encode document image
        document_base64 = encode_image(document_path)

        # Build the payload (document only)
        payload = {
            "profile": profile_id,
            "document": document_base64
        }

        # Set headers
        headers = {
            'X-API-KEY': api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # Send the POST request
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        
        # Parse the response
        response_data = response.json()
        
        # Extract decision and response text
        decision = response_data.get('decision', 'unknown')
        
        return {
            'success': True,
            'decision': decision,
            'response_data': response_data,
            'raw_response': response.text
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'decision': 'error'
        }

@app.route('/')
def index():
    # Redirect logged-in users to their dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect logged-in users to their dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, user_type, full_name FROM users WHERE username = ? AND password_hash = ?',
                      (username, hash_password(password)))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['user_type'] = user[2]
            session['full_name'] = user[3]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect logged-in users to their dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        full_name = request.form['full_name']
        phone = request.form.get('phone', '')

        # Validate password strength
        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, 'error')
            return render_template('register.html')

        # Handle ID document upload for local guides
        id_verification_result = None
        id_document = None
        if user_type == 'local':
            if 'id_document' not in request.files:
                flash('ID document is required for local guides.', 'error')
                return render_template('register.html')
            
            id_document = request.files['id_document']
            if id_document.filename == '':
                flash('Please select an ID document.', 'error')
                return render_template('register.html')
            
            if not allowed_file(id_document.filename):
                flash('Invalid file type for ID document. Please upload images (PNG, JPG, JPEG, GIF, BMP) or PDF.', 'error')
                return render_template('register.html')

        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, email, password_hash, user_type, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)',
                          (username, email, hash_password(password), user_type, full_name, phone))
            conn.commit()
            
            # Get the new user ID
            cursor.execute('SELECT id, username, user_type, full_name FROM users WHERE username = ?',
                          (username,))
            user = cursor.fetchone()
            
            if user:
                # Handle local guide profile creation
                if user_type == 'local':
                    # Create basic local guide profile first
                    cursor.execute('''
                        INSERT INTO local_guides (user_id, city, country, university, employment, bio, hourly_rate, 
                                                is_verified, verification_status, home_country, field_of_study, 
                                                languages, dietary_preferences, cultural_background)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user[0], 'Not Set', 'Not Set', '', '', 'New local guide - profile setup required', 2.0, 
                          0, 'pending', '', '', '', '', ''))
                    
                    # Handle ID verification for local guides
                    if id_document:
                        # Save and verify ID document
                        document_filename = secure_filename(id_document.filename)
                        timestamp = str(int(time.time()))
                        document_filename = f"registration_{user[0]}_{timestamp}_{document_filename}"
                        document_path = os.path.join(app.config['UPLOAD_FOLDER'], document_filename)
                        id_document.save(document_path)
                        
                        # Verify document using IDAnalyzer API
                        id_verification_result = verify_document(document_path)
                        
                        # Clean up uploaded file
                        try:
                            os.remove(document_path)
                        except:
                            pass
                        
                        # Update verification status based on result
                        if id_verification_result['success'] and id_verification_result['decision'] == 'approve':
                            cursor.execute('UPDATE local_guides SET verification_status = ?, is_verified = ? WHERE user_id = ?', 
                                         ('approved', 1, user[0]))
                            flash('Registration successful! Your identity has been verified automatically. Please complete your profile to start receiving bookings!', 'success')
                        else:
                            cursor.execute('UPDATE local_guides SET verification_status = ? WHERE user_id = ?', 
                                         ('pending', user[0]))
                            flash('Registration successful! Your ID document is under review. Please complete your profile to start receiving bookings!', 'info')
                    else:
                        flash('Registration successful! Please complete your profile to start receiving bookings!', 'info')
                    
                    conn.commit()
                
                # Auto-login after successful registration
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['user_type'] = user[2]
                session['full_name'] = user[3]
                
                if user_type == 'student':
                    flash('Registration successful! Welcome to LocalLink!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    # For local guides, redirect to become_local page to complete profile
                    return redirect(url_for('become_local'))
            
        except sqlite3.IntegrityError as e:
            flash('Username or email already exists. Please choose different credentials.', 'error')
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user data from database
    conn = sqlite3.connect('local_link.db')
    cursor = conn.cursor()
    
    # Get user stats based on type
    if session['user_type'] == 'student':
        # Get student stats
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE student_id = ?', (session['user_id'],))
        sessions_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_cost) FROM sessions WHERE student_id = ? AND status = "completed"', (session['user_id'],))
        total_spent = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM reviews WHERE student_id = ?', (session['user_id'],))
        reviews_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(duration) FROM sessions WHERE student_id = ? AND status = "completed"', (session['user_id'],))
        hours_learning = cursor.fetchone()[0] or 0
        
        conn.close()
        return render_template('student_dashboard.html', 
                             sessions_count=sessions_count,
                             total_spent=total_spent,
                             reviews_count=reviews_count,
                             hours_learning=hours_learning)
    else:
        # Check if local guide profile exists and is complete
        cursor.execute('SELECT id, city, country, is_verified, verification_status FROM local_guides WHERE user_id = ?', (session['user_id'],))
        local_profile = cursor.fetchone()
        
        if not local_profile:
            conn.close()
            return render_template('become_local.html')
        
        # Check if profile is complete (not just "Not Set" values)
        if local_profile[1] == 'Not Set' or local_profile[2] == 'Not Set':
            conn.close()
            flash('Please complete your local guide profile to start receiving bookings!', 'info')
            return render_template('become_local.html')
        
        # Get local guide stats
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE local_id = ?', (local_profile[0],))
        sessions_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_cost * 0.95) FROM sessions WHERE local_id = ? AND status = "completed"', (local_profile[0],))
        total_earnings = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(rating) FROM reviews WHERE local_id = ?', (local_profile[0],))
        avg_rating = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(duration) FROM sessions WHERE local_id = ? AND status = "completed"', (local_profile[0],))
        hours_helped = cursor.fetchone()[0] or 0
        
        conn.close()
        return render_template('local_dashboard.html',
                             local_profile=local_profile,
                             sessions_count=sessions_count,
                             total_earnings=total_earnings,
                             avg_rating=avg_rating,
                             hours_helped=hours_helped)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))


@app.route('/find-locals')
def find_locals():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('local_link.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT lg.id, u.full_name, lg.city, lg.country, lg.bio, lg.hourly_rate, lg.is_verified, lg.verification_status
        FROM local_guides lg
        JOIN users u ON lg.user_id = u.id
        WHERE lg.city != 'Not Set' AND lg.country != 'Not Set'
        ORDER BY lg.is_verified DESC, lg.created_at DESC
    ''')
    locals = cursor.fetchall()
    conn.close()
    
    return render_template('find_locals.html', locals=locals)

@app.route('/become-local', methods=['GET', 'POST'])
def become_local():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        city = request.form['city']
        country = request.form['country']
        university = request.form.get('university', '')
        employment = request.form.get('employment', '')
        bio = request.form['bio']
        hourly_rate = request.form['hourly_rate']
        
        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        
        # Check if local guide profile already exists
        cursor.execute('SELECT id FROM local_guides WHERE user_id = ?', (session['user_id'],))
        existing_profile = cursor.fetchone()
        
        if existing_profile:
            # Update existing profile
            cursor.execute('''
                UPDATE local_guides 
                SET city = ?, country = ?, university = ?, employment = ?, bio = ?, hourly_rate = ?
                WHERE user_id = ?
            ''', (city, country, university, employment, bio, hourly_rate, session['user_id']))
        else:
            # Create new profile
            cursor.execute('''
                INSERT INTO local_guides (user_id, city, country, university, employment, bio, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], city, country, university, employment, bio, hourly_rate))
        
        conn.commit()
        conn.close()
        
        flash('Local guide profile created! Please complete verification to start receiving bookings.', 'success')
        return redirect(url_for('verification'))
    
    return render_template('become_local.html')

@app.route('/book-session/<int:local_id>', methods=['GET', 'POST'])
def book_session(local_id):
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('local_link.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT lg.id, u.full_name, lg.city, lg.country, lg.hourly_rate
        FROM local_guides lg
        JOIN users u ON lg.user_id = u.id
        WHERE lg.id = ? AND lg.is_verified = 1
    ''', (local_id,))
    local = cursor.fetchone()
    
    if not local:
        flash('Local guide not found', 'error')
        return redirect(url_for('find_locals'))
    
    if request.method == 'POST':
        session_type = request.form['session_type']
        duration = int(request.form['duration'])
        # New pricing: $2 per 2 hours
        total_cost = (duration / 2) * 2
        
        cursor.execute('''
            INSERT INTO sessions (student_id, local_id, session_type, duration, total_cost, scheduled_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], local_id, session_type, duration, total_cost, request.form['scheduled_at']))
        conn.commit()
        conn.close()
        
        flash('Session booked successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    conn.close()
    return render_template('book_session.html', local=local)

@app.route('/verification')
def verification():
    if 'user_id' not in session or session['user_type'] != 'local':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('local_link.db')
    cursor = conn.cursor()
    cursor.execute('SELECT verification_status FROM local_guides WHERE user_id = ?', (session['user_id'],))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return redirect(url_for('become_local'))
    
    return render_template('verification.html', status=result[0])

@app.route('/upload-identity', methods=['POST'])
def upload_identity():
    """Handle identity document upload and verification"""
    if 'user_id' not in session or session['user_type'] != 'local':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        # Check if document file was uploaded
        if 'identity_document' not in request.files:
            flash('Please upload an identity document.', 'error')
            return redirect(url_for('verification'))
        
        document_file = request.files['identity_document']
        
        # Check if file was selected
        if document_file.filename == '':
            flash('Please select an identity document.', 'error')
            return redirect(url_for('verification'))
        
        # Check file type
        if not allowed_file(document_file.filename):
            flash('Invalid file type. Please upload images (PNG, JPG, JPEG, GIF, BMP) or PDF.', 'error')
            return redirect(url_for('verification'))
        
        # Save uploaded file
        document_filename = secure_filename(document_file.filename)
        
        # Add timestamp to avoid filename conflicts
        timestamp = str(int(time.time()))
        document_filename = f"identity_{session['user_id']}_{timestamp}_{document_filename}"
        
        document_path = os.path.join(app.config['UPLOAD_FOLDER'], document_filename)
        document_file.save(document_path)
        
        # Verify document using IDAnalyzer API
        verification_result = verify_document(document_path)
        
        # Clean up uploaded file
        try:
            os.remove(document_path)
        except:
            pass  # Ignore cleanup errors
        
        # Update database with verification result
        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        
        if verification_result['success']:
            # Update verification status based on API decision
            if verification_result['decision'] == 'approve':
                cursor.execute('UPDATE local_guides SET verification_status = ? WHERE user_id = ?', 
                             ('approved', session['user_id']))
                flash('Identity verification successful! Your account has been approved.', 'success')
            else:
                cursor.execute('UPDATE local_guides SET verification_status = ? WHERE user_id = ?', 
                             ('pending', session['user_id']))
                flash('Document uploaded successfully. Manual review in progress.', 'info')
        else:
            flash(f'Verification failed: {verification_result.get("error", "Unknown error")}', 'error')
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('verification'))
        
    except Exception as e:
        flash(f'Error during verification: {str(e)}', 'error')
        return redirect(url_for('verification'))

@app.route('/upload-academic', methods=['POST'])
def upload_academic():
    """Handle academic/employment document upload"""
    if 'user_id' not in session or session['user_type'] != 'local':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        # Check if document file was uploaded
        if 'academic_document' not in request.files:
            flash('Please upload an academic or employment document.', 'error')
            return redirect(url_for('verification'))
        
        document_file = request.files['academic_document']
        
        # Check if file was selected
        if document_file.filename == '':
            flash('Please select an academic or employment document.', 'error')
            return redirect(url_for('verification'))
        
        # Check file type
        if not allowed_file(document_file.filename):
            flash('Invalid file type. Please upload images (PNG, JPG, JPEG, GIF, BMP) or PDF.', 'error')
            return redirect(url_for('verification'))
        
        # Save uploaded file
        document_filename = secure_filename(document_file.filename)
        
        # Add timestamp to avoid filename conflicts
        timestamp = str(int(time.time()))
        document_filename = f"academic_{session['user_id']}_{timestamp}_{document_filename}"
        
        document_path = os.path.join(app.config['UPLOAD_FOLDER'], document_filename)
        document_file.save(document_path)
        
        # For academic documents, we'll just mark as uploaded (no API verification needed)
        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        
        # Update verification status
        cursor.execute('UPDATE local_guides SET verification_status = ? WHERE user_id = ?', 
                      ('pending', session['user_id']))
        
        conn.commit()
        conn.close()
        
        # Clean up uploaded file
        try:
            os.remove(document_path)
        except:
            pass  # Ignore cleanup errors
        
        flash('Academic/Employment document uploaded successfully. Manual review in progress.', 'success')
        return redirect(url_for('verification'))
        
    except Exception as e:
        flash(f'Error uploading document: {str(e)}', 'error')
        return redirect(url_for('verification'))

@app.route('/upload-residence', methods=['POST'])
def upload_residence():
    """Handle residence document upload"""
    if 'user_id' not in session or session['user_type'] != 'local':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        # Check if document file was uploaded
        if 'residence_document' not in request.files:
            flash('Please upload a residence document.', 'error')
            return redirect(url_for('verification'))
        
        document_file = request.files['residence_document']
        
        # Check if file was selected
        if document_file.filename == '':
            flash('Please select a residence document.', 'error')
            return redirect(url_for('verification'))
        
        # Check file type
        if not allowed_file(document_file.filename):
            flash('Invalid file type. Please upload images (PNG, JPG, JPEG, GIF, BMP) or PDF.', 'error')
            return redirect(url_for('verification'))
        
        # Save uploaded file
        document_filename = secure_filename(document_file.filename)
        
        # Add timestamp to avoid filename conflicts
        timestamp = str(int(time.time()))
        document_filename = f"residence_{session['user_id']}_{timestamp}_{document_filename}"
        
        document_path = os.path.join(app.config['UPLOAD_FOLDER'], document_filename)
        document_file.save(document_path)
        
        # For residence documents, we'll just mark as uploaded (no API verification needed)
        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        
        # Update verification status
        cursor.execute('UPDATE local_guides SET verification_status = ? WHERE user_id = ?', 
                      ('pending', session['user_id']))
        
        conn.commit()
        conn.close()
        
        # Clean up uploaded file
        try:
            os.remove(document_path)
        except:
            pass  # Ignore cleanup errors
        
        flash('Residence document uploaded successfully. Manual review in progress.', 'success')
        return redirect(url_for('verification'))
        
    except Exception as e:
        flash(f'Error uploading document: {str(e)}', 'error')
        return redirect(url_for('verification'))

@app.route('/upload-video', methods=['POST'])
def upload_video():
    """Handle introduction video upload"""
    if 'user_id' not in session or session['user_type'] != 'local':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        # Check if video file was uploaded
        if 'intro_video' not in request.files:
            flash('Please upload an introduction video.', 'error')
            return redirect(url_for('verification'))
        
        video_file = request.files['intro_video']
        
        # Check if file was selected
        if video_file.filename == '':
            flash('Please select an introduction video.', 'error')
            return redirect(url_for('verification'))
        
        # Check file type for videos
        allowed_video_extensions = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'}
        if '.' not in video_file.filename or video_file.filename.rsplit('.', 1)[1].lower() not in allowed_video_extensions:
            flash('Invalid file type. Please upload a video file (MP4, AVI, MOV, WMV, FLV, WEBM).', 'error')
            return redirect(url_for('verification'))
        
        # Save uploaded file
        video_filename = secure_filename(video_file.filename)
        
        # Add timestamp to avoid filename conflicts
        timestamp = str(int(time.time()))
        video_filename = f"video_{session['user_id']}_{timestamp}_{video_filename}"
        
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video_file.save(video_path)
        
        # For videos, we'll just mark as uploaded (no API verification needed)
        conn = sqlite3.connect('local_link.db')
        cursor = conn.cursor()
        
        # Update verification status
        cursor.execute('UPDATE local_guides SET verification_status = ? WHERE user_id = ?', 
                      ('pending', session['user_id']))
        
        conn.commit()
        conn.close()
        
        # Clean up uploaded file
        try:
            os.remove(video_path)
        except:
            pass  # Ignore cleanup errors
        
        flash('Introduction video uploaded successfully. Manual review in progress.', 'success')
        return redirect(url_for('verification'))
        
    except Exception as e:
        flash(f'Error uploading video: {str(e)}', 'error')
        return redirect(url_for('verification'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
