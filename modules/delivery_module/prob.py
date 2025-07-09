import sqlite3

conn = sqlite3.connect("path/to/delivery_notes.db")
cur = conn.cursor()

for row in cur.execute("SELECT id, created_at FROM delivery_notes"):
    print(row)

conn.close()
