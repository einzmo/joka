# app.py

import sys
import os
import secrets
import json
import re
import requests
import hmac
import random
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import io
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_file, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from certificate import generate_certificate, check_subject_completion
from models import db, User, Subject, Lesson, Payment, EmailVerification, PasswordReset, Progress, LoginAttempt
from forms import LoginForm, RegistrationForm, PaymentForm, RequestResetForm, ResetPasswordForm
from paychangu import PayChangu
from email_utils import send_verification_email, send_welcome_email, send_payment_confirmation_email, test_smtp_connection, send_password_reset_code, send_verification_code
def generate_reset_code():
    """Generate 6-digit numeric code"""
    return f"{random.randint(100000, 999999)}"


print("=" * 60)
print("Starting app.py...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in current dir: {os.listdir('.')}")
print("=" * 60)

# Email test mode - set to True to skip actual email sending
EMAIL_TEST_MODE = os.getenv('EMAIL_TEST_MODE', 'False') == 'True'






# Check if .env file exists (though on Render you use environment variables)
if os.path.exists('.env'):
    print("✅ .env file found")
else:
    print("⚠️ .env file not found (this is normal on Render)")

print("\nAttempting imports...")
try:
    print("Importing flask...")
    from flask import Flask
    print("✅ Flask imported")
except Exception as e:
    print(f"❌ Failed to import Flask: {e}")
    sys.exit(1)

try:
    print("Importing models...")
    from models import db, User, Subject, Lesson, Payment, EmailVerification, PasswordReset, Progress
    print("✅ Models imported")
except Exception as e:
    print(f"❌ Failed to import models: {e}")
    sys.exit(1)

try:
    print("Importing forms...")
    from forms import LoginForm, RegistrationForm, PaymentForm, RequestResetForm, ResetPasswordForm
    print("✅ Forms imported")
except Exception as e:
    print(f"❌ Failed to import forms: {e}")
    sys.exit(1)

try:
    print("Importing email_utils...")
    from email_utils import mail, send_verification_email, send_welcome_email, send_payment_confirmation_email, test_smtp_connection, send_password_reset_code
    print("✅ Email utils imported")
except Exception as e:
    print(f"❌ Failed to import email_utils: {e}")
    sys.exit(1)

try:
    print("Importing paychangu...")
    from paychangu import PayChangu
    print("✅ PayChangu imported")
except Exception as e:
    print(f"❌ Failed to import paychangu: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
print("=" * 60)


# Import test settings
try:
    from test_settings import TEST_MODE, TEST_PRICES
except ImportError:
    TEST_MODE = False
    TEST_PRICES = {}

def flash_message(message, category='info'):
    """Flash a message that will appear as a toast notification"""
    flash(message, category)




load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Cloudinary integration (optional - app works without it)
try:
    from cloudinary_utils import CloudinaryService
    CLOUDINARY_AVAILABLE = True
    print("✅ Cloudinary module loaded")
except ImportError as e:
    CLOUDINARY_AVAILABLE = False
    print(f"⚠️ Cloudinary not available: {e}")
    CloudinaryService = None


# Initialize Cloudinary (only if available and configured)
cloudinary_service = None
if CLOUDINARY_AVAILABLE and CloudinaryService:
    try:
        cloudinary_service = CloudinaryService(app)  # Pass app to constructor
        if cloudinary_service.available:
            print("✅ Cloudinary service ready")
    except Exception as e:
        print(f"⚠️ Failed to initialize Cloudinary: {e}")
        cloudinary_service = None

# File upload configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['ALLOWED_EXTENSIONS'] = {
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv',  # Video
    'mp3', 'wav', 'ogg', 'm4a',                 # Audio
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt',  # Documents
    'jpg', 'jpeg', 'png', 'gif'                  # Images
}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Session configuration
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

# Database configuration
database_url = os.getenv('DATABASE_URL', 'sqlite:///mymsce.db')

# Fix for Render's PostgreSQL (postgres:// -> postgresql://)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Only add SSL and connection pool settings for PostgreSQL
if 'postgresql' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 5,
        'connect_args': {
            'sslmode': 'require',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
        }
    }
else:
    # For SQLite, use simple options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 1,
        'pool_recycle': 300,
        'pool_pre_ping': True
    }




# Email config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'myMSCE <noreply@mymsce.com>')
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# PayChangu config
app.config['PAYCHANGU_PUBLIC_KEY'] = os.getenv('PAYCHANGU_PUBLIC_KEY')
app.config['PAYCHANGU_SECRET_KEY'] = os.getenv('PAYCHANGU_SECRET_KEY')
app.config['PAYCHANGU_WEBHOOK_SECRET'] = os.getenv('PAYCHANGU_WEBHOOK_SECRET')
app.config['PAYCHANGU_MODE'] = os.getenv('PAYCHANGU_MODE', 'sandbox')
# Site URL for emails and webhooks
app.config['SITE_URL'] = os.getenv('SITE_URL', 'https://mymsce3.onrender.com').rstrip('/')


# Initialize extensions
db.init_app(app)
#mail.init_app(app)
from flask_migrate import Migrate
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# At the top of app.py with other imports
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# After app = Flask(__name__) and db.init_app(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)



def get_user_analytics(user_id):
    """Get comprehensive analytics for a user"""
    
    # Get all progress entries
    progress_entries = Progress.query.filter_by(user_id=user_id).all()
    
    # Total lessons watched (any progress)
    total_started = len(progress_entries)
    
    # Completed lessons (watched 90%+)
    completed_count = sum(1 for p in progress_entries if p.completed)
    
    # Total watch time in seconds
    total_seconds = sum(p.watch_time for p in progress_entries)
    total_hours = round(total_seconds / 3600, 1)
    
    # Average completion rate
    avg_completion = 0
    if total_started > 0:
        avg_completion = round((completed_count / total_started) * 100, 1)
    
    # Current streak (consecutive days with activity)
    streak = calculate_streak(user_id)
    
    # Subject breakdown
    subject_stats = get_subject_analytics(user_id)
    
    # Daily activity (last 7 days)
    daily_activity = get_daily_activity(user_id, days=7)
    
    return {
        'total_started': total_started,
        'completed_count': completed_count,
        'total_hours': total_hours,
        'avg_completion': avg_completion,
        'streak': streak,
        'subject_stats': subject_stats,
        'daily_activity': daily_activity
    }


def calculate_streak(user_id):
    """Calculate current learning streak"""
    from datetime import date, timedelta
    
    # Get all unique dates where user had activity
    result = db.session.query(
        db.func.date(Progress.last_watched)
    ).filter(
        Progress.user_id == user_id,
        Progress.watch_time > 0
    ).distinct().order_by(db.func.date(Progress.last_watched).desc()).all()
    
    if not result:
        return 0
    
    dates = [r[0] for r in result]
    today = date.today()
    
    streak = 0
    check_date = today
    
    while check_date in dates:
        streak += 1
        check_date -= timedelta(days=1)
    
    return streak


def get_subject_analytics(user_id):
    """Get progress breakdown by subject"""
    subjects = Subject.query.all()
    result = []
    
    for subject in subjects:
        lessons = Lesson.query.filter_by(subject_id=subject.id).all()
        lesson_ids = [l.id for l in lessons]
        
        if not lesson_ids:
            continue
        
        # Get progress for all lessons in this subject
        progresses = Progress.query.filter(
            Progress.user_id == user_id,
            Progress.lesson_id.in_(lesson_ids)
        ).all()
        
        completed = sum(1 for p in progresses if p.completed)
        total_watch = sum(p.watch_time for p in progresses)
        
        result.append({
            'id': subject.id,
            'name': subject.name,
            'icon': subject.icon or 'book',
            'total_lessons': len(lesson_ids),
            'completed': completed,
            'progress': round((completed / len(lesson_ids)) * 100, 1) if lesson_ids else 0,
            'watch_time_hours': round(total_watch / 3600, 1)
        })
    
    return sorted(result, key=lambda x: x['progress'], reverse=True)


def get_daily_activity(user_id, days=7):
    """Get daily watch time for last N days"""
    from datetime import date, timedelta
    
    activity = []
    for i in range(days - 1, -1, -1):
        day = date.today() - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        
        total = db.session.query(db.func.sum(Progress.watch_time)).filter(
            Progress.user_id == user_id,
            Progress.last_watched >= day_start,
            Progress.last_watched < day_end
        ).scalar() or 0
        
        activity.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%d %b'),
            'minutes': round(total / 60, 1),
            'has_activity': total > 0
        })
    
    return activity


@app.context_processor
def inject_site_url():
    """Make SITE_URL available in all templates"""
    return dict(site_url=app.config['SITE_URL'])



@app.after_request
def add_no_cache_headers(response):
    """Prevent caching of all pages"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.after_request
def security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Only add HSTS in production (HTTPS)
    if app.config.get('ENV') == 'production' or request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

@app.route('/test-email-debug')
@login_required
def test_email_debug():
    if not current_user.is_admin:
        return "Admin only", 403

    from email_utils import test_smtp_connection
    success, message = test_smtp_connection()

    return f"""
    <h1>Email Test Result</h1>
    <p>Success: {success}</p>
    <p>Message: {message}</p>
    <p>Config:</p>
    <ul>
        <li>MAIL_SERVER: {app.config.get('MAIL_SERVER')}</li>
        <li>MAIL_PORT: {app.config.get('MAIL_PORT')}</li>
        <li>MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}</li>
        <li>MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}</li>
        <li>MAIL_PASSWORD: {'*' * 8 if app.config.get('MAIL_PASSWORD') else 'NOT SET'}</li>
        <li>SITE_URL: {app.config.get('SITE_URL')}</li>
    </ul>
    """



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables and default data
with app.app_context():
    db.create_all()

    # Create admin if not exists
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@mymsce.com')
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            username='admin',
            email=admin_email,
            is_admin=True,
            is_verified=True,
            email_verified=True
        )
        admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
        db.session.add(admin)
        db.session.commit()

        # Create sample subjects
        subjects = [
            Subject(name='Mathematics', form=3, description='Form 3 Mathematics', icon='calculator'),
            Subject(name='Physics', form=3, description='Form 3 Physics', icon='flask'),
            Subject(name='Chemistry', form=3, description='Form 3 Chemistry', icon='beaker'),
            Subject(name='Mathematics', form=4, description='Form 4 Mathematics', icon='calculator'),
            Subject(name='Physics', form=4, description='Form 4 Physics', icon='flask'),
            Subject(name='Chemistry', form=4, description='Form 4 Chemistry', icon='beaker'),
            Subject(name='Biology', form=4, description='Form 4 Biology', icon='leaf'),
        ]
        for subject in subjects:
            db.session.add(subject)
        db.session.commit()


# Helper function for YouTube ID extraction
def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)',
        r'^([a-zA-Z0-9_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
#@limiter.limit("3 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('login'))
        
        # Check if username already exists
        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash('Username already taken. Please choose another.', 'danger')
            return redirect(url_for('register'))

        # Create user - NOT verified yet
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            email_verified=False,
            is_verified=False
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
            
            # Generate 6-digit verification code
            code = generate_reset_code()
            
            # Store in database
            verification = EmailVerification(
                user_id=user.id,
                code=code,
                expires_at=datetime.utcnow() + timedelta(minutes=15)
            )
            db.session.add(verification)
            db.session.commit()
            
            # Send code via email
            send_verification_code(user, code)
            
            # Store user_id in session for verification step
            session['verify_user_id'] = user.id
            
            flash('A verification code has been sent to your email.', 'info')
            return redirect(url_for('verify_email_code'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Database error: {str(e)}")
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html', form=form)

@app.route('/verify-email-code', methods=['GET', 'POST'])
def verify_email_code():
    """Verify email with 6-digit code"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user_id = session.get('verify_user_id')
    if not user_id:
        flash('Please register first.', 'warning')
        return redirect(url_for('register'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        # Find valid verification entry
        verification = EmailVerification.query.filter_by(
            user_id=user_id,
            code=code,
            used=False
        ).first()
        
        if not verification or verification.expires_at < datetime.utcnow():
            flash('Invalid or expired verification code.', 'danger')
            return redirect(url_for('register'))
        
        # Mark as used and verify user
        verification.used = True
        user.email_verified = True
        user.is_verified = True
        db.session.commit()
        
        # Clear session
        session.pop('verify_user_id', None)
        
        # Send welcome email
        send_welcome_email(user)
        
        flash('Email verified successfully! You can now login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('verify_email_code.html', email=user.email)

@app.route('/resend-verification-code')
def resend_verification_code():
    """Resend verification code"""
    user_id = session.get('verify_user_id')
    if not user_id:
        flash('Please register first.', 'warning')
        return redirect(url_for('register'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('register'))
    
    # Generate new code
    code = generate_reset_code()
    
    # Delete old unused codes
    EmailVerification.query.filter_by(user_id=user_id, used=False).delete()
    
    # Store new code
    verification = EmailVerification(
        user_id=user_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.session.add(verification)
    db.session.commit()
    
    # Send new code
    send_verification_code(user, code)
    
    flash('A new verification code has been sent to your email.', 'info')
    return redirect(url_for('verify_email_code'))


@app.route('/test-email-send')
def test_email_send():
    """Test email sending - remove after testing"""
    try:
        from flask_mail import Message
        msg = Message(
            subject="Test Email from myMSCE",
            sender=app.config['MAIL_DEFAULT_SENDER'],

            recipients=["your-test-email@gmail.com"],  # Change this
            body="This is a test email from your myMSCE application."
        )
        mail.send(msg)
        return "Email sent successfully! Check your inbox."
    except Exception as e:
        return f"Email failed: {str(e)}"


@app.route('/verify-email/<token>')
def verify_email(token):
    from email_utils import confirm_token

    email = confirm_token(token)
    if not email:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if user and not user.email_verified:
        user.email_verified = True
        user.is_verified = True
        db.session.commit()

        send_welcome_email(user)
        flash('Your email has been verified! You can now login.', 'success')
    else:
        flash('Email already verified or invalid.', 'info')

    return redirect(url_for('login'))



@app.route('/login', methods=['GET', 'POST'])
#@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    
    # Check for too many failed attempts
    client_ip = request.remote_addr
    failed_attempts = LoginAttempt.query.filter(
        LoginAttempt.ip_address == client_ip,
        LoginAttempt.success == False,
        LoginAttempt.attempted_at >= datetime.utcnow() - timedelta(minutes=15)
    ).count()
    
    if failed_attempts >= 5:
        flash('Too many failed attempts. Please try again later.', 'danger')
        return render_template('login.html', form=LoginForm())
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            if not user.email_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('login'))
            
            login_user(user, remember=form.remember.data)
            
            # Log successful attempt
            attempt = LoginAttempt(email=form.email.data, ip_address=client_ip, success=True)
            db.session.add(attempt)
            db.session.commit()
            
            if user.is_admin:
                flash(f'Welcome back Admin {user.username}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'Welcome back {user.username}!', 'success')
                return redirect(url_for('dashboard'))
        else:
            # Log failed attempt
            attempt = LoginAttempt(email=form.email.data, ip_address=client_ip, success=False)
            db.session.add(attempt)
            db.session.commit()
            
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    username = current_user.username
    was_admin = current_user.is_admin

    print(f"🔓 Logging out user: {username} (admin: {was_admin})")

    # ✅ Store flash message BEFORE clearing session
    flash('You have been successfully logged out.', 'success')

    # Logout user
    logout_user()

    # Clear session (flash survives because Flask saves it)
    session.clear()
    session.permanent = False

    # Create response
    response = redirect(url_for('index'))
    response.delete_cookie('session')

    # Add cache control
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    print(f"✅ Logout complete for {username}")

    return response


@app.route('/forgot-password', methods=['GET', 'POST'])
#@limiter.limit("3 per minute")
def forgot_password():
    """Step 1: Request password reset code"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate 6-digit code
            code = generate_reset_code()
            
            # Delete any existing unused codes for this user
            PasswordReset.query.filter_by(user_id=user.id, used=False).delete()
            
            # Store new code
            reset = PasswordReset(
                user_id=user.id,
                code=code,
                expires_at=datetime.utcnow() + timedelta(minutes=15)
            )
            db.session.add(reset)
            db.session.commit()
            
            # Send code via email
            send_password_reset_code(user, code)
            flash('A verification code has been sent to your email.', 'info')
            
            # Store user_id in session for next step
            session['reset_user_id'] = user.id
            return redirect(url_for('verify_reset_code'))
        else:
            # Don't reveal if email exists (security)
            flash('If an account exists with that email, you will receive a reset code.', 'info')
            return redirect(url_for('login'))
    
    return render_template('forgot_password.html')


@app.route('/verify-reset-code', methods=['GET', 'POST'])
def verify_reset_code():
    """Step 2: Verify the 6-digit code"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('Please request a password reset first.', 'warning')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        # Find valid reset entry
        reset = PasswordReset.query.filter_by(
            user_id=user_id,
            code=code,
            used=False
        ).first()
        
        if not reset or reset.expires_at < datetime.utcnow():
            flash('Invalid or expired verification code.', 'danger')
            return redirect(url_for('forgot_password'))
        
        # Mark as used and redirect to set new password
        reset.used = True
        db.session.commit()
        
        session['reset_verified'] = True
        flash('Code verified. Please enter your new password.', 'success')
        return redirect(url_for('set_new_password'))
    
    return render_template('verify_reset_code.html')


@app.route('/set-new-password', methods=['GET', 'POST'])
def set_new_password():
    """Step 3: Set new password"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if not session.get('reset_verified'):
        flash('Please verify your code first.', 'warning')
        return redirect(url_for('forgot_password'))
    
    user_id = session.get('reset_user_id')
    if not user_id:
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            user = User.query.get(user_id)
            user.set_password(password)
            db.session.commit()
            
            # Clear session
            session.pop('reset_user_id', None)
            session.pop('reset_verified', None)
            
            flash('Your password has been reset! You can now login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('set_new_password.html')



@app.route('/dashboard')
@login_required
def dashboard():
    from flask import make_response
    
    user = User.query.get(current_user.id)
    
    if user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    if not user.email_verified:
        return redirect(url_for('verify_email_reminder'))
    
    # Get subjects with serializable data
    subjects_form3 = Subject.query.filter_by(form=3).order_by(Subject.order).all()
    subjects_form4 = Subject.query.filter_by(form=4).order_by(Subject.order).all()
    
    # Convert subjects to serializable format for JSON
    subjects_form3_serializable = []
    for subject in subjects_form3:
        subjects_form3_serializable.append({
            'id': subject.id,
            'name': subject.name,
            'form': subject.form,
            'description': subject.description,
            'icon': subject.icon,
            'order': subject.order,
            'lesson_count': Lesson.query.filter_by(subject_id=subject.id).count()
        })
    
    subjects_form4_serializable = []
    for subject in subjects_form4:
        subjects_form4_serializable.append({
            'id': subject.id,
            'name': subject.name,
            'form': subject.form,
            'description': subject.description,
            'icon': subject.icon,
            'order': subject.order,
            'lesson_count': Lesson.query.filter_by(subject_id=subject.id).count()
        })
    
    total_lessons = Lesson.query.count()
    
    # Get user's progress
    recent_progress = Progress.query.filter_by(
        user_id=user.id
    ).order_by(Progress.last_watched.desc()).limit(5).all()
    
    recent_lessons = []
    for prog in recent_progress:
        lesson = Lesson.query.get(prog.lesson_id)
        if lesson:
            if lesson.duration and lesson.duration > 0:
                total_seconds = lesson.duration * 60
                watch_time = min(prog.watch_time, total_seconds)
                progress_percent = min(100, int((watch_time / total_seconds) * 100))
            else:
                progress_percent = 50 if prog.watch_time > 0 else 0
            
            recent_lessons.append({
                'id': lesson.id,
                'title': lesson.title,
                'duration': lesson.duration,
                'content_type': lesson.content_type,
                'subject': {'id': lesson.subject.id, 'name': lesson.subject.name},
                'progress': progress_percent,
                'completed': prog.completed,
                'watch_time': prog.watch_time,
                'last_watched': prog.last_watched.isoformat() if prog.last_watched else None
            })
        
        # Get continue watching lessons (recently watched but not completed)
    continue_watching = []
    for prog in recent_progress[:10]:  # Get last 10 recent
        lesson = Lesson.query.get(prog.lesson_id)
        if lesson and not prog.completed:  # Only show incomplete lessons
            if lesson.duration and lesson.duration > 0:
                total_seconds = lesson.duration * 60
                progress_percent = min(100, int((prog.watch_time / total_seconds) * 100))
            else:
                progress_percent = 50 if prog.watch_time > 0 else 0
            
            continue_watching.append({
                'id': lesson.id,
                'title': lesson.title,
                'duration': lesson.duration,
                'content_type': lesson.content_type,
                'subject': lesson.subject.name,
                'subject_icon': lesson.subject.icon or 'book',
                'progress': progress_percent,
                'watch_time': prog.watch_time,
                'last_watched': prog.last_watched
            })
    
    
    completed_lessons = Progress.query.filter_by(
        user_id=user.id,
        completed=True
    ).count()
    
    sample_lessons = Lesson.query.filter_by(is_free=True).order_by(Lesson.created_at.desc()).limit(3).all()
    sample_lessons_serializable = []
    for lesson in sample_lessons:
        sample_lessons_serializable.append({
            'id': lesson.id,
            'title': lesson.title,
            'duration': lesson.duration,
            'subject': {'id': lesson.subject.id, 'name': lesson.subject.name}
        })
    
    # In dashboard route, add:
    analytics = get_user_analytics(user.id)
    
    # Subscription info
    subscription_info = {
        'is_active': user.is_active_subscriber,
        'form': user.subscription_form if user.is_active_subscriber else None,
        'type': user.subscription_type if user.is_active_subscriber else None,
        'days_left': user.get_subscription_days_left() if user.is_active_subscriber else 0,
        'expiry': user.subscription_expiry.strftime('%d %B %Y') if user.is_active_subscriber and user.subscription_expiry else None
    }
    
    response = make_response(render_template('dashboard.html',
        user=user,
        subscription_info=subscription_info,
        subjects_form3=subjects_form3_serializable,
        subjects_form4=subjects_form4_serializable,
        subjects_form3_objects=subjects_form3,  # For template rendering
        subjects_form4_objects=subjects_form4,
        total_lessons=total_lessons,
        continue_watching=continue_watching, 
        completed_lessons=completed_lessons,
        recent_lessons=recent_lessons,
        
        sample_lessons=sample_lessons_serializable,
        sample_lessons_objects=sample_lessons,
        now=datetime.utcnow()
    ))
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/debug-smtp')
def debug_smtp():
    """Debug SMTP connection"""
    import smtplib
    import socket

    results = []

    # Test 1: Check if we can connect to Gmail SMTP
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        results.append("✅ Connected to smtp.gmail.com:587")

        # Test 2: Test STARTTLS
        server.starttls()
        results.append("✅ STARTTLS successful")

        # Test 3: Try to login
        username = app.config.get('MAIL_USERNAME')
        password = app.config.get('MAIL_PASSWORD')

        if username and password:
            try:
                server.login(username, password)
                results.append(f"✅ Login successful for {username}")
            except smtplib.SMTPAuthenticationError as e:
                results.append(f"❌ Authentication failed: {str(e)}")
        else:
            results.append("❌ MAIL_USERNAME or MAIL_PASSWORD not set")

        server.quit()

    except socket.timeout:
        results.append("❌ Connection timeout to smtp.gmail.com:587")
    except Exception as e:
        results.append(f"❌ Error: {str(e)}")

    # Show current config
    results.append("\n📧 Current Email Configuration:")
    results.append(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    results.append(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
    results.append(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
    results.append(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
    results.append(f"MAIL_PASSWORD: {'*' * 8 if app.config.get('MAIL_PASSWORD') else 'NOT SET'}")
    results.append(f"SITE_URL: {app.config.get('SITE_URL')}")

    return "<br>".join(results)



@app.route('/admin/upload-video/<int:lesson_id>')
@login_required
def admin_upload_video_page(lesson_id):
    """Dedicated video upload page"""
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    return render_template('admin/upload_video.html', lesson=lesson)

@app.route('/admin/upload-cloudinary-video', methods=['POST'])
@login_required
def admin_upload_cloudinary_video():
    """Upload video to Cloudinary and attach to lesson"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    print("=" * 50)
    print("📤 UPLOAD REQUEST RECEIVED")
    print(f"Files: {request.files}")
    print(f"Form: {request.form}")
    
    lesson_id = request.form.get('lesson_id')
    video_file = request.files.get('video')
    
    if not lesson_id:
        print("❌ Missing lesson_id")
        return jsonify({'error': 'Missing lesson ID'}), 400
    
    if not video_file:
        print("❌ Missing video file")
        return jsonify({'error': 'Missing video file'}), 400
    
    print(f"✅ Lesson ID: {lesson_id}")
    print(f"✅ Video file: {video_file.filename}")
    
    try:
        lesson = Lesson.query.get_or_404(lesson_id)
        print(f"✅ Lesson found: {lesson.title}")
    except Exception as e:
        print(f"❌ Lesson not found: {e}")
        return jsonify({'error': 'Lesson not found'}), 404
    
    # Check Cloudinary availability
    if not cloudinary_service or not cloudinary_service.available:
        print("❌ Cloudinary not available")
        return jsonify({'error': 'Cloudinary service not configured'}), 500
    
    print("📤 Uploading to Cloudinary...")
    
    # Upload to Cloudinary
    result = cloudinary_service.upload_video(
        video_file,
        tags=[f'lesson_{lesson.id}', lesson.subject.name if lesson.subject else 'general'],
        public_id=f"mymsce_lessons/lesson_{lesson.id}_{int(datetime.utcnow().timestamp())}"
    )
    
    print(f"📦 Upload result: {result}")
    
    if result.get('success'):
        # Update lesson
        lesson.cloudinary_public_id = result['public_id']
        lesson.cloudinary_url = result['url']
        lesson.cloudinary_resource_type = 'video'
        lesson.is_private = True
        lesson.duration = int(result.get('duration', 0)) // 60
        lesson.content_type = 'video'
        db.session.commit()
        
        print("✅ Database updated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Video uploaded successfully',
            'public_id': result['public_id'],
            'url': result['url'],
            'duration': result['duration']
        })
    else:
        error_msg = result.get('error', 'Unknown error')
        print(f"❌ Upload failed: {error_msg}")
        return jsonify({'error': error_msg}), 500
 
    
@app.route('/admin/upload-cloudinary-file', methods=['POST'])
@login_required
def admin_upload_cloudinary_file():
    """Upload any file to Cloudinary"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    lesson_id = request.form.get('lesson_id')
    content_type = request.form.get('content_type')
    file = request.files.get('file')
    
    if not lesson_id or not file:
        return jsonify({'error': 'Missing lesson ID or file'}), 400
    
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Determine resource type
    if content_type == 'video':
        resource_type = 'video'
    elif content_type == 'audio':
        resource_type = 'video'
    else:
        resource_type = 'raw'
    
    # Save file temporarily
    temp_path = f"temp_{datetime.utcnow().timestamp()}"
    file.save(temp_path)
    
    try:
        import cloudinary.uploader
        
        result = cloudinary.uploader.upload(
            temp_path,
            resource_type=resource_type,
            folder='mymsce_lessons',
            use_filename=True,
            unique_filename=True
        )
        
        # Update lesson
        lesson.cloudinary_public_id = result['public_id']
        lesson.cloudinary_url = result['secure_url']
        lesson.file_name = file.filename  # Store original filename
        lesson.file_size = result.get('bytes', 0)
        lesson.file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else None
        lesson.content_type = content_type
        
        if content_type == 'video' or content_type == 'audio':
            lesson.duration = int(result.get('duration', 0)) // 60
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{content_type.capitalize()} uploaded successfully',
            'public_id': result['public_id'],
            'url': result['secure_url'],
            'filename': file.filename
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/subjects/<int:form>')
@login_required
def subjects_by_form(form):
    """Show subjects for a specific form (3 or 4)"""
    if form not in [3, 4]:
        flash('Invalid form selected', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if user has access to this form
    if not current_user.has_access(form) and not current_user.is_admin:
        flash(f'Please subscribe to access Form {form} content.', 'warning')
        return redirect(url_for('pricing'))
    
    subjects = Subject.query.filter_by(form=form).order_by(Subject.order).all()
    
    # Get lesson counts for each subject
    for subject in subjects:
        subject.lesson_count = Lesson.query.filter_by(subject_id=subject.id).count()
    
    return render_template('subjects.html', 
                         subjects=subjects, 
                         form=form,
                         form_name=f'Form {form}')
    
 
 # ==================== CERTIFICATE FUNCTIONS ====================
 
def check_subject_completion(user_id, subject_id):
    """Check if user has completed all lessons in a subject"""
    lessons = Lesson.query.filter_by(subject_id=subject_id).all()
    if not lessons:
        return False, 0, 0, 0
    
    total_lessons = len(lessons)
    completed_lessons = 0
    total_watch_time = 0
    
    for lesson in lessons:
        progress = Progress.query.filter_by(
            user_id=user_id,
            lesson_id=lesson.id
        ).first()
        
        if progress and progress.completed:
            completed_lessons += 1
        if progress:
            total_watch_time += progress.watch_time
    
    is_completed = completed_lessons == total_lessons
    
    return is_completed, completed_lessons, total_lessons, total_watch_time

def generate_certificate_pdf(user, subject, completion_data):
    """Generate professional PDF certificate with Blue/Green/Orange theme"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    import io
    from datetime import datetime
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # ===== COLOR DEFINITIONS =====
    primary_blue = HexColor('#2563EB')
    secondary_green = HexColor('#16A34A')
    accent_orange = HexColor('#F59E0B')
    gray_text = HexColor('#475569')
    white = HexColor('#FFFFFF')
    
    # ===== BACKGROUND =====
    c.setFillColor(HexColor('#EFF6FF'))
    c.rect(0, 0, width, height, fill=1)
    
    # ===== DECORATIVE BORDERS =====
    c.setStrokeColor(primary_blue)
    c.setLineWidth(6)
    c.rect(15, 15, width - 30, height - 30)
    
    c.setStrokeColor(secondary_green)
    c.setLineWidth(2)
    c.rect(25, 25, width - 50, height - 50)
    
    c.setStrokeColor(accent_orange)
    c.setLineWidth(1)
    c.rect(35, 35, width - 70, height - 70)
    
    # ===== INSTITUTION SEAL =====
    c.setFillColor(primary_blue)
    c.circle(width/2, height - 130, 45, fill=1)
    c.setFillColor(white)
    c.circle(width/2, height - 130, 38, fill=1)
    c.setFillColor(primary_blue)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, height - 140, "M")
    
    # ===== TITLE =====
    c.setFillColor(primary_blue)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 210, "CERTIFICATE OF COMPLETION")
    
    # ===== PRESENTATION =====
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height - 255, "This certificate is proudly presented to")
    
    # ===== USER NAME =====
    c.setFillColor(accent_orange)
    c.setFont("Helvetica-Bold", 32)
    name = user.username.upper() if user.username else "VALUED STUDENT"
    if len(name) > 35:
        name = name[:32] + "..."
    c.drawCentredString(width/2, height - 305, name)
    
    # ===== COURSE INFO =====
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height - 345, "for successfully completing")
    
    c.setFillColor(primary_blue)
    c.setFont("Helvetica-Bold", 20)
    course_name = f"{subject.name} - Form {subject.form}"
    if len(course_name) > 45:
        course_name = course_name[:42] + "..."
    c.drawCentredString(width/2, height - 380, course_name)
    
    # ===== COMPLETION DATE =====
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 11)
    completion_date = completion_data['completion_date'].strftime('%d %B %Y')
    c.drawCentredString(width/2, height - 420, f"Completed on {completion_date}")
    
    # ===== STATISTICS =====
    stats_y = height - 470
    c.setFillColor(HexColor('#F8FAFC'))
    c.roundRect(width/4 - 20, stats_y - 5, width/2 + 40, 70, 10, fill=1, stroke=0)
    
    c.setFillColor(primary_blue)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(width/3 - 30, stats_y + 15, "📚 Lessons Completed:")
    c.setFillColor(secondary_green)
    c.drawString(width/3 + 120, stats_y + 15, f"{completion_data['completed_lessons']} / {completion_data['total_lessons']}")
    
    c.setFillColor(primary_blue)
    c.drawString(width/3 - 30, stats_y - 5, "⏱️ Total Study Time:")
    c.setFillColor(secondary_green)
    c.drawString(width/3 + 120, stats_y - 5, f"{completion_data['total_hours']} hours")
    
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 8)
    c.drawString(width/3 - 30, stats_y - 25, f"Certificate ID: {completion_data['certificate_id']}")
    
    # ===== SIGNATURES =====
    signature_y = 90
    c.setStrokeColor(gray_text)
    c.setLineWidth(1)
    c.line(width * 0.2, signature_y, width * 0.35, signature_y)
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width * 0.275, signature_y - 15, "Student Signature")
    
    c.line(width * 0.55, signature_y, width * 0.70, signature_y)
    c.drawCentredString(width * 0.625, signature_y - 15, "Academic Director")
    
    # ===== FOOTER =====
    c.setFillColor(HexColor('#94A3B8'))
    c.setFont("Helvetica", 7)
    c.drawCentredString(width/2, 25, "myMSCE - Malawi's #1 MSCE Tutoring Platform")
    c.drawCentredString(width/2, 15, f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    c.save()
    buffer.seek(0)
    return buffer



@app.route('/certificate/subject/<int:subject_id>')
@login_required
def view_certificate(subject_id):
    """View certificate page for a subject"""
    subject = Subject.query.get_or_404(subject_id)
    
    # Check if user has completed all lessons
    is_completed, completed, total, watch_time = check_subject_completion(current_user.id, subject_id)
    
    if not is_completed:
        flash(f'You need to complete all lessons in {subject.name} to get a certificate.', 'warning')
        return redirect(url_for('view_subject', subject_id=subject_id))
    
    completion_data = {
        'completed_lessons': completed,
        'total_lessons': total,
        'total_hours': round(watch_time / 3600, 1),
        'completion_date': datetime.utcnow(),
        'certificate_id': f"MSCE-{subject_id}-{current_user.id}-{datetime.utcnow().strftime('%Y%m%d')}"
    }
    
    return render_template('certificate.html', 
                         subject=subject, 
                         completion_data=completion_data,
                         user=current_user)

@app.route('/certificate/download/<int:subject_id>')
@login_required
def download_certificate(subject_id):
    """Download PDF certificate"""
    subject = Subject.query.get_or_404(subject_id)
    
    # Check if user has completed all lessons
    is_completed, completed, total, watch_time = check_subject_completion(current_user.id, subject_id)
    
    if not is_completed:
        flash('Complete all lessons first!', 'danger')
        return redirect(url_for('view_subject', subject_id=subject_id))
    
    completion_data = {
        'completed_lessons': completed,
        'total_lessons': total,
        'total_hours': round(watch_time / 3600, 1),
        'completion_date': datetime.utcnow(),
        'certificate_id': f"MSCE-{subject_id}-{current_user.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    }
    
    pdf_buffer = generate_certificate_pdf(current_user, subject, completion_data)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"certificate_{subject.name}_{current_user.username}.pdf",
        mimetype='application/pdf'
    )
    
 # ==================== ADMIN ANALYTICS FUNCTIONS ====================

def get_user_growth_data(days=30):
    """Get user registration growth data for the last N days"""
    from datetime import date, timedelta
    
    data = []
    for i in range(days - 1, -1, -1):
        day = date.today() - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        
        count = User.query.filter(
            User.created_at >= day_start,
            User.created_at < day_end
        ).count()
        
        data.append({
            'date': day.strftime('%d %b'),
            'count': count
        })
    
    return data


def get_lesson_analytics():
    """Get lesson completion analytics"""
    total_lessons = Lesson.query.count()
    total_lessons_with_progress = Progress.query.filter(Progress.watch_time > 0).distinct(Progress.lesson_id).count()
    total_completions = Progress.query.filter_by(completed=True).count()
    
    # Most popular lessons (most views)
    popular_lessons = Lesson.query.order_by(Lesson.access_count.desc()).limit(5).all()
    popular_data = []
    for lesson in popular_lessons:
        popular_data.append({
            'title': lesson.title,
            'views': lesson.access_count or 0,
            'subject': lesson.subject.name
        })
    
    return {
        'total_lessons': total_lessons,
        'lessons_started': total_lessons_with_progress,
        'total_completions': total_completions,
        'popular_lessons': popular_data
    }


def get_payment_analytics():
    """Get payment analytics"""
    from datetime import date, timedelta
    
    # Total revenue
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    
    # Revenue by subscription type
    revenue_by_type = db.session.query(
        Payment.subscription_type,
        db.func.sum(Payment.amount)
    ).filter_by(status='completed').group_by(Payment.subscription_type).all()
    
    revenue_by_type_data = []
    for sub_type, amount in revenue_by_type:
        revenue_by_type_data.append({
            'type': sub_type,
            'amount': float(amount or 0)
        })
    
    # Conversion rate (users who subscribed vs total users)
    total_users = User.query.count()
    subscribers = User.query.filter_by(is_active_subscriber=True).count()
    conversion_rate = round((subscribers / total_users) * 100, 1) if total_users > 0 else 0
    
    # Average revenue per user
    avg_revenue = round(total_revenue / total_users, 2) if total_users > 0 else 0
    
    return {
        'total_revenue': total_revenue,
        'conversion_rate': conversion_rate,
        'avg_revenue_per_user': avg_revenue,
        'revenue_by_type': revenue_by_type_data
    }


def get_daily_activity_analytics(days=7):
    """Get daily user activity"""
    from datetime import date, timedelta
    
    activity = []
    for i in range(days - 1, -1, -1):
        day = date.today() - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        
        # Active users (any progress on that day)
        active_users = db.session.query(Progress.user_id).filter(
            Progress.last_watched >= day_start,
            Progress.last_watched < day_end
        ).distinct().count()
        
        # Total watch time that day
        watch_time = db.session.query(db.func.sum(Progress.watch_time)).filter(
            Progress.last_watched >= day_start,
            Progress.last_watched < day_end
        ).scalar() or 0
        
        activity.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%d %b'),
            'active_users': active_users,
            'watch_time_hours': round(watch_time / 3600, 1)
        })
    
    return activity

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all analytics data
    user_growth = get_user_growth_data(30)
    lesson_stats = get_lesson_analytics()
    payment_stats = get_payment_analytics()
    daily_activity = get_daily_activity_analytics(7)
    
    # Get top performing subjects
    subjects = Subject.query.all()
    subject_stats = []
    for subject in subjects:
        lesson_count = Lesson.query.filter_by(subject_id=subject.id).count()
        completions = db.session.query(Progress).join(Lesson).filter(
            Lesson.subject_id == subject.id,
            Progress.completed == True
        ).count()
        
        subject_stats.append({
            'name': subject.name,
            'form': subject.form,
            'lessons': lesson_count,
            'completions': completions
        })
    
    return render_template('admin/analytics.html',
                         user_growth=user_growth,
                         lesson_stats=lesson_stats,
                         payment_stats=payment_stats,
                         daily_activity=daily_activity,
                         subject_stats=subject_stats)
 
 
@app.route('/debug-cloudinary')
@login_required
def debug_cloudinary():
    if not current_user.is_admin:
        return "Unauthorized", 403
    
    # Test Cloudinary connection
    test_result = cloudinary_service.get_signed_video_url('test', 3600)
    
    return jsonify({
        'cloudinary_available': cloudinary_service.available,
        'test_url_result': test_result,
        'config_check': {
            'cloud_name': app.config.get('CLOUDINARY_CLOUD_NAME'),
            'has_api_key': bool(app.config.get('CLOUDINARY_API_KEY')),
            'has_api_secret': bool(app.config.get('CLOUDINARY_API_SECRET')),
        }
    })


@app.route('/subject/<int:subject_id>')
@login_required
def view_subject(subject_id):
    """View all lessons in a subject with progress tracking"""
    subject = Subject.query.get_or_404(subject_id)

    # ADMINS CAN ACCESS EVERYTHING
    if current_user.is_admin:
        lessons = Lesson.query.filter_by(subject_id=subject_id).order_by(Lesson.order).all()
        # Add progress for admin view
        for lesson in lessons:
            progress = Progress.query.filter_by(
                user_id=current_user.id,
                lesson_id=lesson.id
            ).first()
            lesson.user_progress = progress.watch_time if progress else 0
            lesson.user_completed = progress.completed if progress else False
        return render_template('subject.html', subject=subject, lessons=lessons, all_completed=False)

    # Check access for regular users
    if not current_user.has_access(subject.form):
        flash(f'Please subscribe to access Form {subject.form} content.', 'warning')
        return redirect(url_for('pricing'))

    # Get all lessons for this subject
    lessons = Lesson.query.filter_by(subject_id=subject_id).order_by(Lesson.order).all()
    
    # Add user's progress for each lesson
    for lesson in lessons:
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=lesson.id
        ).first()
        
        if progress:
            # Calculate progress percentage
            if lesson.duration and lesson.duration > 0:
                total_seconds = lesson.duration * 60
                lesson.user_progress = min(100, int((progress.watch_time / total_seconds) * 100))
            else:
                lesson.user_progress = 50 if progress.watch_time > 0 else 0
            lesson.user_completed = progress.completed
            lesson.user_watch_time = progress.watch_time
        else:
            lesson.user_progress = 0
            lesson.user_completed = False
            lesson.user_watch_time = 0
    
    # Check if all lessons are completed
    all_completed = True
    for lesson in lessons:
        if not lesson.user_completed:
            all_completed = False
            break

    return render_template('subject.html', 
                        subject=subject, 
                        lessons=lessons,
                        all_completed=all_completed)




@app.route('/lesson/<int:lesson_id>')
@login_required
def view_lesson(lesson_id):
    """Gateway page - shows lesson info and link to watch"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # ✅ ADMINS CAN ACCESS EVERYTHING
    if current_user.is_admin:
        subject_lessons = Lesson.query.filter_by(
            subject_id=lesson.subject_id
        ).order_by(Lesson.order).all()
        
        return render_template('lesson.html',
                               lesson=lesson,
                               subject_lessons=subject_lessons,
                               progress_percent=0,
                               completed=False)

    # Check access for regular users
    if not current_user.has_access(lesson.form) and not lesson.is_free:
        flash('Please subscribe to access this lesson.', 'warning')
        return redirect(url_for('pricing'))
    
    # Get all lessons in same subject for "More Lessons" section
    subject_lessons = Lesson.query.filter_by(
        subject_id=lesson.subject_id
    ).order_by(Lesson.order).all()
    
    # Get user's progress for THIS lesson
    progress = Progress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson.id
    ).first()
    
    progress_percent = 0
    completed = False
    
    if progress:
        if lesson.duration and lesson.duration > 0:
            total_seconds = lesson.duration * 60
            progress_percent = min(100, int((progress.watch_time / total_seconds) * 100))
        completed = progress.completed
    
    # Get progress for each lesson in the list (for showing completion status)
    for l in subject_lessons:
        l_progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=l.id
        ).first()
        
        if l_progress:
            if l.duration and l.duration > 0:
                total_seconds = l.duration * 60
                l.user_progress = min(100, int((l_progress.watch_time / total_seconds) * 100))
                l.user_completed = l_progress.completed
            else:
                l.user_progress = 50 if l_progress.watch_time > 0 else 0
                l.user_completed = l_progress.completed
        else:
            l.user_progress = 0
            l.user_completed = False
    
    return render_template('lesson.html',
                           lesson=lesson,
                           subject_lessons=subject_lessons,
                           progress_percent=progress_percent,
                           completed=completed)

@app.route('/search')
@login_required
def search():
    """Advanced search with filters"""
    query = request.args.get('q', '').strip()
    form_filter = request.args.get('form', 'all')
    subject_filter = request.args.get('subject', 'all')
    type_filter = request.args.get('type', 'all')
    
    # Base queries
    subjects_query = Subject.query
    lessons_query = Lesson.query
    
    # Apply text search
    if query and len(query) >= 2:
        subjects_query = subjects_query.filter(Subject.name.ilike(f'%{query}%'))
        lessons_query = lessons_query.filter(Lesson.title.ilike(f'%{query}%'))
    
    # Apply form filter
    if form_filter != 'all':
        form_num = int(form_filter)
        subjects_query = subjects_query.filter_by(form=form_num)
        lessons_query = lessons_query.filter(Lesson.form == form_num)
    
    # Apply subject filter (for lessons only)
    if subject_filter != 'all':
        lessons_query = lessons_query.filter_by(subject_id=int(subject_filter))
    
    # Apply type filter
    if type_filter != 'all':
        lessons_query = lessons_query.filter_by(content_type=type_filter)
    
    # Execute queries
    subjects = subjects_query.order_by(Subject.form, Subject.order).all()
    lessons = lessons_query.order_by(Lesson.created_at.desc()).all()
    
    # Get lesson counts for subjects
    for subject in subjects:
        subject.lesson_count = Lesson.query.filter_by(subject_id=subject.id).count()
    
    # Get all subjects for filter dropdown
    all_subjects = Subject.query.order_by(Subject.form, Subject.name).all()
    
    return render_template('search_results.html',
                         query=query,
                         subjects=subjects,
                         lessons=lessons,
                         total_results=len(subjects) + len(lessons),
                         form_filter=form_filter,
                         subject_filter=subject_filter,
                         type_filter=type_filter,
                         all_subjects=all_subjects)

@app.route('/api/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def api_lesson_complete(lesson_id):
    """Mark lesson as complete"""
    lesson = Lesson.query.get_or_404(lesson_id)

    # TODO: Save to Progress model when implemented
    app.logger.info(f"User {current_user.id} completed lesson {lesson_id}")

    return jsonify({
        'success': True,
        'message': 'Lesson marked as complete'
    })


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/subscribe/<form_type>/<duration>')
@login_required
def subscribe(form_type, duration):
    if not current_user.email_verified:
        flash('Please verify your email before subscribing.', 'warning')
        return redirect(url_for('verify_email_reminder'))

    real_prices = {
        'form3': {'daily': 1030, 'weekly': 6695, 'monthly': 12500},
        'form4': {'daily': 1030, 'weekly': 6695, 'monthly': 12500},
        'combined': {'daily': 1545, 'weekly': 8500, 'monthly': 19500}
    }

    # ===== SMARTER UPGRADE LOGIC =====
    # If user already has active subscription, suggest combined plan
    if current_user.is_active_subscriber and current_user.subscription_expiry and current_user.subscription_expiry > datetime.utcnow():
        
        # If already on combined, just extend
        if current_user.subscription_form == 'combined':
            # Can just extend - show normal payment
            pass
        # If buying different form than current, suggest combined
        elif current_user.subscription_form != form_type:
            days_left = current_user.get_subscription_days_left()
            
            # Calculate discounted price (only pay difference)
            current_plan_value = {'form3': 12500, 'form4': 12500, 'combined': 19500}
            current_value = current_plan_value.get(current_user.subscription_form, 0)
            new_value = current_plan_value.get(form_type, 0)
            
            # For combined plan, suggest upgrade price
            if form_type != 'combined':
                flash(f'You currently have {current_user.subscription_form.upper()}. For access to both, upgrade to Combined plan.', 'info')
                return redirect(url_for('pricing'))
        
        # Store in session for confirmation
        session['pending_subscription'] = {
            'form_type': form_type,
            'duration': duration,
            'amount': real_prices[form_type][duration]
        }
        return redirect(url_for('confirm_subscription_upgrade'))

    # ✅ Clear the confirmed_upgrade flag after using it
    if session.get('confirmed_upgrade'):
        session.pop('confirmed_upgrade', None)

    # Use test prices if in TEST_MODE
    if TEST_MODE:
        prices = TEST_PRICES
        flash(
            f'🔧 TEST MODE: You\'re paying {TEST_PRICES[form_type][duration]} MWK instead of {real_prices[form_type][duration]} MWK',
            'info')
    else:
        prices = real_prices

    if form_type not in prices or duration not in prices[form_type]:
        flash('Invalid subscription type.', 'danger')
        return redirect(url_for('pricing'))

    amount = prices[form_type][duration]

    # Generate unique reference
    reference = f"SUB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"
    if TEST_MODE:
        reference = f"TEST-{reference}"

    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        subscription_type=duration,
        subscription_form=form_type,
        reference=reference,
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    return render_template('payment.html',
                           form_type=form_type,
                           duration=duration,
                           amount=amount,
                           reference=reference,
                           payment_id=payment.id,
                           test_mode=TEST_MODE)


@app.route('/confirm-subscription-upgrade')
@login_required
def confirm_subscription_upgrade():
    """Show confirmation page for upgrading subscription"""
    pending = session.get('pending_subscription')

    if not pending:
        flash('No pending subscription found.', 'warning')
        return redirect(url_for('pricing'))

    # Format current plan name
    current_plan = f"{current_user.subscription_form.upper()} - {current_user.subscription_type.title()}"

    # Format new plan name
    new_plan = f"{pending['form_type'].upper()} - {pending['duration'].title()}"

    days_left = current_user.get_subscription_days_left()

    return render_template('confirm_subscription.html',
                           current_plan=current_plan,
                           new_plan=new_plan,
                           days_left=days_left)


@app.route('/process-upgrade', methods=['GET'])
@login_required
def process_upgrade():
    """Process the confirmed upgrade"""
    pending = session.get('pending_subscription')

    if not pending:
        flash('No pending subscription found.', 'warning')
        return redirect(url_for('pricing'))

    # ✅ Set a flag in session that this is a confirmed upgrade
    session['confirmed_upgrade'] = True

    # Redirect to the normal subscribe flow
    return redirect(url_for('subscribe',
                            form_type=pending['form_type'],
                            duration=pending['duration']))


@app.route('/process-payment/<int:payment_id>', methods=['POST'])
@login_required
@limiter.limit("2 per minute")
def process_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))

    phone = request.form.get('phone_number', '').strip()
    method = request.form.get('payment_method')

    if not phone or not method:
        flash('Please provide phone number and payment method', 'danger')
        return redirect(url_for('subscribe', form_type=payment.subscription_form, duration=payment.subscription_type))

    # Clean phone number
    phone = re.sub(r'\D', '', phone)

    if phone.startswith('265'):
        phone = '0' + phone[3:]
    elif not phone.startswith('0'):
        phone = '0' + phone[-9:] if len(phone) >= 9 else phone

    if len(phone) > 10:
        phone = phone[:10]
    elif len(phone) == 9:
        phone = '0' + phone

    payment.phone_number = phone
    payment.payment_method = method
    db.session.commit()

    paychangu = PayChangu(mode=app.config['PAYCHANGU_MODE'])
    app.logger.info(f"Processing payment: {payment.id}, Amount: {payment.amount}, Phone: {phone}, Method: {method}")

    try:
        result = paychangu.initiate_mobile_money_payment(
            amount=payment.amount,
            phone_number=phone,
            email=current_user.email,
            name=current_user.username,
            reference=payment.reference,
            callback_url=f"{app.config['SITE_URL']}/paychangu-webhook"

        )

        app.logger.info(f"PayChangu response: {result}")

        if result and isinstance(result, dict):
            if result.get('status') == 'success' and 'data' in result:
                payment.charge_id = result['data'].get('charge_id')
                payment.paychangu_response = json.dumps(result)
                db.session.commit()
                flash('Payment initiated. Please check your phone to complete the payment.', 'info')
                return redirect(url_for('payment_status', payment_id=payment.id))
            else:
                error_message = result.get('message', 'Unknown error occurred')
                app.logger.error(f"Payment initiation failed: {error_message}")
                flash(f'Payment failed: {error_message}', 'danger')
        else:
            app.logger.error(f"Unexpected response format: {result}")
            flash('Payment service returned an unexpected response. Please try again.', 'danger')

    except Exception as e:
        app.logger.error(f"Exception during payment processing: {str(e)}", exc_info=True)
        flash(f'Payment error: {str(e)}', 'danger')

    return redirect(url_for('pricing'))


@app.route('/payment-status/<int:payment_id>')
def payment_status(payment_id):  # REMOVED @login_required!
    payment = Payment.query.get_or_404(payment_id)

    # If user is logged in and owns the payment, show full details
    if current_user.is_authenticated and payment.user_id == current_user.id:
        return render_template('payment_status.html', payment=payment)

    # Otherwise show limited public version
    return render_template('payment_status_public.html',
                           reference=payment.reference,
                           amount=payment.amount,
                           status=payment.status)


@app.route('/admin/activate-payment-by-ref/<reference>')
@login_required
def admin_activate_payment_by_ref(reference):
    """Manually activate a payment by reference"""
    if not current_user.is_admin:
        return "Admin only", 403

    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        return f"Payment {reference} not found", 404

    if payment.status == 'completed':
        return f"Payment {reference} already completed", 200

    # Activate the payment
    payment.status = 'completed'
    payment.completed_at = datetime.utcnow()

    user = User.query.get(payment.user_id)
    days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
    days = days_map.get(payment.subscription_type, 1)

    if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
        user.subscription_expiry += timedelta(days=days)
    else:
        user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

    user.is_active_subscriber = True
    user.subscription_form = payment.subscription_form
    user.subscription_type = payment.subscription_type

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Payment {reference} activated for user {user.username}',

        'expiry': user.subscription_expiry.isoformat()
    })

@app.route('/api/find-payment-by-charge/<charge_id>')
def find_payment_by_charge(charge_id):
    """Find payment by charge_id (for return URL handling)"""
    payment = Payment.query.filter_by(charge_id=charge_id).first()
    if payment:
        return jsonify({'payment_id': payment.id})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/auto-verify/<int:payment_id>')
@login_required
def auto_verify_payment(payment_id):
    """Auto-verify payment and activate subscription instantly"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Check if user owns this payment
    if payment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # If already completed, return success
    if payment.status == 'completed':
        return jsonify({
            'status': 'completed',
            'message': 'Payment already verified',
            'redirect': url_for('payment_success')
        })
    
    # Call PayChangu to verify
    paychangu = PayChangu(mode=app.config['PAYCHANGU_MODE'])
    result = paychangu.verify_payment(payment.charge_id)
    
    if result.get('success') and result.get('completed'):
        # Activate subscription
        payment.status = 'completed'
        payment.completed_at = datetime.utcnow()
        
        # Update user subscription
        user = User.query.get(payment.user_id)
        days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
        days = days_map.get(payment.subscription_type, 1)
        
        # Set subscription details
        user.is_active_subscriber = True
        user.subscription_form = payment.subscription_form
        user.subscription_type = payment.subscription_type
        
        # Update expiry
        if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
            user.subscription_expiry += timedelta(days=days)
        else:
            user.subscription_expiry = datetime.utcnow() + timedelta(days=days)
        
        db.session.commit()
        
        # Send confirmation email
        try:
            send_payment_confirmation_email(user, payment)
        except Exception as e:
            print(f"Email error: {e}")
        
        return jsonify({
            'status': 'completed',
            'message': 'Payment verified and subscription activated!',
            'redirect': url_for('payment_success')
        })
    elif result.get('success') and not result.get('completed'):
        # Still pending
        return jsonify({
            'status': 'pending',
            'message': 'Payment still processing...',
            'payment_status': result.get('status', 'pending')
        })
    else:
        # Verification failed
        return jsonify({
            'status': 'error',
            'message': result.get('message', 'Verification failed')
        }), 400


@app.route('/paychangu-webhook', methods=['POST'])
@app.route('/paychangu-webhook/', methods=['POST'])
def paychangu_webhook():
    """PayChangu Webhook Handler with signature verification"""
    import json
    from datetime import datetime
    import hmac
    import hashlib
    
    print("\n" + "🔔" * 50)
    print(f"WEBHOOK RECEIVED at {datetime.utcnow()}")
    
    # Get the raw payload for signature verification
    payload = request.get_data()
    signature = request.headers.get('X-PayChangu-Signature', '')
    
    # Verify webhook signature (if configured)
    webhook_secret = app.config.get('PAYCHANGU_WEBHOOK_SECRET')
    if webhook_secret:
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_signature, signature):
            print("❌ Invalid webhook signature - rejecting request")
            return jsonify({'error': 'Invalid signature'}), 401
    
    try:
        data = request.json
        print(f"Parsed JSON data: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"❌ Failed to parse JSON: {e}")
        data = {}
    
    # Process webhook in background
    try:
        process_webhook_payment(data)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
    
    return jsonify({'status': 'received'}), 200


def process_webhook_payment(data):
    """Helper function to process payment from webhook data"""
    from datetime import datetime, timedelta
    import time
    import json

    print("\n📦 PROCESSING WEBHOOK PAYMENT")
    print(f"Raw data type: {type(data)}")
    print(f"Raw data: {data}")

    if not data:
        print("❌ No data received")
        return

    if not isinstance(data, dict):
        print(f"❌ Data is not a dictionary: {type(data)}")
        return

    webhook_reference = data.get('reference') or data.get('data', {}).get('reference')
    charge_id = data.get('charge_id') or data.get('data', {}).get('charge_id')
    tx_ref = data.get('tx_ref') or data.get('data', {}).get('tx_ref')
    ref_id = data.get('ref_id') or data.get('data', {}).get('ref_id')

    print(f"🔍 Looking for payment with:")
    print(f"   - reference: {webhook_reference}")
    print(f"   - charge_id: {charge_id}")
    print(f"   - tx_ref: {tx_ref}")
    print(f"   - ref_id: {ref_id}")

    payment = None

    if webhook_reference and not payment:
        payment = Payment.query.filter_by(reference=webhook_reference).first()
        if payment:
            print(f"✅ Found payment by reference: {webhook_reference}")

    if charge_id and not payment:
        payment = Payment.query.filter_by(charge_id=charge_id).first()
        if payment:
            print(f"✅ Found payment by charge_id: {charge_id}")

    if tx_ref and not payment:
        payment = Payment.query.filter_by(transaction_id=tx_ref).first()
        if payment:
            print(f"✅ Found payment by tx_ref: {tx_ref}")

    if not payment:
        print("🔍 AGGRESSIVE SEARCH in paychangu_response...")
        all_payments = Payment.query.filter_by(status='pending').all()
        print(f"Found {len(all_payments)} pending payments to search")

        for p in all_payments:
            if p.paychangu_response:
                try:
                    response_data = json.loads(p.paychangu_response)
                    if charge_id and charge_id == response_data.get('data', {}).get('charge_id'):
                        payment = p
                        print(f"✅ Found payment {p.id} by charge_id in response")
                        break
                    if webhook_reference and webhook_reference in p.paychangu_response:
                        payment = p
                        print(f"✅ Found payment {p.id} by reference string")
                        break
                    if ref_id and ref_id == response_data.get('data', {}).get('ref_id'):
                        payment = p
                        print(f"✅ Found payment {p.id} by ref_id")
                        break
                    if charge_id and charge_id in p.paychangu_response:
                        payment = p
                        print(f"✅ Found payment {p.id} by charge_id string match")
                        break
                except Exception as e:
                    print(f"⚠️ Error parsing JSON for payment {p.id}: {e}")
                    continue

    if not payment and charge_id:
        print(f"🔍 Direct charge_id search: {charge_id}")
        payment = Payment.query.filter_by(charge_id=charge_id).first()
        if payment:
            print(f"✅ Found payment by direct charge_id: {payment.id}")

    if not payment:
        print("⏳ Payment not found - will retry up to 3 times with delays...")
        for attempt in range(1, 4):
            print(f"⏳ Retry attempt {attempt}/3...")
            time.sleep(2)
            db.session.remove()
            if charge_id:
                payment = Payment.query.filter_by(charge_id=charge_id).first()
                if payment:
                    print(f"✅ Found payment on retry attempt {attempt}: {payment.id}")
                    break
            if not payment and webhook_reference:
                payment = Payment.query.filter_by(reference=webhook_reference).first()
                if payment:
                    print(f"✅ Found payment by reference on retry attempt {attempt}: {payment.id}")
                    break
            if not payment and tx_ref:
                payment = Payment.query.filter_by(transaction_id=tx_ref).first()
                if payment:
                    print(f"✅ Found payment by tx_ref on retry attempt {attempt}: {payment.id}")
                    break
        if not payment:
            print("❌ Payment still not found after 3 retries")

    if payment:
        print(f"✅ Found payment ID: {payment.id}, User: {payment.user_id}")

        if payment.status == 'pending':
            print("✅ Payment is pending - activating now...")

            user = User.query.get(payment.user_id)
            if not user:
                print(f"❌ User not found for payment {payment.id}")
                return

            # Calculate days based on subscription type
            days = {'daily': 1, 'weekly': 7, 'monthly': 30}.get(payment.subscription_type, 1)

            # ===== SMARTER SUBSCRIPTION LOGIC =====
            user.is_active_subscriber = True
            user.subscription_type = payment.subscription_type

            # Check if user already has an active subscription
            has_active = user.subscription_expiry and user.subscription_expiry > datetime.utcnow()

            if has_active:
                # User has active subscription - extend expiry
                user.subscription_expiry += timedelta(days=days)
                print(f"📅 Extended existing subscription by {days} days")
                
                # If buying a different form, upgrade to combined
                if user.subscription_form != payment.subscription_form and user.subscription_form != 'combined':
                    user.subscription_form = 'combined'
                    print(f"🔄 Upgraded to combined plan")
                else:
                    print(f"📋 Keeping existing form: {user.subscription_form}")
            else:
                # New subscription
                user.subscription_expiry = datetime.utcnow() + timedelta(days=days)
                user.subscription_form = payment.subscription_form
                print(f"📅 New subscription for {days} days")

            # Update payment
            payment.status = 'completed'
            payment.completed_at = datetime.utcnow()
            if tx_ref:
                payment.transaction_id = tx_ref

            db.session.commit()

            print(f"✅✅✅ ACTIVATED: {user.username}")
            print(f"📊 Form: {user.subscription_form}, Type: {user.subscription_type}, Expiry: {user.subscription_expiry}")

            try:
                send_payment_confirmation_email(user, payment)
                print(f"📧 Confirmation email sent to {user.email}")
            except Exception as e:
                print(f"⚠️ Email sending failed: {e}")
        else:
            print(f"⚠️ Payment already processed with status: {payment.status}")
    else:
        print(f"❌ NO PAYMENT FOUND for any reference")
        print(f"   - reference: {webhook_reference}")
        print(f"   - charge_id: {charge_id}")
        print(f"   - tx_ref: {tx_ref}")
        print(f"   - ref_id: {ref_id}")



@app.route('/payment-success')
def payment_success():
    flash('Payment successful! You now have access to your lessons.', 'success')
    response = redirect(url_for('dashboard'))

    # Force browser to get fresh data
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@app.route('/payment-failed')
def payment_failed():
    flash('Payment failed. Please try again.', 'danger')
    return redirect(url_for('pricing'))


@app.route('/verify-payment/<reference>')
@login_required
def verify_payment(reference):
    """Manually verify payment status with PayChangu API"""
    import requests

    # Find the payment
    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        flash('Payment not found', 'danger')
        return redirect(url_for('dashboard'))

    # Only the user who made payment can verify
    if payment.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))

    # Call PayChangu to verify transaction status
    try:
        # PayChangu transaction verification endpoint
        url = f"https://api.paychangu.com/transactions/verify/{payment.transaction_id or payment.charge_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {app.config['PAYCHANGU_SECRET_KEY']}"
        }

        print(f"🔍 Verifying payment with PayChangu: {url}")
        response = requests.get(url, headers=headers, timeout=30)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            # Check different possible status fields
            tx_status = data.get('status') or data.get('data', {}).get('status')

            if tx_status in ['success', 'successful', 'completed']:
                # Update payment status
                payment.status = 'completed'
                payment.completed_at = datetime.utcnow()

                # Activate subscription
                user = User.query.get(payment.user_id)
                days = payment.get_days_for_subscription()

                user.is_active_subscriber = True
                user.subscription_type = payment.subscription_type
                user.subscription_form = payment.subscription_form

                if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
                    user.subscription_expiry += timedelta(days=days)
                else:
                    user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

                db.session.commit()
                flash('✅ Payment verified! Your subscription is now active.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f'⏳ Payment status: {tx_status or "pending"}', 'warning')
        else:
            # Try alternative endpoint
            alt_url = f"https://api.paychangu.com/verify-payment/{reference}"
            alt_response = requests.get(alt_url, headers=headers, timeout=30)

            if alt_response.status_code == 200:
                alt_data = alt_response.json()
                if alt_data.get('status') == 'success':
                    # Same activation code as above
                    payment.status = 'completed'
                    payment.completed_at = datetime.utcnow()

                    user = User.query.get(payment.user_id)
                    days = payment.get_days_for_subscription()
                    user.is_active_subscriber = True
                    user.subscription_type = payment.subscription_type
                    user.subscription_form = payment.subscription_form

                    if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
                        user.subscription_expiry += timedelta(days=days)
                    else:
                        user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

                    db.session.commit()
                    flash('✅ Payment verified! Your subscription is now active.', 'success')
                    return redirect(url_for('dashboard'))

            flash('Could not verify payment status at this time. Please try again later.', 'danger')

    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        flash(f'Error verifying payment: {str(e)}', 'danger')

    return redirect(url_for('payment_status', payment_id=payment.id))


@app.route('/profile')
@login_required
def profile():
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    analytics = get_user_analytics(current_user.id)
    
    # Get subscription info
    subscription_info = {
        'is_active': current_user.is_active_subscriber,
        'form': current_user.subscription_form if current_user.is_active_subscriber else None,
        'type': current_user.subscription_type if current_user.is_active_subscriber else None,
        'days_left': current_user.get_subscription_days_left() if current_user.is_active_subscriber else 0,
        'expiry': current_user.subscription_expiry.strftime('%d %B %Y') if current_user.is_active_subscriber and current_user.subscription_expiry else None
    }
    
    return render_template('profile.html', 
                         payments=payments, 
                         analytics=analytics,
                         user=current_user,
                         subscription_info=subscription_info)
@app.route('/verify-email-reminder')
@login_required
def verify_email_reminder():
    if current_user.email_verified:
        return redirect(url_for('dashboard'))
    
    # Generate and send new code if needed
    return render_template('verify_email_reminder.html', user=current_user)


@app.route('/resend-verification')
@login_required
def resend_verification():
    """Resend verification email to current user"""
    if current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('dashboard'))

    send_verification_email(current_user)
    flash('Verification email sent. Please check your inbox.', 'info')
    return redirect(url_for('verify_email_reminder'))


@app.route('/user-menu')
@login_required
def user_menu():
    """User menu page with all account options"""
    return render_template('user_menu.html', user=current_user)


# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        app.logger.warning(f"Non-admin user {current_user.username} attempted to access admin dashboard")
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    app.logger.info(f"Admin {current_user.username} accessing admin dashboard")

    # Get current time for template
    now = datetime.utcnow()

    # User stats
    total_users = User.query.count()
    new_users_today = User.query.filter(
        User.created_at >= datetime.utcnow().date()
    ).count()

    # Subscription stats
    active_subscribers = User.query.filter_by(is_active_subscriber=True).count()

    # Payment stats
    completed_payments = Payment.query.filter_by(status='completed').count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0

    # Content stats
    total_subjects = Subject.query.count()
    total_lessons = Lesson.query.count()

    # Recent data
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # Subscription breakdown
    form3_count = User.query.filter_by(subscription_form='form3', is_active_subscriber=True).count()
    form4_count = User.query.filter_by(subscription_form='form4', is_active_subscriber=True).count()
    combined_count = User.query.filter_by(subscription_form='combined', is_active_subscriber=True).count()

    # Revenue chart data (last 30 days)
    daily_revenue = []
    dates = []

    for i in range(30):
        day = datetime.utcnow() - timedelta(days=29 - i)
        next_day = day + timedelta(days=1)

        day_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.completed_at >= day,
            Payment.completed_at < next_day
        ).scalar() or 0

        daily_revenue.append(float(day_revenue))
        dates.append(day.strftime('%d %b'))

    # Get test mode from session or global
    test_mode = session.get('test_mode', TEST_MODE)

    return render_template('admin/dashboard.html',
                           datetime=datetime,
                           total_users=total_users,
                           new_users_today=new_users_today,
                           active_subscribers=active_subscribers,
                           total_revenue=total_revenue,
                           completed_payments=completed_payments,
                           total_subjects=total_subjects,
                           total_lessons=total_lessons,
                           recent_payments=recent_payments,
                           recent_users=recent_users,
                           form3_count=form3_count,
                           form4_count=form4_count,
                           combined_count=combined_count,
                           revenue_labels=dates,
                           revenue_data=daily_revenue,
                           test_mode=test_mode)







@app.route('/admin/user/<int:user_id>/payments')
@login_required
def admin_user_payments(user_id):
    """View payment history for a specific user"""
    user = User.query.get_or_404(user_id)
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    return render_template('admin/user_payments.html', user=user, payments=payments)




@app.route('/admin/toggle-test-mode')
@login_required
def toggle_test_mode():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        current_test_mode = session.get('test_mode', False)
        session['test_mode'] = not current_test_mode
        return jsonify({'success': True, 'test_mode': session['test_mode']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/user/<int:user_id>')
@login_required
def admin_user_detail(user_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    return render_template('admin/user_detail.html', user=user, payments=payments)


@app.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get_or_404(user_id)

    try:
        token = secrets.token_urlsafe(32)
        reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(reset)
        db.session.commit()

        send_password_reset_email(user, token)
        app.logger.info(f"Admin {current_user.username} reset password for user {user.username}")

        return jsonify({'success': True, 'message': f'Password reset email sent to {user.email}'})
    except Exception as e:
        app.logger.error(f"Error resetting password: {str(e)}")
        return jsonify({'success': False, 'message': f'Error sending reset email: {str(e)}'}), 500


@app.route('/admin/subjects')
@login_required
def admin_subjects():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subjects = Subject.query.order_by(Subject.form, Subject.order).all()
    return render_template('admin/subjects.html', subjects=subjects)


@app.route('/admin/subject/create', methods=['GET', 'POST'])
@login_required
def admin_create_subject():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        subject = Subject(
            name=request.form.get('name'),
            form=request.form.get('form'),
            description=request.form.get('description'),
            icon=request.form.get('icon', 'book'),
            order=request.form.get('order', 0)
        )
        db.session.add(subject)
        db.session.commit()
        flash('Subject created successfully', 'success')
        return redirect(url_for('admin_subjects'))

    return render_template('admin/create_subject.html')


@app.route('/admin/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_subject(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)

    if request.method == 'POST':
        subject.name = request.form.get('name')
        subject.form = request.form.get('form')
        subject.description = request.form.get('description')
        subject.icon = request.form.get('icon', 'book')
        subject.order = request.form.get('order', 0)
        db.session.commit()
        flash('Subject updated successfully', 'success')
        return redirect(url_for('admin_subjects'))

    return render_template('admin/edit_subject.html', subject=subject)


@app.route('/admin/subject/<int:subject_id>/delete')
@login_required
def admin_delete_subject(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully', 'success')
    return redirect(url_for('admin_subjects'))


@app.route('/admin/lessons')
@login_required
def admin_lessons():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    lessons = Lesson.query.order_by(Lesson.created_at.desc()).all()
    return render_template('admin/lessons.html', lessons=lessons)

@app.route('/admin/lesson/create', methods=['GET', 'POST'])
@login_required
def admin_create_lesson():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subjects = Subject.query.all()

    if request.method == 'POST':
        subject = Subject.query.get(request.form.get('subject_id'))
        content_type = request.form.get('content_type', 'video')
        
        # Handle file upload to Cloudinary
        file = request.files.get('file')
        cloudinary_data = None
        
        if file and file.filename and allowed_file(file.filename):
            # Determine file type for Cloudinary
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            if file_ext in ['mp4', 'avi', 'mov', 'mkv']:
                upload_type = 'video'
            elif file_ext in ['mp3', 'wav', 'm4a', 'ogg']:
                upload_type = 'audio'
            else:
                upload_type = 'raw'
            
            # Upload to Cloudinary
            result = cloudinary_service.upload_file(
                file, 
                file_type=upload_type,
                folder=f'mymsce_lessons/{subject.name}'
            )
            
            if result['success']:
                cloudinary_data = result
        
        # In admin_create_lesson, when creating the lesson
        lesson = Lesson(
            title=request.form.get('title'),
            description=request.form.get('description'),
            content=request.form.get('content'),
            content_type=content_type,
            cloudinary_public_id=cloudinary_data['public_id'] if cloudinary_data else None,
            cloudinary_url=cloudinary_data['url'] if cloudinary_data else None,
            file_name=file.filename if file else None,
            file_size=cloudinary_data['bytes'] if cloudinary_data else 0,
            file_extension=file.filename.rsplit('.', 1)[1].lower() if file else None,
            video_url=request.form.get('video_url') if content_type == 'youtube' else None,
            subject_id=subject.id,
            form=subject.form,
            order=request.form.get('order', 0),
            is_free=request.form.get('is_free') == 'on',
            downloadable=request.form.get('downloadable') == 'on' or content_type == 'document'  # Documents are downloadable by default
        )
        
        db.session.add(lesson)
        db.session.commit()
        flash('Lesson created successfully', 'success')
        return redirect(url_for('admin_lessons'))

    return render_template('admin/create_lesson.html', subjects=subjects)


@app.route('/debug-db')
def debug_db():
    """Check database connection status"""
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()

        return jsonify({
            'status': 'connected',
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'][:50] + '...',
            'pool_settings': app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}),
            'test_query': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/admin/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_lesson(lesson_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    subjects = Subject.query.all()
    
    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.description = request.form.get('description')
        lesson.content_type = request.form.get('content_type')
        lesson.order = int(request.form.get('order', 0))
        lesson.is_free = request.form.get('is_free') == 'on'
        lesson.downloadable = request.form.get('downloadable') == 'on'
        
        # Handle subject update
        subject = Subject.query.get(request.form.get('subject_id'))
        if subject:
            lesson.subject_id = subject.id
            lesson.form = subject.form
        
        # Handle file upload based on content type
        if lesson.content_type == 'video':
            video_file = request.files.get('video')
            if video_file and video_file.filename:
                result = cloudinary_service.upload_video(video_file)
                if result['success']:
                    lesson.cloudinary_public_id = result['public_id']
                    lesson.cloudinary_url = result['url']
                    lesson.duration = int(result.get('duration', 0)) // 60
        
        elif lesson.content_type == 'audio':
            audio_file = request.files.get('audio')
            if audio_file and audio_file.filename:
                result = cloudinary_service.upload_file(audio_file, 'audio')
                if result['success']:
                    lesson.cloudinary_public_id = result['public_id']
                    lesson.cloudinary_url = result['url']
        
        elif lesson.content_type == 'document':
            doc_file = request.files.get('document')
            if doc_file and doc_file.filename:
                result = cloudinary_service.upload_file(doc_file, 'raw')
                if result['success']:
                    lesson.cloudinary_public_id = result['public_id']
                    lesson.cloudinary_url = result['url']
                    lesson.file_name = doc_file.filename
                    lesson.file_size = result['bytes']
        
        elif lesson.content_type == 'youtube':
            lesson.video_url = request.form.get('video_url')
        
        db.session.commit()
        flash('Lesson updated successfully', 'success')
        return redirect(url_for('admin_lessons'))
    
    return render_template('admin/edit_lesson.html', lesson=lesson, subjects=subjects)

@app.route('/admin/lesson/<int:lesson_id>/delete')
@login_required
def admin_delete_lesson(lesson_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    lesson_title = lesson.title
    
    try:
        # With CASCADE, this automatically deletes all related progress records
        db.session.delete(lesson)
        db.session.commit()
        flash(f'Lesson "{lesson_title}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting lesson: {str(e)}', 'danger')
    
    return redirect(url_for('admin_lessons'))


@app.route('/admin/lesson/<int:lesson_id>/make-sample', methods=['POST'])
@login_required
def make_lesson_sample(lesson_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.is_free = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Lesson is now a free sample'})


@app.route('/admin/lesson/<int:lesson_id>/remove-sample', methods=['POST'])
@login_required
def remove_lesson_sample(lesson_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.is_free = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'Sample status removed'})


@app.route('/admin/sample-lessons')
@login_required
def admin_sample_lessons():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    all_lessons = Lesson.query.order_by(Lesson.created_at.desc()).all()
    sample_lessons = [l for l in all_lessons if l.is_free]
    premium_lessons = [l for l in all_lessons if not l.is_free]

    return render_template('admin/sample_lessons.html',
                           sample_lessons=sample_lessons,
                           premium_lessons=premium_lessons,
                           total_lessons=len(all_lessons))


@app.route('/admin/payments')
@login_required
def admin_payments():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    from datetime import datetime
    now = datetime.utcnow()  # Get current time
    payments = Payment.query.order_by(Payment.created_at.desc()).all()

    return render_template('admin/payments.html',
                           payments=payments,
                           now=now)  # Pass the datetime object


@app.route('/admin/activate-payment/<int:payment_id>')
@login_required
def admin_activate_payment(payment_id):
    if not current_user.is_admin:
        return "Admin only", 403

    payment = Payment.query.get_or_404(payment_id)

    payment.status = 'completed'
    payment.completed_at = datetime.utcnow()

    user = User.query.get(payment.user_id)
    days = payment.get_days_for_subscription()

    user.subscription_type = payment.subscription_type
    user.subscription_form = payment.subscription_form
    user.is_active_subscriber = True

    if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
        user.subscription_expiry += timedelta(days=days)
    else:
        user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

    db.session.commit()
    flash(f'Payment manually activated for user {user.username}', 'success')
    return redirect(url_for('admin_payments'))


# API Routes
@app.route('/api/check-subscription')
@login_required
def check_subscription():
    user = User.query.get(current_user.id)

    if user.is_active_subscriber and user.subscription_expiry < datetime.utcnow():
        user.is_active_subscriber = False
        user.subscription_type = 'none'
        user.subscription_form = 'none'
        db.session.commit()
        return jsonify({'changed': True, 'status': 'expired'})

    return jsonify({'changed': False})


@app.route('/api/payment-status/<int:payment_id>')
@login_required
def api_payment_status(payment_id):
    payment = Payment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'status': payment.status,
        'amount': payment.amount,
        'reference': payment.reference
    })

# Debug Routes
@app.route('/debug-paychangu')
@login_required
def debug_paychangu():
    if not current_user.is_admin:
        return "Admin only", 403

    config_info = {
        'mode': app.config.get('PAYCHANGU_MODE'),
        'base_url': 'https://sandbox.paychangu.com' if app.config.get('PAYCHANGU_MODE') == 'sandbox' else 'https://api.paychangu.com',
        'has_public_key': bool(app.config.get('PAYCHANGU_PUBLIC_KEY')),
        'has_secret_key': bool(app.config.get('PAYCHANGU_SECRET_KEY')),
        'public_key': app.config.get('PAYCHANGU_PUBLIC_KEY', '')[:15] + '...',
        'secret_key': app.config.get('PAYCHANGU_SECRET_KEY', '')[:15] + '...',
        'site_url': app.config.get('SITE_URL'),
        'webhook_url': f"{app.config.get('SITE_URL')}/paychangu-webhook"
    }
    return jsonify(config_info)


@app.route('/debug-phone/<phone>')
@login_required
def debug_phone(phone):
    if not current_user.is_admin:
        return "Admin only", 403

    from paychangu import PayChangu

    paychangu = PayChangu(mode=app.config.get('PAYCHANGU_MODE', 'sandbox'))

    digits_only = re.sub(r'\D', '', phone)
    formats = {'original': phone, 'digits_only': digits_only}

    if not digits_only.startswith('0') and len(digits_only) >= 9:
        formats['with_zero'] = '0' + digits_only[-9:]

    if len(digits_only) >= 9:
        formats['with_265'] = '+265' + digits_only[-9:]
        formats['nine_digits'] = digits_only[-9:]

    results = {}
    for fmt_name, fmt_value in formats.items():
        operator_id = paychangu.get_operator_id(fmt_value)
        cleaned = re.sub(r'\D', '', str(fmt_value))
        if cleaned.startswith('265'):
            cleaned = cleaned[3:]
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        prefix = cleaned[:3] if len(cleaned) >= 3 else cleaned

        results[fmt_name] = {
            'input': fmt_value,
            'operator_id': operator_id,
            'detected': bool(operator_id),
            'prefix': prefix,
            'operator': 'Airtel' if operator_id and 'airtel' in operator_id.lower() else 'TNM' if operator_id else 'Unknown'
        }

    mapping = {
        'airtel_prefixes': ['098', '099', '088'],
        'tnm_prefixes': ['088', '089'],
        'airtel_id': '20be6c20-adeb-4b5b-a7ba-0769820df4fb',
        'tnm_id': 'f3d8b6c9-1a2b-3c4d-5e6f-7a8b9c0d1e2f'
    }

    return render_template('debug_phone.html', phone=phone, results=results, mapping=mapping)


@app.route('/debug-video/<int:lesson_id>')
@login_required
def debug_video(lesson_id):
    if not current_user.is_admin:
        return "Admin only", 403

    lesson = Lesson.query.get_or_404(lesson_id)

    def extract_method1(url):
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        return None

    def extract_method2(url):
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    def extract_method3(url):
        match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    def extract_method4(url):
        match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    video_id = None
    methods_tried = []

    if lesson.video_url:
        methods = [
            ('direct_id', extract_method1),
            ('youtu.be', extract_method2),
            ('watch?v=', extract_method3),
            ('embed', extract_method4)
        ]

        for method_name, method_func in methods:
            result = method_func(lesson.video_url)
            methods_tried.append({
                'method': method_name,
                'result': result,
                'success': result is not None
            })
            if result:
                video_id = result
                break

    return jsonify({
        'lesson_id': lesson.id,
        'lesson_title': lesson.title,
        'stored_url': lesson.video_url,
        'video_type': lesson.video_type,
        'extracted_video_id': video_id,
        'methods_tried': methods_tried,
        'embed_url': f'https://www.youtube.com/embed/{video_id}' if video_id else None
    })



@app.route('/db-health')
def db_health():
    """Check database connection"""
    try:
        # Try to execute a simple query
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/fetch-operators')
@login_required
def fetch_operators():
    if not current_user.is_admin:
        return "Admin only", 403

    paychangu = PayChangu(mode=app.config.get('PAYCHANGU_MODE', 'sandbox'))

    try:
        response = requests.get(
            f"{paychangu.base_url}/api/v1/operators",
            headers=paychangu.get_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'message': 'Could not fetch from API, using hardcoded values',
                'operators': [
                    {'name': 'Airtel Money', 'id': '20be6c20-adeb-4b5b-a7ba-0769820df4fb',
                     'prefixes': ['098', '099', '088']},
                    {'name': 'TNM Mpamba', 'id': 'f3d8b6c9-1a2b-3c4d-5e6f-7a8b9c0d1e2f', 'prefixes': ['089', '088']}
                ]
            })
    except Exception as e:
        return jsonify({'error': str(e), 'using_hardcoded': True,
                        'operators': [
                            {'name': 'Airtel Money', 'id': '20be6c20-adeb-4b5b-a7ba-0769820df4fb'},
                            {'name': 'TNM Mpamba', 'id': 'f3d8b6c9-1a2b-3c4d-5e6f-7a8b9c0d1e2f'}
                        ]})


@app.route('/admin/test-webhook', methods=['POST'])
@login_required
def admin_test_webhook():
    """Admin route to manually trigger webhook for testing"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    reference = data.get('reference')

    if not reference:
        return jsonify({'error': 'Reference required'}), 400

    # Find payment
    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Simulate webhook
    with app.test_client() as client:
        webhook_data = {
            'event_type': 'api.charge.payment',
            'status': 'success',
            'reference': reference,
            'charge_id': payment.charge_id or 'test_123',
            'trans_id': f"TRANS_{reference}"
        }

        response = client.post('/paychangu-webhook',
                               json=webhook_data,
                               headers={'Content-Type': 'application/json'})

        return jsonify({
            'message': 'Webhook triggered',
            'status_code': response.status_code,
            'response': response.json()
        })


# Test routes
@app.route('/test-paychangu')
def test_paychangu():
    paychangu = PayChangu(mode=app.config['PAYCHANGU_MODE'])
    test_payment = paychangu.initiate_mobile_money_payment(
        amount=100,
        phone_number='0999123456',
        email='test@example.com',
        name='Test User',
        reference=f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )
    return jsonify(test_payment)


@app.route('/test-paychangu-simple')
def test_paychangu_simple():
    try:
        response = requests.get("https://sandbox.paychangu.com", timeout=10)
        return f"PayChangu Sandbox is {'reachable' if response.status_code == 200 else 'returned status ' + str(response.status_code)}"
    except Exception as e:
        return f"Error connecting to PayChangu: {str(e)}"

@app.route('/stream/<int:lesson_id>')
@login_required
def stream_lesson(lesson_id):
    """Stream video/audio from Cloudinary"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if not current_user.has_access(lesson.form) and not lesson.is_free and not current_user.is_admin:
        abort(403)
    
    # Use the stored Cloudinary URL from the database
    if lesson.cloudinary_url:
        print(f"🔗 STREAM URL (from DB): {lesson.cloudinary_url}")
        return redirect(lesson.cloudinary_url)
    
    flash('File not available', 'danger')
    return redirect(url_for('view_lesson', lesson_id=lesson.id))

@app.route('/download/<int:lesson_id>')
@login_required
def download_lesson(lesson_id):
    """Download files from Cloudinary with proper filename"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if not current_user.has_access(lesson.form) and not lesson.is_free and not current_user.is_admin:
        abort(403)
    
    if not lesson.downloadable:
        flash('This file is not available for download', 'danger')
        return redirect(url_for('view_lesson', lesson_id=lesson.id))
    
    if not lesson.cloudinary_url:
        flash('File not available', 'danger')
        return redirect(url_for('view_lesson', lesson_id=lesson.id))
    
    # Get the file from Cloudinary
    import requests
    import io
    
    try:
        response = requests.get(lesson.cloudinary_url)
        if response.status_code != 200:
            flash('File could not be downloaded', 'danger')
            return redirect(url_for('view_lesson', lesson_id=lesson.id))
        
        # Determine proper filename
        if lesson.file_name:
            # Use stored original filename
            filename = lesson.file_name
        else:
            # Create a clean filename from lesson title
            safe_title = re.sub(r'[^\w\s-]', '', lesson.title).strip().replace(' ', '_')
            ext = lesson.file_extension or 'pdf'
            filename = f"{safe_title}.{ext}"
        
        # Get the file extension from Cloudinary URL if needed
        if '.' not in filename and lesson.cloudinary_url:
            url_path = lesson.cloudinary_url.split('/')[-1]
            if '.' in url_path:
                ext = url_path.split('.')[-1]
                filename = f"{filename}.{ext}"
        
        print(f"📄 Downloading with filename: {filename}")
        
        # Send file with proper name
        return send_file(
            io.BytesIO(response.content),
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        print(f"Download error: {e}")
        flash('Error downloading file', 'danger')
        return redirect(url_for('view_lesson', lesson_id=lesson.id))

@app.route('/test-email')
def test_email():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    success, message = test_smtp_connection()

    if success:
        flash(f'SMTP Test: {message}', 'success')
    else:
        flash(f'SMTP Test Failed: {message}', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/api/lesson/<int:lesson_id>/progress', methods=['POST'])
@login_required
def update_lesson_progress(lesson_id):
    """Update watch progress for a lesson"""
    try:
        data = request.json
        watch_time = data.get('watch_time', 0)
        video_duration = data.get('duration', 0)

        # Find or create progress record
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=lesson_id
        ).first()

        if not progress:
            progress = Progress(
                user_id=current_user.id,
                lesson_id=lesson_id,
                watch_time=watch_time,
                last_watched=datetime.utcnow()
            )
            db.session.add(progress)
        else:
            progress.watch_time = watch_time
            progress.last_watched = datetime.utcnow()

        # Mark as completed if watched 90% or more
        if video_duration > 0 and (watch_time / video_duration) >= 0.9:
            progress.completed = True

        db.session.commit()

        # Calculate progress percentage
        percentage = 0
        if video_duration > 0:
            percentage = min(100, int((watch_time / video_duration) * 100))

        return jsonify({
            'success': True,
            'progress': percentage,
            'completed': progress.completed
        })
    except Exception as e:
        print(f"Error saving progress: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/lesson/<int:lesson_id>/progress', methods=['GET'])
@login_required
def get_lesson_progress(lesson_id):
    """Get progress for a specific lesson"""
    try:
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=lesson_id
        ).first()

        lesson = Lesson.query.get_or_404(lesson_id)

        percentage = 0
        watch_time = 0
        completed = False

        if progress:
            watch_time = progress.watch_time
            completed = progress.completed
            if lesson.duration and lesson.duration > 0:
                percentage = min(100, int((progress.watch_time / (lesson.duration * 60)) * 100))

        return jsonify({
            'progress': percentage,
            'completed': completed,
            'watch_time': watch_time
        })
    except Exception as e:
        print(f"Error getting progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/watch/<int:lesson_id>')
@login_required
def watch_lesson(lesson_id):
    """Handle video playback (Cloudinary & YouTube)"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    print("=" * 50)
    print(f"VIEWING LESSON: {lesson_id}")
    print(f"Title: {lesson.title}")
    print(f"Content Type: {lesson.content_type}")
    
    # Check access
    if not current_user.has_access(lesson.form) and not lesson.is_free and not current_user.is_admin:
        flash('Please subscribe to access this lesson.', 'warning')
        return redirect(url_for('pricing'))
    
    # Get navigation (prev/next lessons)
    subject_lessons = Lesson.query.filter_by(
        subject_id=lesson.subject_id
    ).order_by(Lesson.order).all()
    
    prev_lesson = None
    next_lesson = None
    for i, l in enumerate(subject_lessons):
        if l.id == lesson.id:
            if i > 0:
                prev_lesson = subject_lessons[i - 1]
            if i < len(subject_lessons) - 1:
                next_lesson = subject_lessons[i + 1]
            break
    
    # Get progress
    progress = Progress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson.id
    ).first()
    
    if not progress:
        progress = Progress(
            user_id=current_user.id,
            lesson_id=lesson.id,
            watch_time=0,
            completed=False,
            last_watched=datetime.utcnow()
        )
        db.session.add(progress)
        db.session.commit()
    
    progress_percent = 0
    if lesson.duration and lesson.duration > 0:
        total_seconds = lesson.duration * 60
        progress_percent = min(100, int((progress.watch_time / total_seconds) * 100))
    
    # Handle based on content type
    if lesson.content_type == 'youtube' and lesson.video_url:
        # YouTube video
        video_id = extract_youtube_id(lesson.video_url)
        if not video_id:
            flash('Invalid YouTube URL', 'danger')
            return redirect(url_for('view_lesson', lesson_id=lesson.id))
        
        # Increment view count
        lesson.access_count = (lesson.access_count or 0) + 1
        db.session.commit()
        
        return render_template('youtube_player.html',
                             lesson=lesson,
                             video_id=video_id,
                             prev_lesson=prev_lesson,
                             next_lesson=next_lesson,
                             progress_percent=progress_percent,
                             watch_time=progress.watch_time,
                             completed=progress.completed)
    
    elif lesson.content_type == 'video' and lesson.cloudinary_public_id:
        # Cloudinary video - USE STORED URL FROM DATABASE
        if lesson.cloudinary_url:
            video_url = lesson.cloudinary_url
        else:
            # Fallback to constructed URL
            video_url = f"https://res.cloudinary.com/dtrz5zglt/video/upload/{lesson.cloudinary_public_id}.mp4"
        
        print(f"✅ Using video URL: {video_url}")
        
        # Increment view count
        lesson.access_count = (lesson.access_count or 0) + 1
        db.session.commit()
        
        return render_template('watch.html',
                             lesson=lesson,
                             video_url=video_url,
                             prev_lesson=prev_lesson,
                             next_lesson=next_lesson,
                             progress_percent=progress_percent,
                             watch_time=progress.watch_time,
                             completed=progress.completed)
        
    elif lesson.content_type == 'audio':
        # Audio file - use custom audio player (no download option)
        audio_url = lesson.cloudinary_url
        
        return render_template('audio_player.html',
                            lesson=lesson,
                            audio_url=audio_url,
                            prev_lesson=prev_lesson,
                            next_lesson=next_lesson,
                            progress_percent=progress_percent,
                            watch_time=progress.watch_time,
                            completed=progress.completed)
    
    elif lesson.content_type == 'document':
        # Document - redirect to download or view
        if lesson.downloadable:
            return redirect(url_for('download_lesson', lesson_id=lesson.id))
        else:
            return redirect(url_for('stream_lesson', lesson_id=lesson.id))
    
    else:
        flash('No content available for this lesson', 'danger')
        return redirect(url_for('view_lesson', lesson_id=lesson.id))
 
 
@app.route('/debug/lesson/<int:lesson_id>')
@login_required
def debug_lesson(lesson_id):
    if not current_user.is_admin:
        return "Admin only", 403
    
    lesson = Lesson.query.get_or_404(lesson_id)
    
    return jsonify({
        'id': lesson.id,
        'title': lesson.title,
        'cloudinary_public_id': lesson.cloudinary_public_id,
        'cloudinary_url': lesson.cloudinary_url,
        'content_type': lesson.content_type,
        'duration': lesson.duration
    })


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/health')
def health():
    """Health check for Render"""
    return jsonify({'status': 'healthy', 'time': datetime.utcnow().isoformat()})

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# Add this near the bottom of app.py, before if __name__ == '__main__'
with app.app_context():
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1')).scalar()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("⚠️  Continuing startup - app may not function correctly")



if __name__ == '__main__':
    app.run(debug=True)