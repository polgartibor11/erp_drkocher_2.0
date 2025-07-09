import sys
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QDateEdit, QSpinBox, QPushButton,
    QMessageBox, QLineEdit, QDoubleSpinBox, QFrame
)

# sys.path patch a projekt gyökérre
this_dir    = os.path.dirname(__file__)
project_dir = os.path.abspath(os.path.join(this_dir, os.pardir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from modules.manufacturing_module.inventory_db import InventoryDB

class ShiftLoggerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dr. Köcher Kft. – Műszaknapló | Öntöde Üzem")
        self.resize(680, 720)

        self.inv_db = InventoryDB()
        self.prod_db = os.path.join(
            project_dir, "modules", "product_module", "products.db"
        )

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 24, 30, 18)

        # Fejléc: logó + cégnév
        header = QHBoxLayout()
        logo_path = os.path.join(project_dir, "logo.png")
        if os.path.exists(logo_path):
            lbl_logo = QLabel()
            pix = QPixmap(logo_path).scaledToHeight(38, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            header.addWidget(lbl_logo)
        company_title = QLabel(
            '<span style="font-size:15pt; font-weight:bold; color:#2a3a5c;">Dr. Köcher Kft. – Öntöde Üzem</span><br>'
            '<span style="font-size:11pt; font-weight:bold;">Műszaknapló rögzítés</span>'
        )
        company_title.setTextFormat(Qt.RichText)
        header.addWidget(company_title, alignment=Qt.AlignVCenter)
        header.addStretch()
        layout.addLayout(header)

        # Szép elválasztó
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        layout.addWidget(divider)

        # Gép kiválasztó
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Gép:"))
        self.machine_cb = QComboBox()
        machines = [
            "OMS 950T öntőgép",
            "OMS 500T öntőgép",
            "CLOO 400T öntőgép",
            "CLOO 250T függőleges öntőgép"
        ]
        for m in machines:
            if self.inv_db.has_active_job(m):
                self.machine_cb.addItem(m)
        self.machine_cb.currentIndexChanged.connect(self.on_machine_changed)
        h1.addWidget(self.machine_cb)
        h1.addStretch()
        layout.addLayout(h1)

        # Termék infó: fotó + nevek
        info = QHBoxLayout()
        self.prod_photo = QLabel()
        self.prod_photo.setFixedSize(130,130)
        self.prod_photo.setStyleSheet("""
            border:1.5px solid #b6b6b6;
            background: #f8f8fa;
            border-radius:7px;
            """)
        self.prod_photo.setAlignment(Qt.AlignCenter)
        info.addWidget(self.prod_photo)
        txt = QVBoxLayout()
        self.prod_name_lbl = QLabel("Termék: —")
        self.prod_sku_lbl  = QLabel("Cikkszám: —")
        txt.addWidget(self.prod_name_lbl)
        txt.addWidget(self.prod_sku_lbl)
        info.addLayout(txt)
        info.addStretch()
        layout.addLayout(info)

        # Operátor választó
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Operátor:"))
        self.operator_cb = QComboBox()
        self.operator_cb.addItems(self.inv_db.list_operators())
        h2.addWidget(self.operator_cb)
        h2.addStretch()
        layout.addLayout(h2)

        # Új operátor hozzáadás
        h2b = QHBoxLayout()
        self.new_op_le = QLineEdit()
        self.new_op_le.setPlaceholderText("Új operátor neve")
        btn_add_op = QPushButton("Operátor mentése")
        btn_add_op.clicked.connect(self.add_operator)
        h2b.addWidget(self.new_op_le)
        h2b.addWidget(btn_add_op)
        h2b.addStretch()
        layout.addLayout(h2b)

        # Dátum
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("Dátum:"))
        self.date_edit = QDateEdit(datetime.now())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        h3.addWidget(self.date_edit)
        h3.addStretch()
        layout.addLayout(h3)

        # Műszak
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("Műszak:"))
        self.shift_cb = QComboBox()
        for label in ("délelőtt", "délután", "éjszaka"):
            self.shift_cb.addItem(label)
        h4.addWidget(self.shift_cb)
        h4.addStretch()
        layout.addLayout(h4)

        # Öntött lövésszám
        h5 = QHBoxLayout()
        h5.addWidget(QLabel("Öntött lövésszám:"))
        self.shots_sb = QSpinBox()
        self.shots_sb.setRange(0,100000)
        h5.addWidget(self.shots_sb)
        h5.addStretch()
        layout.addLayout(h5)

        # Selejt lövésszám
        h6 = QHBoxLayout()
        h6.addWidget(QLabel("Selejt lövésszám:"))
        self.scrap_sb = QSpinBox()
        self.scrap_sb.setRange(0,100000)
        h6.addWidget(self.scrap_sb)
        h6.addStretch()
        layout.addLayout(h6)

        # Állásidők (max. 3)
        group_lbl = QLabel("Állásidők (max. 3):")
        layout.addWidget(group_lbl)
        self.downtime_reasons = [
            "géphiba", "szerszámhiba", "elektromos hiba",
            "mechanikus hiba", "hidraulika hiba",
            "fémhiány hiba", "általános állás"
        ]
        self.down_widgets = []
        for i in range(1, 4):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Állás {i}:"))
            cb = QComboBox()
            cb.addItem("—")  # nincs
            cb.addItems(self.downtime_reasons)
            sb = QDoubleSpinBox()
            sb.setRange(0, 24)
            sb.setSingleStep(0.5)
            sb.setSuffix(" óra")
            row.addWidget(cb)
            row.addWidget(sb)
            row.addStretch()
            layout.addLayout(row)
            self.down_widgets.append((cb, sb))

        # Műszak rögzítése gomb
        btn = QPushButton("Műszak rögzítése")
        btn.clicked.connect(self.save_shift)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        # fejlesztő alul balra
        lbl_dev = QLabel("Fejlesztő: Polgár Tibor")
        layout.addWidget(lbl_dev, alignment=Qt.AlignLeft)

        # inicializálás
        self.on_machine_changed(0)

    def on_machine_changed(self, idx):
        machine = self.machine_cb.currentText()
        pid = self.inv_db.get_active_job_product(machine)
        if pid is None:
            self.prod_name_lbl.setText("Termék: —")
            self.prod_sku_lbl.setText("Cikkszám: —")
            self.prod_photo.clear()
            self.prod_photo.setText("<i>Nincs kép</i>")
            return
        con = sqlite3.connect(self.prod_db); con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT megnevezes,cikkszam,foto FROM products WHERE id=?", (pid,))
        row = cur.fetchone(); con.close()
        name = row["megnevezes"] if row else "—"
        sku  = row["cikkszam"]   if row else "—"
        photo= row["foto"]      if row else None
        self.prod_name_lbl.setText(f"Termék: {name}")
        self.prod_sku_lbl.setText(f"Cikkszám: {sku}")
        if photo:
            p = photo if os.path.isabs(photo) else os.path.join(project_dir, photo)
            if os.path.exists(p):
                pix = QPixmap(p).scaled(
                    self.prod_photo.width(), self.prod_photo.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.prod_photo.setPixmap(pix)
                return
        self.prod_photo.clear()
        self.prod_photo.setText("<i>Nincs kép</i>")

    def add_operator(self):
        name = self.new_op_le.text().strip()
        if not name:
            QMessageBox.warning(self, "Hiba", "Adj meg egy nevet!"); return
        self.inv_db.add_operator(name)
        self.operator_cb.clear()
        self.operator_cb.addItems(self.inv_db.list_operators())
        self.new_op_le.clear()

    def save_shift(self):
        machine   = self.machine_cb.currentText()
        operator  = self.operator_cb.currentText().strip()
        if not machine:
            QMessageBox.warning(self, "Hiba", "Válassz gépet!"); return
        if not operator:
            QMessageBox.warning(self, "Hiba", "Válassz operátort!"); return

        date       = self.date_edit.date().toString("yyyy-MM-dd")
        shift_type = self.shift_cb.currentText()
        shots      = self.shots_sb.value()
        scrap      = self.scrap_sb.value()

        pid = self.inv_db.get_active_job_product(machine)
        con = sqlite3.connect(self.prod_db); con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT feszekszam FROM products WHERE id = ?", (pid,))
        row = cur.fetchone(); con.close()
        fesz = row["feszekszam"] if row else 0

        good_qty  = shots * fesz
        scrap_qty = scrap * fesz

        # alap műszaknapló
        self.inv_db.add_shift_log(
            machine, operator, date, shift_type,
            shots, scrap, good_qty, scrap_qty
        )

        # állásidők mentése a shift_downtimes táblába
        for cb, sb in self.down_widgets:
            cause = cb.currentText()
            hours = sb.value()
            if cause != "—" and hours > 0:
                self.inv_db.add_downtime(
                    machine=machine,
                    date=date,
                    shift_type=shift_type,
                    cause=cause,
                    hours=hours
                )

        QMessageBox.information(self, "Kész", "Műszak és állásidők sikeresen rögzítve.")
        self.shots_sb.setValue(0)
        self.scrap_sb.setValue(0)
        for cb, sb in self.down_widgets:
            cb.setCurrentIndex(0)
            sb.setValue(0)

def main():
    app = QApplication(sys.argv)
    # NINCS .setFont()
    w = ShiftLoggerWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()





