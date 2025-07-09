# modules/delivery_module/delivery_module.py

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "delivery_notes.db")

class DeliveryNoteDB:
    def __init__(self):
        # Csatlakozás és tábla/oszlop ellenőrzés
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables_and_columns()

    def _ensure_tables_and_columns(self):
        # 1) delivery_notes tábla
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS delivery_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT
                -- további oszlopokat lent adjuk hozzá, ha hiányoznak
            )
        """)

        # 2) delivery_note_items tábla
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS delivery_note_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_note_id INTEGER,
                product_id INTEGER,
                quantity REAL,
                FOREIGN KEY(delivery_note_id) REFERENCES delivery_notes(id)
            )
        """)

        # 3) delivery_notes tábla oszlopai, beleértve a manuális számozáshoz szükséges note_number-t
        needed = {
            "order_id":              "INTEGER",
            "note_number":           "TEXT",
            "customer_name":         "TEXT",
            "customer_address":      "TEXT",
            "customer_tax_number":   "TEXT",
            "customer_eu_tax_number":"TEXT",
            "customer_country":      "TEXT",
            "shipping_name":         "TEXT",
            "shipping_address":      "TEXT",
            "shipping_country":      "TEXT"
        }
        cur = self.conn.execute("PRAGMA table_info(delivery_notes)")
        existing = {row["name"] for row in cur.fetchall()}

        for col, coltype in needed.items():
            if col not in existing:
                self.conn.execute(f"ALTER TABLE delivery_notes ADD COLUMN {col} {coltype}")

        self.conn.commit()

    def get_existing_numbers(self, prefix: str) -> list[str]:
        """
        Visszaadja azokat a note_number-öket, amelyek a megadott prefixszel kezdődnek.
        """
        cur = self.conn.execute("""
            SELECT note_number FROM delivery_notes
            WHERE note_number LIKE ?
        """, (prefix + '%',))
        return [row["note_number"] for row in cur.fetchall() if row["note_number"]]

    def exists_delivery_note_number(self, note_number: str) -> bool:
        """
        Ellenőrzi, hogy a megadott note_number létezik-e már.
        """
        cur = self.conn.execute("""
            SELECT 1 FROM delivery_notes WHERE note_number = ?
        """, (note_number,))
        return cur.fetchone() is not None

    def insert_delivery_note_with_number(self,
                                         order_id: int,
                                         customer_info: dict,
                                         shipping_info: dict,
                                         note_number: str) -> int:
        """
        Beszúr egy új delivery_notes sort a kézi note_number-rel, visszaadja az új ID-t.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO delivery_notes (
                order_id, note_number,
                customer_name, customer_address, customer_tax_number,
                customer_eu_tax_number, customer_country,
                shipping_name, shipping_address, shipping_country
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            note_number,
            customer_info["name"],       customer_info["address"],
            customer_info["tax_number"], customer_info["eu_tax_number"],
            customer_info["country"],
            shipping_info["name"],       shipping_info["address"],
            shipping_info["country"]
        ))
        self.conn.commit()
        return cursor.lastrowid

    def insert_delivery_note_item(self,
                                  delivery_note_id: int,
                                  product_id: int,
                                  quantity: float):
        """
        Beszúr egy tételt a delivery_note_items táblába.
        """
        self.conn.execute("""
            INSERT INTO delivery_note_items (delivery_note_id, product_id, quantity)
            VALUES (?, ?, ?)
        """, (delivery_note_id, product_id, quantity))
        self.conn.commit()


class DeliveryModule:
    def __init__(self):
        self.delivery_db = DeliveryNoteDB()

    def generate_delivery_note_for_order(self,
                                         order_id: int,
                                         customer_info: dict,
                                         shipping_info: dict,
                                         entries: list[dict],
                                         note_number: str) -> int:
        """
        Létrehoz egy szállítólevelet a rendeléshez a megadott note_number-rel,
        majd visszaadja az új delivery_note ID-t.
        """
        # Beszúrjuk a fejléces sort a felhasználó által bevitt számmal
        note_id = self.delivery_db.insert_delivery_note_with_number(
            order_id,
            customer_info,
            shipping_info,
            note_number
        )

        # Beszúrjuk a tételsorokat
        for e in entries:
            self.delivery_db.insert_delivery_note_item(
                note_id, e["product_id"], e["quantity"]
            )

        return note_id






