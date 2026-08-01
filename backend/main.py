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
from synonym_learner import lerne_synonym, lerne_von_ollama_funden, lerne_von_off_ingredients
from ambiguity_checker import braucht_ki_check
from eiweiss_filter import filtere_eiweiss_funde

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
    gesehen = set()
    
    # Ignoriere generische Überschriften
    IGNORIERTE_ZEILEN = {
        "produktbeschreibung", "zutaten", "allergene", "nährwerte", 
        "inhaltsstoffe", "ingredients", "allergens", "nutrition",
        "beschreibung", "details", "information"
    }

    # GTIN/EAN explizit suchen (oft in "GTIN: 1234567890")
    gtin_match = re.search(r'(?:GTIN|EAN|Barcode)[:\s]+(\d{8,13})', text, re.IGNORECASE)
    if gtin_match:
        barcode = gtin_match.group(1)
        kandidaten.append(barcode)
        gesehen.add(barcode.lower())

    # Alle Barcodes (EAN-8, EAN-13) sammeln
    for barcode in re.findall(r'\b\d{8,13}\b', text):
        if barcode.lower() not in gesehen:
            kandidaten.append(barcode)
            gesehen.add(barcode.lower())

    # Produktname aus den ersten Zeilen extrahieren (skip generische Überschriften)
    for zeile in text.splitlines()[:10]:  # Erste 10 Zeilen durchsuchen
        zeile_clean = zeile.strip()
        zeile_lower = zeile_clean.lower()
        
        # Skip zu kurze/lange oder generische Zeilen
        if not (15 < len(zeile_clean) < 100):  # Mindestens 15 Zeichen für echte Produktnamen
            continue
        if zeile_lower in IGNORIERTE_ZEILEN:
            continue
        if any(ig in zeile_lower for ig in IGNORIERTE_ZEILEN):
            continue
        
        # Skip Marketing-Floskeln
        if any(floskeln in zeile_lower for floskeln in ["hoher", "niedriger", "reich an", "ohne", "mit extra"]):
            continue
        
        # Guter Kandidat: Zeile mit Produkt-typischen Wörtern + Marke/Geschmack
        if any(keyword in zeile_lower for keyword in ["riegel", "protein", "schokolade", "müsli", "joghurt", "drink", "snack", "kekse", "chips"]):
            # Muss auch Marke/Geschmack enthalten (nicht nur "Proteinriegel")
            if any(detail in zeile_lower for detail in ["caramel", "vanille", "schoko", "nuss", "beere", "frucht", "geschmack", "%", "sportness", "dm"]):
                if zeile_lower not in gesehen:
                    kandidaten.append(zeile_clean)
                    gesehen.add(zeile_lower)
                    break

    return kandidaten[:5]  # max 5 Versuche


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
    
    # DEBUG: Log KOMPLETTEN extrahierten Text
    print(f"\n{'='*80}")
    print(f"🔍 EMPFANGENER TEXT (KOMPLETT):")
    print(f"{'='*80}")
    print(text)
    print(f"{'='*80}")
    print(f"📊 Text-Länge: {len(text)} Zeichen | Zeilen: {len(text.splitlines())}")
    print(f"👤 User: {user_name} | Allergien: {allergien}")
    print(f"🔎 Suche nach 'cerealien': {'cerealien' in text.lower()}")
    print(f"🔎 Suche nach 'allergen': {'allergen' in text.lower()}")
    print(f"{'='*80}\n")

    funde: list[dict] = []
    methode = "synonym"

    # ══════════════════════════════════════════════════════════════════════════
    # SMART CASCADE: Schnell → Langsam, Lokal → Remote, Lernen bei jedem Schritt
    # ══════════════════════════════════════════════════════════════════════════

    # ── TIER 1: OpenFoodFacts (extern, cached, Synonym-Learning) ─────────────
    print(f"\n🔬 TIER 1: OpenFoodFacts")
    produkt = None
    
    # 1a) Barcode-Suche
    barcodes = re.findall(r'\b\d{8,13}\b', text)
    for barcode in barcodes:
        produkt = suche_off(barcode)
        if produkt and (produkt.get("allergens_tags") or produkt.get("ingredients_text")):
            print(f"   ✅ Produkt via Barcode: {produkt.get('product_name', 'Unbekannt')}")
            break
        produkt = None
    
    # 1b) Produktnamen-Suche
    if not produkt:
        kandidaten = extrahiere_produktnamen(text)
        for kandidat in kandidaten:
            produkt = suche_off(kandidat)
            if produkt and (produkt.get("allergens_tags") or produkt.get("ingredients_text")):
                print(f"   ✅ Produkt via Name: {produkt.get('product_name')} ('{kandidat}')")
                break
            produkt = None
    
    # 1c) Allergene in OFF prüfen + Synonyme lernen
    if produkt:
        off_funde = off_allergene_pruefen(produkt, allergien)
        if off_funde:
            funde = off_funde
            methode = "openfoodfacts"
            print(f"   ✅ {len(off_funde)} Allergene in OFF gefunden!")
            
            # Lerne aus OFF ingredients_text
            for allergie in allergien:
                lerne_von_off_ingredients(produkt, allergie)
        else:
            print(f"   ⚠️ Produkt gefunden, aber keine Allergene in OFF-DB")

    # ── TIER 2: Lokale Synonym-DB (instant <100ms, statisch + gelernt) ───────
    if methode != "openfoodfacts":
        print(f"\n📖 TIER 2: Lokale Synonym-Matching (statisch + gelernt)")
        synonym_funde = synonym_matching(text, allergien)
        
        if synonym_funde:
            gefahr_funde_temp = [f for f in synonym_funde if not f.get("ist_spur")]
            if gefahr_funde_temp:
                print(f"   ✅ {len(gefahr_funde_temp)} DIREKTE Allergene gefunden!")
            else:
                print(f"   ⚠️ {len(synonym_funde)} Spurenhinweise gefunden")
        else:
            print(f"   ℹ️  Keine Allergene per Textanalyse gefunden")
        
        # ── TIER 3: Ollama KI (langsam ~2-3s, als Zusatzsicherheit) ────────
        print(f"\n🤖 TIER 3: KI-Analyse (Ollama) als Zusatzsicherheit")
        try:
            ollama_funde_raw = analyse_mit_ollama(text, allergien)
            print(f"   ✅ KI findet {len(ollama_funde_raw)} Allergene")
            
            # WICHTIG: Filtere Protein-Fehlerkennungen (z.B. "Milcheiweiß" als Ei)
            ollama_funde = filtere_eiweiss_funde(ollama_funde_raw, text)
            if len(ollama_funde) < len(ollama_funde_raw):
                print(f"   🧹 {len(ollama_funde_raw) - len(ollama_funde)} False Positives gefiltert")
            
            # Kombiniere Funde (entferne Duplikate)
            alle_funde = synonym_funde[:]
            for ollama_fund in ollama_funde:
                # Prüfe ob bereits gefunden (gleiche Allergie + ähnliches Synonym)
                ist_duplikat = any(
                    f['allergie'] == ollama_fund['allergie'] and 
                    f['synonym'].lower()[:5] == ollama_fund['synonym'].lower()[:5]
                    for f in alle_funde
                )
                if not ist_duplikat:
                    alle_funde.append(ollama_fund)
                    print(f"      🆕 KI findet zusätzlich: {ollama_fund['allergie']} ({ollama_fund['synonym']})")
            
            funde = alle_funde
            methode = "synonym+ki" if synonym_funde and ollama_funde else ("synonym" if synonym_funde else ("ki" if ollama_funde else "synonym"))
            
        except Exception as e:
            print(f"   ⚠️ KI-Analyse fehlgeschlagen: {e}")
            funde = synonym_funde  # Fallback auf Synonym-Matching
            methode = "synonym"

    print(f"\n{'='*60}")
    print(f"🎯 FINALE METHODE: {methode.upper()}")
    print(f"{'='*60}\n")

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
