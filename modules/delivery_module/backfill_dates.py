# modules/delivery_module/backfill_dates.py

import sqlite3
import os

here    = os.path.dirname(__file__)
DB_PATH = os.path.join(here, "delivery_notes.db")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# Ha empty, állítsd be a created_at-et mostani időre:
cur.execute("""
    UPDATE delivery_notes
       SET created_at = datetime('now')
     WHERE created_at = ''
""")

# shipping_date-et tedd egyenlőre created_at-tel ott, ahol üres:
cur.execute("""
    UPDATE delivery_notes
       SET shipping_date = created_at
     WHERE shipping_date = ''
""")

conn.commit()
conn.close()

print("Backfill kész: régi rekordokhoz now() került created_at és shipping_date mezőbe.")
