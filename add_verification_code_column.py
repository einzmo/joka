# add_verification_code_column.py
import sqlite3

conn = sqlite3.connect('instance/mymsce.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE email_verification ADD COLUMN code VARCHAR(6)')
    conn.commit()
    print("✅ Added code column to email_verification table")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("✅ Code column already exists")
    else:
        print(f"Error: {e}")

conn.close()