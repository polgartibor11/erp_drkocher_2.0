#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
this_dir = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(this_dir, os.pardir))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import sqlite3
import textwrap as _tw
from datetime import datetime
from typing import List, Dict, Set, Tuple
from pathlib import Path

from PyQt5.QtCore import Qt, QDate, QSignalBlocker
from PyQt5.QtGui import QPixmap, QDoubleValidator
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QTextEdit, QPushButton, QDateEdit, QComboBox,
    QMessageBox, QDialog, QFormLayout, QAbstractItemView, QFileDialog
)

from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

from modules.product_module.product_module import Termek, osszes_termek, aktualis_ar
from modules.order_module.order_module import (
    Order, Tetel, osszes_megrendeles,
    hozzaad_megrendeles, frissit_megrendeles,
    torol_megrendeles, uj_id
)

# ha order_gui.py a gui/ mappában van, akkor ERP1.0 a parent
this_dir = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(this_dir, os.pardir))
PRODUCTS_DB = os.path.join(BASE_DIR, "modules", "product_module", "products.db")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def wrap(txt: str, width: int = 40) -> str:
    lines = _tw.wrap(str(txt), width,
                     break_long_words=False, break_on_hyphens=False)
    return "\n".join(lines[:2]) if lines else ""

def plants(prods: List[Termek]) -> List[str]:
    return sorted({u for p in prods for u in p.uzem_lanc})

def customers(prods: List[Termek]) -> List[str]:
    return sorted({p.vevo_nev for p in prods})


class OrderWin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dr. Köcher Kft. – Megrendelés-nyilvántartó")
        self.resize(1800, 860)

        # adatok
        self.termekek: List[Termek] = osszes_termek()
        self.orders:    List[Order] = osszes_megrendeles()
        self.sort_reverse = False

        # PDF-sablonok helye
        self.template_dir = os.path.join(BASE_DIR, "templates")

        self._build_ui()
        self._apply_filter()


    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        main = QVBoxLayout(cw)

        # fejléc
        header = QHBoxLayout()
        logo_path = os.path.join(BASE_DIR, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(80, 80,
                                            Qt.KeepAspectRatio,
                                            Qt.SmoothTransformation)
            header.addWidget(QLabel(pixmap=pix))
        col = QVBoxLayout()
        col.addWidget(QLabel("<h2>Dr. Köcher Kft.</h2>"))
        col.addWidget(QLabel("Megrendelés-nyilvántartó   •   Fejlesztő: Polgár Tibor"))
        header.addLayout(col)
        header.addStretch()
        main.addLayout(header)

        # szűrők
        flt = QHBoxLayout()
        self.cb_vevo = QComboBox()
        self.cb_vevo.addItem("Mind")
        self.cb_vevo.addItems(customers(self.termekek))
        self.cb_vevo.currentTextChanged.connect(self._apply_filter)
        flt.addWidget(self.cb_vevo)

        self.le_cikk = QLineEdit()
        self.le_cikk.setPlaceholderText("Cikkszám")
        self.le_cikk.textChanged.connect(self._apply_filter)
        flt.addWidget(self.le_cikk)

        self.cb_uzem = QComboBox()
        self.cb_uzem.addItem("Mind")
        self.cb_uzem.addItems(plants(self.termekek))
        self.cb_uzem.currentTextChanged.connect(self._apply_filter)
        flt.addWidget(self.cb_uzem)

        self.le_termek = QLineEdit()
        self.le_termek.setPlaceholderText("Terméknév")
        self.le_termek.textChanged.connect(self._apply_filter)
        flt.addWidget(self.le_termek)

        self.cb_sort = QComboBox()
        self.cb_sort.addItems(["Határidő ↑", "Határidő ↓"])
        self.cb_sort.currentIndexChanged.connect(self._on_sort_changed)
        flt.addWidget(self.cb_sort)

        btn_refresh = QPushButton("Adatbázis frissítése")
        btn_refresh.clicked.connect(self._refresh_products)
        flt.addWidget(btn_refresh)

        main.addLayout(flt)

        # táblázat
        cols = [
            "Rend.ID","Megr.szám","Vevő","Termék","Cikkszám",
            "Megr.menny.","Egység","Fennmaradó","Egység","Ár","Valuta",
            "Üzem","Beérk.","Határidő",
            "Customer Name","Customer Address","Customer Tax No",
            "Customer EU Tax No","Customer Country",
            "Shipping Name","Shipping Address","Shipping Country"
        ]
        self.tbl = QTableWidget(0, len(cols))
        self.tbl.setHorizontalHeaderLabels(cols)
        head = self.tbl.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.Interactive)
        head.resizeSection(3, 380)
        head.resizeSection(4, 170)
        head.resizeSection(14, 200)
        head.resizeSection(16, 200)
        head.resizeSection(19, 200)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main.addWidget(self.tbl)

        # gombok
        bar = QHBoxLayout()
        bar.addWidget(QPushButton("Új",      clicked=self._new))
        bar.addWidget(QPushButton("Módosít", clicked=self._edit))
        bar.addWidget(QPushButton("Törlés",  clicked=self._delete))
        bar.addWidget(QPushButton("PDF export", clicked=self._pdf))
        bar.addStretch()
        main.addLayout(bar)


    def _on_sort_changed(self, index: int):
        self.sort_reverse = (index == 1)
        self._apply_filter()


    def _refresh_products(self):
        self.termekek = osszes_termek()
        with QSignalBlocker(self.cb_vevo):
            self.cb_vevo.clear()
            self.cb_vevo.addItem("Mind")
            self.cb_vevo.addItems(customers(self.termekek))
        with QSignalBlocker(self.cb_uzem):
            self.cb_uzem.clear()
            self.cb_uzem.addItem("Mind")
            self.cb_uzem.addItems(plants(self.termekek))
        self._apply_filter()


    def _apply_filter(self):
        v = None if self.cb_vevo.currentText()=="Mind" else self.cb_vevo.currentText().lower()
        c = self.le_cikk.text().lower()
        u = None if self.cb_uzem.currentText()=="Mind" else self.cb_uzem.currentText().lower()
        t = self.le_termek.text().lower()

        filtered = []
        for o in osszes_megrendeles():
            if not o.tetelek: continue
            tet = o.tetelek[0]
            if tet.fennmarado_mennyiseg <= 0: continue
            p = next((x for x in self.termekek if x.id==tet.product_id), None)
            if not p: continue
            if v and v not in o.vevo_nev.lower():        continue
            if c and c not in p.cikkszam.lower():         continue
            if t and t not in p.megnevezes.lower():       continue
            if u and u not in " ".join(p.uzem_lanc).lower(): continue
            filtered.append((o,p,tet))

        filtered.sort(key=lambda x: x[0].szall_hatarido or "", reverse=self.sort_reverse)

        self.tbl.setRowCount(0)
        for o, p, tet in filtered:
            conn = sqlite3.connect(PRODUCTS_DB)
            conn.row_factory = sqlite3.Row
            rec = conn.execute("""
                SELECT customer_name, customer_address, customer_tax_number,
                       customer_eu_tax_number, customer_country,
                       shipping_name, shipping_address, shipping_country
                  FROM products WHERE id = ?
            """, (p.id,)).fetchone()
            conn.close()

            ar_valuta = aktualis_ar(p) or (0.0, "")
            ar, valuta = f"{ar_valuta[0]:.2f}", ar_valuta[1]

            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            vals = [
                str(o.id), o.megrendeles_szam, o.vevo_nev, p.megnevezes,
                p.cikkszam, f"{tet.qty:g}", p.mennyisegi_egyseg,
                f"{tet.fennmarado_mennyiseg:g}", p.mennyisegi_egyseg,
                ar, valuta, ", ".join(p.uzem_lanc),
                o.beerkezes, o.szall_hatarido,
                rec["customer_name"] or "", rec["customer_address"] or "",
                rec["customer_tax_number"] or "", rec["customer_eu_tax_number"] or "",
                rec["customer_country"] or "",
                rec["shipping_name"] or "", rec["shipping_address"] or "",
                rec["shipping_country"] or ""
            ]
            for col, txt in enumerate(vals):
                it = QTableWidgetItem(txt)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if col == 0:
                    it.setData(Qt.UserRole, (o.id, p.id))
                self.tbl.setItem(r, col, it)
            self.tbl.setRowHeight(r, 26)


    def _selected_ids(self) -> Set[int]:
        return {
            self.tbl.item(i.row(), 0).data(Qt.UserRole)[0]
            for i in self.tbl.selectionModel().selectedRows()
        }


    def _new(self):
        dlg = OrderDialog(self, self.termekek)
        dlg.resize(1200, 700)
        if dlg.exec_() != QDialog.Accepted:
            return
        meta = dict(
            vevo_nev=dlg.base_vevo_nev,
            vevo_cim=dlg.base_vevo_cim,
            vevo_adoszam=dlg.base_vevo_adoszam,
            szallitasi_nev=dlg.base_szallitasi_nev,
            szallitasi_cim=dlg.base_szallitasi_cim,
            beerkezes=dlg.base_be,
            megrendeles_szam=dlg.base_nr,
            szall_hatarido=dlg.base_sz,
            megjegyzes=dlg.base_mj,
        )
        for pid, qty in dlg.checked.items():
            egys = next(p.mennyisegi_egyseg for p in self.termekek if p.id==pid)
            order = Order(
                id=uj_id(),
                tetelek=[Tetel(product_id=pid, qty=qty,
                               fennmarado_mennyiseg=qty,
                               mennyisegi_egyseg=egys)],
                **meta,
            )
            hozzaad_megrendeles(order)
            self.orders.append(order)
        self._apply_filter()


    def _edit(self):
        ids = self._selected_ids()
        if len(ids) != 1:
            QMessageBox.warning(self, "Módosítás", "Válassz ki pontosan egy rendelést!")
            return
        rid = next(iter(ids))
        order = next(o for o in self.orders if o.id==rid)
        pid = order.tetelek[0].product_id
        dlg = OrderDialog(self, self.termekek, order, lock_pid=pid)
        dlg.resize(1200, 700)
        if dlg.exec_() != QDialog.Accepted:
            return
        new_qty = list(dlg.checked.values())[0]
        t = order.tetelek[0]
        t.qty = new_qty
        t.fennmarado_mennyiseg = new_qty
        order.vevo_nev = dlg.base_vevo_nev
        order.vevo_cim = dlg.base_vevo_cim
        order.vevo_adoszam = dlg.base_vevo_adoszam
        order.szallitasi_nev = dlg.base_szallitasi_nev
        order.szallitasi_cim = dlg.base_szallitasi_cim
        order.beerkezes = dlg.base_be
        order.szall_hatarido = dlg.base_sz
        order.megrendeles_szam = dlg.base_nr
        order.megjegyzes = dlg.base_mj
        frissit_megrendeles(order)
        self._apply_filter()


    def _delete(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.warning(self, "Törlés", "Nincs kijelölés.")
            return
        if QMessageBox.question(
            self, "Törlés",
            f"Törlöd a kijelölt ({len(ids)}) rendelést?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        for rid in ids:
            torol_megrendeles(rid)
        self.orders = [o for o in self.orders if o.id not in ids]
        self._apply_filter()


    def _pdf(self):
        # 1) Szűrés: fennmaradó >0 és filterfeltételek
        v = None if self.cb_vevo.currentText()=="Mind" else self.cb_vevo.currentText().lower()
        c = self.le_cikk.text().lower()
        u = None if self.cb_uzem.currentText()=="Mind" else self.cb_uzem.currentText().lower()
        t = self.le_termek.text().lower()

        rows = []
        for o in self.orders:
            if not o.tetelek: continue
            tet = o.tetelek[0]
            if tet.fennmarado_mennyiseg <= 0: continue
            p = next((x for x in self.termekek if x.id==tet.product_id), None)
            if not p: continue
            if v and v not in o.vevo_nev.lower():        continue
            if c and c not in p.cikkszam.lower():         continue
            if t and t not in p.megnevezes.lower():       continue
            if u and u not in " ".join(p.uzem_lanc).lower(): continue
            rows.append((o,p,tet))

        if not rows:
            QMessageBox.information(self, "PDF", "Nincs mit exportálni.")
            return

        # 2) Fájlnév és mentés
        default = f"nyitott_rendelesek_{datetime.now():%Y%m%d}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "PDF mentése…", default, "PDF fájl (*.pdf)")
        if not path: return
        if not path.lower().endswith(".pdf"): path += ".pdf"

        # 3) Táblázat HTML
        headers = [
            "Rend.ID","Megr.szám","Vevő neve","Termék","Cikkszám",
            "Megrendelt menny.","Egység","Fennmaradó menny.","Egység",
            "Üzem","Beérkezés","Határidő"
        ]
        thead = "".join(f"<th>{h}</th>" for h in headers)
        tbody = ""
        for o, p, t in rows:
            cells = "".join([
                f"<td>{o.id}</td>",
                f"<td>{o.megrendeles_szam}</td>",
                f"<td>{o.vevo_nev}</td>",
                f"<td>{p.megnevezes}</td>",
                f"<td>{p.cikkszam}</td>",
                f"<td>{t.qty:g}</td>",
                f"<td>{p.mennyisegi_egyseg}</td>",
                f"<td>{t.fennmarado_mennyiseg:g}</td>",
                f"<td>{p.mennyisegi_egyseg}</td>",
                f"<td>{', '.join(p.uzem_lanc)}</td>",
                f"<td>{o.beerkezes}</td>",
                f"<td>{o.szall_hatarido}</td>",
            ])
            tbody += f"<tr>{cells}</tr>"

        table_html = f"""
        <table>
          <thead><tr>{thead}</tr></thead>
          <tbody>{tbody}</tbody>
        </table>
        """

        # 4) Jinja2 render és PDF
        env  = Environment(loader=FileSystemLoader(self.template_dir))
        tmpl = env.get_template("base.html")
        logo_uri = Path(BASE_DIR, "logo.png").absolute().as_uri()
        html = tmpl.render(
            logo_path=logo_uri,
            company_name="Dr. Köcher Kft. – Megrendelés-nyilvántartó",
            report_title="Nyitott megrendelések listája",
            content_table=table_html
        )

        try:
            HTML(string=html).write_pdf(path)
            QMessageBox.information(self, "PDF", f"Sikeresen elmentve:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"PDF generálás sikertelen:\n{e}")


class OrderDialog(QDialog):
    def __init__(self, parent, prods: List[Termek], orig: Order | None = None, lock_pid: int | None = None):
        super().__init__(parent)
        self.setWindowTitle("Megrendelés")
        self.resize(1200, 700)

        self.prods = prods
        self.lock_pid = lock_pid
        self.checked: Dict[int, float] = {t.product_id: t.qty for t in orig.tetelek} if orig else {}
        if lock_pid is not None and lock_pid not in self.checked:
            self.checked[lock_pid] = 1.0

        self._build_ui()
        self._filter()
        if orig:
            self._load_meta(orig)

    def _build_ui(self):
        lay = QVBoxLayout(self)

        sf = QHBoxLayout()
        self.le_v = QLineEdit()
        self.le_v.setPlaceholderText("Vevő")
        self.le_v.textChanged.connect(self._filter)
        self.le_c = QLineEdit()
        self.le_c.setPlaceholderText("Cikkszám")
        self.le_c.textChanged.connect(self._filter)
        self.le_t = QLineEdit()
        self.le_t.setPlaceholderText("Termék")
        self.le_t.textChanged.connect(self._filter)
        self.cb_u = QComboBox()
        self.cb_u.addItem("Mind")
        self.cb_u.addItems(plants(self.prods))
        self.cb_u.currentTextChanged.connect(self._filter)
        for w in (self.le_v, self.le_c, self.le_t, self.cb_u):
            sf.addWidget(w)
        lay.addLayout(sf)

        self.tt = QTableWidget(0, 7)
        self.tt.setHorizontalHeaderLabels(["✓", "ID", "Vevő neve", "Megnevezés", "Cikkszám", "Egység", "Mennyiség"])
        head = self.tt.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.Interactive)
        head.resizeSection(2, 200)
        head.resizeSection(3, 380)
        head.resizeSection(4, 160)
        self.tt.itemChanged.connect(self._track_check)
        lay.addWidget(self.tt)

        form = QFormLayout()
        self.le_vevo_nev = QLineEdit()
        self.le_vevo_cim = QTextEdit(); self.le_vevo_cim.setFixedHeight(60)
        self.le_vevo_adoszam = QLineEdit()
        self.le_szallitasi_nev = QLineEdit()
        self.le_szallitasi_cim = QTextEdit(); self.le_szallitasi_cim.setFixedHeight(60)
        form.addRow("Vevő neve:", self.le_vevo_nev)
        form.addRow("Vevő címe:", self.le_vevo_cim)
        form.addRow("Vevő adószám:", self.le_vevo_adoszam)
        form.addRow("Szállítási név:", self.le_szallitasi_nev)
        form.addRow("Szállítási cím:", self.le_szallitasi_cim)

        self.de_be = QDateEdit(QDate.currentDate(), calendarPopup=True)
        self.de_sz = QDateEdit(QDate.currentDate(), calendarPopup=True)
        self.le_nr = QLineEdit()
        self.te_mj = QTextEdit()
        form.addRow("Beérkezés:", self.de_be)
        form.addRow("Szállítási határidő:", self.de_sz)
        form.addRow("Megrendelési szám:", self.le_nr)
        form.addRow("Megjegyzés:", self.te_mj)

        self.ar_label = QLabel("-")
        self.valuta_label = QLabel("-")
        form.addRow("Aktuális ár:", self.ar_label)
        form.addRow("Valuta:", self.valuta_label)

        lay.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(QPushButton("Mentés", clicked=self._accept))
        btns.addWidget(QPushButton("Mégsem", clicked=self.reject))
        lay.addLayout(btns)

    def _filter(self):
        v = self.le_v.text().lower()
        c = self.le_c.text().lower()
        t = self.le_t.text().lower()
        u = self.cb_u.currentText(); u = None if u == "Mind" else u.lower()

        selected_pid = None
        for r in range(self.tt.rowCount()):
            pid = int(self.tt.item(r, 1).text())
            if pid in self.checked:
                selected_pid = pid
                break

        if selected_pid is not None:
            self._update_price_display(selected_pid)
            self._update_form_fields(selected_pid)
        else:
            self.ar_label.setText("-")
            self.valuta_label.setText("-")
            self._clear_form_fields()

        for r in range(self.tt.rowCount()):
            pid = int(self.tt.item(r, 1).text())
            if pid in self.checked:
                le: QLineEdit = self.tt.cellWidget(r, 6)
                try:
                    self.checked[pid] = float(le.text().replace(",", ".") or 1)
                except ValueError:
                    pass

        self.tt.blockSignals(True)
        self.tt.setRowCount(0)
        for p in self.prods:
            if v and v not in p.vevo_nev.lower():        continue
            if c and c not in p.cikkszam.lower():         continue
            if t and t not in p.megnevezes.lower():       continue
            if u and u not in " ".join(p.uzem_lanc).lower(): continue

            r = self.tt.rowCount()
            self.tt.insertRow(r)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if self.lock_pid and p.id != self.lock_pid:
                chk.setFlags(chk.flags() ^ Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if p.id in self.checked else Qt.Unchecked)
            self.tt.setItem(r, 0, chk)

            self.tt.setItem(r, 1, QTableWidgetItem(str(p.id)))
            self.tt.setItem(r, 2, QTableWidgetItem(p.vevo_nev))
            self.tt.setItem(r, 3, QTableWidgetItem(p.megnevezes))
            self.tt.setItem(r, 4, QTableWidgetItem(p.cikkszam))
            self.tt.setItem(r, 5, QTableWidgetItem(p.mennyisegi_egyseg))

            le_qty = QLineEdit(str(self.checked.get(p.id, 1)))
            le_qty.setValidator(QDoubleValidator(0.01, 1e9, 3))
            if self.lock_pid and p.id != self.lock_pid:
                le_qty.setEnabled(False)
            le_qty.editingFinished.connect(lambda pid=p.id, le=le_qty: self._update_qty(pid, le))
            self.tt.setCellWidget(r, 6, le_qty)
        self.tt.blockSignals(False)

    def _update_price_display(self, pid: int):
        p = next((x for x in self.prods if x.id == pid), None)
        if p:
            ar_valuta = aktualis_ar(p)
            if ar_valuta:
                self.ar_label.setText(f"{ar_valuta[0]:.2f}")
                self.valuta_label.setText(ar_valuta[1])
            else:
                self.ar_label.setText("-")
                self.valuta_label.setText("-")

    def _update_form_fields(self, pid: int):
        conn = sqlite3.connect(PRODUCTS_DB)
        conn.row_factory = sqlite3.Row
        rec = conn.execute("""
            SELECT customer_name, customer_address, customer_tax_number,
                   shipping_name, shipping_address
              FROM products WHERE id = ?
        """, (pid,)).fetchone()
        conn.close()
        if not rec:
            return
        self.le_vevo_nev.setText(rec["customer_name"] or "")
        self.le_vevo_cim.setPlainText(rec["customer_address"] or "")
        self.le_vevo_adoszam.setText(rec["customer_tax_number"] or "")
        self.le_szallitasi_nev.setText(rec["shipping_name"] or "")
        self.le_szallitasi_cim.setPlainText(rec["shipping_address"] or "")

    def _clear_form_fields(self):
        self.le_vevo_nev.clear()
        self.le_vevo_cim.clear()
        self.le_vevo_adoszam.clear()
        self.le_szallitasi_nev.clear()
        self.le_szallitasi_cim.clear()

    def _update_qty(self, pid: int, le: QLineEdit):
        try:
            self.checked[pid] = float(le.text().replace(",", ".") or 1)
            self._update_price_display(pid)
        except ValueError:
            pass

    def _track_check(self, it: QTableWidgetItem):
        if it.column() != 0:
            return
        pid = int(self.tt.item(it.row(), 1).text())
        le: QLineEdit = self.tt.cellWidget(it.row(), 6)
        if it.checkState() == Qt.Checked:
            try:
                self.checked[pid] = float(le.text().replace(",", ".") or 1)
            except ValueError:
                self.checked[pid] = 1.0
            self._update_price_display(pid)
            self._update_form_fields(pid)
        else:
            self.checked.pop(pid, None)
            if not self.checked:
                self.ar_label.setText("-")
                self.valuta_label.setText("-")
                self._clear_form_fields()

    def _load_meta(self, o: Order):
        self.le_vevo_nev.setText(o.vevo_nev)
        self.le_vevo_cim.setPlainText(o.vevo_cim)
        self.le_vevo_adoszam.setText(o.vevo_adoszam)
        self.le_szallitasi_nev.setText(o.szallitasi_nev)
        self.le_szallitasi_cim.setPlainText(o.szallitasi_cim)
        self.de_be.setDate(QDate.fromString(o.beerkezes, "yyyy-MM-dd"))
        self.de_sz.setDate(QDate.fromString(o.szall_hatarido, "yyyy-MM-dd"))
        self.le_nr.setText(o.megrendeles_szam)
        self.te_mj.setPlainText(o.megjegyzes)

    def _accept(self):
        if not self.checked:
            QMessageBox.warning(self, "Hiány", "Nincs kijelölt termék!")
            return
        if not self.le_nr.text().strip():
            QMessageBox.warning(self, "Hiány", "Megrendelési szám kötelező!")
            return
        for pid, q in self.checked.items():
            if q <= 0:
                QMessageBox.warning(self, "Hiba", f"Hibás mennyiség (ID={pid})")
                return

        self.base_be = self.de_be.date().toString("yyyy-MM-dd")
        self.base_sz = self.de_sz.date().toString("yyyy-MM-dd")
        self.base_nr = self.le_nr.text().strip()
        self.base_mj = self.te_mj.toPlainText().strip()

        self.base_vevo_nev = self.le_vevo_nev.text().strip()
        self.base_vevo_cim = self.le_vevo_cim.toPlainText().strip()
        self.base_vevo_adoszam = self.le_vevo_adoszam.text().strip()
        self.base_szallitasi_nev = self.le_szallitasi_nev.text().strip()
        self.base_szallitasi_cim = self.le_szallitasi_cim.toPlainText().strip()

        self.accept()

def main():
    app = QApplication(sys.argv)
    win = OrderWin()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()






















