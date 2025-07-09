# modules/manufacturing_module/inventory_db.py

import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "production_inventory.db")

class InventoryDB:
    def __init__(self):
        # Csatlakozás és row_factory beállítása
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self.conn.cursor()

        # 1) production_inventory
        cur.execute("""
        CREATE TABLE IF NOT EXISTS production_inventory (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id    INTEGER    NOT NULL,
            quantity      REAL       NOT NULL,
            batch_number  TEXT,
            created_at    TEXT       NOT NULL DEFAULT '',
            note          TEXT
        )
        """)

        # 2) inventory_movements
        cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id     INTEGER    NOT NULL,
            movement_type    TEXT       NOT NULL,
            quantity         REAL       NOT NULL,
            movement_at      TEXT       NOT NULL DEFAULT '',
            reference        TEXT
        )
        """)

        # 3) product_tooling
        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_tooling (
            product_id     INTEGER PRIMARY KEY,
            tooling        TEXT       NOT NULL,
            updated_at     TEXT       NOT NULL
        )
        """)

        # 4) product_norms (előírt norma)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_norms (
            product_id INTEGER PRIMARY KEY,
            norm       INTEGER NOT NULL,
            updated_at TEXT    NOT NULL
        )
        """)

        # 5) machine_jobs (aktív gyártások követése)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS machine_jobs (
            machine     TEXT    PRIMARY KEY,
            product_id  INTEGER NOT NULL,
            start_at    TEXT    NOT NULL,
            status      TEXT    NOT NULL    -- 'active' vagy 'stopped'
        )
        """)

        # 6) operators
        cur.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            name TEXT PRIMARY KEY
        )
        """)

        # 7) shift_logs (műszaknapló, most már product_id-vel)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS shift_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            machine       TEXT       NOT NULL,
            product_id    INTEGER    NOT NULL,
            operator      TEXT       NOT NULL,
            start_time    TEXT       NOT NULL,
            end_time      TEXT       NOT NULL,
            date          TEXT       NOT NULL DEFAULT '',
            shift_type    TEXT       NOT NULL DEFAULT '',
            shots         INTEGER    NOT NULL DEFAULT 0,
            scrap_shots   INTEGER    NOT NULL DEFAULT 0,
            good_qty      REAL       NOT NULL DEFAULT 0,
            scrap_qty     REAL       NOT NULL DEFAULT 0,
            created_at    TEXT       NOT NULL DEFAULT ''
        )
        """)

        # 8) shift_downtimes
        cur.execute("""
        CREATE TABLE IF NOT EXISTS shift_downtimes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            machine    TEXT    NOT NULL,
            date       TEXT    NOT NULL,
            shift_type TEXT    NOT NULL,
            cause      TEXT    NOT NULL,
            hours      REAL    NOT NULL
        )
        """)

        # Backfill a régi rekordoknál
        cur.execute("UPDATE production_inventory SET created_at = datetime('now') WHERE created_at = ''")
        cur.execute("UPDATE inventory_movements  SET movement_at = datetime('now')   WHERE movement_at = ''")
        cur.execute("UPDATE shift_logs          SET created_at = datetime('now')   WHERE created_at = ''")
        self.conn.commit()

    # ──────────────────────────────────────────────────────────
    # Gyártási rögzítés, mozgások
    # ──────────────────────────────────────────────────────────

    def add_production(self, product_id: int, quantity: float,
                       batch_number: str = None, note: str = None) -> int:
        """
        Rögzíti a gyártott mennyiséget és naplózza az 'in' mozgást a megadott mennyiséggel.
        """
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO production_inventory
              (product_id, quantity, batch_number, created_at, note)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, quantity, batch_number or '', now, note or ''))
        self.conn.commit()
        inv_id = cur.lastrowid

        # automatikus 'in' mozgás naplózása: itt ADJUK ÁT a mennyiséget is!
        self.log_movement(inv_id, 'in', quantity)
        return inv_id

    def log_movement(self, inventory_id: int, movement_type: str,
                     quantity: float, reference: str = None) -> int:
        """
        Rögzít egy készletmozgást ('in' vagy 'out'), mennyiséggel és opcionális referenciával.
        """
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO inventory_movements
              (inventory_id, movement_type, quantity, movement_at, reference)
            VALUES (?, ?, ?, ?, ?)
        """, (inventory_id, movement_type, quantity, now, reference or ''))
        self.conn.commit()
        return cur.lastrowid

    # ──────────────────────────────────────────────────────────
    # Készlet lekérdezés
    # ──────────────────────────────────────────────────────────

    def get_current_stock(self, product_id: int) -> float:
        cur = self.conn.cursor()
        cur.execute("SELECT SUM(quantity) AS total_in FROM production_inventory WHERE product_id = ?", (product_id,))
        total_in = cur.fetchone()['total_in'] or 0.0
        cur.execute("""
            SELECT SUM(im.quantity) AS total_out
              FROM inventory_movements im
              JOIN production_inventory pi ON im.inventory_id = pi.id
             WHERE im.movement_type = 'out' AND pi.product_id = ?
        """, (product_id,))
        total_out = cur.fetchone()['total_out'] or 0.0
        return total_in - total_out

    # ──────────────────────────────────────────────────────────
    # Szerszám azonosító kezelése
    # ──────────────────────────────────────────────────────────

    def set_tooling(self, product_id: int, tooling: str):
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO product_tooling(product_id, tooling, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
              tooling    = excluded.tooling,
              updated_at = excluded.updated_at
        """, (product_id, tooling, now))
        self.conn.commit()

    def get_tooling(self, product_id: int) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT tooling FROM product_tooling WHERE product_id = ?", (product_id,))
        row = cur.fetchone()
        return row["tooling"] if row else ""

    # ──────────────────────────────────────────────────────────
    # Norma (előírt lövés/shift) kezelése
    # ──────────────────────────────────────────────────────────

    def set_norm(self, product_id: int, norm: int):
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO product_norms(product_id, norm, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
              norm       = excluded.norm,
              updated_at = excluded.updated_at
        """, (product_id, norm, now))
        self.conn.commit()

    def get_norm(self, product_id: int) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT norm FROM product_norms WHERE product_id = ?", (product_id,))
        row = cur.fetchone()
        return row["norm"] if row else 0

    # ──────────────────────────────────────────────────────────
    # Gépmunka kezelése
    # ──────────────────────────────────────────────────────────

    def has_active_job(self, machine: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM machine_jobs WHERE machine = ? AND status = 'active'", (machine,))
        return cur.fetchone() is not None

    def get_active_job_product(self, machine: str):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id FROM machine_jobs WHERE machine = ? AND status = 'active'", (machine,))
        row = cur.fetchone()
        return row["product_id"] if row else None

    def start_job(self, machine: str, product_id: int):
        now = datetime.now().isoformat(timespec='seconds')
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO machine_jobs(machine, product_id, start_at, status)
            VALUES (?, ?, ?, 'active')
            ON CONFLICT(machine) DO UPDATE SET
              product_id = excluded.product_id,
              start_at   = excluded.start_at,
              status     = 'active'
        """, (machine, product_id, now))
        self.conn.commit()

    def stop_job(self, machine: str):
        cur = self.conn.cursor()
        cur.execute("UPDATE machine_jobs SET status = 'stopped' WHERE machine = ?", (machine,))
        self.conn.commit()

    # ──────────────────────────────────────────────────────────
    # Operátorok kezelése
    # ──────────────────────────────────────────────────────────

    def list_operators(self) -> list[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM operators ORDER BY name")
        return [row["name"] for row in cur.fetchall()]

    def add_operator(self, name: str):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO operators(name) VALUES (?)", (name,))
        self.conn.commit()

    # ──────────────────────────────────────────────────────────
    # Műszaknapló kezelése (shift_logs)
    # ──────────────────────────────────────────────────────────

    def add_shift_log(self, machine: str, operator: str, date: str,
                      shift_type: str, shots: int, scrap_shots: int,
                      good_qty: float, scrap_qty: float) -> int:
        now = datetime.now().isoformat(timespec='seconds')
        pid = self.get_active_job_product(machine)
        start_ts = f"{date} 00:00:00"
        end_ts   = f"{date} 23:59:59"
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO shift_logs
              (machine, product_id, operator,
               start_time, end_time, date, shift_type,
               shots, scrap_shots, good_qty, scrap_qty, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            machine, pid, operator,
            start_ts, end_ts, date, shift_type,
            shots, scrap_shots, good_qty, scrap_qty,
            now
        ))
        self.conn.commit()
        return cur.lastrowid

    def list_shift_logs(self, machine: str = None):
        cur = self.conn.cursor()
        if machine:
            cur.execute("SELECT * FROM shift_logs WHERE machine = ? ORDER BY date DESC", (machine,))
        else:
            cur.execute("SELECT * FROM shift_logs ORDER BY date DESC")
        return cur.fetchall()

    # ──────────────────────────────────────────────────────────
    # Állásidő kezelés
    # ──────────────────────────────────────────────────────────

    def add_downtime(self, machine: str, date: str, shift_type: str, cause: str, hours: float) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO shift_downtimes
              (machine, date, shift_type, cause, hours)
            VALUES (?, ?, ?, ?, ?)
        """, (machine, date, shift_type, cause, hours))
        self.conn.commit()
        return cur.lastrowid

    def get_shift_downtime(self, machine: str, date: str, shift_type: str) -> float:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT SUM(hours) AS total
              FROM shift_downtimes
             WHERE machine = ? AND date = ? AND shift_type = ?
        """, (machine, date, shift_type))
        row = cur.fetchone()
        return row["total"] or 0.0








