"""Text filtering to extract only ingredient sections from product descriptions."""

import re
import logging

logger = logging.getLogger(__name__)


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
    # FALLBACK: Wenn nichts gefunden, aber Text kurz → ganzen Text nehmen
    # ══════════════════════════════════════════════════════════════════════
    if not relevante_abschnitte:
        # If text is very short (<400 chars), might be ONLY ingredients
        if len(text) < 400:
            logger.warning(f"[text_filter] No markers, but text short ({len(text)} chars) - analyze all")
            return text
        
        # Long text without markers - probably not product text
        logger.warning("[text_filter] No relevant sections found - analyze NOTHING")
        return ""
    
    # Combine all relevant sections
    kombiniert = "\n\n".join(relevante_abschnitte)
    logger.info(f"[text_filter] {len(relevante_abschnitte)} sections extracted ({len(kombiniert)} chars)")
    
    return kombiniert
