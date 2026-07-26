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
    """Lokales Synonym-Matching als letzter Fallback."""
    funde = []
    text_lower = text.lower()
    for allergie in user_allergien:
        synonyme = synonyme_fuer(allergie)
        for synonym in synonyme:
            if not synonym_trifft(synonym, text_lower):
                continue
            for zeile in text.splitlines():
                if synonym_trifft(synonym, zeile.lower()):
                    zeile_lower = zeile.lower()
                    ist_spur = any(p in zeile_lower for p in SPUREN_PHRASEN)
                    if not ist_spur:
                        pos = text_lower.find(synonym)
                        kontext = text_lower[max(0, pos - 150):pos + 150]
                        ist_spur = any(p in kontext for p in SPUREN_PHRASEN)
                    funde.append({
                        "allergie":   allergie,
                        "synonym":    synonym,
                        "fundstelle": zeile.strip(),
                        "ist_spur":   ist_spur,
                        "ersatz":     ersatz_fuer(synonym),
                    })
                    break
            if any(f["allergie"] == allergie for f in funde):
                break
    return funde
