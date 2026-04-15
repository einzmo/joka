# add_login_attempts.py
import sqlite3

conn = sqlite3.connect('instance/mymsce.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS login_attempt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(120) NOT NULL,
        ip_address VARCHAR(45) NOT NULL,
        success BOOLEAN DEFAULT 0,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()

print("✅ login_attempt table created")