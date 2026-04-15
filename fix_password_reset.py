# fix_password_reset.py
import sqlite3

conn = sqlite3.connect('instance/mymsce.db')
cursor = conn.cursor()

# Remove NOT NULL constraint from token column
cursor.execute("CREATE TABLE password_reset_new (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token VARCHAR(100), code VARCHAR(6), created_at TIMESTAMP, expires_at TIMESTAMP, used BOOLEAN, FOREIGN KEY(user_id) REFERENCES user(id))")
cursor.execute("INSERT INTO password_reset_new (id, user_id, token, code, created_at, expires_at, used) SELECT id, user_id, token, code, created_at, expires_at, used FROM password_reset")
cursor.execute("DROP TABLE password_reset")
cursor.execute("ALTER TABLE password_reset_new RENAME TO password_reset")
conn.commit()
conn.close()

print("✅ Fixed password_reset table - token can now be NULL")