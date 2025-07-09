# gui/view_deliveries_gui.py

import sys
import os
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

# ─── 1) APP_DIR meghatározása ────────────────────────────────────────────
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.argv[0]).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

# ─── 2) Importútvonal ────────────────────────────────────────────────────
sys.path.insert(0, str(APP_DIR / "modules"))

from delivery_module.delivery_note_db import DeliveryNoteDB
from product_module.product_module       import osszes_termek
from order_module.order_module           import osszes_megrendeles

def get_note_value(note, key, default=None):
    # sqlite3.Row fallback getter
    try:
        return note[key]
    except Exception:
        return default

class ViewDeliveriesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dr. Köcher Kft. – Kiszállítások áttekintése")
        self.resize(900, 550)

        # adatbázis és cache
        self.db            = DeliveryNoteDB()
        self._all_products = osszes_termek()
        self._orders       = osszes_megrendeles()

        # UI összeállítása
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        # fejléc
        header = QHBoxLayout()
        logo_path = APP_DIR / "logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(50, 50, Qt.KeepAspectRatio)
            header.addWidget(QLabel(pixmap=pix))
        header.addWidget(QLabel("<h2>Kiszállítások</h2>"))
        header.addStretch()
        v.addLayout(header)

        # szűrők sor
        filter_layout = QHBoxLayout()
        for label_text, attr, placeholder in [
            ("Dátum:",       "filter_date",     "YYYY.MM.DD"),
            ("Vevő:",        "filter_customer", "részlet"),
            ("Cikkszám:",    "filter_sku",      "részlet"),
            ("Termék:",      "filter_product",  "részlet"),
            ("Megrendelés:", "filter_order",    "részlet"),
        ]:
            filter_layout.addWidget(QLabel(label_text))
            le = QLineEdit()
            le.setPlaceholderText(placeholder)
            setattr(self, attr, le)
            filter_layout.addWidget(le)
            le.textChanged.connect(self.load_data)
        v.addLayout(filter_layout)

        # táblázat: 8 oszlop
        self.tbl = QTableWidget(0, 8)
        self.tbl.setHorizontalHeaderLabels([
            "Szállítás dátuma",
            "Szállítólevél száma",
            "Vevő neve",
            "Megrendelési szám",
            "Termék megnevezése",
            "Cikkszám",
            "Szállított mennyiség",
            "Egység",
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.tbl)

        # Frissítés gomb
        btn_refresh = QPushButton("Frissítés")
        btn_refresh.clicked.connect(self.load_data)
        v.addWidget(btn_refresh, alignment=Qt.AlignRight)

        # első adatbetöltés
        self.load_data()

    def load_data(self):
        self.tbl.setRowCount(0)

        date_f = self.filter_date.text().strip()
        cust_f = self.filter_customer.text().strip().lower()
        sku_f  = self.filter_sku.text().strip().lower()
        prod_f = self.filter_product.text().strip().lower()
        order_f= self.filter_order.text().strip().lower()

        for ti in self.db.get_all_delivery_note_items():
            note_id = ti["delivery_note_id"]
            note, _ = self.db.get_delivery_note(note_id)

            raw = get_note_value(note, "shipping_date") or get_note_value(note, "created_at") or ""
            try:
                dt = datetime.fromisoformat(raw)
                ship_date = dt.strftime("%Y.%m.%d")
            except Exception:
                ship_date = raw

            customer_name = get_note_value(note, "customer_name", "")
            order_id      = get_note_value(note, "order_id")
            od            = next((o for o in self._orders if o.id == order_id), None)
            order_number  = od.megrendeles_szam if od else str(order_id)

            prod = next((p for p in self._all_products if p.id == ti["product_id"]), None)
            product_name  = prod.megnevezes        if prod else ""
            cikkszam       = prod.cikkszam          if prod else ""
            unit           = prod.mennyisegi_egyseg if prod else ""
            ship_qty       = ti["quantity"]

            # szűrők
            if date_f  and date_f not in ship_date:          continue
            if cust_f  and cust_f not in customer_name.lower(): continue
            if order_f and order_f not in order_number.lower(): continue
            if sku_f   and sku_f not in cikkszam.lower():    continue
            if prod_f  and prod_f not in product_name.lower(): continue

            r = self.tbl.rowCount()
            self.tbl.insertRow(r)

            vals = [
                dt.strftime("%Y.%m.%d %H:%M") if raw else "",
                get_note_value(note, "note_number", ""),   # <-- Ezt tedd ide!
                customer_name,
                order_number,
                product_name,
                cikkszam,
                ship_qty,
                unit
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.tbl.setItem(r, c, it)

def main():
    app = QApplication(sys.argv)
    w = ViewDeliveriesWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()





