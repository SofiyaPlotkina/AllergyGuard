"""Synonym matching functionality for allergen detection."""

import re
import logging

from allergen_db import get_all_allergen_synonyms, get_replacement_for_term
from config import SPUREN_PHRASEN, WORTGRENZE_SYNONYME
from text_filter import extrahiere_zutaten_sektion
from filters import ist_false_positive

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
                "ersatz":     get_replacement_for_term(synonym),
            })
        
        # Sortiert "direkte" Funde vs Spuren, danach bei Synonymen nach Länge (z.B. Magermilch = spezifischer als Milch)
        if allergen_funde:
            dedupliziert = {}
            for fund in allergen_funde:
                key = fund["fundstelle"][:50] 
        
                if key not in dedupliziert or len(fund["synonym"]) > len(dedupliziert[key]["synonym"]):
                    dedupliziert[key] = fund
    
            beste_funde = list(dedupliziert.values())
            beste_funde.sort(key=lambda f: (f["ist_spur"], -len(f["synonym"])))
    
            funde.append(beste_funde[0])
            gefundene_allergene.add(allergie)
    
    return funde
