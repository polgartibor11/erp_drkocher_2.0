#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Dr. Köcher Kft. – Címkenyomtatás két címke A4-en (nyitott tételek)

import sys
import os
from datetime import datetime
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QUrl
from PyQt5.QtGui import QFont, QPixmap, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableView, QLineEdit, QPushButton, QHeaderView, QFrame,
    QFileDialog, QInputDialog, QMessageBox, QComboBox
)
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# projekt gyökér eléréséhez
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modules.product_module.product_module import osszes_termek
from modules.order_module.order_db         import OrderDB


class OrderLabelViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dr. Köcher Kft. – Címkenyomtatás")
        self.resize(1180, 740)

        self.order_db = OrderDB()
        self.products = osszes_termek()

        self._build_ui()
        self._load_table()

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        main = QVBoxLayout(cw)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(12)

        # fejléc
        header = QHBoxLayout()
        logo_path = os.path.join(BASE_DIR, "logo.png")
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pix = QPixmap(logo_path).scaledToHeight(55, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            header.addWidget(logo_lbl)
        header.addWidget(QLabel(
            "<span style='font-size:19pt;font-weight:bold;color:#20386a;'>Dr. Köcher Kft.</span><br>"
            "<span style='font-size:11pt;color:#555;'>Nyitott rendeléstételek címkézése</span>"
        ), alignment=Qt.AlignVCenter)
        
        header.addStretch()

        # Nyelvválasztó combo
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Magyar címke", "hu")
        self.lang_combo.addItem("Német címke", "de")
        header.addWidget(self.lang_combo)
        
        main.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main.addWidget(line)

        # szűrősáv
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Szűrés:"))
        self.filter_inputs = {}
        for label, col in [("Vevő", 1), ("Termék", 2), ("Cikkszám", 3), ("Határidő", 7)]:
            le = QLineEdit()
            le.setPlaceholderText(label)
            le.setFixedWidth(160)
            le.textChanged.connect(self._apply_filter)
            filter_bar.addWidget(le)
            self.filter_inputs[col] = le
        filter_bar.addStretch()
        main.addLayout(filter_bar)

        # modell és proxy
        self.model = QStandardItemModel(0, 10, self)
        self.model.setHorizontalHeaderLabels([
            "Rend.szám", "Vevő", "Termék", "Cikkszám", "Fennm.", "Egység",
            "Beérk.", "Határidő", "Címzett", "Cím"
        ])
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # táblázat nézet
        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.setStyleSheet("alternate-background-color:#f9f9f9; background:white;")
        hdr = self.view.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setDefaultAlignment(Qt.AlignCenter)
        self.view.verticalHeader().hide()
        main.addWidget(self.view, stretch=1)

        # gombok
        btnbar = QHBoxLayout()
        btnbar.addStretch()
        btn_pdf = QPushButton("Címkék PDF generálása")
        btn_pdf.clicked.connect(self._export_pdf)
        btnbar.addWidget(btn_pdf)
        main.addLayout(btnbar)

    def _load_table(self):
        self.model.setRowCount(0)
        items = self.order_db.get_all_order_items()
        for row in items:
            if row["remaining_qty"] <= 0:
                continue
            vals = [
                row["order_number"] or "",
                row["vevo_nev"] or "",
                row["product_name"] or "",
                row["item_number"] or "",
                f"{row['remaining_qty']:g}",
                row["unit"] or "",
                row["beerkezes"] or "",
                row["szall_hatarido"] or "",
                row["shp_name"] or "",
                row["shp_address"] or ""
            ]
            items = [QStandardItem(str(v)) for v in vals]
            for it in items:
                it.setEditable(False)
                it.setTextAlignment(Qt.AlignCenter)
            self.model.appendRow(items)

    def _apply_filter(self):
        class RowFilter(QSortFilterProxyModel):
            def __init__(self, outer):
                super().__init__(outer)
                self.outer = outer

            def filterAcceptsRow(self, source_row, source_parent):
                for col, le in self.outer.filter_inputs.items():
                    txt = le.text().strip().lower()
                    if txt:
                        idx = self.sourceModel().index(source_row, col, source_parent)
                        cell = self.sourceModel().data(idx)
                        if not cell or txt not in cell.lower():
                            return False
                return True

        proxy = RowFilter(self)
        proxy.setSourceModel(self.model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.view.setModel(proxy)
        self.proxy = proxy

    def _export_pdf(self):
        selected_rows = [idx.row() for idx in self.view.selectionModel().selectedRows()]
        if not selected_rows and self.proxy.rowCount() > 0:
            selected_rows = [0]
        if not selected_rows:
            QMessageBox.information(self, "Figyelem", "Nincs kiválasztott tétel.")
            return

        # max 2 címke, ha csak egy sor, akkor a második ugyanaz lesz
        if len(selected_rows) == 1:
            selected_rows.append(selected_rows[0])

        labels = []
        today = datetime.now().strftime("%Y.%m.%d")
        for r in selected_rows[:2]:
            rec = [self.proxy.data(self.proxy.index(r, c)) for c in range(10)]
            qty, ok = QInputDialog.getInt(
                self, f"Mennyiség megadása ({rec[2]})",
                "Add meg a mennyiséget a címkéhez:", 1, 1
            )
            if not ok:
                return
            # mennyiségi egység keresése a termékek között cikkszám alapján
            prod = next((p for p in self.products if p.cikkszam == rec[3]), None)
            unit = prod.mennyisegi_egyseg if prod else rec[5]
            felulet = getattr(prod, "felulet", "") if prod else ""
            cim_country = getattr(prod, "vevo_orszag", "") if prod else ""
            labels.append({
                "order_number": rec[0],
                "vevo": rec[1],
                "termek": rec[2],
                "cikkszam": rec[3],
                "darab": qty,
                "egyseg": unit,
                "beerkezes": rec[6],
                "hatarido": rec[7],
                "felulet": felulet,
                "created": today,
                "cimzett": rec[8],
                "cim": rec[9],
                "cim_country": cim_country
            })

        # sablon betöltése nyelv alapján
        env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
        lang = self.lang_combo.currentData()
        if lang == "de":
            tmpl_name = "label_base_de.html"
        else:
            tmpl_name = "label_base.html"
        tmpl = env.get_template(tmpl_name)

        html = tmpl.render(labels=labels, logo_uri=QUrl.fromLocalFile(os.path.join(BASE_DIR, "logo.png")).toString())

        # PDF mentése
        path, _ = QFileDialog.getSaveFileName(self, "Címkék PDF mentése", "labels.pdf", "PDF fájl (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            HTML(string=html).write_pdf(path)
            # Windows-on megnyitás automatikusan
            if sys.platform.startswith("win"):
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"PDF generálás sikertelen:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = OrderLabelViewer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



