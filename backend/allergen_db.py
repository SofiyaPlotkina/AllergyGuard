"""Database access layer for allergen data""" # Claude Unterstützung in dieser Datei markieren!

import sqlite3
from typing import List, Dict
import logging

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# In-Memory Cache für Performance
_SYNONYM_CACHE: Dict[str, List[str]] = {}
_REPLACEMENT_CACHE: Dict[str, List[str]] = {}
_OFF_TAG_MAP_CACHE: Dict[str, str] = {}


def load_synonyms_into_cache():
    """Load all synonyms from DB into memory cache (called once at startup)"""
    global _SYNONYM_CACHE
    
    # Wenn schon befüllt, nichts machen
    if _SYNONYM_CACHE:
        return  
    
    logger.info("Loading allergen synonyms from database into cache...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT allergen, synonym FROM allergen_synonyms")
        
        for allergen, synonym in cursor.fetchall():
            if allergen not in _SYNONYM_CACHE:
                _SYNONYM_CACHE[allergen] = []
            _SYNONYM_CACHE[allergen].append(synonym)
        
        total_allergens = len(_SYNONYM_CACHE)
        total_synonyms = sum(len(v) for v in _SYNONYM_CACHE.values())
        logger.info(f"[OK] Loaded {total_allergens} allergens with {total_synonyms} synonyms")
    
    except sqlite3.OperationalError as e:
        logger.warning(f"Could not load synonyms from database: {e}")
        logger.warning("Database might not be migrated yet. Run migrate_allergens.py first!")
    
    finally:
        conn.close()


def get_synonyms_for_allergen(allergen: str) -> List[str]:
    """Get all synonyms for a specific allergen"""
    if not _SYNONYM_CACHE:
        load_synonyms_into_cache()
    
    key = allergen.lower().strip()
    return _SYNONYM_CACHE.get(key, [key])


def get_all_allergen_synonyms() -> Dict[str, List[str]]:
    """Get all allergen synonyms as dict (compatible with old code)"""
    if not _SYNONYM_CACHE:
        load_synonyms_into_cache()
    
    return _SYNONYM_CACHE


def get_replacement_for_term(term: str) -> List[str]:
    """Get replacement suggestions for an allergen term"""
    global _REPLACEMENT_CACHE
    
    # Lazy load replacements --> nur wenn gebraucht!!
    if not _REPLACEMENT_CACHE:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT allergen_term, replacement_de FROM allergen_replacements")
            
            for allergen_term, replacement_de in cursor.fetchall():
                _REPLACEMENT_CACHE[allergen_term] = replacement_de.split(", ")
            
            logger.info(f"[OK] Loaded {len(_REPLACEMENT_CACHE)} replacement suggestions")
        
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not load replacements from database: {e}")
        
        finally:
            conn.close()
    
    # Exact match
    term_lower = term.lower().strip()
    if term_lower in _REPLACEMENT_CACHE:
        return _REPLACEMENT_CACHE[term_lower]
    
    # Partial match (like old code)
    matches = [(k, v) for k, v in _REPLACEMENT_CACHE.items() if k in term_lower or term_lower in k]
    if matches:
        best = max(matches, key=lambda x: len(x[0]))
        return best[1]
    
    return []


def get_off_tag_map() -> Dict[str, str]:
    """OpenFoodFacts-Tag (z.B. 'en:peanuts') -> unser Allergie-Name (z.B. 'erdnuss')"""
    global _OFF_TAG_MAP_CACHE

    if not _OFF_TAG_MAP_CACHE:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT off_tag, allergen FROM off_tag_map")
            for off_tag, allergen in cursor.fetchall():
                _OFF_TAG_MAP_CACHE[off_tag] = allergen

            logger.info(f"[OK] Loaded {len(_OFF_TAG_MAP_CACHE)} OFF-Tag-Zuordnungen")

        except sqlite3.OperationalError as e:
            logger.warning(f"Could not load OFF tag map from database: {e}")

        finally:
            conn.close()

    return _OFF_TAG_MAP_CACHE


def add_synonym_to_db(allergen: str, synonym: str, language: str = "de"):
    """Add a new synonym to the database (e.g., from learning)"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO allergen_synonyms (allergen, synonym, language)
            VALUES (?, ?, ?)
        """, (allergen.lower(), synonym.lower(), language))
        conn.commit()
        
        # Update cache
        if allergen not in _SYNONYM_CACHE:
            _SYNONYM_CACHE[allergen] = []
        if synonym not in _SYNONYM_CACHE[allergen]:
            _SYNONYM_CACHE[allergen].append(synonym)
        
        logger.info(f"[OK] Added new synonym: {synonym} -> {allergen}")
        return True
    
    except Exception as e:
        logger.error(f"[ERROR] Failed to add synonym: {e}")
        return False
    
    finally:
        conn.close()
