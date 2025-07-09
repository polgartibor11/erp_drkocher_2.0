import sqlite3, csv
from pathlib import Path

# Az orders.db elérési útja ugyanott, ahol az export_orders.py van
db_path = Path(__file__).parent / "orders.db"
conn = sqlite3.connect(str(db_path))
cur  = conn.cursor()
cur.execute("SELECT * FROM orders")
rows = cur.fetchall()

# CSV-fájlba írás
out_csv = Path(__file__).parent / "orders_export.csv"
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # fejléc
    writer.writerow([col[0] for col in cur.description])
    # adat
    writer.writerows(rows)

conn.close()
print(f"Exportálva: {out_csv}")
