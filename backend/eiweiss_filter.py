"""Post-Processing Filter für ambige Ollama-Funde."""

import re


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEMATISCHE FALSE-POSITIVE FILTER (für KI-Funde)
# ═══════════════════════════════════════════════════════════════════════════

# Zusammengesetzte Wörter: [PRÄFIX]eiweiß = PROTEIN von [PRÄFIX], KEIN Ei!
ZUSAMMENGESETZTE_PROTEIN_WOERTER = [
    "milcheiweiß", "milcheiweiss",         # Milchprotein (Milchallergie, nicht Ei!)
    "molkeneiweiß", "molkeneiweiss",       # Molkenprotein (Milchallergie, nicht Ei!)
    "sojaeiweiss", "sojaeiweiß",           # Sojaprotein (Sojaallergie, nicht Ei!)
    "pflanzeneiweiss", "pflanzeneiweiß",   # Pflanzenprotein (kein Ei!)
    "erbseneiweiss", "erbseneiweiß",       # Erbsenprotein (kein Ei!)
    "reiseiweiss", "reiseiweiß",           # Reisprotein (kein Ei!)
    "hanfeiweiss", "hanfeiweiß",           # Hanfprotein (kein Ei!)
    "weizeneiweiss", "weizeneiweiß",       # Weizenprotein/Gluten (Glutenallergie, nicht Ei!)
]

# PFLANZENMILCH = KEINE Milch! (laktosefrei, vegan)
PFLANZENMILCH_BEGRIFFE = [
    "mandelmilch", "hafermilch", "sojamilch", "reismilch", "kokosmilch",
    "cashewmilch", "haselnussmilch", "macadamiamilch", "dinkelmilch",
    "hirsemilch", "quinoamilch", "erbsenmilch", "lupinenmilch",
    "hanfmilch", "tigernussmilch", "sesammilch",
    # Englisch
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
]

# VEGANE/PFLANZLICHE BUTTER = KEINE Milch! (laktosefrei, vegan)
VEGANE_BUTTER_BEGRIFFE = [
    "vegane butter", "pflanzliche butter", "pflanzen butter",
    "alsan", "rama", "becel", "flora",  # Bekannte Marken
    "margarine",  # Oft pflanzlich
    "kokosfett", "kokosöl", "palmfett",  # Pflanzliche Fett-Alternativen
    "pflanzenfett", "pflanzliches fett",
    # Englisch
    "vegan butter", "plant butter", "plant-based butter",
]

# PSEUDO-GETREIDE = KEIN Gluten!
GLUTENFREIE_PSEUDOGETREIDE = [
    "buchweizen", "buckwheat",  # KEIN Weizen! Kein Gluten!
    "amaranth", "amarant", "quinoa", "hirse", "teff",
]

PROTEIN_KONTEXT_BEGRIFFE = [
    # Nährwertangaben
    "protein", "g eiweiß", "% eiweiß", "eiweißgehalt", "eiweißquelle",
    "proteingehalt", "proteinquelle", "proteinriegel", "proteinshake",
    
    # Produktbeschreibungen
    "reich an eiweiß", "hoher eiweißgehalt", "mit eiweiß", "riegel mit eiweiß",
    "viel eiweiß", "extra protein", "high protein",
    
    # Nährwerttabelle
    "nährwert", "je 100", "pro portion", "enthält", "davon",
    "kalorien", "kohlenhydrate", "fett", "ballaststoffe",
    
    # Marketing
    "fitness", "sport", "muskel", "bodybuilding", "training"
]

ZUTAT_KONTEXT_BEGRIFFE = [
    "zutaten:", "ingredients:", "enthält:", "besteht aus:",
    "vollei", "eigelb", "eiklar", "hühnerei", "eiprodukt"
]


def ist_protein_kontext(text: str, fundstelle: str) -> bool:
    """
    Prüft ob 'eiweiß' in einem Protein-Kontext steht (= kein Ei-Allergen).
    
    Returns:
        True = Protein-Kontext (KEIN Allergen)
        False = Könnte echtes Ei sein (Zutatenliste)
    """
    text_lower = text.lower()
    fundstelle_lower = fundstelle.lower()
    
    # Finde Position der Fundstelle im Text
    fund_pos = text_lower.find(fundstelle_lower)
    if fund_pos == -1:
        # Fundstelle nicht gefunden → vorsichtshalber als Allergen
        return False
    
    # Extrahiere TWO Kontexte:
    # 1. ENGER Kontext VOR Fundstelle (max 30 Zeichen) + Fundstelle selbst für "Zutaten:" Check
    # 2. BREITER Kontext um Fundstelle (±50 Zeichen) für "Protein" Check
    kontext_vor = text_lower[max(0, fund_pos - 30):fund_pos + len(fundstelle_lower)]
    kontext_breit = text_lower[max(0, fund_pos - 50):min(len(text_lower), fund_pos + len(fundstelle_lower) + 50)]
    
    # WICHTIG: "Zutaten:" muss in/vor der Fundstelle stehen
    for begriff in ZUTAT_KONTEXT_BEGRIFFE:
        if begriff in kontext_vor:
            print(f"   🔍 'eiweiß' in '{begriff}' → ECHTES Ei!")
            return False  # Ist echtes Ei, nicht Protein!
    
    # Prüfe auf Protein-Kontext im breiteren Umfeld
    for begriff in PROTEIN_KONTEXT_BEGRIFFE:
        if begriff in kontext_breit:
            print(f"   🔍 'eiweiß' + '{begriff}' → PROTEIN, kein Ei!")
            return True
    
    # Unsicher → vorsichtshalber als Protein behandeln (false positive vermeiden)
    print(f"   🔍 'eiweiß' ohne klaren Kontext → default: PROTEIN")
    return True


def filtere_eiweiss_funde(funde: list[dict], original_text: str) -> list[dict]:
    """
    SYSTEMATISCHER Filter für KI-Funde: Entfernt False Positives.
    
    - Pflanzenmilch (Mandelmilch, Hafermilch) → KEINE Milch!
    - Pseudo-Getreide (Buchweizen) → KEIN Gluten!
    - Pflanzenprotein (Sojaeiweiß) → KEIN Ei!
    
    Returns:
        Gefilterte Funde-Liste
    """
    gefiltert = []
    
    for fund in funde:
        synonym = fund.get("synonym", "").lower()
        allergie = fund.get("allergie", "").lower()
        fundstelle = fund.get("fundstelle", "").lower()
        
        soll_filtern = False
        filter_grund = ""
        
        # ═════════════════════════════════════════════════════════════════
        # FILTER 1: PFLANZENMILCH + VEGANE BUTTER
        # ═════════════════════════════════════════════════════════════════
        if allergie in ["milch", "milk", "lactose", "laktose", "butter"]:
            # Check Pflanzenmilch
            for pflanzenmilch in PFLANZENMILCH_BEGRIFFE:
                if pflanzenmilch in synonym or pflanzenmilch in fundstelle:
                    soll_filtern = True
                    filter_grund = f"Pflanzenmilch '{pflanzenmilch}' → KEINE Milch!"
                    break
            
            # Check vegane/pflanzliche Butter
            if not soll_filtern:
                for vegane_butter in VEGANE_BUTTER_BEGRIFFE:
                    if vegane_butter in synonym or vegane_butter in fundstelle:
                        soll_filtern = True
                        filter_grund = f"Vegane Butter '{vegane_butter}' → KEINE Milch!"
                        break
                    break
        
        # ═════════════════════════════════════════════════════════════════
        # FILTER 2: PSEUDO-GETREIDE (buchweizen, quinoa, amaranth)
        # ═════════════════════════════════════════════════════════════════
        if allergie in ["gluten", "weizen", "wheat"]:
            for pseudo in GLUTENFREIE_PSEUDOGETREIDE:
                if pseudo in synonym or pseudo in fundstelle:
                    soll_filtern = True
                    filter_grund = f"Pseudo-Getreide '{pseudo}' → KEIN Gluten!"
                    break
        
        # ═════════════════════════════════════════════════════════════════
        # FILTER 3: PFLANZENPROTEIN (sojaeiweiß, erbsenprotein)
        # ═════════════════════════════════════════════════════════════════
        if allergie == "ei":
            # Check 3a: Zusammengesetzte Protein-Wörter
            for zusammengesetzt in ZUSAMMENGESETZTE_PROTEIN_WOERTER:
                if zusammengesetzt in synonym or zusammengesetzt in fundstelle:
                    soll_filtern = True
                    filter_grund = f"Pflanzenprotein '{zusammengesetzt}' → KEIN Ei!"
                    break
            
            # Check 3b: "eiweiß" im Protein-Kontext (Produktbeschreibung)
            if not soll_filtern and synonym == "eiweiß":
                if ist_protein_kontext(original_text, fundstelle):
                    soll_filtern = True
                    filter_grund = "Eiweiß in Protein-Kontext → KEIN Ei!"
        
        # ═════════════════════════════════════════════════════════════════
        # ENTSCHEIDUNG: Filtern oder behalten?
        # ═════════════════════════════════════════════════════════════════
        if soll_filtern:
            print(f"   ❌ GEFILTERT: '{synonym}' in '{fundstelle[:60]}...' → {filter_grund}")
            continue  # Überspringe diesen Fund
        
        # Behalte diesen Fund
        gefiltert.append(fund)
    
    return gefiltert
