from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "orders.db")

def init_order_db() -> None:
    """Létrehozza vagy frissíti az orders adatbázist a szükséges mezőkkel."""
    need_init = not os.path.exists(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if need_init:
            c.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    vevo_nev TEXT,
                    vevo_cim TEXT,
                    vevo_adoszam TEXT,
                    szallitasi_nev TEXT,
                    szallitasi_cim TEXT,
                    beerkezes TEXT,
                    megrendeles_szam TEXT,
                    szall_hatarido TEXT,
                    megjegyzes TEXT
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    order_id INTEGER,
                    product_id INTEGER,
                    qty REAL,
                    fennmarado_mennyiseg REAL,
                    mennyisegi_egyseg TEXT,
                    PRIMARY KEY(order_id, product_id),
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            """)
            conn.commit()
        else:
            # Ha már van adatbázis, ellenőrizzük az oszlopokat és bővítjük, ha hiányoznak
            c.execute("PRAGMA table_info(orders)")
            existing_cols = {col[1] for col in c.fetchall()}
            needed_cols = {
                "vevo_nev": "TEXT",
                "vevo_cim": "TEXT",
                "vevo_adoszam": "TEXT",
                "szallitasi_nev": "TEXT",
                "szallitasi_cim": "TEXT",
            }
            for col_name, col_type in needed_cols.items():
                if col_name not in existing_cols:
                    c.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type} DEFAULT ''")
            conn.commit()

@dataclass
class Tetel:
    product_id: int   # egységesen product_id
    qty: float
    fennmarado_mennyiseg: float
    mennyisegi_egyseg: str

@dataclass
class Order:
    id: int
    vevo_nev: str
    vevo_cim: str
    vevo_adoszam: str
    szallitasi_nev: str
    szallitasi_cim: str
    beerkezes: str
    megrendeles_szam: str
    szall_hatarido: str
    megjegyzes: str
    tetelek: List[Tetel] = field(default_factory=list)

def _row_to_tetel(row) -> Tetel:
    product_id, qty, fennmarado_mennyiseg, mennyisegi_egyseg = row
    return Tetel(product_id, qty, fennmarado_mennyiseg, mennyisegi_egyseg)

def _row_to_order(row, tetelek_rows) -> Order:
    (id_, vevo_nev, vevo_cim, vevo_adoszam, szallitasi_nev, szallitasi_cim,
     beerkezes, megrendeles_szam, szall_hatarido, megjegyzes) = row
    tetelek = [_row_to_tetel(t) for t in tetelek_rows]
    return Order(id_, vevo_nev, vevo_cim, vevo_adoszam, szallitasi_nev, szallitasi_cim,
                 beerkezes, megrendeles_szam, szall_hatarido, megjegyzes, tetelek)

def osszes_megrendeles() -> List[Order]:
    if not os.path.exists(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, vevo_nev, vevo_cim, vevo_adoszam, szallitasi_nev, szallitasi_cim,
                     beerkezes, megrendeles_szam, szall_hatarido, megjegyzes FROM orders""")
        orders_rows = c.fetchall()

        orders = []
        for o_row in orders_rows:
            order_id = o_row[0]
            c.execute("SELECT product_id, qty, fennmarado_mennyiseg, mennyisegi_egyseg FROM order_items WHERE order_id = ?", (order_id,))
            tetel_rows = c.fetchall()
            orders.append(_row_to_order(o_row, tetel_rows))
        return orders

def uj_id() -> int:
    if not os.path.exists(DB_PATH):
        return 1
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(id) FROM orders")
        max_id = c.fetchone()[0]
        return (max_id or 0) + 1

def hozzaad_megrendeles(o: Order) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO orders (id, vevo_nev, vevo_cim, vevo_adoszam, szallitasi_nev, szallitasi_cim,
                                beerkezes, megrendeles_szam, szall_hatarido, megjegyzes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (o.id, o.vevo_nev, o.vevo_cim, o.vevo_adoszam, o.szallitasi_nev, o.szallitasi_cim,
              o.beerkezes, o.megrendeles_szam, o.szall_hatarido, o.megjegyzes))
        for t in o.tetelek:
            c.execute("""
                INSERT INTO order_items (order_id, product_id, qty, fennmarado_mennyiseg, mennyisegi_egyseg)
                VALUES (?, ?, ?, ?, ?)
            """, (o.id, t.product_id, t.qty, t.fennmarado_mennyiseg, t.mennyisegi_egyseg))
        conn.commit()

def frissit_megrendeles(o: Order) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE orders SET
                vevo_nev = ?, vevo_cim = ?, vevo_adoszam = ?, szallitasi_nev = ?, szallitasi_cim = ?,
                beerkezes = ?, megrendeles_szam = ?, szall_hatarido = ?, megjegyzes = ?
            WHERE id = ?
        """, (o.vevo_nev, o.vevo_cim, o.vevo_adoszam, o.szallitasi_nev, o.szallitasi_cim,
              o.beerkezes, o.megrendeles_szam, o.szall_hatarido, o.megjegyzes, o.id))
        c.execute("DELETE FROM order_items WHERE order_id = ?", (o.id,))
        for t in o.tetelek:
            c.execute("""
                INSERT INTO order_items (order_id, product_id, qty, fennmarado_mennyiseg, mennyisegi_egyseg)
                VALUES (?, ?, ?, ?, ?)
            """, (o.id, t.product_id, t.qty, t.fennmarado_mennyiseg, t.mennyisegi_egyseg))
        conn.commit()

def torol_megrendeles(rid: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM order_items WHERE order_id = ?", (rid,))
        c.execute("DELETE FROM orders WHERE id = ?", (rid,))
        conn.commit()

def frissit_megrendeles_tetel(order_id: int, product_id: int, uj_fennmarado: float) -> None:
    """Frissíti az adott megrendelés adott termékének fennmaradó mennyiségét."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE order_items
            SET fennmarado_mennyiseg = ?
            WHERE order_id = ? AND product_id = ?
        """, (uj_fennmarado, order_id, product_id))
        conn.commit()









