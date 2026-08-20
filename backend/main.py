'''from fastapi import FastAPI
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
# from filters import filtere_funde  # Nicht mehr benötigt - Filter in ollama_client.py

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
load_synonyms_into_cache()  # Load allergen synonyms from DB into memory


# ── Endpunkte ─────────────────────────────────────────────────────────────────
@app.get("/users")
def list_users():
    """
    List all saved user profiles.

    Multiple profiles can be "selected" at once — their allergen lists are
    combined when checking a recipe (e.g. for a dinner party with several
    guests who each have their own profile).

    Returns:
        list[dict]: All profiles ordered by id, each with keys:
            - id (int)
            - name (str)
            - allergy (str): Comma-separated list of allergens
            - selected (bool): Whether this profile is included in checks
    """
    conn = db()
    rows = conn.execute('SELECT id, name, allergy, selected FROM users ORDER BY id').fetchall()
    conn.close()
    return [
        {"id": r["id"], "name": r["name"], "allergy": r["allergy"], "selected": bool(r["selected"])}
        for r in rows
    ]


@app.post("/users")
def create_user(req: UserProfile):
    """
    Create a new user profile. New profiles are selected by default.

    Args:
        req (UserProfile): name and comma-separated allergy list.

    Returns:
        dict: The created profile, including its new id and selected=True.
    """
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
    """
    Update an existing user profile's name and allergy list.
    """
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
    """
    Delete a user profile.
    """
    conn = db()
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.patch("/users/{user_id}/selection")
def set_user_selection(user_id: int, req: SelectionUpdate):
    """
    Mark a user profile as selected/unselected for allergen checks.

    Multiple users can be selected simultaneously; their allergen lists are
    combined (union) when checking a recipe via /check-recipe.
    """
    conn = db()
    conn.execute('UPDATE users SET selected=? WHERE id=?', (1 if req.selected else 0, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/history")
def get_history():
    """
    Get the allergen check history.
    
    Returns the last 20 allergen checks performed by the user, ordered by
    timestamp (most recent first).
    
    Returns:
        list[dict]: List of history entries, each containing:
            - id (int): Unique entry ID
            - timestamp (str): ISO format timestamp
            - ingredient_text (str): Text that was checked
            - result (str): Check result ("SICHER", "WARNUNG", or "GEFAHR")
            - detected_allergens (str): Comma-separated list of detected allergens
    
    Example response:
        [
            {
                "id": 42,
                "timestamp": "2024-01-15T14:30:00",
                "ingredient_text": "Mehl, Eier, Zucker",
                "result": "GEFAHR",
                "detected_allergens": "ei"
            }
        ]
    """
    conn = db()
    rows = conn.execute(
        'SELECT * FROM history ORDER BY timestamp DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/check-recipe")
def check_recipe(request: RecipeRequest):
    """
    Check ingredient text for allergens using a 3-tier detection system.
    
    This is the core endpoint that performs allergen detection using:
    - Tier 1: OpenFoodFacts database (external API, cached for 7 days)
    - Tier 2: Local synonym matching (1200+ synonyms, <100ms)
    - Tier 3: AI analysis with Ollama/Mistral (2-3s, as additional safety net)
    
    The system learns new synonyms automatically from successful detections
    and applies false-positive filtering to reduce errors.
    
    Args:
        request (RecipeRequest): Request data containing:
            - ingredients (str): Product text, ingredient list, or barcode
    
    Returns:
        dict: Detection result with keys:
            - urteil (str): Overall assessment ("SICHER", "WARNUNG", or "GEFAHR")
            - gefunden (str): Allergen synonym found (empty if safe)
            - fundort (str): Location where allergen was found
            - methode (str): Detection method used ("openfoodfacts", "synonym", "ki", or combined)
            - allergien (list[str]): User's allergen list
            - ersatzvorschlag (str): Replacement suggestions for detected allergen
            - alle_funde (list[dict]): All detected allergens with details
    
    Example request body:
        {
            "ingredients": "Mehl, Eier, Zucker, Vanilleschote"
        }
    
    Example response (allergen detected):
        {
            "urteil": "GEFAHR",
            "gefunden": "eier",
            "fundort": "Mehl, Eier, Zucker",
            "methode": "synonym",
            "allergien": ["ei", "milch"],
            "ersatzvorschlag": "Leinsamen | Apfelmus | Banane | Chiasamen | Sojamehl",
            "alle_funde": [
                {
                    "allergie": "ei",
                    "synonym": "eier",
                    "fundstelle": "Mehl, Eier, Zucker",
                    "ist_spur": false
                }
            ]
        }
    
    Example response (safe):
        {
            "urteil": "SICHER",
            "gefunden": "",
            "fundort": "",
            "methode": "synonym",
            "allergien": ["ei", "milch"],
            "ersatzvorschlag": "",
            "alle_funde": []
        }
    """
    conn = db()
    selected_users = conn.execute('SELECT name, allergy FROM users WHERE selected=1').fetchall()
    conn.close()
    if not selected_users:
        return {"error": "Kein Benutzerprofil ausgewählt. Bitte mindestens ein Profil im Profil-Tab auswählen."}

    user_name = ", ".join(u["name"] for u in selected_users)

    # Allergien aller ausgewählten Profile kombinieren (Vereinigung, ohne Duplikate)
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

    # SMART CASCADE: Tier 1 und Tier 2 ergänzen sich (ein erkanntes OFF-Produkt
    # deckt nicht automatisch alle anderen im Text genannten Zutaten ab), nur
    # Tier 3 (KI) ist ein echter Fallback für den Fall, dass beide nichts finden.

    # TIER 1: OpenFoodFacts (external, cached, Synonym-Learning)
    logger.info("[TIER 1] OpenFoodFacts")
    produkt = None

    # 1a) Barcode-Suche
    barcodes = re.findall(r'\b\d{8,13}\b', text)
    for barcode in barcodes:
        produkt = suche_off(barcode)
        if produkt and (produkt.get("allergens_tags") or produkt.get("ingredients_text")):
            logger.info(f"Product via Barcode: {produkt.get('product_name', 'Unknown')}")
            break
        produkt = None

    # 1b) Produkt im Freitext erkennen: erst lokal bekannte Produkte (kein Netzwerk,
    # kein Rateproblem), erst danach eine verifizierte OFF-Suche als Fallback
    if not produkt:
        produkt = off_produkt_im_text_finden(text)
        if produkt:
            logger.info(f"Product via Textmatch: {produkt.get('product_name')}")

    # 1c) Allergene in OFF prüfen + Synonyme lernen
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

    # TIER 2: Local Synonym-DB (instant <100ms, static + learned) - läuft immer
    # über den GESAMTEN Text, unabhängig davon ob Tier 1 schon etwas gefunden hat.
    # Sonst würde z.B. "Weizenmehl" neben einem erkannten OFF-Produkt ignoriert.
    logger.info("[TIER 2] Local Synonym-Matching")
    synonym_funde = synonym_matching(text, allergien)

    if synonym_funde:
        logger.info(f"{len(synonym_funde)} allergens found via synonym matching!")
        funde.extend(synonym_funde)
        methode_teile.append("synonym")
    else:
        logger.info("No allergens found via synonym matching")

    # TIER 3: Ollama AI (slow ~2-3s) - nur wenn WEDER OFF noch Synonym-Matching
    # irgendetwas gefunden haben (echter Last-Resort-Fallback)
    if not funde:
        logger.info("[TIER 3] AI-Analysis (Ollama) as LAST RESORT FALLBACK")
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

    methode = "+".join(dict.fromkeys(methode_teile)) if methode_teile else "synonym"
    logger.info(f"FINAL METHOD: {methode.upper()}")

    # ── Gesamturteil ──────────────────────────────────────────────────────────
    gefahr_funde = [f for f in funde if not f.get("ist_spur")]
    spuren_funde = [f for f in funde if f.get("ist_spur")]

    # Redundante Spurenhinweise unterdrücken: Wenn ein Allergen bereits direkt
    # (GEFAHR) gefunden wurde, bringt ein zusätzlicher "Kann Spuren enthalten"-
    # Hinweis für DASSELBE Allergen keine neue Information mehr - nur unnötige
    # Verwirrung (z.B. "Milchpulver" in Zutaten + generischer "Kann Spuren von
    # Milch"-Disclaimer). Andere Allergene mit eigenen Spurenhinweisen bleiben.
    bereits_direkt_gefunden = {f["allergie"] for f in gefahr_funde}
    spuren_funde = [f for f in spuren_funde if f["allergie"] not in bereits_direkt_gefunden]
    funde = gefahr_funde + spuren_funde

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
        allergien_liste = ", ".join(dict.fromkeys(f["allergie"] for f in gefahr_funde))
        grund = f'Direkt gefunden: {allergien_liste}. (via {methode})'
    elif urteil == "WARNUNG":
        allergien_liste = ", ".join(dict.fromkeys(f["allergie"] for f in spuren_funde))
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
        '''#INSERT INTO history
           #(timestamp, source, urteil, allergie_geprueft, gefundenes_synonym, fundstelle, grund, methode, result_snapshot)
           #VALUES (?,?,?,?,?,?,?,?,?),
        '''(
            datetime.datetime.now().isoformat(),
            request.source or "Unbekannt",
            urteil, user_allergy,
            gefundenes_synonym, gefunden_in, grund, methode,
            json.dumps(result, ensure_ascii=False),
        )
    )
    conn.execute('''
        #DELETE FROM history WHERE id NOT IN (
            #SELECT id FROM history ORDER BY timestamp DESC LIMIT 20
        #)
    ''')
    conn.commit()
    conn.close()

    return result


if __name__ == "__main__":
    import uvicorn
    from config import SERVER_HOST, SERVER_PORT
    
    logger.info(f"Starting AllergyGuard server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
'''