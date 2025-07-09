import sqlite3
import pandas as pd

db_file = 'products.db'  # Itt a db fájl nevét cseréld!
conn = sqlite3.connect(db_file)

tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
for table_name in tables['name']:
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    df.to_csv(f"{table_name}.csv", index=False)
    print(f"{table_name}.csv exportálva!")

conn.close()
