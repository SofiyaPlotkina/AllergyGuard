"""
Bereinigt die USDA-importierten Zeilen in allergen_synonyms:

1. Fragmente/Artefakte (enthalten {, } oder + - abgeschnittene Ingredienzien-
   Unterlisten wie "Bio-Weizenmehl {Thiamin").
2. Falsch zugeordnete oder zu generische Einträge, die bei einer Rezeptpruefung
   getestet und manuell durchgesehen wurden (siehe Konversation).

Betrifft ausschließlich category='USDA' Zeilen (der frische CSV-Import),
bestehende Alt-Daten (category IS NULL / andere Kategorien) bleiben unberührt.

Erst mit --dry-run pruefen, dann ohne Flag wirklich loeschen.
"""

import sqlite3
import sys

DB_PFAD = "../allergen.db"

# (allergen, synonym) Paare: zu generisch, um verlaesslich zu sein, oder
# schlicht falsch zugeordnet (z.B. Mandeln sind eine Schalenfrucht, kein
# Erdnuss-Synonym; Sahne ist ein Milchprodukt, kein Soja-Synonym)
FALSCH_ODER_ZU_GENERISCH = [
    ("ei", "brownie"), ("ei", "nudeln"), ("ei", "ravioli"),
    ("erdnuss", "aromen"), ("erdnuss", "mandeln"), ("erdnuss", "obst"), ("erdnuss", "pepitas"),
    ("gluten", "bagel"), ("gluten", "brezeln"), ("gluten", "brownie"), ("gluten", "enzyme"),
    ("gluten", "gekocht"), ("gluten", "kekse"), ("gluten", "müsli"), ("gluten", "waffeln"),
    ("milch", "annatto"), ("milch", "aromen"), ("milch", "brownie"), ("milch", "creme"),
    ("milch", "gekocht"), ("milch", "kakao"), ("milch", "keks"), ("milch", "kekse"),
    ("milch", "müsli"), ("milch", "ravioli"), ("milch", "rührei"),
    ("senf", "gewürz"), ("senf", "wasabi"),
    ("soja", "aromen"), ("soja", "bagel"), ("soja", "bonbons"), ("soja", "brezeln"),
    ("soja", "brot"), ("soja", "brownie"), ("soja", "cracker"), ("soja", "farbe"),
    ("soja", "gewürz"), ("soja", "huhn"), ("soja", "keks"), ("soja", "kekse"),
    ("soja", "koka"), ("soja", "müsli"), ("soja", "pepitas"), ("soja", "sahne"),
    ("soja", "senf"),
    ("sulfite", "ananas"), ("sulfite", "papaya"),
]


def main():
    dry_run = "--dry-run" in sys.argv
    conn = sqlite3.connect(DB_PFAD)

    artefakte = conn.execute(
        """SELECT allergen, synonym FROM allergen_synonyms
           WHERE category='USDA' AND (synonym LIKE '%{%' OR synonym LIKE '%}%' OR synonym LIKE '%+%')"""
    ).fetchall()

    print(f"[INFO] {len(artefakte)} Fragmente/Artefakte gefunden")
    print(f"[INFO] {len(FALSCH_ODER_ZU_GENERISCH)} falsch zugeordnete/zu generische Einträge in der Liste")

    if dry_run:
        print("[DRY RUN] Es wird nichts gelöscht.")
        conn.close()
        return

    geloescht = 0
    for allergen, synonym in artefakte:
        conn.execute(
            "DELETE FROM allergen_synonyms WHERE category='USDA' AND allergen=? AND synonym=?",
            (allergen, synonym),
        )
        geloescht += 1

    for allergen, synonym in FALSCH_ODER_ZU_GENERISCH:
        cur = conn.execute(
            "DELETE FROM allergen_synonyms WHERE category='USDA' AND allergen=? AND synonym=?",
            (allergen, synonym),
        )
        geloescht += cur.rowcount

    conn.commit()
    rest = conn.execute("SELECT COUNT(*) FROM allergen_synonyms").fetchone()[0]
    print(f"[OK] {geloescht} Zeilen gelöscht")
    print(f"[OK] Tabelle hat jetzt {rest} Zeilen")
    conn.close()


if __name__ == "__main__":
    main()
