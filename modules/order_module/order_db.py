import sqlite3
import os
from PyQt5.QtCore import Qt

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
ORDERS_DB    = os.path.join(BASE_DIR, "orders.db")
PRODUCTS_DB  = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "product_module", "products.db"))
DELIV_DB     = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "delivery_module", "delivery_notes.db"))

class OrderDB:
    def __init__(self):
        self.conn       = sqlite3.connect(ORDERS_DB)
        self.conn.row_factory = sqlite3.Row
        self.prod_conn  = sqlite3.connect(PRODUCTS_DB)
        self.prod_conn.row_factory = sqlite3.Row
        self.deliv_conn = sqlite3.connect(DELIV_DB)
        self.deliv_conn.row_factory = sqlite3.Row

    def get_all_order_items(self) -> list[dict]:
        """
        Visszaad minden rendelés-tételt az orders.db-ből,
        majd minden sorhoz hozzáfűzi a products.db-ből a termék-,
        ügyfél- és szállítási adatokat.
        """
        # 1) Lekérdezzük az összes rendelés-tételt
        cur = self.conn.execute("""
            SELECT
              o.id               AS order_id,
              o.megrendeles_szam AS order_number,
              o.vevo_nev         AS vevo_nev,
              o.vevo_cim         AS vevo_cim,
              o.vevo_adoszam     AS vevo_adoszam,
              o.szallitasi_nev   AS szallitasi_nev,
              o.szallitasi_cim   AS szallitasi_cim,
              o.beerkezes        AS beerkezes,
              o.szall_hatarido   AS szall_hatarido,
              oi.product_id      AS product_id,
              oi.qty             AS ordered_qty,
              oi.fennmarado_mennyiseg AS remaining_qty,
              oi.mennyisegi_egyseg    AS unit
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            ORDER BY o.id, oi.product_id
        """)
        base_rows = [dict(r) for r in cur.fetchall()]

        result = []
        for r in base_rows:
            # 2) Kiegészítjük a products.db-ből
            p = self.prod_conn.execute("""
                SELECT
                  megnevezes           AS product_name,
                  cikkszam             AS item_number,
                  uzem_lanc            AS plant,                        
                  felulet              AS surface,
                  customer_name        AS cust_name,
                  customer_address     AS cust_address,
                  customer_tax_number  AS cust_tax,
                  customer_eu_tax_number AS cust_eu_tax,
                  customer_country     AS cust_country,
                  shipping_name        AS shp_name,
                  shipping_address     AS shp_address,
                  shipping_country     AS shp_country
                FROM products
                WHERE id = ?
            """, (r["product_id"],)).fetchone()
            prod = dict(p) if p else {}

            result.append({
                # orders + order_items mezők
                "order_id":       r["order_id"],
                "order_number":   r["order_number"],
                "vevo_nev":       r["vevo_nev"],
                "vevo_cim":       r["vevo_cim"],
                "vevo_adoszam":   r["vevo_adoszam"],
                "szallitasi_nev": r["szallitasi_nev"],
                "szallitasi_cim": r["szallitasi_cim"],
                "beerkezes":      r["beerkezes"],
                "szall_hatarido": r["szall_hatarido"],
                "product_id":     r["product_id"],
                "ordered_qty":    r["ordered_qty"],
                "remaining_qty":  r["remaining_qty"],
                "unit":           r["unit"],
                # products.db mezők
                "product_name":   prod.get("product_name", ""),
                "item_number":    prod.get("item_number", ""),
                "plant":          prod.get("plant", ""),
                "price":          prod.get("price", ""),               
                "surface":        prod.get("surface", ""),
                "cust_name":      prod.get("cust_name", ""),
                "cust_address":   prod.get("cust_address", ""),
                "cust_tax":       prod.get("cust_tax", ""),
                "cust_eu_tax":    prod.get("cust_eu_tax", ""),
                "cust_country":   prod.get("cust_country", ""),
                "shp_name":       prod.get("shp_name", ""),
                "shp_address":    prod.get("shp_address", ""),
                "shp_country":    prod.get("shp_country", "")
            })
        return result

    def get_order_items(self, order_id: int) -> list[dict]:
        """
        Lekérdezi egy rendelés aktuálisan fennmaradó tételeit, és hozzáfűzi a termék nevét.
        """
        cur = self.conn.execute("""
            SELECT product_id,
                   fennmarado_mennyiseg AS quantity
              FROM order_items
             WHERE order_id = ?
               AND fennmarado_mennyiseg > 0
        """, (order_id,))
        rows = cur.fetchall()

        items = []
        for r in rows:
            prod_row = self.prod_conn.execute(
                "SELECT megnevezes AS product_name FROM products WHERE id = ?",
                (r["product_id"],)
            ).fetchone()
            product_name = prod_row["product_name"] if prod_row else ""
            items.append({
                "product_id":   r["product_id"],
                "product_name": product_name,
                "quantity":     r["quantity"]
            })
        return items

    def get_pending_items_list(self) -> list[dict]:
        """
        Visszaadja az összes rendelés-tételt, ahol fennmaradó mennyiség > 0,
        és összevonja az orders, order_items és products táblákból a szükséges mezőket.
        """
        cur = self.conn.execute("""
            SELECT
              oi.order_id,
              o.megrendeles_szam       AS order_number,
              o.vevo_nev               AS customer_name,
              o.vevo_cim               AS customer_address,
              o.vevo_adoszam           AS customer_tax_number,
              o.vevo_eu_adoszam        AS customer_eu_tax_number,
              o.vevo_orszag            AS customer_country,
              o.szallitasi_nev         AS shipping_name,
              o.szallitasi_cim         AS shipping_address,
              o.szallitasi_orszag      AS shipping_country,
              o.beerkezes              AS beerkezes,
              o.szall_hatarido         AS szall_hatarido,
              oi.product_id,
              oi.fennmarado_mennyiseg  AS remaining_qty,
              oi.mennyisegi_egyseg     AS unit
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE oi.fennmarado_mennyiseg > 0
            ORDER BY oi.order_id
        """)
        base_rows = [dict(r) for r in cur.fetchall()]

        items = []
        for r in base_rows:
            prod_row = self.prod_conn.execute(
                """
                SELECT
                  megnevezes  AS product_name,
                  cikkszam    AS item_number,
                  uzem_lanc   AS plant
                FROM products
                WHERE id = ?
                """,
                (r["product_id"],)
            ).fetchone()
            prod = dict(prod_row) if prod_row else {}

            sum_row = self.deliv_conn.execute("""
                SELECT SUM(dni.quantity) AS delivered
                  FROM delivery_notes dn
                  JOIN delivery_note_items dni ON dn.id = dni.delivery_note_id
                 WHERE dn.order_id = ? AND dni.product_id = ?
            """, (r["order_id"], r["product_id"])).fetchone()
            delivered = sum_row["delivered"] or 0
            ordered = r["remaining_qty"] + delivered

            items.append({
                "order_id":               r["order_id"],
                "order_number":           r["order_number"],
                "customer_name":          r["customer_name"],
                "customer_address":       r["customer_address"],
                "customer_tax_number":    r["customer_tax_number"],
                "customer_eu_tax_number": r["customer_eu_tax_number"],
                "customer_country":       r["customer_country"],
                "shipping_name":          r["shipping_name"],
                "shipping_address":       r["shipping_address"],
                "shipping_country":       r["shipping_country"],
                "beerkezes":              r["beerkezes"],
                "szall_hatarido":         r["szall_hatarido"],
                "plant":                  prod.get("plant", ""),
                "product_name":           prod.get("product_name", ""),
                "item_number":            prod.get("item_number", ""),
                "ordered_qty":            ordered,
                "remaining_qty":          r["remaining_qty"],
                "unit":                   r["unit"],
                "product_id":             r["product_id"]
            })
        return items

    def get_order_with_product_info(self, order_id: int, product_id: int) -> dict | None:
        """
        Lekéri egy rendelés+tétel alapadatait az orders.db-ből,
        majd kiegészíti a products.db-ből a termék-, vevő- és szállítási adatokkal.
        """
        # 1) Alapvető order + order_item adatok az orders.db-ből
        cur = self.conn.execute("""
            SELECT
              o.id                      AS order_id,
              o.megrendeles_szam        AS order_number,
              o.vevo_nev                AS customer_name,
              o.vevo_cim                AS customer_address,
              o.vevo_adoszam            AS customer_tax_number,
              o.szallitasi_nev          AS shipping_name,
              o.szallitasi_cim          AS shipping_address,
              o.beerkezes               AS beerkezes,
              o.szall_hatarido          AS szall_hatarido,
              oi.product_id             AS product_id,
              oi.qty                    AS ordered_qty,
              oi.fennmarado_mennyiseg   AS remaining_qty,
              oi.mennyisegi_egyseg      AS unit
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.id = ? AND oi.product_id = ?
        """, (order_id, product_id))
        row = cur.fetchone()
        if not row:
            return None
        info = dict(row)

        # 2) Kiegészítő adatok a products.db-ből
        p = self.prod_conn.execute("""
            SELECT
              megnevezes               AS product_name,
              cikkszam                 AS item_number,
              felulet                  AS surface,
              customer_eu_tax_number   AS customer_eu_tax_number,
              customer_country         AS customer_country,
              shipping_country         AS shipping_country
            FROM products
            WHERE id = ?
        """, (product_id,)).fetchone()

        if p:
            prod = dict(p)
            info.update({
                "product_name":            prod["product_name"],
                "item_number":             prod["item_number"],
                "surface":                 prod.get("surface", ""),
                "customer_eu_tax_number":  prod.get("customer_eu_tax_number", ""),
                "customer_country":        prod.get("customer_country", ""),
                "shipping_country":        prod.get("shipping_country", "")
            })
        else:
            # ha valamiért nem lenne meg a product, adjunk üres mezőket
            info.update({
                "product_name":            "",
                "item_number":             "",
                "surface":                 "",
                "customer_eu_tax_number":  "",
                "customer_country":        "",
                "shipping_country":        ""
            })

        return info

    def decrease_item_qty(self, order_id: int, product_id: int, qty: float):
        self.conn.execute("""
            UPDATE order_items
               SET fennmarado_mennyiseg = fennmarado_mennyiseg - ?
             WHERE order_id = ? AND product_id = ?
        """, (qty, order_id, product_id))
        self.conn.commit()

    def get_remaining_qty(self, order_id: int, product_id: int) -> float:
        cur = self.conn.execute("""
            SELECT fennmarado_mennyiseg AS qty
              FROM order_items
             WHERE order_id = ? AND product_id = ?
        """, (order_id, product_id))
        row = cur.fetchone()
        return row["qty"] if row else 0.0

    def delete_item(self, order_id: int, product_id: int):
        self.conn.execute("""
            DELETE FROM order_items
             WHERE order_id = ? AND product_id = ?
        """, (order_id, product_id))
        self.conn.commit()

    def count_items(self, order_id: int) -> int:
        cur = self.conn.execute("""
            SELECT COUNT(*) AS cnt
              FROM order_items
             WHERE order_id = ?
        """, (order_id,))
        return cur.fetchone()["cnt"]

    def delete_order(self, order_id: int):
        self.conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        self.conn.commit()







