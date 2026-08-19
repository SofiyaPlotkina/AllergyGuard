"""Text filtering to extract only ingredient sections from product descriptions."""

import re
import logging

logger = logging.getLogger(__name__)

# Wörter, die auf manchen Rezeptseiten als eigene Überschrift OHNE Doppelpunkt
# auftauchen (z.B. "Zutaten" als Widget-Titel, gefolgt von Backform-Einstellungen
# und erst danach der eigentlichen Liste)
_ALLEINSTEHENDE_UEBERSCHRIFTEN = {
    "zutaten", "ingredients", "inhaltsstoffe", "zusammensetzung",
    "allergene", "allergens", "składniki", "ingrediënten", "ingrédients",
    "ingredientes", "ingredienti",
}


def _ergaenze_fehlende_doppelpunkte(text: str) -> str:
    """
    Erkennt Zeilen, die nur aus einem Überschriftswort ohne Doppelpunkt bestehen
    (z.B. "Zutaten" als eigene Zeile), und ergänzt den Doppelpunkt - damit die
    normale Marker-Erkennung unten das trotzdem als Abschnittsstart erkennt.
    """
    zeilen = text.split("\n")
    for i, zeile in enumerate(zeilen):
        if zeile.strip().lower() in _ALLEINSTEHENDE_UEBERSCHRIFTEN:
            zeilen[i] = zeile.rstrip() + ":"
    return "\n".join(zeilen)


def extrahiere_zutaten_sektion(text: str) -> str:
    """
    Extrahiert RELEVANTE Sektionen: Zutaten UND Allergene UND Spurenhinweise.
    
    KRITISCH: Muss flexibel sein für verschiedene Website-Strukturen!
    
    ANALYSIERE:
    - Zutaten/Ingredients
    - Allergene/Allergen information
    - Spurenhinweise/Traces
    - "Kann enthalten von..."
    
    IGNORIERE:
    - Verwendungshinweise ("Ideal auf Brot", "Perfekt für...")
    - Marketing ("Lecker", "Genießen Sie...")
    - Detaillierte Nährwerttabellen (nur die Tabelle, nicht die Header)
    
    Returns:
        - Relevante Sektionen kombiniert
        - Original text wenn keine klaren Sektionen (sicherer als nichts zu finden)
    """
    text = _ergaenze_fehlende_doppelpunkte(text)
    text_lower = text.lower()
    
    # ══════════════════════════════════════════════════════════════════════
    # MARKER die RELEVANTE Sektionen einleiten
    # ══════════════════════════════════════════════════════════════════════
    relevante_marker = [
        # Zutaten
        "zutaten:", "ingredients:", "inhaltsstoffe:", "zusammensetzung:",
        "besteht aus:", "enthält:",
        "składniki:",  # Polnisch
        "ingrediënten:",  # Niederländisch  
        "ingrédients:",  # Französisch
        "ingredientes:",  # Spanisch
        "ingredienti:",  # Italienisch
        
        # Allergene - SEHR WICHTIG!
        "allergene:", "allergen", "allergens:",
        "kann spuren enthalten", "may contain traces",
        "spuren von", "traces of",
        "allergen information", "allergie-hinweis",
        "hergestellt in einem betrieb", "in derselben anlage",
    ]
    
    # ══════════════════════════════════════════════════════════════════════
    # MARKER die zu IGNORIERENDE Bereiche einleiten
    # ══════════════════════════════════════════════════════════════════════
    ignoriere_marker = [
        # Verwendungshinweise
        "verwendung:", "anwendung:", "zubereitung:",
        "verzehrempfehlung:", "dosierung:",
        "ideal auf", "perfekt für", "eignet sich",
        "gebrauchsanweisung:",
        
        # Marketing
        "produktbeschreibung:", "beschreibung:",
        "highlights:", "besonderheiten:",
        
        # Lagerung
        "aufbewahrung", "lagerung", "storage",
        "haltbarkeit", "mindestens haltbar",
        
        # Detaillierte Nährwerttabellen (aber nicht "Nährwerte:" Header!)
        "brennwert", "kalorien", "energie pro",
        "kohlenhydrate", "davon zucker",
        "fett:", "davon gesättigt",
        "ballaststoffe", "natrium",
    ]
    
    # ══════════════════════════════════════════════════════════════════════
    # STRATEGIE: Extrahiere ALLE relevanten Sektionen
    # ══════════════════════════════════════════════════════════════════════
    
    relevante_abschnitte = []
    
    # Finde alle relevanten Start-Positionen
    for marker in relevante_marker:
        pos = 0
        while True:
            pos = text_lower.find(marker, pos)
            if pos == -1:
                break
            
            # Finde Ende dieses Abschnitts
            ende = len(text)
            
            # Suche nächsten Abschnitts-Marker (egal ob relevant oder nicht)
            for end_marker in relevante_marker + ignoriere_marker:
                next_pos = text_lower.find(end_marker, pos + len(marker))
                if next_pos != -1 and next_pos < ende:
                    ende = next_pos
            
            # Extrahiere Abschnitt
            abschnitt = text[pos:ende].strip()
            
            # Überprüfe ob dieser Abschnitt ignoriert werden soll
            abschnitt_lower = abschnitt.lower()
            sollte_ignorieren = False
            
            for ignore in ignoriere_marker:
                if ignore in abschnitt_lower[:100]:  # Nur Anfang prüfen
                    sollte_ignorieren = True
                    break
            
            if not sollte_ignorieren and len(abschnitt) >= 20:
                relevante_abschnitte.append(abschnitt)
            
            pos += 1
    
    # ══════════════════════════════════════════════════════════════════════
    # FALLBACK: Wenn nichts gefunden → IM ZWEIFEL ALLES ANALYSIEREN!
    # ══════════════════════════════════════════════════════════════════════
    if not relevante_abschnitte:
        # Prüfe auf Rezept-Muster: Mengenangaben wie "200 g", "4 Eier", etc.
        hat_mengenangaben = bool(re.search(r'\d+\s*(g|ml|tl|el|prise|stück|eier?)\b', text_lower))
        
        # KRITISCH FÜR ALLERGIKER: Im Zweifel ALLES analysieren statt NICHTS!
        # Lieber False-Positive als False-Negative (lebensbedrohlich!)
        if len(text) < 3000 or hat_mengenangaben:
            logger.warning(f"[text_filter] No markers, analyzing full text ({len(text)} chars, recipe pattern: {hat_mengenangaben})")
            return text
        
        # Nur bei SEHR langen Texten (>3000 chars) ohne jegliche Marker: wahrscheinlich kein Produkt/Rezept
        logger.warning("[text_filter] Very long text without markers - analyze NOTHING")
        return ""
    
    # Combine all relevant sections
    kombiniert = "\n\n".join(relevante_abschnitte)
    logger.info(f"[text_filter] {len(relevante_abschnitte)} sections extracted ({len(kombiniert)} chars)")
    
    return kombiniert
