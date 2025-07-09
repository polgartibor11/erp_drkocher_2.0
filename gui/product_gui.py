#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
# Az ERP1.0 mappa abszolút útvonala
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import math
import textwrap as _tw
os.environ["QT_OPENGL"] = "software"  # OpenGL-konfliktusok elkerülése

from datetime import date
from pathlib import Path
from typing import List

import pandas as pd
from PyQt5.QtCore  import Qt, QEvent, QSignalBlocker, QDate
from PyQt5.QtGui   import QPixmap, QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QFrame, QGroupBox, QLineEdit, QPushButton, QComboBox, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QSpinBox, QDoubleSpinBox, QTabWidget, QToolTip, QTextEdit,
    QDateEdit, QDialogButtonBox, QScrollArea
)

from modules.product_module.product_module import (
    Termek, ArSor,
    osszes_termek, hozzaad_termek, frissit_termek, torol_termek,
    aktualis_ar
)

IMG_MAX = 300  # Tooltip max méret px
NO_LOAD_OPTION = "--- Nincs betöltés ---"

# --- segédfüggvények ---
def clean(v):
    if v is None: return ""
    if isinstance(v, float) and math.isnan(v): return ""
    s = str(v)
    return "" if s.lower() == "nan" else s

def wrap(txt, w=35):
    return "\n".join(_tw.wrap(clean(txt), w))

def num(v, dec=3):
    try:
        f = float(v)
        return "" if math.isnan(f) else f"{f:.{dec}f}"
    except:
        return ""

def plants(lst):
    return sorted({p for t in lst for p in t.uzem_lanc})

class ProductWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dr. Köcher Kft. – Termékkezelő")
        self.resize(1580, 800)
        self.products: List[Termek] = []
        self._build_ui()
        self._load_products()  # Első adatbetöltés

    def _build_ui(self):
        cw = QWidget()
        cw.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(cw)
        main = QVBoxLayout(cw)
        main.setSpacing(15)
        self._header(main)
        self._search(main)
        self._table(main)
        self._crud(main)

    def _header(self, box):
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(15)

        logo_path = os.path.join(base_dir, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            header_layout.addWidget(QLabel(pixmap=pix))

        col = QVBoxLayout()
        col.addWidget(QLabel("<h2>Dr. Köcher Kft.</h2>"))
        col.addWidget(QLabel("Fejlesztő: Polgár Tibor"))
        header_layout.addLayout(col)

        header_layout.addStretch()

        btn_refresh = QPushButton("Adatbázis frissítése")
        btn_refresh.clicked.connect(self._on_refresh_database)
        header_layout.addWidget(btn_refresh)

        box.addWidget(header_frame)

        header_frame.setStyleSheet("""
            QFrame#headerFrame {
                background-color: #f2f2f2;
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            QLabel {
                font-family: Arial, sans-serif;
            }
        """)

    def _on_refresh_database(self):
        self._load_products()
        QMessageBox.information(self, "Frissítés", "Adatbázis sikeresen frissítve!")

    def _load_products(self):
        try:
            self.products = osszes_termek()
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Nem sikerült betölteni az adatbázist:\n{e}")

    def _search(self, box):
        grp = QGroupBox("Keresés")
        l = QHBoxLayout(grp)
        l.setSpacing(10)
        self.en, self.ec, self.ev = QLineEdit(), QLineEdit(), QLineEdit()
        self.cb = QComboBox()
        for e in (self.en, self.ec, self.ev):
            e.textChanged.connect(self._filter)
        self.cb.currentTextChanged.connect(self._filter)

        l.addWidget(QLabel("Megnevezés:")); l.addWidget(self.en)
        l.addWidget(QLabel("Cikkszám:"));    l.addWidget(self.ec)
        l.addWidget(QLabel("Vevő:"));        l.addWidget(self.ev)
        l.addWidget(QLabel("Üzem:"));        l.addWidget(self.cb)

        b1 = QPushButton("Törlés");       b1.clicked.connect(self._clear)
        b2 = QPushButton("Excel import"); b2.clicked.connect(self._import_excel)
        l.addWidget(b1); l.addWidget(b2)
        box.addWidget(grp)

    def _table(self, box):
        headers = [
            "Vevő", "Megnevezés", "Cikkszám", "Egység", "Felulet", "Alapanyagok",
            "Ár", "Valuta", "Súly", "Egys.", "Üzemlánc", "Fészkek",
            "Csokosúly", "Cs.egys.", "Szállítási név", "Szállítási cím", "_foto"
        ]
        self.tbl = QTableWidget(0, len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setColumnHidden(len(headers) - 1, True)

        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        h.setStretchLastSection(True)

        self.tbl.setAlternatingRowColors(True)
        self.tbl.setWordWrap(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.itemDoubleClicked.connect(self._edit)
        self.tbl.viewport().installEventFilter(self)
        box.addWidget(self.tbl)

    def _crud(self, box):
        row = QHBoxLayout()
        row.setSpacing(10)
        for txt, fn in [("Új", self._new), ("Módosít", self._edit), ("Törlés", self._delete)]:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        box.addLayout(row)

    def eventFilter(self, obj, event):
        if obj is self.tbl.viewport() and event.type() == QEvent.ToolTip:
            idx = self.tbl.indexAt(event.pos())
            if idx.isValid():
                foto = self.tbl.item(idx.row(), self.tbl.columnCount() - 1).text()
                if foto and Path(foto).exists():
                    img = QPixmap(foto)
                    if not img.isNull():
                        if img.width() > IMG_MAX or img.height() > IMG_MAX:
                            img = img.scaled(IMG_MAX, IMG_MAX, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        html = f"<img src='{foto}' width='{img.width()}'/>"
                        QToolTip.showText(event.globalPos(), html,
                            self.tbl, self.tbl.visualItemRect(self.tbl.item(idx.row(), idx.column())))
                        return True
            QToolTip.hideText()
        return super().eventFilter(obj, event)

    def _refresh(self, rows: List[Termek] | None = None):
        full = rows is None
        rows = rows or self.products
        self.tbl.setRowCount(0)
        for t in rows:
            ar, val = aktualis_ar(t) or (0, "")
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            cells = [
                clean(t.vevo_nev),
                wrap(t.megnevezes),
                clean(t.cikkszam),
                clean(t.mennyisegi_egyseg),
                clean(t.felulet),
                ", ".join(t.alapanyagok),
                num(ar, 2),
                clean(val),
                num(t.suly, 3),
                clean(t.suly_mertekegyseg),
                ", ".join(t.uzem_lanc),
                str(t.feszekszam),
                num(t.csokosuly, 3),
                clean(t.csokosuly_mertekegyseg),
                clean(getattr(t, "shipping_name", "")),
                clean(getattr(t, "shipping_address", "")),
                t.foto
            ]
            for c, v in enumerate(cells):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() ^ Qt.ItemIsEditable)
                if c == 0:
                    it.setData(Qt.UserRole, t.id)
                self.tbl.setItem(r, c, it)
            self.tbl.setRowHeight(r,
                min(150, max(50, 20 * math.ceil(len(str(t.megnevezes)) / 35))))
        if full:
            with QSignalBlocker(self.cb):
                self.cb.clear()
                self.cb.addItem("Mind")
                self.cb.addItems(plants(self.products))

    def _filter(self):
        n, c, v, p = (self.en.text().lower(), self.ec.text().lower(),
                      self.ev.text().lower(), self.cb.currentText())
        rows = [
            t for t in self.products
            if (not n or n in t.megnevezes.lower())
            and (not c or c in t.cikkszam.lower())
            and (not v or v in t.vevo_nev.lower())
            and (p == "Mind" or p in t.uzem_lanc)
        ]
        self._refresh(rows)

    def _clear(self):
        for w in (self.en, self.ec, self.ev):
            w.clear()
        self.cb.setCurrentText("Mind")
        self._refresh()

    def _sel_id(self):
        r = self.tbl.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Figyelem", "Válassz egy sort!")
            return None
        return self.tbl.item(r, 0).data(Qt.UserRole)

    def _new(self):
        dlg = ProductDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            if dlg.result.id == 0:
                max_id = max((p.id for p in self.products), default=0)
                dlg.result.id = max_id + 1
            try:
                hozzaad_termek(dlg.result)
            except Exception as e:
                QMessageBox.critical(self, "Hiba",
                    f"Hiba a termék hozzáadásakor:\n{e}")
                return
            self._load_products()

    def _edit(self, *_):
        pid = self._sel_id()
        if pid is None:
            return
        prod = next(p for p in self.products if p.id == pid)
        dlg = ProductDialog(self, prod)
        if dlg.exec_() == QDialog.Accepted:
            try:
                frissit_termek(dlg.result)
            except Exception as e:
                QMessageBox.critical(self, "Hiba",
                    f"Hiba a termék frissítésekor:\n{e}")
                return
            self._load_products()

    def _delete(self):
        pid = self._sel_id()
        if pid is None:
            return
        if QMessageBox.question(self, "Törlés", f"Törlöd ID={pid}?") == QMessageBox.Yes:
            try:
                torol_termek(pid)
            except Exception as e:
                QMessageBox.critical(self, "Hiba",
                    f"Hiba a termék törlésekor:\n{e}")
                return
            self._load_products()

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self,
            "Excel kiválasztása", "", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            df = pd.read_excel(path)
        except Exception as e:
            QMessageBox.critical(self, "Hiba", str(e))
            return

        dlg = MappingDialog(self, df)
        if dlg.exec_() != QDialog.Accepted:
            return
        mp = dlg.mapping
        next_id = max((p.id for p in self.products), default=0) + 1

        def cell(row, col, dv=""):
            if col == NO_LOAD_OPTION:
                return dv
            if col not in df.columns:
                return dv
            v = row[col]
            if pd.isna(v) or str(v).lower() == "nan" or str(v).strip() == "":
                return dv
            return v

        for _, row in df.iterrows():
            try:
                t = Termek(
                    id=next_id,
                    vevo_nev=cell(row, mp.get("vevo_nev", NO_LOAD_OPTION)),
                    megnevezes=cell(row, mp.get("megnevezes", NO_LOAD_OPTION)),
                    cikkszam=cell(row, mp.get("cikkszam", NO_LOAD_OPTION)),
                    mennyisegi_egyseg=cell(row, mp.get("mennyisegi_egyseg", NO_LOAD_OPTION)),
                    felulet=cell(row, mp.get("felulet", NO_LOAD_OPTION)),
                    alapanyagok=[s.strip() for s in str(cell(
                        row, mp.get("alapanyagok", NO_LOAD_OPTION)
                    )).split(",") if s.strip()],
                    suly=float(cell(row, mp.get("suly", NO_LOAD_OPTION), 0)),
                    suly_mertekegyseg=cell(row, mp.get("suly_mertekegyseg", NO_LOAD_OPTION)),
                    uzem_lanc=[s.strip() for s in str(cell(
                        row, mp.get("uzem_lanc", NO_LOAD_OPTION)
                    )).split(",") if s.strip()],
                    feszekszam=int(cell(row, mp.get("feszekszam", NO_LOAD_OPTION), 1)),
                    csokosuly=float(cell(row, mp.get("csokosuly", NO_LOAD_OPTION), 0)),
                    csokosuly_mertekegyseg=cell(
                        row, mp.get("csokosuly_mertekegyseg", NO_LOAD_OPTION)
                    ),
                    foto=cell(row, mp.get("foto", NO_LOAD_OPTION)),
                    arak=[ArSor(
                        ar=float(cell(row, mp.get("ar", NO_LOAD_OPTION), 0)),
                        valuta=cell(row, mp.get("valuta", NO_LOAD_OPTION)),
                        kezdet=date.today().isoformat(),
                        veg=None
                    )],
                    shipping_name=cell(row, mp.get("shipping_name", NO_LOAD_OPTION)),
                    shipping_address=cell(row, mp.get("shipping_address", NO_LOAD_OPTION))
                )
                hozzaad_termek(t)
                next_id += 1
            except Exception as ex:
                print(f"Hiba az importálás során: {ex}")
        self._load_products()
        

# === PRODUCT DIALOG ===
class ProductDialog(QDialog):
    def __init__(self, parent, termek: Termek | None = None):
        super().__init__(parent)
        self.setWindowTitle("Termék szerkesztése" if termek else "Új termék")
        self.original = termek
        self.result: Termek | None = None

        tabs = QTabWidget(self)
        self._build_main_tab(tabs)
        self._build_price_tab(tabs)

        row = QHBoxLayout()
        row.addWidget(QPushButton("Mentés", clicked=self.accept))
        row.addWidget(QPushButton("Mégse", clicked=self.reject))
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addLayout(row)

        if termek:
            self._load(termek)

    def _build_main_tab(self, tabs: QTabWidget):
        w = QWidget()
        f = QFormLayout(w)
        self.ev, self.en, self.ec, self.eu, self.es, self.ea = (QLineEdit() for _ in range(6))
        self.le_foto = QLineEdit()
        btn_foto = QPushButton("Fotó…")
        btn_foto.clicked.connect(self._pick_foto)

        hfoto = QHBoxLayout()
        hfoto.addWidget(self.le_foto)
        hfoto.addWidget(btn_foto)

        self.sp_s = QDoubleSpinBox(maximum=1e9, decimals=3)
        self.ed_su = QLineEdit()
        self.ed_pl = QLineEdit()
        self.sp_f = QSpinBox(maximum=100)
        self.sp_cs = QDoubleSpinBox(maximum=1e9, decimals=3)
        self.ed_cs = QLineEdit()

        # Új mezők a vevő és szállítási adatokhoz
        self.ev_customer_name = QLineEdit()
        self.ev_customer_address = QTextEdit()
        self.ev_customer_address.setFixedHeight(50)
        self.ev_customer_tax_number = QLineEdit()
        self.ev_customer_eu_tax_number = QLineEdit()
        self.ev_customer_country = QLineEdit()
        self.ev_shipping_name = QLineEdit()
        self.ev_shipping_address = QTextEdit()
        self.ev_shipping_address.setFixedHeight(50)
        self.ev_shipping_country = QLineEdit()

        f.addRow("Vevő neve:", self.ev)
        f.addRow("Megnevezés:", self.en)
        f.addRow("Cikkszám:", self.ec)
        f.addRow("Egység:", self.eu)
        f.addRow("Felulet:", self.es)
        f.addRow("Alapanyagok (vessző):", self.ea)
        f.addRow("Fotó fájl:", hfoto)
        f.addRow("Súly:", self.sp_s)
        f.addRow("Súly-egység:", self.ed_su)
        f.addRow("Üzemlánc (vessző):", self.ed_pl)
        f.addRow("Fészkek:", self.sp_f)
        f.addRow("Csokosúly:", self.sp_cs)
        f.addRow("Csok.egység:", self.ed_cs)

        # Új sorok hozzáadása a vevői adatoknak
        f.addRow("Vevői név:", self.ev_customer_name)
        f.addRow("Vevői cím:", self.ev_customer_address)
        f.addRow("Vevői adószám:", self.ev_customer_tax_number)
        f.addRow("Vevői EU adószám:", self.ev_customer_eu_tax_number)
        f.addRow("Vevői ország:", self.ev_customer_country)

        # Új sorok hozzáadása a szállítási adatoknak
        f.addRow("Szállítási név:", self.ev_shipping_name)
        f.addRow("Szállítási cím:", self.ev_shipping_address)
        f.addRow("Szállítási ország:", self.ev_shipping_country)

        tabs.addTab(w, "Alapadatok")

    def _pick_foto(self):
        path, _ = QFileDialog.getOpenFileName(self, "Kép kiválasztása", "", "Képek (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.le_foto.setText(path)

    def _build_price_tab(self, tabs: QTabWidget):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tblp = QTableWidget(0, 4)
        self.tblp.setHorizontalHeaderLabels(["Ár", "Valuta", "Kezdet", "Vég"])
        self.tblp.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tblp)

        hb = QHBoxLayout()
        hb.addWidget(QPushButton("+ Új ár", clicked=self._add_price))
        hb.addWidget(QPushButton("Töröl ár", clicked=lambda: self.tblp.removeRow(self.tblp.currentRow())))
        hb.addStretch()
        lay.addLayout(hb)

        tabs.addTab(w, "Ártörténet")

    def _add_price(self):
        dlg = AddPriceDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self._append_price(dlg.result)

    def _append_price(self, s: ArSor):
        r = self.tblp.rowCount()
        self.tblp.insertRow(r)
        for c, v in enumerate([f"{s.ar:.2f}", s.valuta, s.kezdet, s.veg or ""]):
            it = QTableWidgetItem(v)
            it.setFlags(it.flags() ^ Qt.ItemIsEditable)
            self.tblp.setItem(r, c, it)

    def _load(self, t: Termek):
        self.ev.setText(t.vevo_nev)
        self.en.setText(t.megnevezes)
        self.ec.setText(t.cikkszam)
        self.eu.setText(t.mennyisegi_egyseg)
        self.es.setText(t.felulet)
        self.ea.setText(", ".join(t.alapanyagok))
        self.le_foto.setText(t.foto)
        self.sp_s.setValue(t.suly)
        self.ed_su.setText(t.suly_mertekegyseg)
        self.ed_pl.setText(", ".join(t.uzem_lanc))
        self.sp_f.setValue(t.feszekszam)
        self.sp_cs.setValue(t.csokosuly)
        self.ed_cs.setText(t.csokosuly_mertekegyseg)
        for s in t.arak:
            self._append_price(s)

        # Új mezők betöltése (vevői és szállítási)
        self.ev_customer_name.setText(getattr(t, "customer_name", ""))
        self.ev_customer_address.setPlainText(getattr(t, "customer_address", ""))
        self.ev_customer_tax_number.setText(getattr(t, "customer_tax_number", ""))
        self.ev_customer_eu_tax_number.setText(getattr(t, "customer_eu_tax_number", ""))
        self.ev_customer_country.setText(getattr(t, "customer_country", ""))

        self.ev_shipping_name.setText(getattr(t, "shipping_name", ""))
        self.ev_shipping_address.setPlainText(getattr(t, "shipping_address", ""))
        self.ev_shipping_country.setText(getattr(t, "shipping_country", ""))

    def accept(self):
        try:
            arak = []
            for r in range(self.tblp.rowCount()):
                ar = float(self.tblp.item(r, 0).text())
                val = self.tblp.item(r, 1).text()
                d0 = self.tblp.item(r, 2).text()
                d1 = self.tblp.item(r, 3).text() or None
                arak.append(ArSor(ar=ar, valuta=val, kezdet=d0, veg=d1))
            if not arak:
                arak = [ArSor(ar=0.0, valuta="", kezdet=date.today().isoformat(), veg=None)]

            self.result = Termek(
                id=self.original.id if self.original else 0,
                vevo_nev=self.ev.text(),
                megnevezes=self.en.text(),
                cikkszam=self.ec.text(),
                mennyisegi_egyseg=self.eu.text(),
                felulet=self.es.text(),
                alapanyagok=[s.strip() for s in self.ea.text().split(",") if s.strip()],
                suly=self.sp_s.value(),
                suly_mertekegyseg=self.ed_su.text(),
                uzem_lanc=[s.strip() for s in self.ed_pl.text().split(",") if s.strip()],
                feszekszam=self.sp_f.value(),
                csokosuly=self.sp_cs.value(),
                csokosuly_mertekegyseg=self.ed_cs.text() or self.ed_su.text(),
                foto=self.le_foto.text(),
                arak=arak,
                customer_name=self.ev_customer_name.text(),
                customer_address=self.ev_customer_address.toPlainText(),
                customer_tax_number=self.ev_customer_tax_number.text(),
                customer_eu_tax_number=self.ev_customer_eu_tax_number.text(),
                customer_country=self.ev_customer_country.text(),
                shipping_name=self.ev_shipping_name.text(),
                shipping_address=self.ev_shipping_address.toPlainText(),
                shipping_country=self.ev_shipping_country.text()
            )
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Hiba a mentéskor:\n{e}")

# Az AddPriceDialog és MappingDialog változatlanok maradnak.

class AddPriceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Új ár felvétele")
        self.result = None

        form = QFormLayout(self)

        self.sp_ar     = QDoubleSpinBox(decimals=2, maximum=1e9)
        self.le_valuta = QLineEdit()
        self.de_kezdet = QDateEdit(QDate.currentDate(), calendarPopup=True)
        self.de_veg    = QDateEdit(QDate.currentDate(), calendarPopup=True)

        form.addRow("Ár:", self.sp_ar)
        form.addRow("Valuta:", self.le_valuta)
        form.addRow("Kezdet:", self.de_kezdet)
        form.addRow("Vég:", self.de_veg)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _on_accept(self):
        # Átalakítjuk ArSor objektummá
        self.result = ArSor(
            ar     = float(self.sp_ar.value()),
            valuta = self.le_valuta.text().strip(),
            kezdet = self.de_kezdet.date().toString("yyyy-MM-dd"),
            veg    = self.de_veg.date().toString("yyyy-MM-dd")
        )
        self.accept()


class MappingDialog(QDialog):
    def __init__(self, parent, dataframe: pd.DataFrame):
        super().__init__(parent)
        self.setWindowTitle("Oszlopok hozzárendelése")
        self.df = dataframe
        self.mapping = {}

        # Fő layout
        main_lay = QVBoxLayout(self)

        # 1) Preview: az első 5 sor megjelenítése QTableWidget-ben
        preview = QTableWidget(min(5, len(dataframe)), len(dataframe.columns))
        preview.setHorizontalHeaderLabels(list(dataframe.columns))
        preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, (_, row) in enumerate(dataframe.head(5).iterrows()):
            for j, col in enumerate(dataframe.columns):
                preview.setItem(i, j, QTableWidgetItem(str(row[col])))
        main_lay.addWidget(QLabel("Adat előnézet (első 5 sor):"))
        main_lay.addWidget(preview)

        # 2) Görgethető form a hozzárendeléseknek
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        frm_container = QWidget()
        form = QFormLayout(frm_container)

        # A Termek mezőnevek, amiket importálni tudsz
        fields = [
            "vevo_nev", "megnevezes", "cikkszam", "mennyisegi_egyseg",
            "felulet", "alapanyagok", "suly", "suly_mertekegyseg",
            "uzem_lanc", "feszekszam", "csokosuly",
            "csokosuly_mertekegyseg", "foto",
            "ar", "valuta", "kezdet", "veg",
            "shipping_name", "shipping_address", "shipping_country"
        ]

        # minden mezőhöz egy legördülő, amelyben a DataFrame oszlopai + "Nincs betöltés"
        self._combos = {}
        choices = [NO_LOAD_OPTION] + list(dataframe.columns)
        for fld in fields:
            cb = QComboBox()
            cb.addItems(choices)
            form.addRow(f"{fld} oszlopa:", cb)
            self._combos[fld] = cb

        scroll.setWidget(frm_container)
        main_lay.addWidget(scroll, stretch=1)

        # 3) Ok/Cancel gombok
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        main_lay.addWidget(bb)

    def _on_accept(self):
        # Összegyűjtjük, amit kiválasztottál
        for fld, cb in self._combos.items():
            val = cb.currentText()
            if val != NO_LOAD_OPTION:
                self.mapping[fld] = val
        self.accept()
def main():
    app = QApplication(sys.argv)
    # Szebb, egységes Fusion-stílus + világos paletta
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(250, 250, 250))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, QColor(240, 240, 240))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor(225, 225, 225))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.Highlight, QColor(30, 144, 255))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)

    win = ProductWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


