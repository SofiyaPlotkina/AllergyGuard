"""OpenFoodFacts API client and allergen checking."""

import datetime
import json
import re
import time
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


def _off_get(url: str, params: Optional[dict] = None, timeout: int = 6) -> Optional[dict]:
    """
    GET-Request gegen die OFF-API mit einem kurzen Retry bei transienten Fehlern.
    OFF begrenzt z.B. Suchanfragen auf 10/Minute - eine kurze Pause + ein zweiter
    Versuch reicht meistens, um einen einzelnen fehlgeschlagenen Request abzufangen.
    """
    for versuch in range(2):
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"User-Agent": "AllergyGuard/1.0"})
            return r.json()
        except requests.RequestException as e:
            logger.warning(f"OpenFoodFacts request failed ({url}): {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse OpenFoodFacts response ({url}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling OpenFoodFacts ({url}): {e}")
            break  # unerwarteter Fehler - kein Retry
        if versuch == 0:
            time.sleep(0.6)
    return None


def _ergaenze_markenname(produkt: dict) -> dict:
    """
    OFF trennt Marke ('brands') und Produktname ('product_name') in zwei Feldern,
    z.B. product_name='Wunderland Sauer', brands='Katjes'. Für Textabgleich und
    Anzeige wird aber der volle Name inkl. Marke gebraucht - sonst schlägt z.B. die
    Suche nach "Katjes" im Rezepttext fehl, obwohl OFF das Produkt korrekt gefunden hat.
    """
    name = (produkt.get("product_name") or "").strip()
    marke = (produkt.get("brands") or "").split(",")[0].strip()
    if marke and marke.lower() not in name.lower():
        produkt = {**produkt, "product_name": f"{marke} {name}".strip() if name else marke}
    return produkt


def suche_off(query: str) -> Optional[dict]:
    """Sucht ein Produkt auf OpenFoodFacts. Gibt None zurück wenn nichts gefunden."""
    cached = off_cache_lesen(query)
    if cached is not None:
        return cached

    # Barcode-Suche
    if re.fullmatch(r'\d{8,13}', query):
        url = f"https://world.openfoodfacts.org/api/v2/product/{query}.json"
        data = _off_get(url, timeout=5)
        if data and data.get("status") == 1:
            result = _ergaenze_markenname(data.get("product", {}))
            off_cache_schreiben(query, result)
            # Barcode-Treffer sind eindeutig -> ohne Vorbehalt in die lokale Tabelle
            off_produkt_cachen(result, quelle="barcode")
            return result
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
        "fields": "product_name,brands,code,allergens_tags,allergens,traces_tags,ingredients_text",
    }
    data = _off_get(url, params=params, timeout=7)
    if data:
        for p in data.get("products", []):
            if p.get("allergens_tags") or p.get("ingredients_text"):
                p = _ergaenze_markenname(p)
                off_cache_schreiben(query, p)
                return p

    return None


# ── Lokale Produkterkennung (Phase A: bekannt, Phase B: verifizierte Suche) ────

_MENGENANGABE_MUSTER = re.compile(
    r'\b\d+([.,]\d+)?\s*(g|kg|ml|l|stk|stück|pack|packung)\b', re.IGNORECASE
)
MIN_MATCH_LAENGE = 4          # zu kurze Produktnamen führen zu Falschtreffern (z.B. "Ei")
VERIFIKATIONS_SCHWELLE = 1.0  # welcher Anteil der Kandidaten-Wörter im Treffer stecken muss

# Deutsche Koch-/Back-/Rezeptbegriffe: großgeschrieben (Nomen), aber praktisch nie
# Markennamen - werden aus den Markennamen-Kandidaten rausgefiltert
HAEUFIGE_KOCHWOERTER = {
    "zutaten", "zubereitung", "rezept", "portion", "portionen", "mehl",
    "zucker", "salz", "wasser", "milch", "butter", "sahne", "quark", "ei",
    "eier", "hefe", "backpulver", "vanille", "schokolade", "honig", "zimt",
    "minuten", "stunden", "grad", "ofen", "pfanne", "topf", "schüssel",
    "prise", "esslöffel", "teelöffel", "tasse", "packung", "beutel",
    "riegel", "kekse", "chips", "drink", "snack", "müsli", "joghurt",
    "produktbeschreibung", "allergene", "nährwerte", "inhaltsstoffe",
    "beschreibung", "details", "information", "geschmack",
}
# Häufige Satzanfänge/Funktionswörter, die im Deutschen ebenfalls großgeschrieben sind
HAEUFIGE_FUNKTIONSWOERTER = {
    "ich", "der", "die", "das", "und", "für", "mit", "bei", "ein", "eine",
    "dann", "danach", "heute", "dabei", "dazu", "alles", "man", "wir",
}


def normalisiere_name(name: str) -> str:
    """Normalisiert einen Produkt-/Kandidatennamen für den Textabgleich."""
    name = name.lower()
    name = _MENGENANGABE_MUSTER.sub(' ', name)
    name = re.sub(r'[^a-zäöüß0-9\s]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def _kandidat_abdeckung(kandidat: str, produktname: str) -> float:
    """
    Anteil der Wörter aus `kandidat`, die auch im `produktname` vorkommen (0-1).

    Bewusst nicht symmetrisch (kein Jaccard): ein kurzer Kandidat wie "Bueno" soll
    nicht dafür bestraft werden, dass der offizielle OFF-Name länger ist
    ("Kinder Bueno White") - es zählt nur, ob der Kandidat komplett im Treffer steckt.
    """
    tokens_kandidat = set(normalisiere_name(kandidat).split())
    tokens_produkt = set(normalisiere_name(produktname).split())
    if not tokens_kandidat or not tokens_produkt:
        return 0.0
    return len(tokens_kandidat & tokens_produkt) / len(tokens_kandidat)


def _markennamen_kandidaten(text: str) -> list[str]:
    """
    Grobe Heuristik für mögliche Markennamen im Freitext: einzelne großgeschriebene
    Wörter (Marken sind so gut wie immer großgeschrieben - auch bei kurzer manueller
    Eingabe wie "Bueno"), abzüglich gängiger deutscher Koch-/Funktionswörter.

    Bewusst großzügig: die eigentliche Absicherung gegen Falschtreffer passiert über
    die Wort-Abdeckungs-Prüfung in off_produkt_im_text_finden, nicht schon hier.
    """
    kandidaten = []
    gesehen = set()
    for match in re.finditer(r'\b[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ]{2,}\b', text):
        wort = match.group(0)
        key = wort.lower()
        if key in HAEUFIGE_KOCHWOERTER or key in HAEUFIGE_FUNKTIONSWOERTER or key in gesehen:
            continue
        gesehen.add(key)
        kandidaten.append(wort)
    return kandidaten


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

    # Zwei ergänzende Kandidatenquellen: die enge Heuristik (strukturierter
    # Produkttext) plus großgeschriebene Wörter (deckt auch kurze, direkte
    # Markennamen-Eingaben wie "Bueno" ab) - Reihenfolge, Dopplungen entfernt
    kandidaten = []
    gesehen = set()
    for kandidat in extrahiere_produktnamen(text) + _markennamen_kandidaten(text):
        key = kandidat.lower()
        if key in gesehen:
            continue
        gesehen.add(key)
        kandidaten.append(kandidat)

    for kandidat in kandidaten[:6]:  # Anzahl der Live-Suchen pro Scan begrenzen
        if re.fullmatch(r'\d{8,13}', kandidat):
            continue  # Barcodes laufen bereits über den eigenen Barcode-Pfad in main.py

        treffer = suche_off(kandidat)
        if not treffer:
            continue

        abdeckung = _kandidat_abdeckung(kandidat, treffer.get("product_name", ""))
        if abdeckung >= VERIFIKATIONS_SCHWELLE:
            off_produkt_cachen(treffer, quelle="search_confirmed")
            return treffer

        logger.info(
            f"OFF-Suchtreffer verworfen (Abdeckung {abdeckung:.2f} < {VERIFIKATIONS_SCHWELLE}): "
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
