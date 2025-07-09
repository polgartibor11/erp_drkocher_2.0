#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import sqlite3
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel,
    QDialog, QDialogButtonBox, QComboBox,
    QFormLayout, QLineEdit, QMessageBox, QInputDialog
)

# ─── 1) Hol vannak a fájljaink: bundle vs. app ───────────────────────────
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    APP_DIR    = Path(sys.argv[0]).resolve().parent
else:
    BUNDLE_DIR = APP_DIR = Path(__file__).resolve().parent

os.chdir(APP_DIR)

# ─── 1b) modules mappa import útvonal ─────────────────────────────────────
if getattr(sys, "frozen", False):
    sys.path.insert(0, str(BUNDLE_DIR / "modules"))
else:
    sys.path.insert(0, str(APP_DIR / "modules"))

# ─── 2) sqlite3.connect monkey-patch ───────────────────────────────────────
_orig_connect = sqlite3.connect
def _patched_connect(database, *args, **kwargs):
    p = Path(database)
    if not p.is_absolute():
        candidate = APP_DIR / database
        if not candidate.exists() and getattr(sys, "frozen", False):
            candidate = BUNDLE_DIR / database
        candidate.parent.mkdir(parents=True, exist_ok=True)
        database = str(candidate)
    return _orig_connect(database, *args, **kwargs)
sqlite3.connect = _patched_connect

# ─── LOGIN DIALÓGUS ───────────────────────────────────────────────────────
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Felhasználó kiválasztása")
        self.resize(300, 120)
        layout = QFormLayout(self)
        self.combo = QComboBox(self)
        self.combo.addItems([
            "Polgár Tibor", "Kovács Zsuzsanna", "Németh Judit",
            "Király Éva",  "Kovács Attila",    "Fekszi György"
        ])
        layout.addRow("Felhasználó:", self.combo)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                Qt.Horizontal, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_user(self):
        return self.combo.currentText()

# ─── DB-EDITOR AUTH DIALÓGUS ───────────────────────────────────────────────
class DBAuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adatbázis szerkesztő belépés")
        self.resize(300, 120)
        layout = QFormLayout(self)
        self.user_edit = QLineEdit(self)
        self.pw_edit   = QLineEdit(self)
        self.pw_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("Felhasználó:", self.user_edit)
        layout.addRow("Jelszó:",     self.pw_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                Qt.Horizontal, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_credentials(self):
        return self.user_edit.text(), self.pw_edit.text()

# ─── DB VIEWER import ─────────────────────────────────────────────────────
from gui.db_viewer import DatabaseViewer

# ─── FŐABLAK ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle(
            f"ERP Főképernyő – Dr. Köcher Kft.  (Bejelentkezve: {self.current_user})"
        )
        self.resize(800, 600)
        self._children = []

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(50,50,50,50)
        outer.setSpacing(30)
        outer.setAlignment(Qt.AlignCenter)

        self.logo_path = str(BUNDLE_DIR / "logo.png")

        btn_font = QFont("Arial", 18, QFont.Bold)
        orig_buttons = [
            ("Termékek Nyilvántartása",        self._open_products),
            ("Megrendelések Nyilvántása",      self._open_orders),
            ("Vevői és szállítási cím adatok", self._open_delivery_note_input),
            # itt szúrjuk be a címkenyomtatót
            ("Címke Készítése!",               self._open_label_maker),
            ("Kiszállítás és Szállítólevél",   self._open_delivery),
            ("Kiszállítások Megtekintése",     self._open_view_deliveries),
            ("Adatbázis szerkesztő",           self._open_db_viewer),
        ]
        new_buttons = [
            ("Gyártás indítása...",     self._open_manufacturing),
            ("Műszaknapló...",          self._open_shift_logger),
            ("Műszakgyártások",         self._open_foundry_products),
            ("Készletnyilvántartás",    self._open_stock_overview),
        ]

        left_layout  = QVBoxLayout()
        right_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        right_layout.setSpacing(20)

        for text, handler in orig_buttons:
            btn = QPushButton(text)
            btn.setFont(btn_font)
            btn.setMinimumHeight(60)
            btn.clicked.connect(handler)
            left_layout.addWidget(btn)
        left_layout.addStretch()

        # Fejlesztő név a bal sáv alján
        dev_lbl = QLabel("Fejlesztő: Polgár Tibor")
        dev_lbl.setFont(QFont("Arial", 10, QFont.StyleItalic))
        left_layout.addWidget(dev_lbl, alignment=Qt.AlignLeft)

        for text, handler in new_buttons:
            btn = QPushButton(text)
            btn.setFont(btn_font)
            btn.setMinimumHeight(60)
            btn.clicked.connect(handler)
            right_layout.addWidget(btn)
        label = QLabel("Öntöde")
        label.setFont(QFont("Arial", 32, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(label)
        right_layout.addStretch()

        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setSpacing(50)
        h_layout.addLayout(left_layout)
        h_layout.addLayout(right_layout)
        outer.addWidget(container)
        outer.addStretch()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if os.path.exists(self.logo_path):
            pix = QPixmap(self.logo_path).scaled(
                self.size() * 0.6,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            painter.setOpacity(0.1)
            x = (self.width() - pix.width()) // 2
            y = (self.height() - pix.height()) // 2
            painter.drawPixmap(x, y, pix)
        painter.setOpacity(1.0)
        super().paintEvent(event)

    def _open_db_viewer(self):
        auth = DBAuthDialog(self)
        if auth.exec_() != QDialog.Accepted:
            return
        user, pw = auth.get_credentials()
        if user.lower() != "polgartibor" or pw != "12345678":
            QMessageBox.warning(self, "Hiba", "Érvénytelen felhasználó vagy jelszó!")
            return
        w = DatabaseViewer(parent=self)
        w.show()
        self._children.append(w)

    # ─── további modulok ─────────────────────────────────────────────────
    def _open_products(self):
        from gui.product_gui import ProductWindow
        w = ProductWindow(); w.show(); self._children.append(w)

    def _open_orders(self):
        from gui.order_gui import OrderWin
        w = OrderWin(); w.show(); self._children.append(w)

    def _open_delivery_note_input(self):
        from gui.delivery_note_input import DeliveryNoteInputWindow
        w = DeliveryNoteInputWindow(); w.show(); self._children.append(w)

    def _open_delivery(self):
        from gui.delivery_gui import DeliveryWindow
        w = DeliveryWindow(); w.show(); self._children.append(w)

    def _open_view_deliveries(self):
        from gui.view_deliveries_gui import ViewDeliveriesWindow
        w = ViewDeliveriesWindow(); w.show(); self._children.append(w)

    def _open_label_maker(self):
        from gui.order_label_viewer import OrderLabelViewer
        w = OrderLabelViewer(); w.show(); self._children.append(w)

    def _open_manufacturing(self):
        from gui.manufacturing_gui import ManufacturingWindow
        w = ManufacturingWindow(); w.show(); self._children.append(w)

    def _open_shift_logger(self):
        from gui.shift_logger_gui import ShiftLoggerWindow
        w = ShiftLoggerWindow(); w.show(); self._children.append(w)

    def _open_foundry_products(self):
        from gui.foundry_products_gui import FoundryProductsWindow
        w = FoundryProductsWindow(); w.show(); self._children.append(w)

    def _open_stock_overview(self):
        from gui.stock_overview_gui import StockOverviewWindow
        w = StockOverviewWindow(); w.show(); self._children.append(w)


def main():
    conn = sqlite3.connect("user.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)
    user = login.get_user()

    # ─── csak polgár tiborhoz kérünk jelszót
    if user == "Polgár Tibor":
        pwd, ok = QInputDialog.getText(
            None, "Jelszó", "Add meg a jelszót:", QLineEdit.Password
        )
        if not ok or pwd != "12345678":
            QMessageBox.critical(None, "Hiba", "Érvénytelen jelszó!")
            sys.exit(1)

    win = MainWindow(user)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()










