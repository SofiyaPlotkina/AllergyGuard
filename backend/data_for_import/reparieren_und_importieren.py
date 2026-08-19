"""
Import von data_for_import/cleaned.csv in die allergen_synonyms Tabelle.

- Bestehende Daten werden NICHT geloescht, nur ergaenzt (INSERT OR IGNORE,
  Duplikate ueber UNIQUE(allergen, synonym) werden uebersprungen).
- 94 Zeilen in der CSV sind kaputt (unescapte Kommas im "name"-Feld haben die
  Spalten verschoben) - werden hier best-effort repariert, siehe repariere_zeile().
- Mapping: name -> synonym, language -> language, source -> category (meist "USDA"),
  created_at bekommt den echten Zeitstempel von jetzt (Tabellen-Default).

Erst mit --dry-run pruefen, dann ohne Flag wirklich importieren.
"""

import csv
import sqlite3
import sys

CSV_PFAD = "cleaned.csv"
DB_PFAD = "../allergen.db"


def repariere_zeile(raw_line: str, zeilennr: int) -> dict | None:
    """Rekonstruiert eine durch unescapte Kommas verschobene Zeile aus dem Rohtext."""
    raw = raw_line.rstrip("\n")
    tokens = raw.split(",")
    if len(tokens) < 3:
        print(f"   ! Zeile {zeilennr}: zu wenig Felder, übersprungen: {raw!r}")
        return None

    allergen = tokens[1].strip()

    if raw.endswith(",de,USDA"):
        name_tokens = tokens[2:-2]
        language, source = "de", "USDA"
    elif raw.endswith(",de"):
        name_tokens = tokens[2:-1]
        language, source = "de", None
    else:
        # Kein erkennbares Sprache/Quelle-Suffix mehr vorhanden - kompletter Rest ist der Name
        name_tokens = tokens[2:]
        language, source = "de", None

    name = ", ".join(t.strip() for t in name_tokens if t.strip())
    name = name.rstrip('"').strip()  # verwaiste Anführungszeichen vom Zeilenumbruch entfernen

    if not allergen or not name:
        print(f"   ! Zeile {zeilennr}: allergen oder name leer nach Reparatur, übersprungen: {raw!r}")
        return None

    return {"allergen": allergen, "synonym": name, "language": language, "category": source}


def lade_zeilen():
    with open(CSV_PFAD, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        geparst = list(reader)
    with open(CSV_PFAD, encoding="utf-8") as f:
        rohzeilen = f.readlines()[1:]

    sauber, repariert = [], []
    for i, row in enumerate(geparst):
        if row["language"] == "de":
            sauber.append({
                "allergen": row["allergen"].strip(),
                "synonym": row["name"].strip(),
                "language": "de",
                "category": row["source"].strip() or None,
            })
        else:
            fix = repariere_zeile(rohzeilen[i], i + 2)
            if fix:
                repariert.append(fix)

    return sauber + repariert, len(repariert)


def main():
    dry_run = "--dry-run" in sys.argv

    zeilen, anzahl_repariert = lade_zeilen()
    print(f"[INFO] {len(zeilen)} Zeilen aus CSV geladen ({anzahl_repariert} davon repariert)")

    conn = sqlite3.connect(DB_PFAD)
    vor_import = conn.execute("SELECT COUNT(*) FROM allergen_synonyms").fetchone()[0]

    eingefuegt = 0
    for z in zeilen:
        if dry_run:
            continue
        cur = conn.execute(
            """INSERT OR IGNORE INTO allergen_synonyms (allergen, synonym, language, category)
               VALUES (?, ?, ?, ?)""",
            (z["allergen"].lower(), z["synonym"].lower(), z["language"], z["category"]),
        )
        if cur.rowcount > 0:
            eingefuegt += 1

    if dry_run:
        print("[DRY RUN] Es wurde nichts geschrieben. Beispiele reparierter Zeilen:")
        repariert_beispiele = [z for z in zeilen][-anzahl_repariert:][:15]
        for z in repariert_beispiele:
            print(f"   {z['allergen']:12} | {z['synonym']!r:60} | category={z['category']}")
    else:
        conn.commit()
        nach_import = conn.execute("SELECT COUNT(*) FROM allergen_synonyms").fetchone()[0]
        print(f"[OK] {eingefuegt} neue Synonyme eingefügt (Duplikate übersprungen)")
        print(f"[OK] Tabelle: {vor_import} -> {nach_import} Zeilen")

    conn.close()


if __name__ == "__main__":
    main()
