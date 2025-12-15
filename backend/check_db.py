import sqlite3
import os

db_path = "sparkle.db"
print(f"Checking database at: {os.path.abspath(db_path)}")

if not os.path.exists(db_path):
    print("Database file does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables found:", [t[0] for t in tables])
conn.close()
