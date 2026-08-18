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


def _ergaenze_fehlende_doppelpunkte(text: str) -> tuple[str, set[int]]:
    """
    Erkennt Zeilen, die nur aus einem Überschriftswort ohne Doppelpunkt bestehen
    (z.B. "Zutaten" als eigene Zeile), und ergänzt den Doppelpunkt - damit die
    normale Marker-Erkennung unten das trotzdem als Abschnittsstart erkennt.

    Gibt zusätzlich die Zeichen-Positionen zurück, an denen ein Doppelpunkt neu
    ergänzt wurde (= reine Widget-Überschrift, kein natürlich vorkommender
    Marker) - relevant, damit sich wiederholende ECHTE Marker im Text (z.B.
    mehrere "Kann Spuren enthalten von ..."-Sätze, einer pro Allergen) nicht
    fälschlich als Überschrift-Duplikat behandelt werden.
    """
    zeilen = text.split("\n")
    synthetische_positionen: set[int] = set()
    cursor = 0
    for i, zeile in enumerate(zeilen):
        gestrippt = zeile.strip()
        if gestrippt.lower() in _ALLEINSTEHENDE_UEBERSCHRIFTEN:
            synthetische_positionen.add(cursor + zeile.find(gestrippt))
            zeilen[i] = zeile.rstrip() + ":"
        cursor += len(zeilen[i]) + 1  # +1 für den Zeilenumbruch beim Wieder-Zusammenfügen
    return "\n".join(zeilen), synthetische_positionen


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
    text, ueberschrift_positionen = _ergaenze_fehlende_doppelpunkte(text)
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
        # (bewusst NUR mit Doppelpunkt/als Phrase, nicht das bloße Wort "allergen" -
        # das würde bei JEDER Erwähnung im Fließtext eine neue Sektion aufreißen,
        # die dann bis zum nächsten Marker reicht und dabei auch Marketing-Text
        # zwischen zwei Markern mit einschließt)
        "allergene:", "allergens:",
        "kann spuren enthalten", "may contain traces",
        "spuren von", "traces of",
        "allergen information", "allergie-hinweis",
        "hergestellt in einem betrieb", "in derselben anlage",
    ]

    # Diese Marker leiten typischerweise EINEN kurzen Satz ein (nicht eine lange
    # kommagetrennte Liste wie "Zutaten:"). Deshalb wird ihr Abschnitt zusätzlich
    # am ersten Satzende gekappt - sonst kann bis zum nächsten (weit entfernten)
    # Marker auch dazwischenliegender Marketing-Text mit erfasst werden.
    KURZE_AUSSAGE_MARKER = {
        "allergene:", "allergens:",
        "kann spuren enthalten", "may contain traces",
        "spuren von", "traces of",
        "allergen information", "allergie-hinweis",
        "hergestellt in einem betrieb", "in derselben anlage",
    }

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
            ende_marker = None

            # Suche nächsten Abschnitts-Marker (egal ob relevant oder nicht)
            for end_marker in relevante_marker + ignoriere_marker:
                next_pos = text_lower.find(end_marker, pos + len(marker))
                if next_pos != -1 and next_pos < ende:
                    ende = next_pos
                    ende_marker = end_marker

            # Manche Seiten zeigen denselben Marker zweimal: einmal als reine
            # Widget-Überschrift ("Zutaten" ganz oben, künstlich mit Doppelpunkt
            # versehen), einmal als echter Listen-Start weiter unten ("Zutaten:
            # Mehl, Zucker, ..."). NUR wenn DIESES Vorkommen eine solche künstlich
            # erzeugte Überschrift ist UND bis zu einem identischen Marker läuft,
            # wird es übersprungen (das zweite, echte Vorkommen liefert den
            # Inhalt sowieso). Natürlich wiederholte Marker im Originaltext (z.B.
            # mehrere "Kann Spuren enthalten von ..."-Sätze, einer pro Allergen)
            # bleiben davon unberührt - jeder ist ein eigener, echter Fund.
            if ende_marker == marker and pos in ueberschrift_positionen:
                pos += 1
                continue

            # Bei kurzen Aussage-Markern: zusätzlich am ersten Satzende kappen,
            # damit nicht auch noch der nächste (unabhängige) Satz mit reinrutscht
            if marker in KURZE_AUSSAGE_MARKER:
                satzende = re.search(r'[.!?](?=\s+[A-ZÄÖÜ]|\s*$)', text[pos:ende])
                if satzende:
                    ende = pos + satzende.end()

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
