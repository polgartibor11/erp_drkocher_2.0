import os
import sqlite3

DB_PATH = os.path.join("data", "orders.db")

def init_order_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Külső kulcs támogatás bekapcsolása
        c.execute("PRAGMA foreign_keys = ON")

        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                vevo TEXT,
                beerkezes TEXT,
                megrendeles_szam TEXT,
                szall_hatarido TEXT,
                megjegyzes TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id INTEGER,
                qty REAL,
                fennmarado_mennyiseg REAL,
                mennyisegi_egyseg TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        """)
        # Index order_items.order_id mezőre (teljesítmény)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)
        """)
        conn.commit()
    print(f"Order adatbázis inicializálva: {DB_PATH}")

if __name__ == "__main__":
    init_order_db()
