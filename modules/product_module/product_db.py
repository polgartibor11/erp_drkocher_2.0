import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "products.db")

def init_db():
    if os.path.exists(DB_PATH):
        print("Adatbázis már létezik, nem hozom létre újra.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                vevo_nev TEXT,
                megnevezes TEXT,
                cikkszam TEXT,
                mennyisegi_egyseg TEXT,
                felulet TEXT,
                alapanyagok TEXT,
                suly REAL,
                suly_mertekegyseg TEXT,
                uzem_lanc TEXT,
                feszekszam INTEGER,
                csokosuly REAL,
                csokosuly_mertekegyseg TEXT,
                foto TEXT
            )
        """)
        c.execute("""
            CREATE TABLE arak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                ar REAL,
                valuta TEXT,
                kezdet TEXT,
                veg TEXT,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        conn.commit()
        print("Adatbázis létrehozva.")

if __name__ == "__main__":
    init_db()
