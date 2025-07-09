#!/usr/bin/env python3

import sys
import os
import sqlite3
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QComboBox, QLineEdit,
    QSpacerItem, QSizePolicy,
    QFileDialog, QMessageBox
)

# Projekt gyökér hozzáadása a path-hoz
this_dir = os.path.dirname(__file__)
project_dir = os.path.abspath(os.path.join(this_dir, os.pardir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from modules.manufacturing_module.inventory_db import InventoryDB

class FoundryProductsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dr. Köcher Kft. – Öntöde Üzem | Műszakgyártások")
        self.resize(1200, 650)

        # PDF sablonok mappája
        self.template_dir = os.path.join(project_dir, "templates")

        # Adatbázis & downtime-ok
        self.inv_db = InventoryDB()
        self.prod_db = os.path.join(
            project_dir, "modules", "product_module", "products.db"
        )
        cur = self.inv_db.conn.cursor()
        cur.execute("SELECT DISTINCT cause FROM shift_downtimes")
        self.downtime_causes = [row["cause"] for row in cur.fetchall()]

        # --- GUI felépítés ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Fejléc (logó + cím)
        header_layout = QHBoxLayout()
        logo_path = os.path.join(project_dir, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaledToHeight(50, Qt.SmoothTransformation)
            logo_lbl = QLabel()
            logo_lbl.setPixmap(pix)
            header_layout.addWidget(logo_lbl)
        title_lbl = QLabel(
            '<span style="font-size:15pt;font-weight:bold;">'
            'Dr. Köcher Kft. – Öntöde Üzem</span>'
        )
        title_lbl.setFont(QFont("Arial", 13, QFont.Bold))
        header_layout.addWidget(title_lbl, alignment=Qt.AlignVCenter)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Alfejléc
        subheader = QLabel("Műszakgyártások áttekintése")
        subheader.setFont(QFont("Arial", 12, QFont.Bold))
        subheader.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subheader)

        # Szűrők
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Operátor:"))
        self.op_cb = QComboBox()
        self.op_cb.addItem("Összes", "")
        for op in self.inv_db.list_operators():
            self.op_cb.addItem(op, op)
        self.op_cb.currentIndexChanged.connect(self.load_shift_logs)
        filter_layout.addWidget(self.op_cb)

        filter_layout.addWidget(QLabel("Gép:"))
        self.machine_cb = QComboBox()
        self.machine_cb.addItem("Összes", "")
        machines = [r["machine"] for r in self.inv_db.conn.execute(
            "SELECT DISTINCT machine FROM shift_logs"
        )]
        for m in machines:
            if m and self.machine_cb.findData(m) < 0:
                self.machine_cb.addItem(m, m)
        self.machine_cb.currentIndexChanged.connect(self.load_shift_logs)
        filter_layout.addWidget(self.machine_cb)

        filter_layout.addWidget(QLabel("Termék:"))
        self.prod_le = QLineEdit()
        self.prod_le.setPlaceholderText("keresés…")
        self.prod_le.textChanged.connect(self.load_shift_logs)
        filter_layout.addWidget(self.prod_le)

        filter_layout.addWidget(QLabel("Cikkszám:"))
        self.sku_le = QLineEdit()
        self.sku_le.setPlaceholderText("keresés…")
        self.sku_le.textChanged.connect(self.load_shift_logs)
        filter_layout.addWidget(self.sku_le)

        filter_layout.addWidget(QLabel("Dátum:"))
        self.date_le = QLineEdit()
        self.date_le.setPlaceholderText("YYYY-MM-DD")
        self.date_le.textChanged.connect(self.load_shift_logs)
        filter_layout.addWidget(self.date_le)

        filter_layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        main_layout.addLayout(filter_layout)

        # Akciógombok
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        for txt, slot in [
            ("Frissítés", self.load_shift_logs),
            ("Mentés", self.save_changes),
            ("PDF generálás…", self.generate_pdf),
        ]:
            b = QPushButton(txt)
            b.clicked.connect(slot)
            btn_layout.addWidget(b)
        main_layout.addLayout(btn_layout)

        # Táblázat
        cols = 12 + 1 + len(self.downtime_causes)
        self.tbl = QTableWidget(0, cols)
        headers = [
            "Dátum", "Operátor", "Gép", "Termék", "Cikkszám",
            "Műszak", "Öntött lövés", "Előírt norma", "Teljesítmény (%)",
            "Jó darabszám", "Selejt lövés", "Selejt (%)"
        ] + ["Aktív munkaidő"] + self.downtime_causes
        self.tbl.setHorizontalHeaderLabels(headers)
        for i in range(cols):
            self.tbl.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.Interactive
            )
        self.tbl.setAlternatingRowColors(True)
        main_layout.addWidget(self.tbl)

        # Fejlesztő infó
        dev_lbl = QLabel("Fejlesztő: Polgár Tibor")
        dev_lbl.setFont(QFont("", 8, QFont.StyleItalic))
        main_layout.addWidget(dev_lbl, alignment=Qt.AlignLeft)

        # Első betöltés
        self.load_shift_logs()

    def load_shift_logs(self):
        self.tbl.setRowCount(0)
        logs = self.inv_db.list_shift_logs()
        op_f = self.op_cb.currentData()
        mch_f = self.machine_cb.currentData()
        pd_f = self.prod_le.text().lower()
        sku_f = self.sku_le.text().lower()
        dt_f = self.date_le.text()

        for log in logs:
            if op_f and log["operator"] != op_f:
                continue
            if mch_f and log["machine"] != mch_f:
                continue
            if dt_f and not log["date"].startswith(dt_f):
                continue

            # Termékadatok lekérdezése
            pid = self.inv_db.get_active_job_product(log["machine"])
            name, sku, unit, cav = "—", "—", "", 1
            if pid:
                con = sqlite3.connect(self.prod_db)
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                cur.execute(
                    "SELECT megnevezes,cikkszam,mennyisegi_egyseg,feszekszam "
                    "FROM products WHERE id=?", (pid,)
                )
                prow = cur.fetchone()
                con.close()
                if prow:
                    name = prow["megnevezes"]
                    sku = prow["cikkszam"]
                    unit = prow["mennyisegi_egyseg"] or ""
                    cav = int(prow["feszekszam"] or 1)

            if pd_f and pd_f not in name.lower():
                continue
            if sku_f and sku_f not in sku.lower():
                continue

            shots = log["shots"]
            scrap_sh = log["scrap_shots"]
            total_q = shots * cav
            good_q = (shots - scrap_sh) * cav
            scrap_q = scrap_sh * cav
            scrap_pct = (scrap_q / total_q * 100) if total_q > 0 else 0

            norma = self.inv_db.get_norm(pid) or 0
            shift_h = 8.0
            cur = self.inv_db.conn.cursor()
            cur.execute(
                "SELECT cause,hours FROM shift_downtimes "
                "WHERE machine=? AND date=? AND shift_type=?",
                (log["machine"], log["date"], log["shift_type"])
            )
            dt_list = {r["cause"]: r["hours"] for r in cur.fetchall()}
            sum_dt = sum(dt_list.values())
            eff_h = max(0.0, shift_h - sum_dt)

            adj_norm = norma * (eff_h / shift_h) if shift_h > 0 else norma
            perf_pct = ((shots * cav) / adj_norm) if adj_norm > 0 else 0
            scrap_frac = scrap_pct / 100.0

            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            row_vals = [
                log["date"], log["operator"], log["machine"],
                name, sku, log["shift_type"], shots,
                norma, perf_pct, f"{good_q} {unit}",
                scrap_sh, scrap_frac, f"{eff_h:.2f} h"
            ] + [dt_list.get(c, 0.0) for c in self.downtime_causes]

            for c, v in enumerate(row_vals):
                it = QTableWidgetItem()
                if c in (8, 11):
                    it.setData(Qt.EditRole, v)
                else:
                    it.setText(str(v))
                    if c not in (6, 10):
                        it.setFlags(it.flags() & ~Qt.ItemIsEditable)

                # Színezés GUI‐ban
                if c == 8:
                    color = 'lightgreen' if v >= 0.80 else 'yellow' if v >= 0.60 else 'red'
                    it.setBackground(QColor(color))
                    it.setText(f"{v:.1%}")
                if c == 11:
                    color = 'lightgreen' if v <= 0.07 else 'yellow' if v <= 0.10 else 'red'
                    it.setBackground(QColor(color))
                    it.setText(f"{v:.1%}")

                self.tbl.setItem(r, c, it)

            self.tbl.item(r, 0).setData(Qt.UserRole, log["id"])

        self.tbl.resizeColumnsToContents()

    def save_changes(self):
        ans = QMessageBox.question(
            self, "Megerősítés",
            "Biztosan mented a módosításokat?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        cur = self.inv_db.conn.cursor()
        for r in range(self.tbl.rowCount()):
            rec = self.tbl.item(r, 0).data(Qt.UserRole)
            shots = int(self.tbl.item(r, 6).text())
            scraps = int(self.tbl.item(r, 10).text())
            cur.execute(
                "UPDATE shift_logs SET shots=?, scrap_shots=? WHERE id=?",
                (shots, scraps, rec)
            )
        self.inv_db.conn.commit()
        QMessageBox.information(self, "Mentés", "Módosítások sikeresen mentve.")
        self.load_shift_logs()

    def generate_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF mentése…", "", "PDF fájl (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        # Fejléc és sorok kigyűjtése, numerikus százalékok parse-olása
        headers = [
            self.tbl.horizontalHeaderItem(c).text()
            for c in range(self.tbl.columnCount())
        ]
        rows = []
        for r in range(self.tbl.rowCount()):
            d = {}
            for c, h in enumerate(headers):
                item = self.tbl.item(r, c)
                if h in ("Teljesítmény (%)", "Selejt (%)"):
                    txt = item.text().strip().strip('%')
                    try:
                        val = float(txt) / 100.0
                    except:
                        val = 0.0
                    d[h] = val
                else:
                    d[h] = item.text()
            rows.append(d)

        html = self._render_html(rows, headers)

        try:
            HTML(string=html, base_url=project_dir).write_pdf(path)
            QMessageBox.information(self, "Kész", f"PDF elkészült:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"PDF generálás sikertelen:\n{e}")

    def _render_html(self, rows, headers):
        env = Environment(loader=FileSystemLoader(self.template_dir))
        tmpl = env.get_template("base.html")

        thead = "".join(f"<th>{h}</th>" for h in headers)
        tbody = ""
        for row in rows:
            cells = ""
            for h in headers:
                if h == "Teljesítmény (%)":
                    v = row[h]
                    col = 'lightgreen' if v >= 0.80 else 'yellow' if v >= 0.60 else 'red'
                    cells += f'<td style="background-color:{col}">{v:.1%}</td>'
                elif h == "Selejt (%)":
                    v = row[h]
                    col = 'lightgreen' if v <= 0.07 else 'yellow' if v <= 0.10 else 'red'
                    cells += f'<td style="background-color:{col}">{v:.1%}</td>'
                else:
                    cells += f"<td>{row[h]}</td>"
            tbody += f"<tr>{cells}</tr>"

        table_html = f"""
        <table>
          <thead><tr>{thead}</tr></thead>
          <tbody>{tbody}</tbody>
        </table>
        """

        return tmpl.render(
            logo_path=os.path.join(project_dir, "logo.png"),
            company_name="Dr. Köcher Kft. – Öntöde Üzem",
            report_title="Műszakgyártások áttekintése",
            content_table=table_html
        )

def main():
    app = QApplication(sys.argv)
    w = FoundryProductsWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
