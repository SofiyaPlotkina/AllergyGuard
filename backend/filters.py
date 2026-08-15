"""Zentrale Filter-Logik für Allergen-Detection."""

import re
import logging

logger = logging.getLogger(__name__)


# FILTER-KONSTANTEN (einmal definiert, überall genutzt)

# Pflanzenproteine die KEIN Ei sind
PFLANZENPROTEIN_BEGRIFFE = [
    "sojaeiweiss", "sojaeiweiß", "pflanzeneiweiss", "pflanzeneiweiß",
    "erbseneiweiss", "erbseneiweiß", "erbsenprotein",
    "reiseiweiss", "reiseiweiß", "reisprotein",
    "hanfeiweiss", "hanfeiweiß", "hanfprotein",
    "weizeneiweiss", "weizeneiweiß", "weizenprotein",
    "lupinenprotein", "sonnenblumenprotein", "kartoffelprotein",
]

# Vanille-Produkte die KEIN Ei enthalten (trotz "ei" in "Vanilleschote")
VANILLE_BEGRIFFE = [
    "vanille", "vanilleschote", "vanilleschoten", "vanilleextrakt",
    "vanillezucker", "vanillearoma", "bourbon vanille", "vanillepaste",
    "vanilla", "vanilla pod", "vanilla pods", "vanilla extract",
    "vanilla sugar", "vanilla aroma", "vanilla paste",
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

# Kontext der anzeigt, dass ein Allergen NICHT vorhanden ist (z.B. Ersatz/Negation)
OHNE_KONTEXT_MARKER = [
    "ohne ", "statt ", "ersetzt durch", "anstelle von", "anstatt ",
    "anstatt von", "frei von", "without ", "instead of", "free from",
    "free of",
]


# ═══════════════════════════════════════════════════════════════════════════
# FILTER-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

def ist_false_positive(allergen: str, synonym: str, fundstelle: str) -> bool:
    """
    Prüft ob ein Fund ein False Positive ist.
    
    Returns:
        True wenn False Positive (Fund ignorieren)
        False wenn echter Fund (Fund behalten)
    """
    allergen_lower = allergen.lower()
    synonym_lower = synonym.lower()
    fundstelle_lower = fundstelle.lower()

    # Filter 0: Leere Fundstelle
    if not fundstelle_lower.strip():
        return True

    # Filter 0b: Negations-/Ersatz-Kontext ("ohne Ei", "statt Butter", …)
    for marker in OHNE_KONTEXT_MARKER:
        if marker in fundstelle_lower:
            return True

    # Filter 1: Pflanzenmilch / vegane Butter
    if allergen_lower in ["milch", "milk", "lactose", "laktose", "butter"]:
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
        
        # Filter 3b: Vanille (enthält "ei" aber kein Ei-Allergen)
        for vanille in VANILLE_BEGRIFFE:
            if vanille in synonym_lower or vanille in fundstelle_lower:
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
        
        # Discard empty findings
        if not fundstelle or not fundstelle.strip():
            logger.debug("Empty finding location")
            continue
        
        # Standard false-positive check
        ist_fp = ist_false_positive(allergie, synonym, fundstelle)
        if ist_fp:
            logger.debug(f"'{synonym}' is false positive")
            continue
        
        # Special check for "eiweiß" (only if original_text provided)
        if allergie.lower() == "ei" and synonym.lower() == "eiweiß" and original_text:
            if ist_protein_kontext(original_text, fundstelle):
                logger.debug("'eiweiß' is protein context")
                continue
        
        # Finding is OK
        gefiltert.append(fund)
    
    logger.info(f"{len(gefiltert)}/{len(funde)} findings remaining after filters")
    return gefiltert