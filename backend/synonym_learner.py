"""Dynamisches Synonym-Learning-System für verteilte Architektur."""

import datetime
import logging
from database import db

logger = logging.getLogger(__name__)


def hole_gelernte_synonyme(allergen: str) -> list[str]:
    """
    Holt alle gelernten Synonyme für ein Allergen aus der DB.
    Sortiert nach Confidence (häufig genutzte zuerst).
    """
    conn = db()
    rows = conn.execute(
        'SELECT synonym FROM learned_synonyms WHERE allergen=? AND confidence >= 2 ORDER BY confidence DESC',
        (allergen.lower(),)
    ).fetchall()
    conn.close()
    return [r['synonym'] for r in rows]


def lerne_synonym(allergen: str, synonym: str, quelle: str):
    """
    Speichert ein neues Synonym in der Lern-DB.
    
    Args:
        allergen: z.B. "Gluten"
        synonym: z.B. "glutenhaltige Cerealien"
        quelle: "ollama", "openfoodfacts", "manual"
    """
    if not synonym or len(synonym) < 3 or len(synonym) > 100:
        return  # Zu kurz/lang
    
    allergen_lower = allergen.lower()
    synonym_lower = synonym.lower().strip()
    now = datetime.datetime.now().isoformat()
    
    conn = db()
    
    # Prüfe ob Synonym bereits existiert
    existing = conn.execute(
        'SELECT id, confidence FROM learned_synonyms WHERE allergen=? AND synonym=?',
        (allergen_lower, synonym_lower)
    ).fetchone()
    
    if existing:
        # Erhöhe Confidence (je öfter gefunden, desto vertrauenswürdiger)
        new_confidence = existing['confidence'] + 1
        conn.execute(
            'UPDATE learned_synonyms SET confidence=?, last_seen=?, quelle=? WHERE id=?',
            (new_confidence, now, quelle, existing['id'])
        )
        logger.info(f"Synonym learned (confidence {new_confidence}): '{synonym_lower}' -> {allergen}")
    else:
        # New synonym
        conn.execute(
            'INSERT INTO learned_synonyms (allergen, synonym, quelle, first_seen, last_seen) VALUES (?,?,?,?,?)',
            (allergen_lower, synonym_lower, quelle, now, now)
        )
        logger.info(f"New synonym learned: '{synonym_lower}' -> {allergen} (via {quelle})")
    
    conn.commit()
    conn.close()


def lerne_von_ollama_funden(funde: list[dict]):
    """
    Extrahiert neue Synonyme aus Ollama-Funden und speichert sie.
    """
    for fund in funde:
        allergen = fund.get("allergie")
        synonym = fund.get("synonym")
        if allergen and synonym:
            lerne_synonym(allergen, synonym, "ollama")


def lerne_von_off_ingredients(produkt: dict, allergen: str):
    """
    Extrahiert Synonyme aus OpenFoodFacts ingredients_text.
    Beispiel: "Zutaten: WEIZENMEHL, Zucker..." → lerne "weizenmehl" für Gluten
    """
    ingredients = produkt.get("ingredients_text", "")
    if not ingredients:
        return
    
    # Extrahiere Wörter in Großbuchstaben (OFF markiert Allergene so)
    import re
    allergen_words = re.findall(r'\b[A-ZÄÖÜ]{4,}\b', ingredients)
    
    for word in allergen_words:
        if len(word) > 3:  # Mindestlänge
            lerne_synonym(allergen, word, "openfoodfacts")


def statistik_learned_synonyms() -> dict:
    """Gibt Statistiken über gelernte Synonyme zurück."""
    conn = db()
    stats = {
        "gesamt": conn.execute('SELECT COUNT(*) as c FROM learned_synonyms').fetchone()['c'],
        "confident": conn.execute('SELECT COUNT(*) as c FROM learned_synonyms WHERE confidence >= 3').fetchone()['c'],
        "pro_allergen": {}
    }
    
    rows = conn.execute(
        'SELECT allergen, COUNT(*) as cnt FROM learned_synonyms GROUP BY allergen'
    ).fetchall()
    
    for row in rows:
        stats["pro_allergen"][row['allergen']] = row['cnt']
    
    conn.close()
    return stats
