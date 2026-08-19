from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import datetime
import json
import re
import logging

from config import SPUREN_PHRASEN
from database import db, init_db
from models import UserProfile, SelectionUpdate, RecipeRequest
from allergen_db import get_replacement_for_term, load_synonyms_into_cache
from synonym_matcher import synonyme_fuer, synonym_matching
from openfoodfacts_client import suche_off, off_allergene_pruefen, off_produkt_im_text_finden
from ollama_client import analyse_mit_ollama
from synonym_learner import lerne_synonym, lerne_von_off_ingredients

# Logging einrichtenn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS-Config: Alle origins erlaubt zum DEV Testen derzeit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Tabellen anlegen bzw Synonyme in Cache laden, wenn noch nicht bisher
init_db()
load_synonyms_into_cache() 


# ENDPUNKTE

@app.get("/users")
def list_users():


    #Zeigt alle Nutzerprofile an, plus welche gerade aktiviert sind (selected Spalte). 
    # Es können hier mehrere auf einmal aktiviert sein, deren Allergene werden kombiniert geprüft dann


    conn = db()
    rows = conn.execute('SELECT id, name, allergy, selected FROM users ORDER BY id').fetchall()
    conn.close()
    return [
        {"id": r["id"], "name": r["name"], "allergy": r["allergy"], "selected": bool(r["selected"])}
        for r in rows
    ]


@app.post("/users")
def create_user(req: UserProfile):
    
    # Neuen User anlegen (default ist "aktiv" (selected = 1))

    conn = db()
    cursor = conn.execute(
        'INSERT INTO users (name, allergy, selected) VALUES (?, ?, 1)', (req.name, req.allergy)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "name": req.name, "allergy": req.allergy, "selected": True}


@app.put("/users/{user_id}")
def update_user(user_id: int, req: UserProfile):
   
    # Bestehenden User updaten (Name / Allergien) --> "Selected" hier unverändert

    conn = db()
    existing = conn.execute('SELECT id FROM users WHERE id=?', (user_id,)).fetchone()
    if not existing:
        conn.close()
        return {"error": "Profil nicht gefunden."}
    conn.execute('UPDATE users SET name=?, allergy=? WHERE id=?', (req.name, req.allergy, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    
    # User löschen

    conn = db()
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.patch("/users/{user_id}/selection")
def set_user_selection(user_id: int, req: SelectionUpdate):
    
    # Schauen, ob User aktiv (selected = 1)

    conn = db()
    conn.execute('UPDATE users SET selected=? WHERE id=?', (1 if req.selected else 0, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/history")
def get_history():
    
    # Lädt letze 20 checks für den Verlaufs Tab

    conn = db()
    rows = conn.execute(
        'SELECT * FROM history ORDER BY timestamp DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Endpunkt für Kern-Rezeptcheck!!

@app.post("/check-recipe")
def check_recipe(request: RecipeRequest):
    # Prüft ein Rezept auf Allergene, basierend auf den aktuell ausgewählten usern

    conn = db()
    selected_users = conn.execute('SELECT name, allergy FROM users WHERE selected=1').fetchall()
    conn.close()
    if not selected_users: # exit hier, wenn kein Profil ausgewählt ist
        return {"error": "Kein Benutzerprofil ausgewählt. Bitte mindestens ein Profil im Profil-Tab auswählen."}

    user_name = ", ".join(u["name"] for u in selected_users)

    # Allergien aller ausgewählten user kombinieren (ohne Duplikate)
    allergien: list[str] = []
    gesehen = set()
    for u in selected_users:
        for a in u["allergy"].split(","):
            a = a.strip()
            if a and a.lower() not in gesehen:
                gesehen.add(a.lower())
                allergien.append(a)
    user_allergy = ", ".join(allergien)
    text         = request.ingredients
    
    # DEBUG: Log KOMPLETTEN extrahierten Text
    logger.debug("="*80)
    logger.debug("[RECEIVED TEXT - COMPLETE]:")
    logger.debug("="*80)
    logger.debug(text)
    logger.debug("="*80)
    logger.info(f"Text length: {len(text)} chars | Lines: {len(text.splitlines())}")
    logger.info(f"User: {user_name} | Allergies: {allergien}")
    logger.debug(f"Search 'cerealien': {'cerealien' in text.lower()}")
    logger.debug(f"Search 'allergen': {'allergen' in text.lower()}")
    logger.debug("="*80)

    funde: list[dict] = []
    methode_teile: list[str] = []

    # Hier kommen jetzt die Tiers 1 bis 3
    # Wichtig: Tier 1 und 2 ergänzen sich, Tier 2 wird nie übersprungen, nur weil 1 was gefunden hat, 
    # weil etwas erkanntes auf OFF nicht automatisch alle Zutaten deckt

    # TIER 1: OpenFoodFacts API
    logger.info("[TIER 1] OpenFoodFacts")
    produkt = None

    # Barcode-Suche mit Regex (8-13 Ziffern) - sonst überspringen
    barcodes = re.findall(r'\b\d{8,13}\b', text)
    for barcode in barcodes:
        produkt = suche_off(barcode)
        if produkt and (produkt.get("allergens_tags") or produkt.get("ingredients_text")):
            logger.info(f"Product via Barcode: {produkt.get('product_name', 'Unknown')}")
            break
        produkt = None

    # Wenn kein Barcode da - Produkt im Freitext erkennen
    if not produkt:
        produkt = off_produkt_im_text_finden(text)
        if produkt:
            logger.info(f"Product via Textmatch: {produkt.get('product_name')}")

    # Wenn Produkt im Freitext - Allergene aus OFF, dann Synonym Learning
    if produkt:
        off_funde = off_allergene_pruefen(produkt, allergien)
        if off_funde:
            funde.extend(off_funde)
            methode_teile.append("openfoodfacts")
            logger.info(f"{len(off_funde)} allergens found in OFF!")

            # Lerne aus OFF ingredients_text
            for allergie in allergien:
                lerne_von_off_ingredients(produkt, allergie)
        else:
            logger.warning("Product found, but no allergens in OFF-DB")

    # TIER 2: Lokale Synonym DB
    # Läuft immer, auch wenn in Tier 1 etwas gefunden
    logger.info("[TIER 2] Local Synonym-Matching")
    synonym_funde = synonym_matching(text, allergien)

    if synonym_funde:
        logger.info(f"{len(synonym_funde)} allergens found via synonym matching!")
        funde.extend(synonym_funde)
        methode_teile.append("synonym")
    else:
        logger.info("No allergens found via synonym matching")

    # TIER 3: Ollama AI, nur wenn WEDER OFF noch Synonym-Matching etwas finden
    if not funde:
        logger.info("[TIER 3] AI-Analysis (Ollama) as FALLBACK")
        try:
            ollama_funde = analyse_mit_ollama(text, allergien)

            if ollama_funde:
                logger.info(f"AI finds {len(ollama_funde)} allergens")
                funde = ollama_funde
                methode_teile = ["ki"]
            else:
                logger.info("AI also finds nothing - product is safe")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")

    # Gibt aus, welches Tier am Ende etwas gefunden hat
    methode = "+".join(dict.fromkeys(methode_teile)) if methode_teile else "synonym"
    logger.info(f"FINAL METHOD: {methode.upper()}")

  # Gefundenes splitten in "echte" Zutat vs Spuren
    gefahr_funde = [f for f in funde if not f.get("ist_spur")]
    spuren_funde = [f for f in funde if f.get("ist_spur")]

    # Spuren Deduplizierung - Wenn bestimmtes Allergen schon als echte Zutat gefunden wurde, dann Spuren Fund ignorieren
    # Gegen redundante Info Anzeige
    bereits_direkt_gefunden = {f["allergie"] for f in gefahr_funde}
    spuren_funde = [f for f in spuren_funde if f["allergie"] not in bereits_direkt_gefunden]
    funde = gefahr_funde + spuren_funde

    # Finales "Urteil" ermitteln
    if gefahr_funde:
        urteil = "GEFAHR"
    elif spuren_funde:
        urteil = "WARNUNG"
    else:
        urteil = "SICHER"

    # Text für Ausgabe Zusammenbauen    
    erster_fund        = (gefahr_funde or spuren_funde or [None])[0]
    gefundenes_synonym = erster_fund["synonym"] if erster_fund else ""
    gefunden_in        = erster_fund["fundstelle"] if erster_fund else ""

    if urteil == "GEFAHR":
        allergien_liste = ", ".join(dict.fromkeys(f["allergie"] for f in gefahr_funde))
        grund = f'Direkt gefunden: {allergien_liste}. (via {methode})'
    elif urteil == "WARNUNG":
        allergien_liste = ", ".join(dict.fromkeys(f["allergie"] for f in spuren_funde))
        grund = f'Spurenhinweise auf: {allergien_liste}. (via {methode})'
    else:
        grund = f'Keine Allergene gefunden. (via {methode})'

    # JSON Response erstellen
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

    # Diesen Durchlauf in den Verlauf schreiben (letzte 20 Einträge bleiben drin)
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

# Server starten, wenn direkt ausgeführt
if __name__ == "__main__":
    import uvicorn
    from config import SERVER_HOST, SERVER_PORT
    
    logger.info(f"Starting AllergyGuard server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
