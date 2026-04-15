# add_settings_table.py
import sqlite3

conn = sqlite3.connect('instance/mymsce.db')
cursor = conn.cursor()

# Create admin_settings table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_setting (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key VARCHAR(100) UNIQUE NOT NULL,
        value TEXT,
        category VARCHAR(50) DEFAULT 'general',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

print("✅ admin_settings table created successfully")