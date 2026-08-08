"""Zentrale Filter-Logik für Allergen-Detection."""

import re


# ═══════════════════════════════════════════════════════════════════════════
# FILTER-KONSTANTEN (einmal definiert, überall genutzt)
# ═══════════════════════════════════════════════════════════════════════════

# Pflanzenproteine die KEIN Ei sind
PFLANZENPROTEIN_BEGRIFFE = [
    "milcheiweiß", "milcheiweiss", "molkeneiweiß", "molkeneiweiss",
    "sojaeiweiss", "sojaeiweiß", "pflanzeneiweiss", "pflanzeneiweiß",
    "erbseneiweiss", "erbseneiweiß", "reiseiweiss", "reiseiweiß",
    "hanfeiweiss", "hanfeiweiß", "weizeneiweiss", "weizeneiweiß",
]

# Pflanzenmilch die KEINE Milch ist
PFLANZENMILCH_BEGRIFFE = [
    "mandelmilch", "hafermilch", "sojamilch", "reismilch", "kokosmilch",
    "cashewmilch", "haselnussmilch", "macadamiamilch", "dinkelmilch",
    "mandeldrink", "haferdrink", "sojadrink", "reisdrink", "kokosdrink",
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
]

# Vegane Butter die KEINE Milch ist
VEGANE_BUTTER_BEGRIFFE = [
    "vegane butter", "pflanzliche butter", "pflanzen butter",
    "alsan", "rama", "becel", "flora", "margarine",
    "kokosfett", "kokosöl", "palmfett", "pflanzenfett",
    "vegan butter", "plant butter", "plant-based butter",
]

# Pseudo-Getreide das KEIN Gluten enthält
GLUTENFREIE_PSEUDOGETREIDE = [
    "buchweizen", "buckwheat", "amaranth", "amarant", 
    "quinoa", "hirse", "teff",
]

# Pflanzliche Basen
NUSS_UND_PFLANZEN_BASIS = [
    "mandel", "hasel", "cashew", "walnuss", "erdnuss", "macadamia",
    "sesam", "sonnenblumen", "kürbiskern", "leinsamen", "chia",
    "soja", "erbse", "lupine", "kicher",
    "hafer", "reis", "kokos", "dinkel", "hirse", "quinoa",
]

PFLANZENBASIS_MARKER = [
    "auf basis von", "basis von", "basis:", "hergestellt aus",
    "made from", "based on", "aus",
]

# Kontext-Marker
VEGAN_MARKER = [
    "vegan", "vegane", "veganer", "veganes", "veganen",
    "pflanzlich", "pflanzliche", "pflanzlicher", "pflanzliches",
    "plant-based", "plant based",
]

GLUTENFREI_MARKER = [
    "glutenfrei", "glutenfreie", "glutenfreier", "glutenfreies",
    "gluten-frei", "gluten-free", "gluten free",
]

PROTEIN_KONTEXT_BEGRIFFE = [
    "protein", "g eiweiß", "% eiweiß", "eiweißgehalt", "eiweißquelle",
    "proteingehalt", "proteinriegel", "proteinshake",
    "reich an eiweiß", "hoher eiweißgehalt", "viel eiweiß",
    "nährwert", "je 100", "pro portion", "fitness", "sport",
]

ZUTAT_KONTEXT_BEGRIFFE = [
    "zutaten:", "ingredients:", "enthält:", "besteht aus:",
    "vollei", "eigelb", "eiklar", "hühnerei",
]


# ═══════════════════════════════════════════════════════════════════════════
# FILTER-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

def ist_false_positive(allergen: str, synonym: str, fundstelle: str) -> bool:
    """
    Prüft ob ein Fund ein False Positive ist.
    
    Returns:
        (True, grund) wenn False Positive
        (False, "") wenn echter Fund
    """
    allergen_lower = allergen.lower()
    synonym_lower = synonym.lower()
    fundstelle_lower = fundstelle.lower()
    
    # Filter 1: Pflanzenmilch
    if allergen_lower in ["milch", "milk", "lactose", "laktose"]:
        for pflanze in PFLANZENMILCH_BEGRIFFE:
            if pflanze in synonym_lower or pflanze in fundstelle_lower:
                return True
        
        for butter in VEGANE_BUTTER_BEGRIFFE:
            if butter in synonym_lower or butter in fundstelle_lower:
                return True
        
        # Check pflanzliche Basis
        for marker in PFLANZENBASIS_MARKER:
            if marker in fundstelle_lower:
                for pflanze in NUSS_UND_PFLANZEN_BASIS:
                    if pflanze in fundstelle_lower:
                        return True
    
    # Filter 2: Pseudo-Getreide
    if allergen_lower in ["gluten", "weizen", "wheat"]:
        for pseudo in GLUTENFREIE_PSEUDOGETREIDE:
            if pseudo in synonym_lower or pseudo in fundstelle_lower:
                return True
    
    # Filter 3: Pflanzenprotein
    if allergen_lower == "ei":
        for protein in PFLANZENPROTEIN_BEGRIFFE:
            if protein in synonym_lower or protein in fundstelle_lower:
                return True
    
    # Filter 4: Vegan/Glutenfrei-Kontext
    if allergen_lower in ["milch", "milk", "ei", "egg"]:
        for marker in VEGAN_MARKER:
            if marker in fundstelle_lower:
                return True
    
    if allergen_lower in ["gluten", "weizen", "wheat"]:
        for marker in GLUTENFREI_MARKER:
            if marker in fundstelle_lower:
                return True
    
    return False


def ist_protein_kontext(text: str, fundstelle: str) -> bool:
    """
    Prüft ob 'eiweiß' in Protein-Kontext steht (Nährwert vs. Zutat).
    
    Returns:
        True = Marketing/Nährwert (kein Allergen)
        False = Zutatenliste (echtes Ei)
    """
    text_lower = text.lower()
    fundstelle_lower = fundstelle.lower()
    
    fund_pos = text_lower.find(fundstelle_lower)
    if fund_pos == -1:
        return False
    
    # Enger Kontext für Zutaten-Check
    kontext_vor = text_lower[max(0, fund_pos - 30):fund_pos + len(fundstelle_lower)]
    for zutat_marker in ZUTAT_KONTEXT_BEGRIFFE:
        if zutat_marker in kontext_vor:
            return False  # Echtes Ei in Zutatenliste!
    
    # Breiter Kontext für Protein-Check
    kontext_breit = text_lower[max(0, fund_pos - 50):min(len(text_lower), fund_pos + len(fundstelle_lower) + 50)]
    for protein_marker in PROTEIN_KONTEXT_BEGRIFFE:
        if protein_marker in kontext_breit:
            return True  # Protein-Kontext!
    
    # Default: Als Protein behandeln (False Positives vermeiden)
    return True


def filtere_funde(funde: list[dict], original_text: str = "") -> list[dict]:
    """
    Zentrale Filter-Funktion für Synonym-Matching UND KI-Funde.
    
    Args:
        funde: Liste von Fund-Dicts mit {allergie, synonym, fundstelle, ...}
        original_text: Original-Text für Kontext-Analyse (optional)
    
    Returns:
        Gefilterte Liste ohne False Positives
    """
    gefiltert = []
    
    for fund in funde:
        allergie = fund.get("allergie", "")
        synonym = fund.get("synonym", "")
        fundstelle = fund.get("fundstelle", "")
        
        # Leere Fundstellen verwerfen
        if not fundstelle or not fundstelle.strip():
            print(f"   ❌ GEFILTERT: Leere Fundstelle")
            continue
        
        # Standard False-Positive-Check
        ist_fp = ist_false_positive(allergie, synonym, fundstelle)
        if ist_fp:
            print(f"   ❌ GEFILTERT: '{synonym}' → False Positive")
            continue
        
        # Spezial-Check für "eiweiß" (nur wenn original_text gegeben)
        if allergie.lower() == "ei" and synonym.lower() == "eiweiß" and original_text:
            if ist_protein_kontext(original_text, fundstelle):
                print(f"   ❌ GEFILTERT: 'eiweiß' → Protein-Kontext")
                continue
        
        # Fund ist OK
        gefiltert.append(fund)
    
    print(f"   ✅ {len(gefiltert)}/{len(funde)} Funde nach Filtern übrig")
    return gefiltert