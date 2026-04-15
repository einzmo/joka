# check_status.py
import os
import sqlite3
import sys

def check_database_status():
    """Check current database state"""
    print("=" * 50)
    print("DATABASE STATUS REPORT")
    print("=" * 50)
    
    # Connect directly to SQLite to avoid Flask app context issues
    conn = sqlite3.connect('instance/mymsce.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\n📊 TABLES FOUND: {len(tables)}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   - {table[0]}: {count} records")
    
    # Check users table if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM user")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user WHERE is_verified=1")
        verified_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user WHERE is_admin=1")
        admin_users = cursor.fetchone()[0]
        
        print(f"\n📊 USERS:")
        print(f"   Total users: {total_users}")
        print(f"   Verified: {verified_users}")
        print(f"   Admins: {admin_users}")
    
    # Check subjects table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subject';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM subject")
        total_subjects = cursor.fetchone()[0]
        print(f"\n📚 SUBJECTS: {total_subjects}")
        
        # List all subjects
        cursor.execute("SELECT id, name FROM subject")
        subjects = cursor.fetchall()
        for subject in subjects:
            print(f"   - {subject[1]} (ID: {subject[0]})")
    
    # Check lessons table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lesson';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM lesson")
        total_lessons = cursor.fetchone()[0]
        print(f"\n📖 LESSONS: {total_lessons}")
    
    # Check payments table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM payment")
        total_payments = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM payment WHERE status='completed'")
        successful_payments = cursor.fetchone()[0]
        
        print(f"\n💰 PAYMENTS:")
        print(f"   Total transactions: {total_payments}")
        print(f"   Successful: {successful_payments}")
    
    conn.close()
    print("\n" + "=" * 50)

def check_app_files():
    """Check if critical app files exist"""
    print("\n📁 CRITICAL FILES CHECK:")
    print("-" * 50)
    
    critical_files = ['app.py', 'models.py', 'forms.py', 'email_utils.py', 'paychangu.py']
    for file in critical_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING!")
    
    # Check templates
    if os.path.exists('templates'):
        template_count = len([f for f in os.listdir('templates') if f.endswith('.html')])
        print(f"✅ Templates folder with {template_count} HTML files")
    else:
        print("❌ Templates folder missing")

def check_environment():
    """Check environment configuration"""
    print("\n🔧 ENVIRONMENT CHECK:")
    print("-" * 50)
    
    # Check .env file
    if os.path.exists('.env'):
        print("✅ .env file exists")
        with open('.env', 'r') as f:
            env_vars = [line for line in f if '=' in line and not line.startswith('#')]
            print(f"   Contains {len(env_vars)} variables")
            # Check for critical vars (without showing values)
            critical_vars = ['SECRET_KEY', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'PAYCHANGU_API_KEY']
            for var in critical_vars:
                found = any(var in line for line in env_vars)
                print(f"   {'✅' if found else '❌'} {var}")
    else:
        print("❌ .env file missing - create from .env.example")

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    check_database_status()
    check_app_files()
    check_environment()