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
                # Barcode-Treffer sind eindeutig -> ohne Vorbehalt in die lokale Tabelle
                off_produkt_cachen(result, quelle="barcode")
                return result

        except requests.RequestException as e:
            logger.warning(f"OpenFoodFacts API request failed for barcode {query}: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OpenFoodFacts response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error querying OpenFoodFacts: {e}")

        return None

    # Unverifizierte OFF-Volltextsuche. Nicht direkt vertrauen (siehe
    # off_produkt_im_text_finden) - der erste Treffer kann ein völlig anderes
    # Produkt sein als das gesuchte.
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 3,
        "fields": "product_name,code,allergens_tags,allergens,traces_tags,ingredients_text",
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


# ── Lokale Produkterkennung (Phase A: bekannt, Phase B: verifizierte Suche) ────

_MENGENANGABE_MUSTER = re.compile(
    r'\b\d+([.,]\d+)?\s*(g|kg|ml|l|stk|stück|pack|packung)\b', re.IGNORECASE
)
MIN_MATCH_LAENGE = 4          # zu kurze Produktnamen führen zu Falschtreffern (z.B. "Ei")
VERIFIKATIONS_SCHWELLE = 0.5  # Mindest-Wortüberlappung, damit ein Suchtreffer akzeptiert wird


def normalisiere_name(name: str) -> str:
    """Normalisiert einen Produkt-/Kandidatennamen für den Textabgleich."""
    name = name.lower()
    name = _MENGENANGABE_MUSTER.sub(' ', name)
    name = re.sub(r'[^a-zäöüß0-9\s]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def _wort_ueberlappung(a: str, b: str) -> float:
    """Jaccard-Ähnlichkeit zweier Namen auf Wortbasis (0 = nichts gemeinsam, 1 = identisch)."""
    tokens_a = set(normalisiere_name(a).split())
    tokens_b = set(normalisiere_name(b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def off_produkt_cachen(produkt: dict, quelle: str):
    """Speichert ein OFF-Produkt strukturiert in der lokalen off_products-Tabelle."""
    barcode = produkt.get("code")
    name = produkt.get("product_name")
    if not barcode or not name:
        return
    conn = db()
    conn.execute('''
        INSERT INTO off_products
            (barcode, produktname, produktname_normalisiert, allergens_tags, traces_tags, quelle)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(barcode) DO UPDATE SET
            produktname=excluded.produktname,
            produktname_normalisiert=excluded.produktname_normalisiert,
            allergens_tags=excluded.allergens_tags,
            traces_tags=excluded.traces_tags,
            quelle=excluded.quelle
    ''', (
        barcode, name, normalisiere_name(name),
        json.dumps(produkt.get("allergens_tags", [])),
        json.dumps(produkt.get("traces_tags", [])),
        quelle,
    ))
    conn.commit()
    conn.close()


def _row_zu_produkt(row: dict) -> dict:
    return {
        "code": row["barcode"],
        "product_name": row["produktname"],
        "allergens_tags": json.loads(row["allergens_tags"]),
        "traces_tags": json.loads(row["traces_tags"]),
    }


def off_lokal_suchen(text: str) -> Optional[dict]:
    """Phase A: Prüft ohne Netzwerkzugriff, ob ein bereits bekanntes OFF-Produkt im Text vorkommt."""
    text_norm = normalisiere_name(text)
    conn = db()
    rows = conn.execute('SELECT * FROM off_products').fetchall()
    conn.close()

    bester_treffer = None
    for row in rows:
        name_norm = row["produktname_normalisiert"]
        if len(name_norm) < MIN_MATCH_LAENGE:
            continue
        if re.search(r'\b' + re.escape(name_norm) + r'\b', text_norm):
            if not bester_treffer or len(name_norm) > len(bester_treffer["produktname_normalisiert"]):
                bester_treffer = row

    return _row_zu_produkt(bester_treffer) if bester_treffer else None


def extrahiere_produktnamen(text: str) -> list[str]:
    """Versucht Produktnamen oder Barcodes aus dem Freitext zu extrahieren."""
    kandidaten = []
    gesehen = set()

    # Ignoriere generische Überschriften
    IGNORIERTE_ZEILEN = {
        "produktbeschreibung", "zutaten", "allergene", "nährwerte",
        "inhaltsstoffe", "ingredients", "allergens", "nutrition",
        "beschreibung", "details", "information"
    }

    # GTIN/EAN explizit suchen (oft in "GTIN: 1234567890")
    gtin_match = re.search(r'(?:GTIN|EAN|Barcode)[:\s]+(\d{8,13})', text, re.IGNORECASE)
    if gtin_match:
        barcode = gtin_match.group(1)
        kandidaten.append(barcode)
        gesehen.add(barcode.lower())

    # Alle Barcodes (EAN-8, EAN-13) sammeln
    for barcode in re.findall(r'\b\d{8,13}\b', text):
        if barcode.lower() not in gesehen:
            kandidaten.append(barcode)
            gesehen.add(barcode.lower())

    # Produktname aus den ersten Zeilen extrahieren (skip generische Überschriften)
    for zeile in text.splitlines()[:10]:  # Erste 10 Zeilen durchsuchen
        zeile_clean = zeile.strip()
        zeile_lower = zeile_clean.lower()

        # Skip zu kurze/lange oder generische Zeilen
        if not (15 < len(zeile_clean) < 100):  # Mindestens 15 Zeichen für echte Produktnamen
            continue
        if zeile_lower in IGNORIERTE_ZEILEN:
            continue
        if any(ig in zeile_lower for ig in IGNORIERTE_ZEILEN):
            continue

        # Skip Marketing-Floskeln
        if any(floskeln in zeile_lower for floskeln in ["hoher", "niedriger", "reich an", "ohne", "mit extra"]):
            continue

        # Guter Kandidat: Zeile mit Produkt-typischen Wörtern + Marke/Geschmack
        if any(keyword in zeile_lower for keyword in ["riegel", "protein", "schokolade", "müsli", "joghurt", "drink", "snack", "kekse", "chips"]):
            # Muss auch Marke/Geschmack enthalten (nicht nur "Proteinriegel")
            if any(detail in zeile_lower for detail in ["caramel", "vanille", "schoko", "nuss", "beere", "frucht", "geschmack", "%", "sportness", "dm"]):
                if zeile_lower not in gesehen:
                    kandidaten.append(zeile_clean)
                    gesehen.add(zeile_lower)
                    break

    return kandidaten[:5]  # max 5 Versuche


def off_produkt_im_text_finden(text: str) -> Optional[dict]:
    """
    Ermittelt ein OFF-Produkt aus Freitext (z.B. einer Rezeptseite) zweistufig:

    Phase A: Abgleich gegen lokal bekannte Produkte (kein Netzwerk, kein Rateproblem).
    Phase B: Nur falls nichts bekannt ist, OFF-Volltextsuche mit aus dem Text
             extrahierten Kandidaten - ein Treffer wird aber nur akzeptiert (und in
             die lokale Tabelle aufgenommen), wenn er wirklich zum Kandidaten passt.
             Sonst wird verworfen statt ein falsches Produkt zu übernehmen.
    """
    lokal = off_lokal_suchen(text)
    if lokal:
        return lokal

    for kandidat in extrahiere_produktnamen(text):
        if re.fullmatch(r'\d{8,13}', kandidat):
            continue  # Barcodes laufen bereits über den eigenen Barcode-Pfad in main.py

        treffer = suche_off(kandidat)
        if not treffer:
            continue

        ähnlichkeit = _wort_ueberlappung(kandidat, treffer.get("product_name", ""))
        if ähnlichkeit >= VERIFIKATIONS_SCHWELLE:
            off_produkt_cachen(treffer, quelle="search_confirmed")
            return treffer

        logger.info(
            f"OFF-Suchtreffer verworfen (Wortüberlappung {ähnlichkeit:.2f} < {VERIFIKATIONS_SCHWELLE}): "
            f"'{kandidat}' -> '{treffer.get('product_name')}'"
        )

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
