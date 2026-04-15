# fix_email_verification.py
import sqlite3

conn = sqlite3.connect('instance/mymsce.db')
cursor = conn.cursor()

# Drop and recreate email_verification table with nullable token
cursor.execute('DROP TABLE IF EXISTS email_verification_new')
cursor.execute('''
    CREATE TABLE email_verification_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token VARCHAR(100),
        code VARCHAR(6),
        created_at TIMESTAMP,
        expires_at TIMESTAMP,
        used BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES user(id)
    )
''')

# Copy existing data
cursor.execute('''
    INSERT INTO email_verification_new (id, user_id, token, code, created_at, expires_at, used)
    SELECT id, user_id, token, code, created_at, expires_at, used FROM email_verification
''')

# Replace old table
cursor.execute('DROP TABLE email_verification')
cursor.execute('ALTER TABLE email_verification_new RENAME TO email_verification')
conn.commit()
conn.close()

print("✅ Fixed email_verification table - token can now be NULL")