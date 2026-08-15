"""OpenFoodFacts API client and allergen checking."""

import datetime
import json
import re
import requests
import logging
from typing import Optional

from allergen_data import OFF_TAG_MAP
from allergen_db import get_replacement_for_term

logger = logging.getLogger(__name__)
from config import OFF_CACHE_TTL_DAYS
from database import db


def off_cache_lesen(key: str) -> Optional[dict]:
    """Liest einen Eintrag aus dem OpenFoodFacts-Cache."""
    conn = db()
    row = conn.execute(
        'SELECT response_json, cached_at FROM off_cache WHERE query_key=?', (key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    # TTL prüfen
    cached = datetime.datetime.fromisoformat(row["cached_at"])
    if (datetime.datetime.now() - cached).days >= OFF_CACHE_TTL_DAYS:
        return None
    return json.loads(row["response_json"])


def off_cache_schreiben(key: str, data: dict):
    """Schreibt einen Eintrag in den OpenFoodFacts-Cache."""
    conn = db()
    conn.execute(
        'INSERT OR REPLACE INTO off_cache (query_key, response_json, cached_at) VALUES (?,?,?)',
        (key, json.dumps(data), datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def suche_off(query: str) -> Optional[dict]:
    """Sucht ein Produkt auf OpenFoodFacts. Gibt None zurück wenn nichts gefunden."""
    cached = off_cache_lesen(query)
    if cached is not None:
        return cached

    # Barcode-Suche
    if re.fullmatch(r'\d{8,13}', query):
        url = f"https://world.openfoodfacts.org/api/v2/product/{query}.json"
        try:
            r = requests.get(url, timeout=5,
                             headers={"User-Agent": "AllergyGuard/1.0"})
            data = r.json()
            if data.get("status") == 1:
                result = data.get("product", {})
                off_cache_schreiben(query, result)
                return result
                
        except requests.RequestException as e:
            logger.warning(f"OpenFoodFacts API request failed for barcode {query}: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OpenFoodFacts response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error querying OpenFoodFacts: {e}")
            
        return None

    # Textsuche
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 3,
        "fields": "product_name,allergens_tags,allergens,traces_tags,ingredients_text",
    }
    try:
        r = requests.get(url, params=params, timeout=6,
                         headers={"User-Agent": "AllergyGuard/1.0"})
        data = r.json()
        products = data.get("products", [])
        # Ersten Treffer mit Allergen-Daten bevorzugen
        for p in products:
            if p.get("allergens_tags") or p.get("ingredients_text"):
                off_cache_schreiben(query, p)
                return p
                
    except requests.RequestException as e:
        logger.warning(f"OpenFoodFacts search request failed for '{query}': {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse OpenFoodFacts search response: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in OpenFoodFacts search: {e}")
        
    return None


def off_allergene_pruefen(produkt: dict, user_allergien: list[str]) -> list[dict]:
    """Gleicht OFF-Allergen-Tags mit dem Nutzerprofil ab. Gibt Funde zurück."""
    funde = []
    allergen_tags    = produkt.get("allergens_tags", [])
    spuren_tags      = produkt.get("traces_tags", [])
    produkt_name     = produkt.get("product_name", "Unbekanntes Produkt")

    for allergie in user_allergien:
        # Prüfen ob ein OFF-Tag zu dieser Allergie passt
        for tag, schluessel in OFF_TAG_MAP.items():
            if schluessel != allergie.lower().strip() and schluessel not in allergie.lower():
                continue
            if tag in allergen_tags:
                syn = tag.replace("en:", "")
                funde.append({
                    "allergie":   allergie,
                    "synonym":    syn,
                    "fundstelle": f"OpenFoodFacts: {produkt_name}",
                    "ist_spur":   False,
                    "ersatz":     get_replacement_for_term(syn),
                })
                break
            if tag in spuren_tags:
                syn = tag.replace("en:", "")
                funde.append({
                    "allergie":   allergie,
                    "synonym":    syn,
                    "fundstelle": f"OpenFoodFacts (Spur): {produkt_name}",
                    "ist_spur":   True,
                    "ersatz":     get_replacement_for_term(syn),
                })
                break
    return funde
