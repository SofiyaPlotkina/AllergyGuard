"""One-time seed script: bekannte Marken-Barcodes in die lokale off_products-Tabelle laden.

Nutzt echte, verifizierte OpenFoodFacts-Barcodes, damit die Tier-1-Texterkennung
(off_produkt_im_text_finden) von Anfang an ein paar bekannte Produkte findet,
statt erst durch Nutzung langsam zu wachsen.

Run once: python seed_off_products.py
"""

from openfoodfacts_client import suche_off, off_produkt_cachen

# barcode -> Kommentar, worum es sich handelt (nur zur Doku, nicht Teil des Imports)
SEED_BARCODES = {
    "3017620422003": "Nutella 450g",
    "4012367012608": "Weizenmehl Type 405",
    "40111308": "Snickers",
    "4061458018159": "Zöpfli Frischei-Nudeln (CH)",
}


def seed():
    print("[SEED] Lade bekannte Produkte von OpenFoodFacts...")
    geladen = 0
    for barcode, beschreibung in SEED_BARCODES.items():
        produkt = suche_off(barcode)
        if produkt:
            off_produkt_cachen(produkt, quelle="seed")
            print(f"   • {produkt.get('product_name')} ({barcode}) - {beschreibung}")
            geladen += 1
        else:
            print(f"   ! Nicht gefunden: {barcode} ({beschreibung})")
    print(f"[OK] {geladen}/{len(SEED_BARCODES)} Produkte in off_products geladen")


if __name__ == "__main__":
    seed()
