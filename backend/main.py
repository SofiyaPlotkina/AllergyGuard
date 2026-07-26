from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime
import json
import re

from config import SPUREN_PHRASEN
from database import db, init_db
from models import ProfileRequest, RecipeRequest
from allergen_data import ersatz_fuer
from synonym_matcher import synonyme_fuer, synonym_matching
from openfoodfacts_client import suche_off, off_allergene_pruefen
from ollama_client import analyse_mit_ollama

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def extrahiere_produktnamen(text: str) -> list[str]:
    """Versucht Produktnamen oder Barcodes aus dem Freitext zu extrahieren."""
    kandidaten = []

    # Barcode (EAN-8, EAN-13)
    for barcode in re.findall(r'\b\d{8,13}\b', text):
        kandidaten.append(barcode)

    # Erste nicht-leere Zeile als Produktname (oft Überschrift / Seitentitel)
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if 5 < len(zeile) < 80:
            kandidaten.append(zeile)
            break

    # Zutaten-Substring (erste 120 Zeichen nach "Zutaten:" o.Ä.)
    m = re.search(r'(?:zutaten|ingredients)[:\s]+(.{10,120})', text, re.IGNORECASE)
    if m:
        kandidaten.append(m.group(1).strip())

    return kandidaten[:3]  # max 3 Versuche


# ── Endpunkte ─────────────────────────────────────────────────────────────────
@app.get("/profile")
def get_profile():
    conn = db()
    user = conn.execute('SELECT name, allergy FROM users LIMIT 1').fetchone()
    conn.close()
    if not user:
        return {"name": "", "allergy": ""}
    return {"name": user["name"], "allergy": user["allergy"]}


@app.post("/profile")
def save_profile(req: ProfileRequest):
    conn = db()
    existing = conn.execute('SELECT id FROM users LIMIT 1').fetchone()
    if existing:
        conn.execute('UPDATE users SET name=?, allergy=? WHERE id=?',
                     (req.name, req.allergy, existing["id"]))
    else:
        conn.execute('INSERT INTO users (name, allergy) VALUES (?,?)', (req.name, req.allergy))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/history")
def get_history():
    conn = db()
    rows = conn.execute(
        'SELECT * FROM history ORDER BY timestamp DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/check-recipe")
def check_recipe(request: RecipeRequest):
    conn = db()
    user = conn.execute('SELECT name, allergy FROM users LIMIT 1').fetchone()
    conn.close()
    if not user:
        return {"error": "Kein Benutzerprofil gefunden. Bitte Profil anlegen."}

    user_name    = user["name"]
    user_allergy = user["allergy"]
    allergien    = [a.strip() for a in user_allergy.split(",") if a.strip()]
    text         = request.ingredients

    funde: list[dict] = []
    methode = "synonym"

    # ── 1. OpenFoodFacts — NUR bei Barcode ───────────────────────────────────
    # Freitext-Rezepte liefern auf OFF zufällige Produkte (z.B. "Biscoff"),
    # daher wird OFF ausschließlich bei erkanntem EAN-8/EAN-13-Barcode genutzt.
    barcodes = re.findall(r'\b\d{8,13}\b', text)
    for barcode in barcodes:
        produkt = suche_off(barcode)
        if produkt:
            off_funde = off_allergene_pruefen(produkt, allergien)
            if off_funde or produkt.get("allergens_tags"):
                funde = off_funde
                methode = "openfoodfacts"
                break

    # ── 2. Ollama-Fallback ────────────────────────────────────────────────────
    if methode != "openfoodfacts":
        ollama_funde = analyse_mit_ollama(text, allergien)
        if ollama_funde:
            funde = ollama_funde
            methode = "ollama"

    # ── 3. Lokales Synonym-Matching als letzter Fallback ──────────────────────
    if methode not in ("openfoodfacts", "ollama"):
        funde = synonym_matching(text, allergien)
        methode = "synonym"

    # ── Gesamturteil ──────────────────────────────────────────────────────────
    gefahr_funde = [f for f in funde if not f.get("ist_spur")]
    spuren_funde = [f for f in funde if f.get("ist_spur")]

    if gefahr_funde:
        urteil = "GEFAHR"
    elif spuren_funde:
        urteil = "WARNUNG"
    else:
        urteil = "SICHER"

    erster_fund        = (gefahr_funde or spuren_funde or [None])[0]
    gefundenes_synonym = erster_fund["synonym"] if erster_fund else ""
    gefunden_in        = erster_fund["fundstelle"] if erster_fund else ""

    if urteil == "GEFAHR":
        allergien_liste = ", ".join(f["allergie"] for f in gefahr_funde)
        grund = f'Direkt gefunden: {allergien_liste}. (via {methode})'
    elif urteil == "WARNUNG":
        allergien_liste = ", ".join(f["allergie"] for f in spuren_funde)
        grund = f'Spurenhinweise auf: {allergien_liste}. (via {methode})'
    else:
        grund = f'Keine Allergene gefunden. (via {methode})'

    # ── Result-Objekt bauen ───────────────────────────────────────────────────
    result = {
        "nutzer":             user_name,
        "allergie_geprueft":  user_allergy,
        "urteil":             urteil,
        "gefundenes_synonym": gefundenes_synonym,
        "fundstelle":         gefunden_in,
        "grund":              grund,
        "methode":            methode,
        "alle_funde":         funde,
    }

    # ── Verlauf speichern ─────────────────────────────────────────────────────
    conn = db()
    conn.execute(
        '''INSERT INTO history
           (timestamp, source, urteil, allergie_geprueft, gefundenes_synonym, fundstelle, grund, methode, result_snapshot)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        (
            datetime.datetime.now().isoformat(),
            request.source or "Unbekannt",
            urteil, user_allergy,
            gefundenes_synonym, gefunden_in, grund, methode,
            json.dumps(result, ensure_ascii=False),
        )
    )
    conn.execute('''
        DELETE FROM history WHERE id NOT IN (
            SELECT id FROM history ORDER BY timestamp DESC LIMIT 20
        )
    ''')
    conn.commit()
    conn.close()

    return result
