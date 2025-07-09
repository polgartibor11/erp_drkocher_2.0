import sys
import os
import sqlite3
from pathlib import Path
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QSpinBox, QPushButton, QMessageBox,
    QSizePolicy, QInputDialog, QFrame
)

this_dir    = os.path.dirname(__file__)
project_dir = os.path.abspath(os.path.join(this_dir, os.pardir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from modules.manufacturing_module.inventory_db import InventoryDB

class ManufacturingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gyártás indítása – Öntöde Üzem")
        self.resize(960, 600)
        self.setStyleSheet("""
            QWidget      { font-family: Arial, sans-serif; font-size: 11pt; }
            QComboBox,
            QLineEdit,
            QSpinBox     { font-size: 12pt; min-width: 150px;}
            QPushButton  { font-weight: bold; padding: 8px 26px; background: #1976d2; color: white; border-radius: 5px;}
            QPushButton:hover { background: #1565c0;}
            QLabel[dev="1"] { color: #aaa; font-size: 8.5pt; }
            QFrame#line   { background: #ddd; max-width: 2px; }
        """)

        # adatbázisok
        self.inv_db   = InventoryDB()
        self.prod_db  = os.path.join(project_dir, "modules", "product_module", "products.db")
        self.machines = [
            "OMS 950T öntőgép",
            "OMS 500T öntőgép",
            "CLOO 400T öntőgép",
            "CLOO 250T függőleges öntőgép"
        ]

        # --- Central widget és layout ---
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(30, 25, 30, 25)
        main.setSpacing(22)

        # -------- Bal oldal (Űrlapok) --------
        form = QVBoxLayout()
        form.setSpacing(13)
        main.addLayout(form, stretch=1)

        # Fejléc: logó + cégnév
        header = QHBoxLayout()
        logo_path = os.path.join(project_dir, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo = QLabel()
            lbl_logo.setPixmap(pix)
            header.addWidget(lbl_logo, alignment=Qt.AlignLeft)
        lbl_title = QLabel('<span style="font-size:18pt; font-weight:bold;">Dr. Köcher Kft. – Öntöde Üzem</span>')
        header.addWidget(lbl_title, alignment=Qt.AlignVCenter)
        header.addStretch()
        form.addLayout(header)

        form.addSpacing(8)

        # Gép kiválasztó
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Gép:", alignment=Qt.AlignRight))
        self.machine_cb = QComboBox()
        h1.addWidget(self.machine_cb)
        form.addLayout(h1)

        # Vevő-szűrő
        h0 = QHBoxLayout()
        h0.addWidget(QLabel("Vevő:", alignment=Qt.AlignRight))
        self.customer_cb = QComboBox()
        self.customer_cb.currentIndexChanged.connect(self.load_products)
        h0.addWidget(self.customer_cb)
        form.addLayout(h0)

        # Termék kiválasztó
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Termék:", alignment=Qt.AlignRight))
        self.product_cb = QComboBox()
        self.product_cb.currentIndexChanged.connect(self.on_product_changed)
        h2.addWidget(self.product_cb)
        form.addLayout(h2)

        # Info mezők
        self.sku_lbl          = QLabel("Cikkszám: —")
        self.weight_lbl       = QLabel("Súly: —")
        self.bunch_weight_lbl = QLabel("Csokor súly: —")
        self.fesz_lbl         = QLabel("Feszékszám: —")
        for lbl in (self.sku_lbl, self.weight_lbl, self.bunch_weight_lbl, self.fesz_lbl):
            lbl.setStyleSheet("padding-left:5px; font-size:11pt;")
            form.addWidget(lbl)

        # Szerszám
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("Szerszám:", alignment=Qt.AlignRight))
        self.tooling_le = QLineEdit()
        self.tooling_le.setPlaceholderText("szerszám azonosító")
        h3.addWidget(self.tooling_le)
        form.addLayout(h3)

        # Előírt norma
        h_norm = QHBoxLayout()
        h_norm.addWidget(QLabel("Norma (lövés/shift):", alignment=Qt.AlignRight))
        self.norm_sb = QSpinBox()
        self.norm_sb.setRange(0, 1_000_000)
        h_norm.addWidget(self.norm_sb)
        btn_norm = QPushButton("Norma mentése")
        btn_norm.clicked.connect(self.save_norm)
        h_norm.addWidget(btn_norm)
        form.addLayout(h_norm)

        # Mennyiség
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("Mennyiség:", alignment=Qt.AlignRight))
        self.qty_sb = QSpinBox()
        self.qty_sb.setRange(1, 100_000)
        self.qty_sb.setValue(1)
        h4.addWidget(self.qty_sb)
        form.addLayout(h4)

        # Gyártás indítása/leállítása
        self.start_btn = QPushButton("Gyártás indítása")
        self.start_btn.clicked.connect(self.start_production)
        self.stop_btn = QPushButton("Gyártás leállítása")
        self.stop_btn.clicked.connect(self.stop_production)
        btnbox = QHBoxLayout()
        btnbox.addWidget(self.start_btn)
        btnbox.addWidget(self.stop_btn)
        form.addLayout(btnbox)

        form.addSpacing(16)
        form.addStretch()

        # Fejlesztő név jobbra lent
        lbl_dev = QLabel("Fejlesztő: Polgár Tibor")
        lbl_dev.setProperty("dev", 1)
        form.addWidget(lbl_dev, alignment=Qt.AlignRight)

        # ---- Függőleges elválasztó vonal ----
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        main.addWidget(vline)

        # -------- Jobb oldal (Fénykép) --------
        self.photo_label = QLabel(alignment=Qt.AlignCenter)
        self.photo_label.setMinimumSize(320, 320)
        self.photo_label.setMaximumSize(360, 360)
        self.photo_label.setFixedSize(340, 340)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 1.8px solid #bbb;
                background: #f8fafc;
            }
        """)
        main.addWidget(self.photo_label, stretch=0, alignment=Qt.AlignCenter)

        # inicializálunk
        self.refresh_machine_list()
        self.load_customers()
        self.load_products()

    def refresh_machine_list(self):
        model = QStandardItemModel()
        for m in self.machines:
            item = QStandardItem(m)
            if self.inv_db.has_active_job(m):
                item.setEnabled(False)
                item.setToolTip("Foglalt: futó gyártás van rajta")
            model.appendRow(item)
        self.machine_cb.setModel(model)

    def load_customers(self):
        self.customer_cb.clear()
        con = sqlite3.connect(self.prod_db); cur = con.cursor()
        cur.execute("SELECT DISTINCT vevo_nev FROM products ORDER BY vevo_nev")
        names = [r[0] for r in cur.fetchall() if r[0]]
        con.close()
        self.customer_cb.addItem("Összes vevő", None)
        for n in names:
            self.customer_cb.addItem(n, n)

    def load_products(self):
        cust = self.customer_cb.currentData()
        self.product_cb.clear()
        con = sqlite3.connect(self.prod_db); cur = con.cursor()
        sql = "SELECT id, megnevezes FROM products WHERE uzem_lanc LIKE '%Öntöde%' COLLATE NOCASE"
        params = []
        if cust:
            sql += " AND vevo_nev = ?"; params.append(cust)
        sql += " ORDER BY megnevezes"
        cur.execute(sql, params)
        rows = cur.fetchall()
        con.close()
        if not rows:
            self.product_cb.addItem("— nincs termék —", -1)
            self.on_product_changed(0)
        else:
            for pid, name in rows:
                self.product_cb.addItem(name, pid)
            self.on_product_changed(0)

    def on_product_changed(self, idx):
        pid = self.product_cb.currentData()
        if pid is None or pid < 0:
            self._clear_info()
            return

        # Norma
        norm = self.inv_db.get_norm(pid)
        self.norm_sb.setValue(norm or 0)

        # Szerszám
        tooling = self.inv_db.get_tooling(pid)
        self.tooling_le.setText(tooling)

        # Egyéb termékinfók + kép
        con = sqlite3.connect(self.prod_db)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT foto, cikkszam, suly, suly_mertekegyseg,
                   csokosuly, csokosuly_mertekegyseg, feszekszam
              FROM products WHERE id=?
        """, (pid,))
        row = cur.fetchone()
        con.close()

        # Fénykép egységes, középre illesztett
        self.photo_label.clear()
        self.photo_label.setText("<i>Nincs kép</i>")
        if row and row["foto"]:
            p = row["foto"]
            if not os.path.isabs(p): p = os.path.join(project_dir, p)
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    # Egységesen 320x320 px méretű keretbe igazítva (kitöltés nélkül, arányosan!)
                    scaled = pix.scaled(
                        320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    self.photo_label.setPixmap(scaled)
                    self.photo_label.setAlignment(Qt.AlignCenter)
                    self.photo_label.setStyleSheet("""
                        QLabel {
                            border: 1.8px solid #bbb;
                            background: #fff;
                        }
                    """)
            # else: meghagyjuk az <i>Nincs kép</i>-t

        self.sku_lbl.setText(f"Cikkszám: {row['cikkszam'] or '—'}")
        self.weight_lbl.setText(f"Súly: {row['suly'] or 0} {row['suly_mertekegyseg'] or ''}")
        self.bunch_weight_lbl.setText(
            f"Csokor súly: {row['csokosuly'] or 0} {row['csokosuly_mertekegyseg'] or ''}"
        )
        self.fesz_lbl.setText(f"Feszékszám: {row['feszekszam'] or 0}")

    def save_norm(self):
        pid = self.product_cb.currentData()
        if pid is None or pid < 0:
            QMessageBox.warning(self, "Hiba", "Előbb válassz terméket!"); return
        norm = self.norm_sb.value()
        self.inv_db.set_norm(pid, norm)
        QMessageBox.information(self, "Norma mentve", f"Norma ({norm} lövés) elmentve.")

    def _clear_info(self):
        self.photo_label.clear()
        self.photo_label.setText("<i>Nincs kép</i>")
        for lbl in (self.sku_lbl, self.weight_lbl, self.bunch_weight_lbl, self.fesz_lbl):
            lbl.setText(lbl.text().split(':')[0] + ": —")
        self.tooling_le.clear()
        self.norm_sb.setValue(0)

    def start_production(self):
        machine = self.machine_cb.currentText()
        pid     = self.product_cb.currentData()
        if pid is None or pid < 0:
            QMessageBox.warning(self, "Hiba", "Válassz terméket!"); return

        tool = self.tooling_le.text().strip()
        if not tool:
            QMessageBox.warning(self, "Hiba", "Adj meg szerszámot!"); return

        qty = self.qty_sb.value()

        # mentjük a tooling-et és normát
        self.inv_db.set_tooling(pid, tool)
        self.inv_db.set_norm(pid, self.norm_sb.value())

        # indítjuk a gép-munkát és gyártást
        self.inv_db.start_job(machine, pid)
        note = f"Gép:{machine}; Szerszám:{tool}"
        inv_id = self.inv_db.add_production(pid, qty, batch_number=None, note=note)

        QMessageBox.information(
            self, "Gyártás indítva",
            f"„{machine}” gépen: „{self.product_cb.currentText()}”\nInv ID: {inv_id}"
        )
        self.refresh_machine_list()

    def stop_production(self):
        active = [m for m in self.machines if self.inv_db.has_active_job(m)]
        if not active:
            QMessageBox.information(self, "Nincs aktív munka",
                "Egyik gépen sincs futó gyártás."); return

        machine, ok = QInputDialog.getItem(
            self, "Gyártás leállítása",
            "Válassz gépet a leállításhoz:", active, 0, False
        )
        if not ok: return

        self.inv_db.stop_job(machine)
        QMessageBox.information(self, "Leállítva",
            f"A „{machine}” gépen futó gyártás sikeresen leállítva.")
        self.refresh_machine_list()

def main():
    app = QApplication(sys.argv)
    w = ManufacturingWindow()
    w.show()
    sys.exit(app.exec_())

if __name__=="__main__":
    main()










