import sys
import os
# Add project root to Python path so we can import main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main


def test_main_imports():
    # Ensure the main module defines a main() function
    assert hasattr(main, "main"), "main.py should define a main() function"
