import os
import sqlite3

DB_PATH = os.path.join("data", "products.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Külső kulcs támogatás bekapcsolása
        c.execute("PRAGMA foreign_keys = ON")

        # Termékek tábla
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
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

        # Árak tábla
        c.execute("""
            CREATE TABLE IF NOT EXISTS arak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                ar REAL,
                valuta TEXT,
                kezdet TEXT,
                veg TEXT,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        """)

        # Index a teljesítményhez
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_arak_product_id ON arak(product_id)
        """)

        conn.commit()
    print(f"Adatbázis inicializálva: {DB_PATH}")

if __name__ == "__main__":
    init_db()
