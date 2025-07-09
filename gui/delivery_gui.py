
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os
from datetime import date
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QMessageBox,
    QFileDialog, QInputDialog, QDialog, QDateEdit, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDate, QUrl

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# project / modules útvonalak
this_dir    = os.path.dirname(__file__)
project_dir = os.path.abspath(os.path.join(this_dir, os.pardir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from modules.product_module.product_module     import osszes_termek
from modules.order_module.order_db             import OrderDB
from modules.delivery_module.delivery_module   import DeliveryModule


class DateDialog(QDialog):
    """Szállítási határidő választó."""
    def __init__(self, default_date, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Szállítás dátuma")
        layout = QVBoxLayout(self)
        self.date_edit = QDateEdit(default_date)
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(QLabel("Szállítási dátuma:"))
        layout.addWidget(self.date_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def date_str(self):
        return self.date_edit.date().toString("yyyy.MM.dd")


class DeliveryWindow(QWidget):
    def __init__(self):
        super().__init__()
        # útvonalak
        self.project_dir  = project_dir
        self.template_dir = os.path.join(self.project_dir, "templates")

        # DB és terméklista
        self.order_db = OrderDB()
        self.dm       = DeliveryModule()
        self.products = osszes_termek()

        # betöltés + ship_qty előkészítése
        self.data = self.order_db.get_all_order_items()
        for r in self.data:
            r['ship_qty'] = r['remaining_qty']

        # UI kezdeti állapot
        self.current_lang = "hu"
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        self.setWindowTitle("Kiszállítási modul")
        self.resize(1000, 600)
        main = QVBoxLayout(self)

        # — fejléc: logo + cég + cím + nyelvválasztó —
        hdr = QHBoxLayout()
        logo_lbl = QLabel()
        lp = os.path.join(self.project_dir, "logo.png")
        if os.path.exists(lp):
            logo_lbl.setPixmap(QPixmap(lp).scaledToHeight(30, Qt.SmoothTransformation))
        hdr.addWidget(logo_lbl, alignment=Qt.AlignLeft)
        hdr.addWidget(QLabel(
            "<b>Dr. Köcher Kft.</b><br/>2300 Ráckeve, Vásártér utca 15, Magyarország"
        ))
        hdr.addStretch()
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Magyar", "hu")
        self.lang_combo.addItem("Deutsch", "de")
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        hdr.addWidget(self.lang_combo, alignment=Qt.AlignRight)
        main.addLayout(hdr)

        # — vevő szűrő —
        main.addWidget(QLabel("Vevő szűrés:"))
        self.customer_combo = QComboBox()
        self.customer_combo.addItem("Összes vevő")
        # egyedi vevőnevek a data alapján
        neveks = sorted({r["cust_name"] for r in self.data if r["cust_name"]})
        for name in neveks:
            self.customer_combo.addItem(name)
        self.customer_combo.currentIndexChanged.connect(self._refresh_table)
        main.addWidget(self.customer_combo)

        # — táblázat —
        self.table = QTableWidget()
        cols = [
            ("Küld",              None,            "checkbox"),
            ("Megrendelési szám", "order_number",  None),
            ("Vevő neve",         "cust_name",     None),
            ("Termék neve",       "product_name",  None),
            ("Cikkszám",          "item_number",   None),
            ("Felület",           "surface",       None),
            ("Megrendelt",        "ordered_qty",   None),
            ("Fennmaradó",        "remaining_qty", None),
            ("Egység",            "unit",          None),
            ("Szállítási menny.", "ship_qty",      "editable"),
            ("Határidő",          "szall_hatarido",None),
        ]
        self.columns = cols
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([h[0] for h in cols])
        main.addWidget(self.table)

        # — generálás gomb —
        btn = QPushButton("Szállítólevél generálása")
        btn.clicked.connect(self.on_generate)
        main.addWidget(btn, alignment=Qt.AlignRight)

        self.setLayout(main)

    def _on_lang_changed(self, _):
        self.current_lang = self.lang_combo.currentData()
        # (ha a vevőlista nyelve is változna, itt frissíthetnéd)

    def _refresh_table(self):
        # először szűrjük vevőre
        sel = self.customer_combo.currentText()
        if sel == "Összes vevő":
            rows = [r for r in self.data if r["remaining_qty"] > 0]
        else:
            rows = [r for r in self.data
                    if r["remaining_qty"] > 0 and r["cust_name"] == sel]

        self.filtered = rows
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, (hdr, key, mode) in enumerate(self.columns):
                if mode == "checkbox":
                    it = QTableWidgetItem()
                    it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    it.setCheckState(Qt.Unchecked)
                    self.table.setItem(r, c, it)
                elif mode == "editable":
                    le = QLineEdit(str(row.get(key, 0)))
                    le.setProperty("remaining_qty", row["remaining_qty"])
                    self.table.setCellWidget(r, c, le)
                else:
                    val = row.get(key, "")
                    self.table.setItem(r, c, QTableWidgetItem(str(val)))
        self.table.resizeColumnsToContents()

    def on_generate(self):
        # 1) összegyűjtjük a kiválasztott tételeket vevőnként
        groups = {}
        for r, row in enumerate(self.filtered):
            cb = self.table.item(r, 0)
            if cb.checkState() != Qt.Checked:
                continue
            qty_w = self.table.cellWidget(r, 9)
            try:
                qty = float(qty_w.text())
            except:
                QMessageBox.warning(self, "Hiba", "Érvénytelen szállítási mennyiség!")
                return
            rem = qty_w.property("remaining_qty")
            if qty < 0 or qty > rem:
                QMessageBox.warning(
                    self, "Hiba",
                    f"A szállítási mennyiség 0 és {rem} között lehet."
                )
                return

            cust = row["cust_name"]
            grp = groups.setdefault(cust, {
                "order_id": row["order_id"],
                "customer": {
                    "name":         row["cust_name"],
                    "address":      row["cust_address"],
                    "country":      row["cust_country"],
                    # tax mezők üresen, de így nincs KeyError
                    "tax_number":   "",
                    "eu_tax_number":""
                },
                "shipping": {
                    "name":         row["shp_name"],
                    "address":      row["shp_address"],
                    "country":      row["shp_country"],
                    "tax_number":   "",
                    "eu_tax_number":""
                },
                "entries": []
            })
            grp["entries"].append({
                "product_id":   row["product_id"],
                "order_number": row["order_number"],
                "product_name": row["product_name"],
                "item_number":  row["item_number"],
                "ship_qty":     qty,
                "unit":         row["unit"]
            })

        if not groups:
            QMessageBox.warning(self, "Figyelem", "Legalább egy tételt jelölj meg!")
            return

        # 2) számozás előkészítése
        today    = date.today().strftime("%Y%m%d")
        prefix   = f"DRK-{today}-"
        existing = self.dm.delivery_db.get_existing_numbers(prefix)
        nums     = [int(s.rsplit("-",1)[1]) for s in existing if "-" in s]

        # 3) vevőnként PDF + DB művelet
        for cust, grp in groups.items():
            default_num = f"{prefix}{(max(nums)+1 if nums else 1):03d}"
            note, ok = QInputDialog.getText(
                self, "Szállítólevél száma", "Szállítólevél száma:", text=default_num
            )
            if not ok: continue
            note = note.strip()
            if not note:
                QMessageBox.warning(self, "Hiba", "A szám nem lehet üres!"); continue

            # határidő
            dd = DateDialog(QDate.currentDate(), self)
            if dd.exec_() != QDialog.Accepted: continue
            delivery_date = dd.date_str()

            # raklapok
            euros, ok_e = QInputDialog.getInt(
                self, "Europaletták", "Europaletták száma:", 0, 0
            )
            if not ok_e: continue
            one, ok_o = QInputDialog.getInt(
                self, "Egyutas raklapok", "Egyutas raklapok száma:", 0, 0
            )
            if not ok_o: continue

            # --- mentés DB-be ---
            note_id = self.dm.delivery_db.insert_delivery_note_with_number(
                grp["order_id"], grp["customer"], grp["shipping"], note
            )
            for e in grp["entries"]:
                self.dm.delivery_db.insert_delivery_note_item(
                    note_id, e["product_id"], e["ship_qty"]
                )
                self.order_db.decrease_item_qty(
                    grp["order_id"], e["product_id"], e["ship_qty"]
                )

            # súlyok
            net = 0.0
            for e in grp["entries"]:
                prod   = next((p for p in self.products if p.id==e["product_id"]), None)
                unit_w = getattr(prod, "suly", 1.0) if prod else 1.0
                net   += e["ship_qty"] * unit_w
            gross = net + euros*24 + one*14

            # --- PDF generálás sablonnal ---
            env  = Environment(loader=FileSystemLoader(self.template_dir))
            tpl  = "delivery_base_de.html" if self.current_lang=="de" else "delivery_base_hu.html"
            tmpl = env.get_template(tpl)
            html = tmpl.render(
                logo_uri      = QUrl.fromLocalFile(os.path.join(self.project_dir,"logo.png")).toString(),
                buyer_name    = grp["customer"]["name"],
                buyer_address = grp["customer"]["address"],
                buyer_country = grp["customer"]["country"],
                ship_name     = grp["shipping"]["name"],
                ship_address  = grp["shipping"]["address"],
                ship_country  = grp["shipping"]["country"],
                note_number   = note,
                delivery_date = delivery_date,
                entries       = grp["entries"],
                net_weight    = f"{net:.2f}",
                gross_weight  = f"{gross:.2f}",
                euro_count    = euros,
                one_count     = one,
                exchange_euro = 0,
                exchange_one  = 0
            )

            path, _ = QFileDialog.getSaveFileName(
                self, "PDF mentése", f"{note}.pdf", "PDF fájl (*.pdf)"
            )
            if not path:
                continue
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            try:
                HTML(string=html).write_pdf(path)
                QMessageBox.information(self, "Kész", f"PDF elmentve:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"PDF generálás sikertelen:\n{e}")

        # 4) tábla frissítése
        self.data = self.order_db.get_all_order_items()
        for r in self.data:
            r['ship_qty'] = r['remaining_qty']
        self._refresh_table()


def main():
    app = QApplication(sys.argv)
    w   = DeliveryWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

