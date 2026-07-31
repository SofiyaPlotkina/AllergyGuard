"""Synonym matching functionality for allergen detection."""

import re

from allergen_data import ALLERGEN_SYNONYME, ersatz_fuer
from config import SPUREN_PHRASEN, WORTGRENZE_SYNONYME


def synonyme_fuer(allergen: str) -> list[str]:
    """Gibt die Liste der Synonyme für ein Allergen zurück."""
    key = allergen.lower().strip()
    if key in ALLERGEN_SYNONYME:
        return ALLERGEN_SYNONYME[key]
    for k, synonyme in ALLERGEN_SYNONYME.items():
        if k in key or key in k:
            return synonyme
    return [key]


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
    """
    funde = []
    text_lower = text.lower()
    
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
            
            # Fundstelle: Extrahiere die Zeile der ersten Position
            erste_pos = matches[0].start()
            zeile_start = text.rfind('\n', 0, erste_pos)
            zeile_start = 0 if zeile_start == -1 else zeile_start + 1
            
            zeile_end = text.find('\n', erste_pos)
            zeile_end = len(text) if zeile_end == -1 else zeile_end
            
            fundstelle = text[zeile_start:zeile_end].strip()
            if not fundstelle:
                fundstelle = text[:100].strip() + "..."
            
            # Gefunden! Sammle diesen Fund
            allergen_funde.append({
                "allergie":   allergie,
                "synonym":    synonym,
                "fundstelle": fundstelle,
                "ist_spur":   ist_spur,
                "ersatz":     ersatz_fuer(synonym),
            })
        
        # Wähle den BESTEN Fund für dieses Allergen:
        # Priorität 1: Direkter Fund (ist_spur=False)
        # Priorität 2: Spurenhinweis (ist_spur=True)
        if allergen_funde:
            # Sortiere: Direkte Funde zuerst, dann Spuren
            allergen_funde.sort(key=lambda f: f["ist_spur"])
            bester_fund = allergen_funde[0]
            
            funde.append(bester_fund)
            gefundene_allergene.add(allergie)
    
    return funde
