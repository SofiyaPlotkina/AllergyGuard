"""Post-Processing Filter für ambige Ollama-Funde."""

import re


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
    Filtert Ollama-Funde: Entfernt 'eiweiß' wenn es im Protein-Kontext steht.
    
    Returns:
        Gefilterte Funde-Liste
    """
    gefiltert = []
    
    for fund in funde:
        synonym = fund.get("synonym", "").lower()
        allergie = fund.get("allergie", "").lower()
        fundstelle = fund.get("fundstelle", "").lower()
        
        # WICHTIG: "Milcheiweiß" etc. sind NIEMALS Ei-Allergene!
        if allergie == "ei":
            # Check 1: Ist das Synonym selbst ein zusammengesetztes Wort?
            ist_zusammengesetzt = False
            for zusammengesetzt in ZUSAMMENGESETZTE_PROTEIN_WOERTER:
                # Nur im SYNONYM und FUNDSTELLE prüfen, NICHT im gesamten Text!
                if zusammengesetzt in synonym or zusammengesetzt in fundstelle:
                    print(f"   ❌ GEFILTERT: '{synonym}' in '{fundstelle[:60]}...' enthält '{zusammengesetzt}' → KEIN Ei!")
                    ist_zusammengesetzt = True
                    break
            
            if ist_zusammengesetzt:
                continue  # Überspringe diesen Fund
            
            # Check 2: Ist es "eiweiß" im Protein-Kontext (Produktbeschreibung)?
            if synonym == "eiweiß":
                if ist_protein_kontext(original_text, fundstelle):
                    print(f"   ❌ GEFILTERT: '{synonym}' ist Protein, kein Ei-Allergen")
                    continue  # Überspringe
        
        # Behalte alle anderen Funde
        gefiltert.append(fund)
    
    return gefiltert
