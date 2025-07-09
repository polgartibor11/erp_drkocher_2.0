import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "delivery_notes.db")

class DeliveryNoteDB:
    def __init__(self):
        # Megnyitjuk (vagy létrehozzuk) az adatbázist
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()

        # 1) delivery_notes tábla definíciója DEFAULT ''-el
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id             INTEGER    NOT NULL DEFAULT 0,
            note_number          TEXT,      -- <<< EZ KELL!!!
            created_at           TEXT       NOT NULL DEFAULT '',
            status               TEXT       NOT NULL DEFAULT 'pending',
            customer_name        TEXT,
            customer_address     TEXT,
            customer_tax_number  TEXT,
            shipping_name        TEXT,
            shipping_address     TEXT,
            shipping_date        TEXT       NOT NULL DEFAULT ''
        )
        """)

        # 2) delivery_note_items tábla
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_note_items (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_note_id     INTEGER    NOT NULL,
            product_id           INTEGER    NOT NULL,
            quantity             REAL       NOT NULL,
            FOREIGN KEY(delivery_note_id) REFERENCES delivery_notes(id)
        )
        """)

        # 3) Migráció: ha korábbi verzióból futunk, pótoljuk az új oszlopokat
        cols = [row["name"] for row in self.conn.execute(
            "PRAGMA table_info(delivery_notes)"
        ).fetchall()]

        if "order_id" not in cols:
            cur.execute(
                "ALTER TABLE delivery_notes "
                "ADD COLUMN order_id INTEGER NOT NULL DEFAULT 0"
            )
        
        if "note_number" not in cols:
            cur.execute("ALTER TABLE delivery_notes ADD COLUMN note_number TEXT")
            
            
        if "created_at" not in cols:
            cur.execute(
                "ALTER TABLE delivery_notes "
                "ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
        if "status" not in cols:
            cur.execute(
                "ALTER TABLE delivery_notes "
                "ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'"
            )
        if "shipping_date" not in cols:
            cur.execute(
                "ALTER TABLE delivery_notes "
                "ADD COLUMN shipping_date TEXT NOT NULL DEFAULT ''"
            )

        # 4) Backfill: régi sorokra töltsük fel a hiányzó dátumokat
        #   - created_at: ha üres, mostani időpont
        #   - shipping_date: ha üres, legyen egyenlő created_at-tal
        cur.execute("""
            UPDATE delivery_notes
               SET created_at = datetime('now')
             WHERE created_at = ''
        """)
        cur.execute("""
            UPDATE delivery_notes
               SET shipping_date = created_at
             WHERE shipping_date = ''
        """)

        self.conn.commit()

    def insert_delivery_note(self, order_id, customer_info, shipping_info, note_number):
        """
        Új szállítólevél beszúrása. A shipping_date-hez automatikusan
        ugyanazt az időpontot használjuk, mint a created_at-hez.
        """
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO delivery_notes (
                order_id, note_number, created_at, status,
                customer_name, customer_address, customer_tax_number,
                shipping_name, shipping_address, shipping_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, note_number, now, 'pending',
            customer_info.get("customer_name"),
            customer_info.get("customer_address"),
            customer_info.get("customer_tax_number"),
            shipping_info.get("shipping_name"),
            shipping_info.get("shipping_address"),
            now
        ))
        self.conn.commit()
        return cur.lastrowid

    def insert_delivery_note_item(self, delivery_note_id, product_id, quantity):
        self.conn.execute("""
            INSERT INTO delivery_note_items
                (delivery_note_id, product_id, quantity)
            VALUES (?, ?, ?)
        """, (delivery_note_id, product_id, quantity))
        self.conn.commit()

    def get_delivery_note(self, delivery_note_id):
        note = self.conn.execute("""
            SELECT
                id, order_id, note_number, created_at, status,
                customer_name, customer_address, customer_tax_number,
                shipping_name, shipping_address, shipping_date
            FROM delivery_notes
            WHERE id = ?
        """, (delivery_note_id,)).fetchone()

        items = self.conn.execute(
            "SELECT * FROM delivery_note_items WHERE delivery_note_id = ?",
            (delivery_note_id,)
        ).fetchall()

        return note, items

    def get_all_delivery_notes(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT
                id,
                order_id,
                created_at,
                status,
                customer_name,
                shipping_name,
                shipping_date
            FROM delivery_notes
            ORDER BY
                CASE
                  WHEN length(shipping_date)>0 THEN shipping_date
                  WHEN length(created_at)>0  THEN created_at
                  ELSE '1970-01-01'
                END DESC,
                id DESC
        """)
        return cur.fetchall()

    def get_all_delivery_note_items(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT
                id,
                delivery_note_id,
                product_id,
                quantity
            FROM delivery_note_items
            ORDER BY delivery_note_id
        """)
        return cur.fetchall()







