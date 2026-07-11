import datetime
import json
import re
from typing import Optional

import requests

try:
    from .config import OFF_CACHE_TTL_DAYS, OLLAMA_MODEL, OLLAMA_URL
    from .db import get_connection
except ImportError:  # pragma: no cover - fallback for direct execution
    from config import OFF_CACHE_TTL_DAYS, OLLAMA_MODEL, OLLAMA_URL
    from db import get_connection


ALLERGEN_SYNONYME: dict[str, list[str]] = {
    "erdnuss": [
        "erdnuss", "erdnüsse", "erdnussöl", "erdnussbutter", "peanut", "peanut oil",
        "peanut butter", "arachis", "satay"
    ],
    "milch": [
        "milch", "sahne", "butter", "käse", "joghurt", "kasein", "molke", "whey",
        "milk", "cream", "cheese"
    ],
    "ei": [
        "ei", "eier", "eigelb", "eiklar", "eiweiß", "egg", "egg white", "egg yolk",
        "mayonnaise", "meringue"
    ],
    "gluten": [
        "gluten", "weizen", "dinkel", "roggen", "gerste", "hafer", "mehl", "brot",
        "nudeln", "pasta", "wheat", "barley", "oats"
    ],
    "soja": [
        "soja", "sojasoße", "tofu", "tempeh", "miso", "soy", "soy sauce", "soybean"
    ],
    "nüsse": [
        "nuss", "nüsse", "mandel", "haselnuss", "walnuss", "cashew", "pistazie",
        "almond", "hazelnut", "walnut", "nut"
    ],
    "fisch": [
        "fisch", "lachs", "thunfisch", "sardine", "anchovis", "fish", "salmon", "tuna"
    ],
    "sellerie": ["sellerie", "celery"],
    "senf": ["senf", "mustard"],
    "sesam": ["sesam", "sesame"],
    "lupine": ["lupine", "lupin"],
    "weichtiere": ["muschel", "auster", "tintenfisch", "mussel", "squid"],
    "krebstiere": ["krebstier", "garnele", "garnelen", "shrimp", "crab"],
    "sulfite": ["sulfite", "sulfit", "schwefeldioxid", "sulphite"],
}

OFF_TAG_MAP = {
    "en:gluten": "gluten",
    "en:wheat": "gluten",
    "en:milk": "milch",
    "en:eggs": "ei",
    "en:egg": "ei",
    "en:fish": "fisch",
    "en:peanuts": "erdnuss",
    "en:peanut": "erdnuss",
    "en:soybeans": "soja",
    "en:soy": "soja",
    "en:nuts": "nüsse",
    "en:almonds": "nüsse",
    "en:hazelnuts": "nüsse",
    "en:walnuts": "nüsse",
    "en:cashews": "nüsse",
    "en:celery": "sellerie",
    "en:mustard": "senf",
    "en:sesame": "sesam",
    "en:lupin": "lupine",
    "en:molluscs": "weichtiere",
    "en:crustaceans": "krebstiere",
    "en:sulphites": "sulfite",
    "en:sulphur-dioxide-and-sulphites": "sulfite",
}

ERSATZ: dict[str, list[str]] = {
    "erdnuss": ["Sonnenblumenöl", "Mandelmus"],
    "milch": ["Hafermilch", "Reismilch"],
    "butter": ["Kokosöl", "Pflanzliche Margarine"],
    "ei": ["Aquafaba", "Leinsamen-Ei"],
    "gluten": ["Reismehl", "Buchweizenmehl"],
    "soja": ["Kichererbsen", "Erbsenprotein"],
    "nuss": ["Sonnenblumenkerne", "Kürbiskerne"],
    "fisch": ["Tofu", "Jackfrucht"],
    "sellerie": ["Fenchel", "Pastinake"],
    "senf": ["Meerrettich", "Wasabi"],
    "sesam": ["Sonnenblumenkerne", "Kürbiskerne"],
    "lupin": ["Erbsenprotein", "Kichererbsenmehl"],
    "muschel": ["Austernpilze", "Artischocken"],
    "garnele": ["Herzhafter Tofu", "Jackfrucht"],
    "sulfit": ["Frische Zutaten", "Ungeschwefelte Trockenfrüchte"],
}

SPUREN_PHRASEN = [
    "kann spuren enthalten",
    "may contain",
    "spuren von",
    "traces of",
    "nicht geeignet für personen mit allergie",
    "hergestellt in einem betrieb",
    "in derselben anlage",
    "-haltig",  # z.B. "glutenhaltigen", "nusshaltig"
    " haltig",
]

WORTGRENZE_SYNONYME = {"ei", "eier", "nut", "nuts", "cod", "rye", "oat", "oats", "malt", "crab", "bass", "clam", "aal", "feta", "brie"}


def ersatz_fuer(gefundener_begriff: str) -> list[str]:
    """Gibt Ersatzvorschläge für einen gefundenen Begriff zurück. Nutzt Substring-Matching."""
    begriff = gefundener_begriff.lower().strip()
    if begriff in ERSATZ:
        return ERSATZ[begriff]
    # Substring-Matching: längster passender Key gewinnt
    treffer = [(key, values) for key, values in ERSATZ.items() if key in begriff or begriff in key]
    if treffer:
        bester = max(treffer, key=lambda x: len(x[0]))
        return bester[1]
    # Fallback: prüfe ob es ein ähnlicher Allergen-Schlüssel ist (z.B. "mehl" -> "gluten")
    for allergie_key, allergie_synonyme in ALLERGEN_SYNONYME.items():
        if begriff in allergie_synonyme or any(syn in begriff for syn in allergie_synonyme[:3]):
            # Versuche Ersatz basierend auf der Allergie-Kategorie zu finden
            if allergie_key in ERSATZ:
                return ERSATZ[allergie_key]
    return []


def synonyme_fuer(allergen: str) -> list[str]:
    key = allergen.lower().strip()
    if key in ALLERGEN_SYNONYME:
        return ALLERGEN_SYNONYME[key]
    for k, synonyme in ALLERGEN_SYNONYME.items():
        if k in key or key in k:
            return synonyme
    return [key]


def extrahiere_produktnamen(text: str) -> list[str]:
    """Extrahiert Produktnamen aus Zutatenliste für OFF-Suche."""
    kandidaten = []
    
    # 1. Barcodes (wenn vorhanden)
    for barcode in re.findall(r"\b\d{8,13}\b", text):
        kandidaten.append(barcode)
    
    # 2. Einzelne Zutaten: Zeilen mit Mengenangaben
    for zeile in text.splitlines():
        zeile = zeile.strip()
        # Format: "10 EL Mehl" -> "Mehl"
        if re.match(r"^[\d,\s]*(EL|g|ml|TL|Prise)", zeile, re.IGNORECASE):
            produkt = re.sub(r"^[\d,\s]*(EL|g|ml|TL|Prise)[\s]*", "", zeile, flags=re.IGNORECASE).strip()
            produkt = re.split(r"[,(]", produkt)[0].strip()
            if 2 < len(produkt) < 50:
                kandidaten.append(produkt)
        # Format: "- Paniermehl" -> "Paniermehl"
        elif re.match(r"^[-*]\s", zeile):
            produkt = re.sub(r"^[-*]\s", "", zeile).strip()
            produkt = re.split(r"[,(]", produkt)[0].strip()
            if 2 < len(produkt) < 50:
                kandidaten.append(produkt)
    
    return list(dict.fromkeys(kandidaten))[:5]  # Duplikate entfernen, max 5 Versuche


def off_cache_lesen(key: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT response_json, cached_at FROM off_cache WHERE query_key=?", (key,)).fetchone()
    conn.close()
    if not row:
        return None
    cached = datetime.datetime.fromisoformat(row["cached_at"])
    if (datetime.datetime.now() - cached).days >= OFF_CACHE_TTL_DAYS:
        return None
    return json.loads(row["response_json"])


def off_cache_schreiben(key: str, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO off_cache (query_key, response_json, cached_at) VALUES (?, ?, ?)",
        (key, json.dumps(data), datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def suche_off(query: str) -> Optional[dict]:
    cached = off_cache_lesen(query)
    if cached is not None:
        return cached
    if re.fullmatch(r"\d{8,13}", query):
        url = f"https://world.openfoodfacts.org/api/v2/product/{query}.json"
        try:
            r = requests.get(url, timeout=5, headers={"User-Agent": "AllergyGuard/1.0"})
            data = r.json()
            if data.get("status") == 1:
                result = data.get("product", {})
                off_cache_schreiben(query, result)
                return result
        except Exception:
            pass
        return None

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
        r = requests.get(url, params=params, timeout=6, headers={"User-Agent": "AllergyGuard/1.0"})
        data = r.json()
        products = data.get("products", [])
        for product in products:
            if product.get("allergens_tags") or product.get("ingredients_text"):
                off_cache_schreiben(query, product)
                return product
    except Exception:
        pass
    return None


def off_allergene_pruefen(produkt: dict, user_allergien: list[str]) -> list[dict]:
    funde = []
    allergen_tags = produkt.get("allergens_tags", [])
    spuren_tags = produkt.get("traces_tags", [])
    produkt_name = produkt.get("product_name", "Unbekanntes Produkt")

    for allergie in user_allergien:
        allergie_key = allergie.lower().strip()
        for tag, schluessel in OFF_TAG_MAP.items():
            if schluessel != allergie_key and schluessel not in allergie_key:
                continue
            if tag in allergen_tags:
                funde.append({
                    "allergie": allergie,
                    "synonym": tag.replace("en:", ""),
                    "fundstelle": f"OpenFoodFacts: {produkt_name}",
                    "ist_spur": False,
                    "ersatz": ersatz_fuer(tag.replace("en:", "")),
                })
                break
            if tag in spuren_tags:
                funde.append({
                    "allergie": allergie,
                    "synonym": tag.replace("en:", ""),
                    "fundstelle": f"OpenFoodFacts (Spur): {produkt_name}",
                    "ist_spur": True,
                    "ersatz": ersatz_fuer(tag.replace("en:", "")),
                })
                break
    return funde


def analyse_mit_ollama(text: str, user_allergien: list[str]) -> list[dict]:
    allergien_str = ", ".join(user_allergien)
    prompt = (
        f"Du bist ein Allergie-Assistent. Analysiere den Produkttext auf Allergen-Hinweise.\n\n"
        f"Zu prüfende Allergene: {allergien_str}\n\n"
        f"Text: {text[:2000]}\n\n"
        f"WICHTIG - Beantworte die Frage mit einem JSON-Array im genau diesen Format:\n"
        f'[{{"allergie": "ALLERGEN_NAME", "synonym": "Gefundenes Wort (z.B. Mehl)", "fundstelle": "Kontext (z.B. 10 EL Mehl)", "ist_spur": true/false, "ersatz": ["Alt1", "Alt2"]}}]\n\n'
        f"Regeln:\n"
        f'- ist_spur = true nur wenn Text "Spuren", "kann enthalten", "Kontamination" enthält\n'
        f'- ist_spur = false wenn Allergen als Hauptzutat genannt ist\n'
        f"- ersatz = immer ein Array, auch wenn leer: []\n"
        f"- synonym = das konkret gefundene Wort, NICHT leer\n"
        f"- Wenn nichts gefunden: antworte mit []\n"
        f"- NUR JSON, keine weiteren Worte"
    )
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        raw = response.json().get("response", "[]").strip()
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            # Validiere und bereinige die Antwort
            cleaned = []
            for item in parsed:
                if isinstance(item, dict):
                    # Stelle sicher, dass alle erforderlichen Felder existieren und den richtigen Typ haben
                    if not item.get("synonym"):  # Überspringe Einträge ohne synonym
                        continue
                    cleaned_item = {
                        "allergie": item.get("allergie", ""),
                        "synonym": str(item.get("synonym", "")).strip(),
                        "fundstelle": str(item.get("fundstelle", "")).strip(),
                        "ist_spur": bool(item.get("ist_spur", False)),
                        "ersatz": item.get("ersatz", []) if isinstance(item.get("ersatz"), list) else [],
                    }
                    if cleaned_item["synonym"]:  # Nur hinzufügen wenn synonym nicht leer
                        cleaned.append(cleaned_item)
            return cleaned
    except Exception:
        pass
    return []


def synonym_trifft(synonym: str, text_lower: str) -> bool:
    if synonym in WORTGRENZE_SYNONYME or len(synonym) <= 3:
        pattern = r"(?<![a-zäöüß])" + re.escape(synonym) + r"(?![a-zäöüß])"
        return bool(re.search(pattern, text_lower))
    return synonym in text_lower


def synonym_matching(text: str, user_allergien: list[str]) -> list[dict]:
    """Lokales Synonym-Matching. Prüft Kontext DAVOR und DANACH auf Spuren-Hinweise."""
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
                    # Spur-Check: Kontext DAVOR und DANACH
                    ist_spur = False
                    pos = text_lower.find(synonym)
                    if pos >= 0:
                        # Kontext: 100 Zeichen davor und danach
                        kontext_davor = text_lower[max(0, pos - 100):pos]
                        kontext_danach = text_lower[pos:min(len(text_lower), pos + 100)]
                        kontext_gesamt = kontext_davor + synonym + kontext_danach
                        
                        # Prüfe auf Spuren-Indikatoren
                        ist_spur = any(phrase in kontext_gesamt for phrase in SPUREN_PHRASEN)
                    
                    funde.append({
                        "allergie": allergie,
                        "synonym": synonym,
                        "fundstelle": zeile.strip(),
                        "ist_spur": ist_spur,
                        "ersatz": ersatz_fuer(synonym),
                    })
                    break
            if any(item["allergie"] == allergie for item in funde):
                break
    return funde


def analyze_text(text: str, user_allergien: list[str]) -> dict:
    funde: list[dict] = []
    methode = "synonym"

    # ── 1. OpenFoodFacts: versuche Barcodes ──
    barcodes = re.findall(r"\b\d{8,13}\b", text)
    for barcode in barcodes:
        produkt = suche_off(barcode)
        if produkt:
            off_funde = off_allergene_pruefen(produkt, user_allergien)
            if off_funde or produkt.get("allergens_tags"):
                funde = off_funde
                methode = "openfoodfacts"
                break

    # ── 2. OpenFoodFacts: versuche Produktnamen aus Zutaten ──
    if methode == "synonym":
        produktnamen = extrahiere_produktnamen(text)
        for produktname in produktnamen:
            produkt = suche_off(produktname)
            if produkt:
                off_funde = off_allergene_pruefen(produkt, user_allergien)
                if off_funde:
                    funde = off_funde
                    methode = "openfoodfacts"
                    break

    # ── 3. Ollama-Fallback ──
    if methode == "synonym":
        ollama_funde = analyse_mit_ollama(text, user_allergien)
        if ollama_funde:
            funde = ollama_funde
            methode = "ollama"

    # ── 4. Lokales Synonym-Matching als letzter Fallback ──
    if methode == "synonym":
        funde = synonym_matching(text, user_allergien)
        methode = "synonym"

    gefahr_funde = [item for item in funde if not item.get("ist_spur")]
    spuren_funde = [item for item in funde if item.get("ist_spur")]

    if gefahr_funde:
        urteil = "GEFAHR"
    elif spuren_funde:
        urteil = "WARNUNG"
    else:
        urteil = "SICHER"

    erster_fund = (gefahr_funde or spuren_funde or [None])[0]
    gefundenes_synonym = erster_fund["synonym"] if erster_fund else ""
    gefunden_in = erster_fund["fundstelle"] if erster_fund else ""

    if urteil == "GEFAHR":
        allergien_liste = ", ".join(item["allergie"] for item in gefahr_funde)
        grund = f"Direkt gefunden: {allergien_liste}. (via {methode})"
    elif urteil == "WARNUNG":
        allergien_liste = ", ".join(item["allergie"] for item in spuren_funde)
        grund = f"Spurenhinweise auf: {allergien_liste}. (via {methode})"
    else:
        grund = f"Keine Allergene gefunden. (via {methode})"

    # Alle Ersatz-Vorschläge sammeln
    alle_ersatz = []
    for fund in funde:
        if fund.get("ersatz"):
            alle_ersatz.extend(fund.get("ersatz"))
    alle_ersatz = list(dict.fromkeys(alle_ersatz))  # Duplikate entfernen

    return {
        "urteil": urteil,
        "gefundenes_synonym": gefundenes_synonym,
        "fundstelle": gefunden_in,
        "grund": grund,
        "methode": methode,
        "alle_funde": funde,
        "alle_ersatz_vorschlaege": alle_ersatz,
    }
