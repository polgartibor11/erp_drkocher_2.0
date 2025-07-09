# gui/label_preview_window.py

import os
from PyQt5.QtCore        import Qt, QRectF
from PyQt5.QtGui         import QPixmap, QFont, QPainter
from PyQt5.QtWidgets     import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QWidget, QInputDialog, QSizeGrip
)
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from datetime            import date

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

class LabelPreviewDialog(QDialog):
    def __init__(self, label_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Címke előnézet (A4 - 3 db egymás alatt)")
        # Engedélyezzük a szabad átméretezést
        self.setSizeGripEnabled(True)
        # (Opcionálisan beállíthatsz minimumméretet is:)
        # self.setMinimumSize(600, 400)

        self.label_data = label_data[:3]
        self.logo_path   = os.path.join(BASE_DIR, "logo.png")
        self.current_quantities = []
        for row in self.label_data:
            try:
                self.current_quantities.append(float(row[4]))
            except:
                self.current_quantities.append(0.0)

        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(12,12,12,12)
        main_v.addWidget(QLabel("<b>Címke előnézet (egy A4-en három címke egymás alatt)</b>"))

        hl = QHBoxLayout()
        self.canvas = LabelCanvas(self.label_data,
                                  self.current_quantities,
                                  self.logo_path, self)
        hl.addWidget(self.canvas, 1)

        gb = QVBoxLayout()
        for i in range(3):
            btn = QPushButton(f"Mennyiség módosítása ({i+1}. címke)")
            btn.setFixedWidth(180)
            btn.clicked.connect(lambda _, idx=i: self.modify_quantity(idx))
            gb.addWidget(btn)
            gb.addSpacing(12)
        gb.addStretch()
        btn_print = QPushButton("Nyomtatási előnézet")
        btn_print.setFixedWidth(180)
        btn_print.clicked.connect(self.print_preview)
        gb.addWidget(btn_print)
        hl.addLayout(gb)

        main_v.addLayout(hl)

        # Size grip a jobb alsó sarokhoz
        grip = QSizeGrip(self)
        grip.setFixedSize(grip.sizeHint())
        grip_layout = QHBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(grip)
        main_v.addLayout(grip_layout)

        footer = QHBoxLayout(); footer.addStretch()
        btn_close = QPushButton("Bezárás")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        main_v.addLayout(footer)

    def modify_quantity(self, idx):
        old = self.current_quantities[idx]
        val, ok = QInputDialog.getDouble(
            self, "Mennyiség módosítása",
            f"Új mennyiség ({idx+1}. címke):",
            value=old, min=0.01, max=1e6, decimals=3
        )
        if ok:
            self.current_quantities[idx] = val
            self.label_data[idx][4] = f"{val:g}"
            self.canvas.current_quantities[idx] = val
            self.canvas.update()

    def print_preview(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        dlg = QPrintPreviewDialog(printer, self)
        dlg.setWindowTitle("Nyomtatási előnézet")
        dlg.resize(1000, 800)
        dlg.paintRequested.connect(self._render)
        dlg.exec_()

    def _render(self, printer):
        painter = QPainter(printer)
        rect = printer.pageRect()
        pix  = self.canvas.grab()
        pix  = pix.scaled(rect.width(), rect.height(),
                          Qt.IgnoreAspectRatio,
                          Qt.SmoothTransformation)
        painter.drawPixmap(0, 0, pix)
        painter.end()

class LabelCanvas(QWidget):
    def __init__(self, labels, quantities, logo_path, parent=None):
        super().__init__(parent)
        self.labels             = labels
        self.current_quantities = quantities
        self.logo_path          = logo_path
        # Opcionálisan állíthatsz minimumméretet is:
        self.setMinimumSize(800, 900)

    def paintEvent(self, e):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        W, H = self.width(), self.height()
        M    = 30
        block_h = (H - 4*M) / 3
        block_w = W - 2*M

        f_big  = QFont("Arial", 14, QFont.Bold)
        f_mid  = QFont("Arial", 12, QFont.Bold)
        f_norm = QFont("Arial", 11)
        today  = date.today().isoformat()

        for i in range(3):
            x0 = M
            y0 = M + i*(block_h+M)
            qp.setPen(Qt.black)
            qp.setBrush(Qt.white)
            qp.drawRect(QRectF(x0, y0, block_w, block_h))

            d = self.labels[i]
            if not any(d):
                continue

            # LOGO
            if os.path.exists(self.logo_path):
                pix = QPixmap(self.logo_path).scaled(70,70,
                                                    Qt.KeepAspectRatio,
                                                    Qt.SmoothTransformation)
                qp.drawPixmap(int(x0+10), int(y0+10), pix)

            # CÉGNÉV
            qp.setFont(f_big)
            qp.drawText(QRectF(x0+95, y0+20, block_w-105, 30),
                        Qt.AlignLeft, "Dr. Köcher Kft.")
            y = y0 + 20 + 30 + 30

            # Vevő és termék
            qp.setFont(f_mid)
            qp.drawText(int(x0+15), int(y),     d[1]);           y+=24
            qp.drawText(int(x0+15), int(y),     f"Termék: {d[2]}"); y+=24

            # Részletek
            qp.setFont(f_norm)
            qp.drawText(int(x0+15), int(y),     f"Cikkszám: {d[3]}");                y+=20
            qp.drawText(int(x0+15), int(y),     f"Mennyiség: {self.current_quantities[i]:g} {d[5]}"); y+=20
            qp.drawText(int(x0+15), int(y),     f"Rend. szám: {d[0]}");               y+=20
            qp.drawText(int(x0+15), int(y),     f"Beérkezés: {d[6]}");               y+=20
            qp.drawText(int(x0+15), int(y),     f"Elkészülés ideje: {today}");       y+=20
            qp.drawText(int(x0+15), int(y),     f"Címzett: {d[8]}");                 y+=20
            qp.drawText(int(x0+15), int(y),     f"Cím: {d[9]}")

        qp.end()




