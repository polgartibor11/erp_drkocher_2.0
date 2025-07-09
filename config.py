import os

BASE_DIR = os.path.dirname(__file__)

DB_PATHS = {
    'product': os.getenv('PRODUCT_DB', os.path.join(BASE_DIR, 'products.db')),
    'order':   os.getenv('ORDER_DB',   os.path.join(BASE_DIR, 'orders.db')),
    'delivery': os.getenv('DELIVERY_DB', os.path.join(BASE_DIR, 'delivery_notes.db')),
    'manufacturing': os.getenv('MANU_DB', os.path.join(BASE_DIR, 'production_inventory.db'))
}

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

