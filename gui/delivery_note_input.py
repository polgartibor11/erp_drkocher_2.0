import sys
import os
import sqlite3
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QTableView, QVBoxLayout, QHBoxLayout, QApplication,
    QMessageBox, QFormLayout, QComboBox, QFrame
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPixmap
from PyQt5.QtCore import Qt, QSortFilterProxyModel

# Projekt gyökér hozzáadása az import útvonalhoz
this_dir    = os.path.dirname(__file__)
project_dir = os.path.abspath(os.path.join(this_dir, os.pardir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Termékadatbázis elérési útja
PRODUCTS_DB = os.path.join(project_dir, "modules", "product_module", "products.db")

class DeliveryNoteInputWindow(QWidget):
    """
    Csak a products.db-ben lévő termékekhez ad hozzá
    vevői és szállítási adatokat tömegesen.
    Vizuális tuninggal, logóval, cégnévvel és vevőválasztóval.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vevői és szállítási címek hozzáadása")
        self.resize(950, 720)

        self.ensure_columns_exist()

        # Céges fejléc logóval
        header_layout = QHBoxLayout()
        logo_path = os.path.join(project_dir, "logo.png")
        if os.path.exists(logo_path):
            logo = QLabel()
            logo.setPixmap(QPixmap(logo_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header_layout.addWidget(logo, alignment=Qt.AlignLeft)
        header_layout.addSpacing(10)
        company_label = QLabel("<b><span style='font-size:18pt'>Dr. Köcher Kft.</span></b>")
        header_layout.addWidget(company_label)
        header_layout.addStretch()

        # Vevőválasztó (adatkitöltéssel)
        self.customer_select_combo = QComboBox()
        self.customer_select_combo.setEditable(False)
        self.customer_select_combo.setMinimumWidth(220)
        self.customer_select_combo.currentIndexChanged.connect(self.on_customer_selected)

        # Vevői adatok mezők
        self.customer_name_edit          = QLineEdit()
        self.customer_address_edit       = QTextEdit();    self.customer_address_edit.setFixedHeight(50)
        self.customer_tax_number_edit    = QLineEdit()
        self.customer_eu_tax_number_edit = QLineEdit()
        self.customer_country_edit       = QLineEdit()

        # Szállítási adatok mezők
        self.shipping_name_edit    = QLineEdit()
        self.shipping_address_edit = QTextEdit(); self.shipping_address_edit.setFixedHeight(50)
        self.shipping_country_edit = QLineEdit()

        # Vevői űrlap
        customer_form = QFormLayout()
        customer_form.addRow("Vevő választás:", self.customer_select_combo)
        customer_form.addRow("Vevő neve:",        self.customer_name_edit)
        customer_form.addRow("Vevő címe:",        self.customer_address_edit)
        customer_form.addRow("Vevő adószáma:",    self.customer_tax_number_edit)
        customer_form.addRow("Vevő EU adószáma:", self.customer_eu_tax_number_edit)
        customer_form.addRow("Vevő országa:",     self.customer_country_edit)

        # Szállítási űrlap
        shipping_form = QFormLayout()
        shipping_form.addRow("Szállítási név:",    self.shipping_name_edit)
        shipping_form.addRow("Szállítási cím:",    self.shipping_address_edit)
        shipping_form.addRow("Szállítási ország:", self.shipping_country_edit)

        v_splitter = QFrame()
        v_splitter.setFrameShape(QFrame.VLine)
        v_splitter.setFrameShadow(QFrame.Sunken)

        top_layout = QHBoxLayout()
        top_layout.addLayout(customer_form)
        top_layout.addWidget(v_splitter)
        top_layout.addLayout(shipping_form)

        # Szűrő és tábla
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Összes vevő")
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)

        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.MultiSelection)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)
        self.table.setModel(self.proxy_model)

        # Gombok
        self.save_btn    = QPushButton("Adatok mentése")
        self.save_btn.clicked.connect(self.on_save)
        self.refresh_btn = QPushButton("Frissítés")
        self.refresh_btn.clicked.connect(self.load_products)

        # Fő elrendezés
        v_layout = QVBoxLayout(self)
        v_layout.addLayout(header_layout)
        v_layout.addSpacing(8)
        v_layout.addLayout(top_layout)
        v_layout.addSpacing(8)
        v_layout.addWidget(QLabel("Szűrés vevő neve szerint:"))
        v_layout.addWidget(self.filter_combo)
        v_layout.addWidget(QLabel("Válassza ki a termékeket:"))
        v_layout.addWidget(self.table)
        v_layout.addSpacing(8)
        h_btn = QHBoxLayout()
        h_btn.addWidget(self.save_btn)
        h_btn.addWidget(self.refresh_btn)
        h_btn.addStretch()
        v_layout.addLayout(h_btn)

        # Stílus
        self.setStyleSheet("""
            QWidget { font-family: Arial, sans-serif; font-size: 10pt; }
            QLineEdit, QTextEdit, QComboBox { font-size: 11pt; }
            QPushButton { font-weight: bold; padding: 6px 30px; border-radius: 4px; background: #1976d2; color: white; }
            QPushButton:hover { background: #1565c0; }
            QTableView { background: #f7f9fc; alternate-background-color: #eef3f9; }
            QHeaderView::section { background: #e3e9f1; font-weight: bold; }
        """)

        self.load_products()
        self.load_customers()

    def ensure_columns_exist(self):
        """Ha hiányoznak a customer_/shipping_ oszlopok, hozzáadjuk őket."""
        needed = {
            "customer_name":          "TEXT",
            "customer_address":       "TEXT",
            "customer_tax_number":    "TEXT",
            "customer_eu_tax_number": "TEXT",
            "customer_country":       "TEXT",
            "shipping_name":          "TEXT",
            "shipping_address":       "TEXT",
            "shipping_country":       "TEXT"
        }
        conn = sqlite3.connect(PRODUCTS_DB)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        existing = [row[1] for row in cur.fetchall()]
        for col, coltype in needed.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE products ADD COLUMN {col} {coltype}")
        conn.commit()
        conn.close()

    def load_products(self):
        """Betölti a products táblát, beállítja a táblázatot és a szűrő listát."""
        try:
            conn = sqlite3.connect(PRODUCTS_DB)
            conn.row_factory = sqlite3.Row
            cur = conn.execute("""
                SELECT id,
                       vevo_nev,
                       megnevezes, cikkszam, uzem_lanc,
                       customer_name, customer_address, customer_tax_number,
                       customer_eu_tax_number, customer_country,
                       shipping_name, shipping_address, shipping_country
                  FROM products
                 ORDER BY megnevezes
            """)
            rows = cur.fetchall()
            conn.close()

            # Frissítjük a legördülő szűrőt vevőnév szerint
            vevo_set = sorted({row["vevo_nev"] for row in rows if row["vevo_nev"]})
            self.filter_combo.blockSignals(True)
            self.filter_combo.clear()
            self.filter_combo.addItem("Összes vevő")
            for name in vevo_set:
                self.filter_combo.addItem(name)
            self.filter_combo.setCurrentIndex(0)
            self.filter_combo.blockSignals(False)
            self.proxy_model.setFilterWildcard("*")

            # Model összeállítása
            headers = [
                "Vevő neve", "Termék", "Cikkszám", "Üzem",
                "Customer neve", "Vevő címe", "Vevő adószám",
                "Vevő EU adószám", "Vevő országa",
                "Szállítási név", "Szállítási cím", "Szállítási ország"
            ]
            model = QStandardItemModel(len(rows), len(headers))
            model.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for col, key in enumerate([
                    "vevo_nev", "megnevezes", "cikkszam", "uzem_lanc",
                    "customer_name", "customer_address", "customer_tax_number",
                    "customer_eu_tax_number", "customer_country",
                    "shipping_name", "shipping_address", "shipping_country"
                ]):
                    item = QStandardItem(row[key] or "")
                    item.setData(row["id"], Qt.UserRole)
                    model.setItem(i, col, item)

            self.proxy_model.setSourceModel(model)
            self.table.resizeColumnsToContents()

            self.load_customers()  # frissítjük a vevőválasztót is
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Termékek betöltése sikertelen: {e}")

    def load_customers(self):
        """A products.db-ből egyedi vevőket betölti a vevőválasztó comboboxba."""
        try:
            conn = sqlite3.connect(PRODUCTS_DB)
            cur = conn.execute("""
                SELECT DISTINCT customer_name, customer_address, customer_tax_number,
                                customer_eu_tax_number, customer_country
                  FROM products
                 WHERE customer_name IS NOT NULL AND customer_name != ''
                 ORDER BY customer_name
            """)
            self.customer_select_combo.blockSignals(True)
            self.customer_select_combo.clear()
            self.customer_select_combo.addItem("Új vevő (kézi rögzítés)")
            self._customers = []
            for row in cur.fetchall():
                display = row[0]
                self.customer_select_combo.addItem(display)
                self._customers.append(row)
            self.customer_select_combo.blockSignals(False)
        except Exception as e:
            self.customer_select_combo.clear()
            self.customer_select_combo.addItem("Új vevő (kézi rögzítés)")
            self._customers = []

    def on_customer_selected(self, idx):
        """Ha meglévő vevőt választunk, tölti az adatmezőket."""
        if idx == 0:
            self.customer_name_edit.clear()
            self.customer_address_edit.clear()
            self.customer_tax_number_edit.clear()
            self.customer_eu_tax_number_edit.clear()
            self.customer_country_edit.clear()
        else:
            data = self._customers[idx-1]
            self.customer_name_edit.setText(data[0] or "")
            self.customer_address_edit.setText(data[1] or "")
            self.customer_tax_number_edit.setText(data[2] or "")
            self.customer_eu_tax_number_edit.setText(data[3] or "")
            self.customer_country_edit.setText(data[4] or "")

    def on_filter_changed(self, index):
        """A kiválasztott vevőnév szerint szűrjük a táblázatot."""
        if index == 0:
            self.proxy_model.setFilterWildcard("*")
        else:
            name = self.filter_combo.currentText()
            self.proxy_model.setFilterFixedString(name)

    def on_save(self):
        """A kiválasztott sorokat frissíti a megadott címekkel."""
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            QMessageBox.warning(self, "Figyelem", "Legalább egy terméket válassz ki!")
            return

        cust = {
            "customer_name":          self.customer_name_edit.text().strip(),
            "customer_address":       self.customer_address_edit.toPlainText().strip(),
            "customer_tax_number":    self.customer_tax_number_edit.text().strip(),
            "customer_eu_tax_number": self.customer_eu_tax_number_edit.text().strip(),
            "customer_country":       self.customer_country_edit.text().strip(),
        }
        ship = {
            "shipping_name":    self.shipping_name_edit.text().strip(),
            "shipping_address": self.shipping_address_edit.toPlainText().strip(),
            "shipping_country": self.shipping_country_edit.text().strip(),
        }

        if not cust["customer_name"] or not cust["customer_address"]:
            QMessageBox.warning(self, "Hiányzó adat", "Add meg a vevő nevét és címét!")
            return
        if not ship["shipping_name"] or not ship["shipping_address"]:
            QMessageBox.warning(self, "Hiányzó adat", "Add meg a szállítási nevet és címet!")
            return

        try:
            conn = sqlite3.connect(PRODUCTS_DB)
            cur = conn.cursor()
            for proxy_index in selection:
                src_index = self.proxy_model.mapToSource(proxy_index)
                prod_id = self.proxy_model.sourceModel().item(src_index.row(), 0).data(Qt.UserRole)
                cur.execute("""
                    UPDATE products SET
                        customer_name          = ?,
                        customer_address       = ?,
                        customer_tax_number    = ?,
                        customer_eu_tax_number = ?,
                        customer_country       = ?,
                        shipping_name          = ?,
                        shipping_address       = ?,
                        shipping_country       = ?
                    WHERE id = ?
                """, (
                    cust["customer_name"],
                    cust["customer_address"],
                    cust["customer_tax_number"],
                    cust["customer_eu_tax_number"],
                    cust["customer_country"],
                    ship["shipping_name"],
                    ship["shipping_address"],
                    ship["shipping_country"],
                    prod_id
                ))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Siker", "Adatok sikeresen mentve.")
            self.load_products()
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Mentés sikertelen: {e}")

def main():
    app = QApplication(sys.argv)
    w = DeliveryNoteInputWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()



















