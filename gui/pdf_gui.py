# gui/pdf_gui.py

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox
)
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


class PDFGui(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Jelentés Generátor")
        self.data_rows = []
        self.output_path = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Adatok betöltése gomb
        self.btn_load = QPushButton("Adatok betöltése", self)
        self.btn_load.clicked.connect(self._load_data)
        layout.addWidget(self.btn_load)

        # Kimeneti fájl kiválasztása
        self.btn_select_output = QPushButton("Kimeneti PDF fájl kiválasztása", self)
        self.btn_select_output.clicked.connect(self._select_output_file)
        layout.addWidget(self.btn_select_output)

        self.lbl_output = QLabel("Kimeneti fájl: nincs kiválasztva", self)
        layout.addWidget(self.lbl_output)

        # PDF generálása gomb
        self.btn_generate = QPushButton("PDF generálása", self)
        self.btn_generate.setEnabled(False)
        self.btn_generate.clicked.connect(self._generate_pdf)
        layout.addWidget(self.btn_generate)

    def _load_data(self):
        opts = QFileDialog.Options()
        path, _ = QFileDialog.getOpenFileName(
            self, "Adatok fájl kiválasztása",
            "", "JSON fájl (*.json);;CSV fájl (*.csv);;Minden fájl (*)",
            options=opts
        )
        if not path:
            return

        try:
            self.data_rows = self._read_data(path)
            QMessageBox.information(self, "Siker", "Adatok betöltve.")
            if self.output_path:
                self.btn_generate.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Adatok beolvasása sikertelen:\n{e}")

    def _read_data(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif ext == ".csv":
            import csv
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)
        else:
            raise ValueError(f"Támogatott formátum: .json vagy .csv (te: {ext})")

    def _select_output_file(self):
        opts = QFileDialog.Options()
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF mentése ide", "", "PDF fájl (*.pdf)",
            options=opts
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self.output_path = path
        self.lbl_output.setText(f"Kimeneti fájl: {os.path.basename(path)}")
        if self.data_rows:
            self.btn_generate.setEnabled(True)

    def _generate_pdf(self):
        if not self.data_rows or not self.output_path:
            QMessageBox.warning(self, "Figyelem", "Előbb töltsd be az adatokat és válaszd ki a kimeneti fájlt.")
            return

        try:
            html = self._render_html(self.data_rows)
            HTML(string=html).write_pdf(self.output_path)
            QMessageBox.information(self, "Kész", f"PDF elkészült:\n{self.output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"PDF generálás sikertelen:\n{e}")

    def _render_html(self, rows):
        # Betöltjük a sablont
        env = Environment(loader=FileSystemLoader("templates"))
        tmpl = env.get_template("base.html")

        # Táblázat HTML generálása
        headers = rows[0].keys() if rows else []
        thead = "".join(f"<th>{h}</th>" for h in headers)
        tbody = ""
        for row in rows:
            cells = "".join(f"<td>{row.get(h, '')}</td>" for h in headers)
            tbody += f"<tr>{cells}</tr>"

        table_html = f"""
        <table>
          <thead><tr>{thead}</tr></thead>
          <tbody>{tbody}</tbody>
        </table>
        """

        return tmpl.render(
            logo_path="static/logo.png",
            report_title="Automatikus Jelentés",
            content_table=table_html
        )


# Példa integráció a main.py-ben:
# from gui.pdf_gui import PDFGui
# pdf_win = PDFGui()
# pdf_win.show()
# ...
