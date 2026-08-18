"""Synonym matching functionality for allergen detection."""

import re
import logging

from allergen_db import get_all_allergen_synonyms, get_replacement_for_term
from config import SPUREN_PHRASEN, SPUREN_MUSTER, WORTGRENZE_SYNONYME
from text_filter import extrahiere_zutaten_sektion
from filters import ist_false_positive, ist_protein_kontext

logger = logging.getLogger(__name__)  


def synonyme_fuer(allergen: str) -> list[str]:
    """
    Gibt die Liste der Synonyme für ein Allergen zurück.
    Kombiniert DB-Synonyme + dynamisch gelernte.
    """
    key = allergen.lower().strip()
    synonyme = []
    
    # 1. Synonyme aus Datenbank (migriert von allergen_data.py)
    ALLERGEN_SYNONYME = get_all_allergen_synonyms()
    
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
    except ImportError:
        logger.debug("synonym_learner module not available, using only static synonyms")
    except Exception as e:
        logger.warning(f"Failed to load learned synonyms: {e}")
    
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
        logger.warning("[synonym_matcher] No ingredients section found, no matching")
        return []
    
    logger.debug(f"[synonym_matcher] Ingredients text ({len(zutaten_text)} chars): {zutaten_text[:100]}...")
    
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
            
            # SYSTEMATIC CHECK: Is this a false positive?
            if ist_false_positive(allergie, synonym, fundstelle_temp):
                logger.debug(f"FALSE POSITIVE filtered: '{synonym}' in '{fundstelle_temp[:60]}...'")
                continue  # Skip this finding!
            
            # FILTER: "Eiweiß" ist im Alltagsdeutsch meistens Protein, nicht Ei
            # (Nährwerttabelle, Proteinriegel, ...). Nur bei klarem Zutaten-Kontext
            # ("Zutaten: ... Eiweiß", "Eigelb, Eiweiß") wirklich als Ei werten.
            if synonym == "eiweiß" and ist_protein_kontext(zutaten_text, fundstelle_temp):
                logger.debug(f"'eiweiß' in Protein-Kontext gefiltert: '{fundstelle_temp[:60]}...'")
                continue
            
            # Prüfe JEDE Position auf Spurenhinweise
            # Wenn IRGENDEINE Position eine Spur ist, ist das GANZE eine Spur
            ist_spur = False

            for match in matches:
                pos = match.start()
                # Kontext = eigene Zeile (nicht ein festes ±150-Zeichen-Fenster!),
                # sonst "bleedet" der Kontext über Zeilen-/Abschnittsgrenzen hinweg
                # und eine Zutat wie "Milchpulver" wird fälschlich zur Spur, nur
                # weil ein "Kann Spuren von..."-Hinweis irgendwo in der Nähe steht.
                zeile_start = zutaten_text.rfind('\n', 0, pos)
                zeile_start = 0 if zeile_start == -1 else zeile_start + 1
                zeile_end = zutaten_text.find('\n', pos)
                zeile_end = len(zutaten_text) if zeile_end == -1 else zeile_end
                kontext = text_lower[zeile_start:zeile_end]

                # Wenn IRGENDWO im Kontext eine Spurenphrase ist → ist_spur = True
                if any(p in kontext for p in SPUREN_PHRASEN) or re.search(SPUREN_MUSTER, kontext):
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
                "ersatz":     get_replacement_for_term(synonym),
            })
        
        # Sortiert "direkte" Funde vs Spuren, danach bei Synonymen nach Länge (z.B. Magermilch = spezifischer als Milch)
        if allergen_funde:
            # Deduplizierung: Gleiche Fundstelle → längeres Synonym gewinnt
            dedupliziert = {}
            for fund in allergen_funde:
                key = fund["fundstelle"][:50] 
        
                if key not in dedupliziert or len(fund["synonym"]) > len(dedupliziert[key]["synonym"]):
                    dedupliziert[key] = fund
    
            alle_funde_list = list(dedupliziert.values())
            alle_funde_list.sort(key=lambda f: (f["ist_spur"], -len(f["synonym"])))
    
            # NEU: Füge ALLE Funde hinzu (nicht nur besten!)
            # So kann Frontend gruppiert anzeigen: [Milch] mascarpone, sahne, magerquark
            for fund in alle_funde_list:
                funde.append(fund)
            
            gefundene_allergene.add(allergie)
    
    return funde
