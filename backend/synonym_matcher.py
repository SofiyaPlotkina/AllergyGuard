"""Synonym matching functionality for allergen detection."""

import re

from allergen_data import ALLERGEN_SYNONYME, ersatz_fuer
from config import SPUREN_PHRASEN, WORTGRENZE_SYNONYME
from text_filter import extrahiere_zutaten_sektion
from filters import ist_false_positive  


def synonyme_fuer(allergen: str) -> list[str]:
    """
    Gibt die Liste der Synonyme für ein Allergen zurück.
    Kombiniert statische Synonyme + dynamisch gelernte.
    """
    key = allergen.lower().strip()
    synonyme = []
    
    # 1. Statische Synonyme aus allergen_data.py
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
    except Exception:
        pass  # DB nicht verfügbar, nur statische nutzen
    
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
        print("[synonym_matcher] ⚠️  Keine Zutaten-Sektion gefunden → kein Matching")
        return []
    
    print(f"[synonym_matcher] ✅ Zutaten-Text ({len(zutaten_text)} Zeichen): {zutaten_text[:100]}...")
    
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
            
            # SYSTEMATISCHER CHECK: Ist das ein False Positive?
            if ist_false_positive(allergie, synonym, fundstelle_temp):
                print(f"   🧹 FALSE POSITIVE gefiltert: '{synonym}' in '{fundstelle_temp[:60]}...'")
                continue  # Überspringe diesen Fund!
            
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
