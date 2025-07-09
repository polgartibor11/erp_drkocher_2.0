# gui/db_viewer.py

import sys, os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableView, QFileDialog, QMessageBox
)
from PyQt5.QtSql import QSqlDatabase, QSqlTableModel

class DatabaseViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SQLite DB Viewer / Editor")
        self.resize(800, 600)

        # UI elemek
        self.db_label = QLabel("No database loaded")
        self.open_btn = QPushButton("Open .db file…")
        self.table_combo = QComboBox()
        self.reload_tables_btn = QPushButton("Reload Tables")
        self.view = QTableView()
        self.delete_btn = QPushButton("Delete Selected Row(s)")
        self.submit_btn = QPushButton("Submit Changes")
        self.revert_btn = QPushButton("Revert Changes")

        # Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.db_label)
        top_layout.addStretch()
        top_layout.addWidget(self.open_btn)

        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("Table:"))
        table_layout.addWidget(self.table_combo)
        table_layout.addWidget(self.reload_tables_btn)
        table_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.submit_btn)
        btn_layout.addWidget(self.revert_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(top_layout)
        main_layout.addLayout(table_layout)
        main_layout.addWidget(self.view)
        main_layout.addLayout(btn_layout)

        # gombok inaktív állapotban induláskor
        self.table_combo.setEnabled(False)
        self.reload_tables_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.submit_btn.setEnabled(False)
        self.revert_btn.setEnabled(False)

        # kapcsolatok
        self.open_btn.clicked.connect(self.open_database)
        self.reload_tables_btn.clicked.connect(self.load_table_list)
        self.table_combo.currentTextChanged.connect(self.change_table)
        self.delete_btn.clicked.connect(self.delete_rows)
        # submit/revert gombok kötése a change_table-ben történik

    def open_database(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open SQLite Database", "", "SQLite Database (*.db *.sqlite)"
        )
        if not path:
            return
        # ha korábbi kapcsolat van, zárjuk
        if QSqlDatabase.contains("sqlite_connection"):
            QSqlDatabase.removeDatabase("sqlite_connection")

        self.db = QSqlDatabase.addDatabase("QSQLITE", "sqlite_connection")
        self.db.setDatabaseName(path)
        if not self.db.open():
            QMessageBox.critical(
                self, "Error",
                f"Could not open {path}:\n{self.db.lastError().text()}"
            )
            return

        self.db_label.setText(os.path.basename(path))
        self.table_combo.setEnabled(True)
        self.reload_tables_btn.setEnabled(True)
        self.load_table_list()

    def load_table_list(self):
        tables = self.db.tables()
        self.table_combo.clear()
        self.table_combo.addItems(tables)

    def change_table(self, table_name: str):
        if not table_name:
            return

        # új model példány
        self.model = QSqlTableModel(self, self.db)
        self.model.setTable(table_name)
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        self.view.setModel(self.model)
        self.view.resizeColumnsToContents()

        # Engedélyezzük a gombokat
        self.delete_btn.setEnabled(True)
        self.submit_btn.setEnabled(True)
        self.revert_btn.setEnabled(True)

        # Bind-eljük a submit/revert gombokat
        # Először töröljük az esetleges korábbi kötéseket
        try:
            self.submit_btn.clicked.disconnect()
        except TypeError:
            pass
        try:
            self.revert_btn.clicked.disconnect()
        except TypeError:
            pass

        self.submit_btn.clicked.connect(self.model.submitAll)
        self.revert_btn.clicked.connect(self.model.revertAll)

    def delete_rows(self):
        selection = self.view.selectionModel().selectedRows()
        if not selection:
            return
        # Fordított sorrendben törlünk, hogy a sorindexek ne csússzanak el
        for index in sorted(selection, key=lambda x: x.row(), reverse=True):
            self.model.removeRow(index.row())
        # A tényleges törlést a felhasználó a "Submit Changes" gombbal erősítheti meg


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DatabaseViewer()
    win.show()
    sys.exit(app.exec_())


