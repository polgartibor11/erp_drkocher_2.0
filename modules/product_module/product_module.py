from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional
import sqlite3
import os

# Az abszolút útvonal használata az adatbázis eléréséhez:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "products.db")

@dataclass
class ArSor:
    ar: float
    valuta: str
    kezdet: str
    veg: Optional[str]

@dataclass
class Termek:
    id: int
    vevo_nev: str
    megnevezes: str
    cikkszam: str
    mennyisegi_egyseg: str
    felulet: str
    alapanyagok: List[str]
    suly: float
    suly_mertekegyseg: str
    uzem_lanc: List[str]
    feszekszam: int
    csokosuly: float
    csokosuly_mertekegyseg: str
    foto: str

    # Új vevői és szállítási mezők
    customer_name: Optional[str] = ""
    customer_address: Optional[str] = ""
    customer_tax_number: Optional[str] = ""
    customer_eu_tax_number: Optional[str] = ""
    customer_country: Optional[str] = ""
    shipping_name: Optional[str] = ""
    shipping_address: Optional[str] = ""
    shipping_country: Optional[str] = ""

    arak: List[ArSor] = field(default_factory=list)

def _list_to_str(lst: List[str]) -> str:
    return ",".join(lst)

def _str_to_list(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def osszes_termek() -> List[Termek]:
    if not os.path.exists(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""SELECT id, vevo_nev, megnevezes, cikkszam, mennyisegi_egyseg, felulet,
                     alapanyagok, suly, suly_mertekegyseg, uzem_lanc, feszekszam,
                     csokosuly, csokosuly_mertekegyseg, foto,
                     customer_name, customer_address, customer_tax_number, customer_eu_tax_number, customer_country,
                     shipping_name, shipping_address, shipping_country
                     FROM products""")
        products_rows = c.fetchall()

        termekek = []
        for row in products_rows:
            (id_, vevo_nev, megnevezes, cikkszam, mennyisegi_egyseg, felulet,
             alapanyagok, suly, suly_mertekegyseg, uzem_lanc, feszekszam,
             csokosuly, csokosuly_mertekegyseg, foto,
             customer_name, customer_address, customer_tax_number, customer_eu_tax_number, customer_country,
             shipping_name, shipping_address, shipping_country) = row

            c.execute("SELECT ar, valuta, kezdet, veg FROM arak WHERE product_id = ? ORDER BY kezdet", (id_,))
            arak_rows = c.fetchall()
            arak = [ArSor(ar=ar, valuta=valuta, kezdet=kezdet, veg=veg) for ar, valuta, kezdet, veg in arak_rows]

            termekek.append(
                Termek(
                    id=id_,
                    vevo_nev=vevo_nev,
                    megnevezes=megnevezes,
                    cikkszam=cikkszam,
                    mennyisegi_egyseg=mennyisegi_egyseg,
                    felulet=felulet,
                    alapanyagok=_str_to_list(alapanyagok),
                    suly=suly,
                    suly_mertekegyseg=suly_mertekegyseg,
                    uzem_lanc=_str_to_list(uzem_lanc),
                    feszekszam=feszekszam,
                    csokosuly=csokosuly,
                    csokosuly_mertekegyseg=csokosuly_mertekegyseg,
                    foto=foto,
                    customer_name=customer_name or "",
                    customer_address=customer_address or "",
                    customer_tax_number=customer_tax_number or "",
                    customer_eu_tax_number=customer_eu_tax_number or "",
                    customer_country=customer_country or "",
                    shipping_name=shipping_name or "",
                    shipping_address=shipping_address or "",
                    shipping_country=shipping_country or "",
                    arak=arak
                )
            )
        return termekek

def hozzaad_termek(t: Termek) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products WHERE id = ?", (t.id,))
        if c.fetchone()[0] > 0:
            raise ValueError(f"Duplikált ID: {t.id}")

        c.execute("""
            INSERT INTO products (
                id, vevo_nev, megnevezes, cikkszam, mennyisegi_egyseg, felulet,
                alapanyagok, suly, suly_mertekegyseg, uzem_lanc, feszekszam,
                csokosuly, csokosuly_mertekegyseg, foto,
                customer_name, customer_address, customer_tax_number, customer_eu_tax_number, customer_country,
                shipping_name, shipping_address, shipping_country
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t.id,
            t.vevo_nev,
            t.megnevezes,
            t.cikkszam,
            t.mennyisegi_egyseg,
            t.felulet,
            _list_to_str(t.alapanyagok),
            t.suly,
            t.suly_mertekegyseg,
            _list_to_str(t.uzem_lanc),
            t.feszekszam,
            t.csokosuly,
            t.csokosuly_mertekegyseg,
            t.foto,
            t.customer_name,
            t.customer_address,
            t.customer_tax_number,
            t.customer_eu_tax_number,
            t.customer_country,
            t.shipping_name,
            t.shipping_address,
            t.shipping_country
        ))

        for ar in t.arak:
            c.execute("""
                INSERT INTO arak (product_id, ar, valuta, kezdet, veg) VALUES (?, ?, ?, ?, ?)
            """, (t.id, ar.ar, ar.valuta, ar.kezdet, ar.veg))
        conn.commit()

def frissit_termek(t: Termek) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products WHERE id = ?", (t.id,))
        if c.fetchone()[0] == 0:
            raise ValueError(f"Nincs ilyen ID: {t.id}")

        c.execute("""
            UPDATE products SET
            vevo_nev = ?, megnevezes = ?, cikkszam = ?, mennyisegi_egyseg = ?, felulet = ?,
            alapanyagok = ?, suly = ?, suly_mertekegyseg = ?, uzem_lanc = ?, feszekszam = ?,
            csokosuly = ?, csokosuly_mertekegyseg = ?, foto = ?,
            customer_name = ?, customer_address = ?, customer_tax_number = ?, customer_eu_tax_number = ?, customer_country = ?,
            shipping_name = ?, shipping_address = ?, shipping_country = ?
            WHERE id = ?
        """, (
            t.vevo_nev,
            t.megnevezes,
            t.cikkszam,
            t.mennyisegi_egyseg,
            t.felulet,
            _list_to_str(t.alapanyagok),
            t.suly,
            t.suly_mertekegyseg,
            _list_to_str(t.uzem_lanc),
            t.feszekszam,
            t.csokosuly,
            t.csokosuly_mertekegyseg,
            t.foto,
            t.customer_name,
            t.customer_address,
            t.customer_tax_number,
            t.customer_eu_tax_number,
            t.customer_country,
            t.shipping_name,
            t.shipping_address,
            t.shipping_country,
            t.id
        ))
        c.execute("DELETE FROM arak WHERE product_id = ?", (t.id,))
        for ar in t.arak:
            c.execute("""
                INSERT INTO arak (product_id, ar, valuta, kezdet, veg) VALUES (?, ?, ?, ?, ?)
            """, (t.id, ar.ar, ar.valuta, ar.kezdet, ar.veg))
        conn.commit()

def torol_termek(tid: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM arak WHERE product_id = ?", (tid,))
        c.execute("DELETE FROM products WHERE id = ?", (tid,))
        conn.commit()

def aktualis_ar(t: Termek, nap: Optional[date] = None) -> Optional[tuple[float, str]]:
    nap = nap or date.today()
    for s in sorted(t.arak, key=lambda x: x.kezdet, reverse=True):
        d0 = datetime.fromisoformat(s.kezdet).date()
        d1 = datetime.max.date() if s.veg is None else datetime.fromisoformat(s.veg).date()
        if d0 <= nap <= d1:
            return s.ar, s.valuta
    return None

def uj_ar(t: Termek, uj_ar: float, valuta: str, mettol: date) -> None:
    for s in t.arak:
        d0 = datetime.fromisoformat(s.kezdet).date()
        d1 = datetime.max.date() if s.veg is None else datetime.fromisoformat(s.veg).date()
        if d0 <= mettol <= d1:
            s.veg = (mettol - timedelta(days=1)).isoformat()
            break
    t.arak.append(ArSor(ar=uj_ar, valuta=valuta, kezdet=mettol.isoformat(), veg=None))
    t.arak.sort(key=lambda x: x.kezdet)
    frissit_termek(t)










