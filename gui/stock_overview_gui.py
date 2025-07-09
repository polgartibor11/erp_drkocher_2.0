# gui/stock_overview_gui.py (1/2)

import sys
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QTextDocument
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QSpacerItem, QSizePolicy,
    QDialogButtonBox, QComboBox, QFileDialog, QMessageBox, QLineEdit, QFrame
)

# sys.path patch a projekt gyökérre
this_dir    = os.path.dirname(__file__)
project_dir = os.path.abspath(os.path.join(this_dir, os.pardir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from modules.manufacturing_module.inventory_db import InventoryDB
from modules.delivery_module.delivery_note_db import DeliveryNoteDB

# ---------------------------------------------------
# Hozzáadott dialógus: Készlet módosítása
# ---------------------------------------------------
class StockAdjustDialog(QDialog):
    def __init__(self, inv_db: InventoryDB, prod_db_path: str, parent=None):
        super().__init__(parent)
        self.inv_db       = inv_db
        self.prod_db_path = prod_db_path
        self.setWindowTitle("Készlet módosítása")
        self.resize(400, 130)

        layout = QVBoxLayout(self)

        # Termékválasztó
        hl1 = QHBoxLayout()
        hl1.addWidget(QLabel("Termék:"))
        self.prod_cb = QComboBox()
        self._load_products()
        hl1.addWidget(self.prod_cb)
        layout.addLayout(hl1)

        # Mennyiség megadása
        hl2 = QHBoxLayout()
        hl2.addWidget(QLabel("Változtatás (±):"))
        self.delta_le = QLineEdit()
        self.delta_le.setPlaceholderText("pl. +10 vagy -5")
        hl2.addWidget(self.delta_le)
        layout.addLayout(hl2)

        # OK / Mégse
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_products(self):
        con = sqlite3.connect(self.prod_db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT id, megnevezes FROM products ORDER BY megnevezes")
        for r in cur.fetchall():
            self.prod_cb.addItem(r["megnevezes"], userData=r["id"])
        con.close()

    def on_accept(self):
        # Érvényes szám?
        try:
            delta = float(self.delta_le.text())
        except ValueError:
            QMessageBox.warning(self, "Hiba", "Kérlek, érvényes számot adj meg!")
            return

        prod_id = self.prod_cb.currentData()

        # shift_logs táblába bejegyzés – most már end_time-ot is adunk
        cur = self.inv_db.conn.cursor()
        cur.execute("""
            INSERT INTO shift_logs
                (product_id, date, start_time, end_time, machine, good_qty, scrap_qty, operator)
            VALUES
                (?, DATE('now'), TIME('now'), TIME('now'), ?, ?, 0, ?)
        """, (
            prod_id,    # product_id
            "GUI",      # machine
            delta,      # good_qty
            "GUI"       # operator
        ))
        self.inv_db.conn.commit()
        QMessageBox.information(self, "Siker", f"{delta:+} mennyiség hozzáadva a készlethez.")
        self.accept()


class MonthlyReportDialog(QDialog):
    def __init__(self, inv_db: InventoryDB, prod_db: str, delivery_db: DeliveryNoteDB, parent=None):
        super().__init__(parent)
        self.inv_db      = inv_db
        self.prod_db     = prod_db
        self.delivery_db = delivery_db
        self.setWindowTitle("Havi riport – Öntöde Üzem")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Havi riport</h2>"))

        # hónap választó + gombok
        ctl = QHBoxLayout()
        ctl.addWidget(QLabel("Hónap:"))
        self.month_cb = QComboBox()
        year = datetime.now().year
        for m in range(1,13):
            self.month_cb.addItem(f"{year}-{m:02d}")
        ctl.addWidget(self.month_cb)
        btn_reload = QPushButton("Frissítés")
        btn_reload.clicked.connect(self.load_data)
        ctl.addWidget(btn_reload)
        ctl.addStretch()
        btn_export = QPushButton("Export")
        btn_export.clicked.connect(self.export_report)
        ctl.addWidget(btn_export)
        layout.addLayout(ctl)

        # Öntés-tábla
        self.tbl_cast = QTableWidget(0,6)
        self.tbl_cast.setHorizontalHeaderLabels([
            "Termék","Cikkszám","Db","Egységnyi súly",
            "Mértékegység","Össz súly"
        ])
        self.tbl_cast.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("<b>Gyártott (Öntés)</b>"))
        layout.addWidget(self.tbl_cast, stretch=1)

        # Kiszállítás-tábla
        self.tbl_deliv = QTableWidget(0,6)
        self.tbl_deliv.setHorizontalHeaderLabels([
            "Termék","Cikkszám","Db","Egységnyi súly",
            "Mértékegység","Össz súly"
        ])
        self.tbl_deliv.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("<b>Kiszállított</b>"))
        layout.addWidget(self.tbl_deliv, stretch=1)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.load_data()

    def load_data(self):
        mon = self.month_cb.currentText()
        self.tbl_cast.setRowCount(0)
        self.tbl_deliv.setRowCount(0)

        # gyártott havonta
        cur = self.inv_db.conn.cursor()
        cur.execute("""
            SELECT product_id, SUM(good_qty+scrap_qty) AS qty
              FROM shift_logs
             WHERE substr(date,1,7)=?
             GROUP BY product_id
        """, (mon,))
        made = {r["product_id"]: r["qty"] for r in cur.fetchall()}

        # kiszállított havonta
        cur_dn = self.delivery_db.conn.cursor()
        cur_dn.execute("""
            SELECT dni.product_id, SUM(dni.quantity) AS qty
              FROM delivery_note_items AS dni
              JOIN delivery_notes AS dn ON dn.id=dni.delivery_note_id
             WHERE substr(dn.shipping_date,1,7)=?
             GROUP BY dni.product_id
        """, (mon,))
        delivered = {r["product_id"]: r["qty"] for r in cur_dn.fetchall()}

        # termékadatok
        con_p = sqlite3.connect(self.prod_db)
        con_p.row_factory = sqlite3.Row
        cur_p = con_p.cursor()
        cur_p.execute("""
            SELECT id, megnevezes, cikkszam, suly, suly_mertekegyseg
              FROM products
             WHERE uzem_lanc LIKE '%Öntöde%' COLLATE NOCASE
        """)
        prods = {r["id"]: r for r in cur_p.fetchall()}
        con_p.close()

        # összesített listázás
        all_ids = sorted(set(made.keys()) | set(delivered.keys()))
        for pid in all_ids:
            info = prods.get(pid)
            if not info: continue
            name = info["megnevezes"]
            sku  = info["cikkszam"]
            w    = info["suly"] or 0
            u    = info["suly_mertekegyseg"] or ""
# gui/stock_overview_gui.py (2/2)

            # Öntés
            qty_m = made.get(pid, 0)
            tot_m = qty_m * w
            r = self.tbl_cast.rowCount()
            self.tbl_cast.insertRow(r)
            for c, val in enumerate((name, sku, qty_m, w, u, tot_m)):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.tbl_cast.setItem(r, c, it)

            # Kiszállítás
            qty_d = delivered.get(pid, 0)
            tot_d = qty_d * w
            r2 = self.tbl_deliv.rowCount()
            self.tbl_deliv.insertRow(r2)
            for c, val in enumerate((name, sku, qty_d, w, u, tot_d)):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.tbl_deliv.setItem(r2, c, it)

    def export_report(self):
        path, fmt = QFileDialog.getSaveFileName(
            self, "Riport exportálása", "",
            "HTML fájl (*.html);;PDF fájl (*.pdf)"
        )
        if not path:
            return

        def make_table(tbl, title):
            s  = f"<h2>{title}</h2><table border='1' cellpadding='4'>"
            s += "<tr>" + "".join(f"<th>{tbl.horizontalHeaderItem(i).text()}</th>"
                                  for i in range(tbl.columnCount())) + "</tr>"
            total_weight = 0.0
            for r in range(tbl.rowCount()):
                s += "<tr>"
                for c in range(tbl.columnCount()):
                    v = tbl.item(r,c).text()
                    s += f"<td>{v}</td>"
                try:
                    w = float(tbl.item(r, tbl.columnCount()-1).text())
                except:
                    w = 0.0
                total_weight += w
                s += "</tr>"
            s += "</table>"
            s += f"<p><b>Összes súly ({title}): {total_weight:.2f}</b></p>"
            return s

        html = "<html><head><meta charset='utf-8'></head><body>"
        html += f"<h1>Havi riport: {self.month_cb.currentText()}</h1>"
        html += make_table(self.tbl_cast, "Gyártott (Öntés)")
        html += make_table(self.tbl_deliv, "Kiszállított")
        html += "</body></html>"

        if path.lower().endswith(".html"):
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "Export kész", f"HTML mentve: {path}")
        else:
            doc = QTextDocument()
            doc.setHtml(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            doc.print_(printer)
            QMessageBox.information(self, "Export kész", f"PDF mentve: {path}")
class StockOverviewWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raktárkészlet áttekintés – Öntöde Üzem")
        self.resize(1080, 700)

        self.inv_db      = InventoryDB()
        self.prod_db     = os.path.join(project_dir,
                                        "modules","product_module","products.db")
        self.delivery_db = DeliveryNoteDB()

        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(20,20,20,20)
        main.setSpacing(10)

        # Fejléc
        hdr_layout = QHBoxLayout()
        logo_path = os.path.join(project_dir, "logo.png")
        if os.path.exists(logo_path):
            lbl_logo = QLabel()
            pix = QPixmap(logo_path).scaledToHeight(42, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            hdr_layout.addWidget(lbl_logo)
        title = QLabel(
            "<span style='font-size:18pt; font-weight:bold; color:#20386a;'>"
            "Dr. Köcher Kft. – Öntöde Üzem</span><br>"
            "<span style='font-size:12pt; font-weight:bold;'>"
            "Raktárkészlet áttekintés</span>"
        )
        title.setTextFormat(Qt.RichText)
        hdr_layout.addWidget(title, alignment=Qt.AlignVCenter)
        hdr_layout.addStretch()
        main.addLayout(hdr_layout)

        # Elválasztó
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        main.addWidget(divider)

        # Szűrők
        filter_layout = QHBoxLayout()
        self.vevo_le = QLineEdit();    self.vevo_le.setPlaceholderText("Vevő keresés…")
        self.vevo_le.textChanged.connect(self.load_stock)
        filter_layout.addWidget(self.vevo_le)
        self.termek_le = QLineEdit();  self.termek_le.setPlaceholderText("Termék keresés…")
        self.termek_le.textChanged.connect(self.load_stock)
        filter_layout.addWidget(self.termek_le)
        self.sku_le = QLineEdit();     self.sku_le.setPlaceholderText("Cikkszám keresés…")
        self.sku_le.textChanged.connect(self.load_stock)
        filter_layout.addWidget(self.sku_le)
        filter_layout.addItem(QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum))
        main.addLayout(filter_layout)

        # Gombok
        ctl = QHBoxLayout()
        ctl.addItem(QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum))
        btn_refresh = QPushButton("Frissítés")
        btn_refresh.clicked.connect(self.load_stock)
        ctl.addWidget(btn_refresh)
        btn_report = QPushButton("Havi riport")
        btn_report.clicked.connect(self.open_monthly_report)
        ctl.addWidget(btn_report)

        # Új gomb: Készlet módosítása
        btn_adjust = QPushButton("Készlet módosítása")
        btn_adjust.clicked.connect(self.open_stock_adjust)
        ctl.addWidget(btn_adjust)

        main.addLayout(ctl)

        # Táblázat
        self.tbl = QTableWidget(0,4)
        headers = ["Vevő","Termék","Cikkszám","Akt. készlet"]
        self.tbl.setHorizontalHeaderLabels(headers)
        for i in range(4):
            self.tbl.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        main.addWidget(self.tbl)

        self.load_stock()

    def load_stock(self):
        self.tbl.setRowCount(0)

        # (1) Lekérdezzük az "öntöde üzem" lánc termékeit
        con = sqlite3.connect(self.prod_db)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT id, vevo_nev, megnevezes, cikkszam
              FROM products
             WHERE uzem_lanc LIKE '%öntöde%'
                OR uzem_lanc LIKE '%Öntöde%'
             ORDER BY vevo_nev, megnevezes
        """)
        prods = cur.fetchall()
        con.close()

        # (2) Kiszállított mennyiség előkészítése
        cur_dn = self.delivery_db.conn.cursor()
        cur_dn.execute("""
            SELECT product_id, SUM(quantity) AS qty
              FROM delivery_note_items
             GROUP BY product_id
        """)
        delivered_map = {r["product_id"]: r["qty"] for r in cur_dn.fetchall()}

        # (3) A GUI-be tölti csak ezt a szűrt listát
        vevo_f   = self.vevo_le.text().lower()
        termek_f = self.termek_le.text().lower()
        sku_f    = self.sku_le.text().lower()

        for p in prods:
            pid   = p["id"]
            vevo  = p["vevo_nev"] or "—"
            name  = p["megnevezes"]
            sku   = p["cikkszam"]

            # opcionális szöveges-szűrés a mezőkben
            if vevo_f and vevo_f not in vevo.lower(): continue
            if termek_f and termek_f not in name.lower(): continue
            if sku_f and sku_f not in sku.lower(): continue

            # készletszámítás shift_logs + delivery_note_items alapján
            cur2 = self.inv_db.conn.cursor()
            cur2.execute("""
                SELECT SUM(good_qty) AS g, SUM(scrap_qty) AS s
                  FROM shift_logs
                 WHERE product_id=?
            """, (pid,))
            r2 = cur2.fetchone()
            good_all  = r2["g"] or 0.0
            scrap_all = r2["s"] or 0.0
            delivered_all = delivered_map.get(pid, 0.0)
            stock = good_all - scrap_all - delivered_all

            # sor beszúrása
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            for c, val in enumerate((vevo, name, sku, stock)):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.tbl.setItem(r, c, it)

        self.tbl.resizeColumnsToContents()

    def open_monthly_report(self):
        dlg = MonthlyReportDialog(self.inv_db, self.prod_db, self.delivery_db, parent=self)
        dlg.exec_()

    def open_stock_adjust(self):
        dlg = StockAdjustDialog(self.inv_db, self.prod_db, parent=self)
        if dlg.exec_():
            self.load_stock()

def main():
    app = QApplication(sys.argv)
    w = StockOverviewWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()





