# modules/delivery_module/inspect_db.py

import sqlite3
import os
from pprint import pprint

# Az aktuális fájl mappája, és a benne lévő .db
here   = os.path.dirname(__file__)
DB_PATH = os.path.join(here, "delivery_notes.db")

# Csatlakozás, Row-factory, kurzor
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1) delivery_notes tábla séma
print("=== delivery_notes séma ===")
for cid, name, ctype, notnull, dflt, pk in cur.execute("PRAGMA table_info(delivery_notes)"):
    print(f"{cid:2d}: {name:20s} {ctype:10s} notnull={notnull} default={dflt} pk={pk}")

# 2) delivery_notes tartalom (csak az első néhány rekord)
print("\n=== delivery_notes rekordok (legfeljebb 5) ===")
for row in cur.execute("SELECT * FROM delivery_notes LIMIT 5"):
    pprint(dict(row))

# 3) delivery_note_items tábla séma
print("\n=== delivery_note_items séma ===")
for cid, name, ctype, notnull, dflt, pk in cur.execute("PRAGMA table_info(delivery_note_items)"):
    print(f"{cid:2d}: {name:20s} {ctype:10s} notnull={notnull} default={dflt} pk={pk}")

# 4) delivery_note_items tartalom
print("\n=== delivery_note_items rekordok (legfeljebb 5) ===")
for row in cur.execute("SELECT * FROM delivery_note_items LIMIT 5"):
    pprint(dict(row))

conn.close()
