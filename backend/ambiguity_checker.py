"""Context-Checking für ambige Allergen-Begriffe."""

import re

# Begriffe die MEHRDEUTIG sind und Kontext-Check brauchen
AMBIGE_SYNONYME = {
    "eiweiß": {
        "allergen": "Ei",
        "false_positive_context": [
            "protein", "eiweißgehalt", "eiweißquelle", "g protein",
            "proteinreich", "eiweiß pro", "gramm eiweiß"
        ],
        "true_positive_context": [
            "vollei", "eigelb", "eiklar", "hühnerei", "flüssigei"
        ]
    }
}


def ist_ambig(synonym: str, allergen: str) -> bool:
    """Prüft ob ein Synonym mehrdeutig ist und KI-Check braucht."""
    synonym_lower = synonym.lower().strip()
    allergen_lower = allergen.lower().strip()
    
    if synonym_lower in AMBIGE_SYNONYME:
        config = AMBIGE_SYNONYME[synonym_lower]
        return config["allergen"].lower() == allergen_lower
    
    return False


def braucht_ki_check(funde: list[dict], text: str) -> bool:
    """
    Prüft ob Funde ambig sind und KI-Validierung brauchen.
    
    Returns:
        True = KI soll nochmal prüfen
        False = Funde sind eindeutig
    """
    for fund in funde:
        synonym = fund.get("synonym", "").lower()
        allergen = fund.get("allergie", "").lower()
        
        # "eiweiß" bei Ei-Allergie ist IMMER ambig (kann Protein oder Ei bedeuten)
        if synonym == "eiweiß" and allergen == "ei":
            print(f"⚠️ AMBIG: 'eiweiß' kann Protein ODER Ei sein → KI-Check!")
            return True
        
        if synonym in AMBIGE_SYNONYME:
            config = AMBIGE_SYNONYME[synonym]
            
            # Extrahiere Kontext um das Synonym (±100 Zeichen)
            text_lower = text.lower()
            pos = text_lower.find(synonym)
            if pos == -1:
                continue
            
            kontext_start = max(0, pos - 100)
            kontext_end = min(len(text_lower), pos + len(synonym) + 100)
            kontext = text_lower[kontext_start:kontext_end]
            
            # Prüfe ob false-positive Kontext vorhanden
            for fp_phrase in config["false_positive_context"]:
                if fp_phrase in kontext:
                    print(f"⚠️ AMBIG: '{synonym}' + '{fp_phrase}' → KI-Check!")
                    return True
    
    return False
