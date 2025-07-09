from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton
)
from PyQt5.QtCore import Qt

class DeliveryNotePreviewDialog(QDialog):
    def __init__(self, order_id, customer_info, shipping_info,  
                 items, header_map, static_labels, parent=None):
        """
        static_labels: dict, pl.
          {
            "title": "...",
            "order": "...",
            "shipper_company": "...",
            "shipper_address": "...",
            "tax_number": "...",
            "eu_tax_number": "...",
            "shipping_address_label": "...",
            "country": "...",
            "buyer_label": "...",
            "cancel": "...",
            "generate": "..."
          }
        """
        super().__init__(parent)

        # Országfordítás a preview ablakban is, csak ha a 'country' magyarul van beírva
        def translate_country(country, lang):
            if lang == "de":
                if country.lower() in ["magyarország", "hungary"]:
                    return "Ungarn"
            return country

        # A bejövő static_labels alapján
        lang = "de" if static_labels.get("country", "") == "Land" else "hu"
        shipping_info["country"] = translate_country(shipping_info.get("country", ""), lang)
        customer_info["country"] = translate_country(customer_info.get("country", ""), lang)

        # állandó cégadatok
        SHIPPER_NAME = "Dr. Köcher Kft."
        SHIPPER_COUNTRY = "Ungarn" if lang == "de" else "Magyarország"
        SHIPPER_ADDRESS = f"2300 Ráckeve, Vásártér utca 15. {SHIPPER_COUNTRY}"
        SHIPPER_TAX = "10970722-2-13"
        SHIPPER_EU_TAX = "HU10970722"

        # ablakcím
        title = static_labels["title"]
        if order_id is not None:
            title += f" – {static_labels['order']} #{order_id}"
        self.setWindowTitle(title)
        self.resize(800, 600)

        main = QVBoxLayout(self)

        # --- Szállító cég adatai ---
        lbl_shipper = QLabel()
        lbl_shipper.setTextFormat(Qt.RichText)
        lbl_shipper.setText(
            f"<b>{static_labels['shipper_company']}:</b><br>"
            f"{SHIPPER_NAME}<br>"
            f"{SHIPPER_ADDRESS}<br>"
            f"{static_labels['tax_number']}: {SHIPPER_TAX}<br>"
            f"{static_labels['eu_tax_number']}: {SHIPPER_EU_TAX}"
        )
        main.addWidget(lbl_shipper)

        # --- Szállítási cím ---
        lbl_ship = QLabel()
        lbl_ship.setTextFormat(Qt.RichText)
        lbl_ship.setText(
            f"<b>{static_labels['shipping_address_label']}:</b><br>"
            f"{shipping_info['name']}<br>"
            f"{shipping_info['address']}<br>"
            f"{static_labels['country']}: {shipping_info.get('country','')}"
        )
        main.addWidget(lbl_ship)

        # --- Vevő adatai ---
        lbl_buyer = QLabel()
        lbl_buyer.setTextFormat(Qt.RichText)
        lbl_buyer.setText(
            f"<b>{static_labels['buyer_label']}:</b><br>"
            f"{customer_info['name']}<br>"
            f"{customer_info['address']}<br>"
            f"{static_labels['tax_number']}: {customer_info['tax_number']}<br>"
            f"{static_labels['eu_tax_number']}: {customer_info.get('eu_tax_number','')}<br>"
            f"{static_labels['country']}: {customer_info.get('country','')}"
        )
        main.addWidget(lbl_buyer)

        # --- Tétel-tábla ---
        tbl = QTableWidget(len(items), 7, self)
        tbl.setHorizontalHeaderLabels([
            header_map["order_number"],
            header_map["vevo_nev"],
            header_map["product_name"],
            header_map["item_number"],
            header_map["ship_qty"],
            header_map["unit"],
            header_map["surface"]
        ])
        for r, it in enumerate(items):
            tbl.setItem(r, 0, QTableWidgetItem(str(it["order_number"])))
            tbl.setItem(r, 1, QTableWidgetItem(str(it["customer_name"])))
            tbl.setItem(r, 2, QTableWidgetItem(str(it["product_name"])))
            tbl.setItem(r, 3, QTableWidgetItem(str(it["item_number"])))
            tbl.setItem(r, 4, QTableWidgetItem(str(it["ship_qty"])))
            tbl.setItem(r, 5, QTableWidgetItem(str(it["unit"])))
            tbl.setItem(r, 6, QTableWidgetItem(str(it["surface"])))
        tbl.resizeColumnsToContents()
        main.addWidget(tbl)

        # --- Gombok ---
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton(static_labels["cancel"])
        btn_ok     = QPushButton(static_labels["generate"])
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        main.addLayout(btn_layout)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)





