"""Synonym matching functionality for allergen detection."""

import re

from allergen_data import ALLERGEN_SYNONYME, ersatz_fuer
from config import SPUREN_PHRASEN, WORTGRENZE_SYNONYME
from text_filter import extrahiere_zutaten_sektion


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEMATISCHE FALSE-POSITIVE FILTER
# ═══════════════════════════════════════════════════════════════════════════
# Diese Begriffe enthalten Allergen-Wörter, sind aber KEINE Allergene!

# PFLANZENMILCH = KEINE Milch! (laktosefrei, vegan)
PFLANZENMILCH_BEGRIFFE = [
    "mandelmilch", "hafermilch", "sojamilch", "reismilch", "kokosmilch",
    "cashewmilch", "haselnussmilch", "macadamiamilch", "dinkelmilch",
    "hirsemilch", "quinoamilch", "erbsenmilch", "lupinenmilch",
    "hanfmilch", "tigernussmilch", "sesammilch",
    # Englisch
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
    "cashew milk", "hazelnut milk", "pea milk", "hemp milk",
]

# VEGANE/PFLANZLICHE BUTTER = KEINE Milch! (laktosefrei, vegan)
VEGANE_BUTTER_BEGRIFFE = [
    "vegane butter", "pflanzliche butter", "pflanzen butter",
    "alsan", "rama", "becel", "flora",  # Bekannte Marken
    "margarine",  # Oft pflanzlich (manchmal mit Milch, aber meist vegan)
    "kokosfett", "kokosöl", "palmfett",  # Pflanzliche Fett-Alternativen
    "pflanzenfett", "pflanzliches fett",
    # Englisch
    "vegan butter", "plant butter", "plant-based butter",
]

# PFLANZENPROTEIN = KEIN Ei! (bereits in eiweiss_filter.py, hier zur Vollständigkeit)
PFLANZENPROTEIN_BEGRIFFE = [
    "sojaeiweiß", "sojaeiweiss", "erbsenprotein", "erbseneiweiß",
    "reisprotein", "hanfprotein", "lupineneiweiß",
    "pflanzenprotein", "pflanzeneiweiß", "pflanzliches protein",
]

# PSEUDO-GETREIDE = KEIN Gluten! (trotz "weizen", "korn" im Namen)
GLUTENFREIE_PSEUDOGETREIDE = [
    "buchweizen",  # KEIN Weizen! Kein Gluten!
    "amaranth", "amarant",  # Pseudogetreide, glutenfrei
    "quinoa",  # Pseudogetreide, glutenfrei
    "hirse",  # Glutenfrei (obwohl Getreide)
    "teff",  # Glutenfrei
    "buckwheat",  # Englisch für Buchweizen
]

# NUSS-UNABHÄNGIGE BEGRIFFE = KEINE Nuss! 
KEINE_NUSS_BEGRIFFE = [
    "kokosnuss", "muskatnuss", "erdnuss",  # Botanisch keine Nüsse (aber Allergen!)
    # Diese SIND Allergene, werden separat gehandelt
]


def ist_false_positive(allergen: str, synonym: str, fundstelle: str) -> bool:
    """
    SYSTEMATISCHER Filter: Prüft ob ein Fund ein False Positive ist.
    
    Beispiele:
    - "milch" in "Mandelmilch" → True (False Positive, ist pflanzlich)
    - "weizen" in "Buchweizen" → True (False Positive, ist glutenfrei)
    - "milch" in "Vollmilch" → False (echte Milch!)
    
    Returns:
        True = False Positive (Fund verwerfen!)
        False = Echter Allergen-Fund
    """
    allergen_lower = allergen.lower()
    synonym_lower = synonym.lower()
    fundstelle_lower = fundstelle.lower()
    
    # ─────────────────────────────────────────────────────────────────────
    # FILTER 1: PFLANZENMILCH + VEGANE BUTTER (mandelmilch, vegane butter, etc.)
    # ─────────────────────────────────────────────────────────────────────
    if allergen_lower in ["milch", "lactose", "laktose", "milk", "butter"]:
        # Prüfe Pflanzenmilch
        for pflanzenmilch in PFLANZENMILCH_BEGRIFFE:
            if pflanzenmilch in synonym_lower or pflanzenmilch in fundstelle_lower:
                return True  # False Positive!
        
        # Prüfe vegane/pflanzliche Butter
        for vegane_butter in VEGANE_BUTTER_BEGRIFFE:
            if vegane_butter in synonym_lower or vegane_butter in fundstelle_lower:
                return True  # False Positive!
    
    # ─────────────────────────────────────────────────────────────────────
    # FILTER 2: PSEUDO-GETREIDE (buchweizen, quinoa, amaranth)
    # ─────────────────────────────────────────────────────────────────────
    if allergen_lower in ["gluten", "weizen", "wheat"]:
        for pseudo in GLUTENFREIE_PSEUDOGETREIDE:
            if pseudo in synonym_lower or pseudo in fundstelle_lower:
                return True  # False Positive!
    
    # ─────────────────────────────────────────────────────────────────────
    # FILTER 3: PFLANZENPROTEIN (sojaeiweiß, erbsenprotein)
    # ─────────────────────────────────────────────────────────────────────
    if allergen_lower in ["ei", "egg", "eier"]:
        for pflanzenprotein in PFLANZENPROTEIN_BEGRIFFE:
            if pflanzenprotein in synonym_lower or pflanzenprotein in fundstelle_lower:
                return True  # False Positive!
    
    return False  # Kein False Positive → echter Fund!


def synonyme_fuer(allergen: str) -> list[str]:
    """
    Gibt die Liste der Synonyme für ein Allergen zurück.
    Kombiniert statische Synonyme + dynamisch gelernte.
    """
    key = allergen.lower().strip()
    synonyme = []
    
    # 1. Statische Synonyme aus allergen_data.py
    if key in ALLERGEN_SYNONYME:
        synonyme.extend(ALLERGEN_SYNONYME[key])
    else:
        for k, syns in ALLERGEN_SYNONYME.items():
            if k in key or key in k:
                synonyme.extend(syns)
    
    # 2. Dynamisch gelernte Synonyme aus DB
    try:
        from synonym_learner import hole_gelernte_synonyme
        learned = hole_gelernte_synonyme(allergen)
        synonyme.extend(learned)
    except Exception:
        pass  # DB nicht verfügbar, nur statische nutzen
    
    return synonyme if synonyme else [key]


def synonym_trifft(synonym: str, text_lower: str) -> bool:
    """Prüft ob ein Synonym im Text vorkommt; kurze Begriffe nur an Wortgrenzen."""
    if synonym in WORTGRENZE_SYNONYME or len(synonym) <= 3:
        pattern = r'(?<![a-zäöüß])' + re.escape(synonym) + r'(?![a-zäöüß])'
        return bool(re.search(pattern, text_lower))
    return synonym in text_lower


def synonym_matching(text: str, user_allergien: list[str]) -> list[dict]:
    """
    Lokales Synonym-Matching als letzter Fallback.
    
    WICHTIG: Diese Funktion MUSS deterministisch sein!
    Gleicher Input = immer gleicher Output (für Allergiker-Sicherheit).
    
    KRITISCH: Analysiert NUR Zutaten-Sektionen, NICHT:
    - Produktbeschreibungen ("Cremiger Brotaufstrich")
    - Verwendungshinweise ("Ideal auf Brot")
    - Nährwerttabellen ("Eiweiß 14 g")
    """
    # ══════════════════════════════════════════════════════════════════════
    # SCHRITT 1: Extrahiere NUR Zutaten-Sektion
    # ══════════════════════════════════════════════════════════════════════
    zutaten_text = extrahiere_zutaten_sektion(text)
    
    # Wenn keine Zutaten gefunden, analysiere nichts
    if not zutaten_text:
        print("[synonym_matcher] ⚠️  Keine Zutaten-Sektion gefunden → kein Matching")
        return []
    
    print(f"[synonym_matcher] ✅ Zutaten-Text ({len(zutaten_text)} Zeichen): {zutaten_text[:100]}...")
    
    funde = []
    text_lower = zutaten_text.lower()  # NUR Zutaten analysieren!
    
    # Gesehene Allergene tracken, um Duplikate zu vermeiden
    gefundene_allergene = set()
    
    for allergie in user_allergien:
        # Skip wenn Allergen bereits gefunden
        if allergie in gefundene_allergene:
            continue
            
        synonyme = synonyme_fuer(allergie)
        
        # Sammle ALLE Funde für dieses Allergen
        allergen_funde = []
        
        for synonym in synonyme:
            # Erstelle Regex-Pattern (mit Wortgrenzen für kurze Begriffe)
            if synonym in WORTGRENZE_SYNONYME or len(synonym) <= 3:
                pattern = r'(?<![a-zäöüß])' + re.escape(synonym) + r'(?![a-zäöüß])'
            else:
                pattern = re.escape(synonym)
            
            # DETERMINISTISCH: Finde ALLE Matches mit ihrer Position
            matches = list(re.finditer(pattern, text_lower))
            
            if not matches:
                continue
            
            # ═══════════════════════════════════════════════════════════════
            # KRITISCHER FILTER: False Positives SOFORT aussortieren!
            # ═══════════════════════════════════════════════════════════════
            # Extrahiere Fundstelle für False-Positive-Check
            erste_pos = matches[0].start()
            zeile_start = zutaten_text.rfind('\n', 0, erste_pos)
            zeile_start = 0 if zeile_start == -1 else zeile_start + 1
            zeile_end = zutaten_text.find('\n', erste_pos)
            zeile_end = len(zutaten_text) if zeile_end == -1 else zeile_end
            fundstelle_temp = zutaten_text[zeile_start:zeile_end].strip()
            
            # SYSTEMATISCHER CHECK: Ist das ein False Positive?
            if ist_false_positive(allergie, synonym, fundstelle_temp):
                print(f"   🧹 FALSE POSITIVE gefiltert: '{synonym}' in '{fundstelle_temp[:60]}...'")
                continue  # Überspringe diesen Fund!
            
            # FILTER: Überspringe Nährwerttabellen-Kontext (z.B. "Eiweiß 14 g")
            if synonym == "eiweiß":
                # Prüfe ob das Pattern "Eiweiß X g" oder "Eiweiß X gramm" ist
                naehrwert_pattern = r'eiweiß\s*\d+[.,]?\d*\s*(g|gramm|mg|%)'
                if any(re.search(naehrwert_pattern, text_lower[m.start():m.end()+20]) for m in matches):
                    continue  # Skip - das ist die Nährwerttabelle
            
            # Prüfe JEDE Position auf Spurenhinweise
            # Wenn IRGENDEINE Position eine Spur ist, ist das GANZE eine Spur
            ist_spur = False
            
            for match in matches:
                pos = match.start()
                # Kontext: ±150 Zeichen um die Fundstelle
                kontext_start = max(0, pos - 150)
                kontext_end = min(len(text_lower), pos + len(synonym) + 150)
                kontext = text_lower[kontext_start:kontext_end]
                
                # Wenn IRGENDWO im Kontext eine Spurenphrase ist → ist_spur = True
                if any(p in kontext for p in SPUREN_PHRASEN):
                    ist_spur = True
                    break  # Wir wissen jetzt, es ist eine Spur
            
            # Fundstelle wurde bereits oben für False-Positive-Check extrahiert
            fundstelle = fundstelle_temp if fundstelle_temp else zutaten_text[:100].strip() + "..."
            
            # Gefunden! Sammle diesen Fund
            allergen_funde.append({
                "allergie":   allergie,
                "synonym":    synonym,
                "fundstelle": fundstelle,
                "ist_spur":   ist_spur,
                "ersatz":     ersatz_fuer(synonym),
            })
        
        # Wähle den BESTEN Fund für dieses Allergen:
        # Priorität 1: Direkter Fund (ist_spur=False)
        # Priorität 2: Spurenhinweis (ist_spur=True)
        if allergen_funde:
            # Sortiere: Direkte Funde zuerst, dann Spuren
            allergen_funde.sort(key=lambda f: f["ist_spur"])
            bester_fund = allergen_funde[0]
            
            funde.append(bester_fund)
            gefundene_allergene.add(allergie)
    
    return funde
