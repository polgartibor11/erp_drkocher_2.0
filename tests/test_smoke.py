# tests/test_smoke.py
import main

def test_main_imports():
    # ellenőrizzük, hogy a main modulban van-e main() függvény
    assert hasattr(main, "main")
