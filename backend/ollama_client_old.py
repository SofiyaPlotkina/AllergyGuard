"""Ollama AI client for allergen analysis."""

import json
import re
import requests
import logging

from config import OLLAMA_MODEL, OLLAMA_URL
from filters import ist_false_positive

logger = logging.getLogger(__name__)


def analyse_mit_ollama(text: str, user_allergien: list[str]) -> list[dict]:
    """
    Fragt Ollama nach Allergenen. LETZTER FALLBACK - nur wenn Synonym-Matching nichts findet.
    
    Strategie: Kurzer, fokussierter Prompt + starke POST-PROCESSING Filter
    """
    allergien_str = ", ".join(user_allergien)
    
    # KURZER, FOKUSSIERTER PROMPT (30 Zeilen statt 170!)
    prompt = f"""Task: Find allergens in ingredient text.

User's allergens: {allergien_str}

Critical rules:
1. Only report allergens ACTUALLY present in text (no hallucinations!)
2. "vegan/plant-based" products → NO dairy/egg
3. "gluten-free" products → NO gluten
4. "protein/Eiweiß" in nutrition context → NO egg allergen
5. "may contain traces" → mark ist_spur=true

Text (first 600 chars):
{text[:600]}

Return JSON array ONLY:
[{{"allergie": "name", "synonym": "found_term", "fundstelle": "context (max 80 chars)", "ist_spur": false}}]

Empty if nothing found: []
No explanations, only JSON!"""
    
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }, timeout=30)
        raw = r.json().get("response", "[]").strip()
        
        # Extract JSON from response
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if not m:
            logger.warning("Ollama returned no valid JSON array")
            return []
        
        funde = json.loads(m.group(0))
        
        # ====== POST-PROCESSING: STARKE FILTER ======
        # Strategie: Kurzer Prompt, aber aggressive Nachfilterung!
        gefilterte_funde = []
        
        for fund in funde:
            synonym = (fund.get("synonym") or "").lower()
            allergie = (fund.get("allergie") or "").lower()
            fundstelle = (fund.get("fundstelle") or "").lower()
            
            # Filter 1: Negative/Informative Entries (Ollama schreibt oft "keine X gefunden")
            if any(neg in synonym for neg in ["kein", "nicht gefunden", "nicht vorhanden", "keine", "not found"]):
                logger.warning(f"Ollama junk filtered: '{synonym}'")
                continue
            
            # Filter 2: Nutrition-Kontext (Eiweiß ≠ Ei)
            if "protein" in fundstelle or "nährwert" in fundstelle or "pro 100" in fundstelle:
                if allergie in ["ei", "egg"]:
                    logger.info(f"Ollama nutrition-context filtered: '{synonym}' (Protein, nicht Ei)")
                    continue
            
            # Filter 3: Vegan/Glutenfrei-Produkte
            if "vegan" in fundstelle or "pflanzlich" in fundstelle:
                if allergie in ["milch", "milk", "dairy", "ei", "egg"]:
                    logger.info(f"Ollama vegan-context filtered: '{synonym}' (vegan, kein Tierprodukt)")
                    continue
            
            if "glutenfrei" in fundstelle or "gluten-free" in fundstelle or "gluten free" in fundstelle:
                if allergie in ["gluten", "weizen", "wheat"]:
                    logger.info(f"Ollama gluten-free-context filtered: '{synonym}' (glutenfrei!)")
                    continue
            
            # Filter 4: Kritische False-Positive-Check mit filters.py (existierendes System!)
            if ist_false_positive(allergie, synonym, fundstelle):
                logger.info(f"Ollama false-positive filtered via filters.py: '{synonym}' for {allergie}")
                continue
            
            # Filter 5: Zu kurze Synonyme (oft Halluzinationen)
            if len(synonym) < 3:
                logger.warning(f"Ollama synonym too short: '{synonym}' (likely hallucination)")
                continue
            
            # Wenn alle Filter passiert: Fund ist valide
            gefilterte_funde.append(fund)
        
        if len(gefilterte_funde) < len(funde):
            logger.info(f"Ollama filtering: {len(funde)} raw → {len(gefilterte_funde)} after POST-PROCESSING")
        
        return gefilterte_funde
            
    except requests.RequestException as e:
        logger.error(f"Ollama API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ollama response parsing failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in Ollama analysis: {e}")
        return []


def analyse_mit_ollama(text: str, user_allergien: list[str]) -> list[dict]:
    """Fragt Ollama nach Allergenen und Ersatzvorschlägen. Gibt Funde zurück."""
    allergien_str = ", ".join(user_allergien)
    prompt = (
        f"Du bist ein Allergie-Assistent. Analysiere den folgenden Text und finde ALLERGENE für: {allergien_str}.\n\n"
        
        f"[CRITICAL] ABSOLUT KRITISCH - KEINE HALLUZINATIONEN!\n"
        f"> MELDE NUR Zutaten die TATSÄCHLICH im Text stehen!\n"
        f"> ERFINDE NIEMALS Zutaten die NICHT im Text sind!\n"
        f"> Wenn du unsicher bist, NICHT melden!\n"
        f"> Beispiel: Text sagt 'glutenfreies Brot', melde KEINE Milch!\n"
        f"> Beispiel: Text sagt 'Haferdrink', melde KEINE Kuhmilch!\n\n"
        
        f"[CRITICAL] Vegan/Glutenfrei-Kontext:\n"
        f"> Wenn 'vegan' oder 'pflanzlich' dabei steht, KEINE Milch/Ei!\n"
        f"  Beispiele (NICHT melden):\n"
        f"    [NO] 'vegane Sahne', KEINE Milch!\n"
        f"    [NO] 'veganer Frischkäse', KEINE Milch!\n"
        f"    [NO] 'pflanzliches Joghurt', KEINE Milch!\n"
        f"> Wenn 'glutenfrei' dabei steht, KEIN Gluten!\n"
        f"  Beispiele (NICHT melden):\n"
        f"    [NO] 'glutenfreies Brot', KEIN Gluten!\n"
        f"    [NO] 'glutenfreie Nudeln', KEIN Gluten!\n\n"
        
        f"[CRITICAL] Unterscheide Nährstoffe von Allergenen:\n"
        f"> 'Eiweiß' in Produktbeschreibungen = Nährstoff (PROTEIN), KEIN Ei-Allergen!\n"
        f"  Beispiele (NICHT als Ei melden):\n"
        f"    [NO] 'Riegel mit Eiweiß', Protein, KEIN Ei!\n"
        f"    [NO] 'hoher Eiweißgehalt', Protein, KEIN Ei!\n"
        f"    [NO] '34% Protein / Eiweiß', Nährstoffangabe, KEIN Ei!\n"
        f"    [NO] 'reich an Eiweiß', Protein, KEIN Ei!\n"
        f"    [NO] 'MILCHEIWEISS', Milch-Protein, KEIN Ei!\n"
        f"    [NO] 'Molkeneiweiss', Molken-Protein, KEIN Ei!\n"
        f"    [NO] 'Sojaeiweiß', Soja-Protein, KEIN Ei!\n"
        f"> 'Eiweiß' in ZUTATENLISTEN = Ei-Produkt, Allergen melden!\n"
        f"  Beispiele (ALS Ei melden):\n"
        f"    [YES] 'Zutaten: Mehl, Eiweiß, Zucker', echtes Ei-Allergen!\n"
        f"    [YES] 'enthält: Eiklar, Eiweiß', echtes Ei-Allergen!\n\n"
        
        f"[CRITICAL] Pflanzenmilch vs. Tiermilch:\n"
        f"> Pflanzenmilch (Mandelmilch, Hafermilch, Haferdrink, etc.) = KEINE Milch-Allergen!\n"
        f"  Beispiele (NICHT als Milch melden):\n"
        f"    [NO] 'Mandelmilch', Pflanzendrink, KEINE Milch!\n"
        f"    [NO] 'Hafermilch', Pflanzendrink, KEINE Milch!\n"
        f"    [NO] 'Haferdrink', Pflanzendrink, KEINE Milch!\n"
        f"    [NO] 'Sojadrink', Pflanzendrink, KEINE Milch!\n"
        f"    [NO] 'Sojamilch', Pflanzendrink, KEINE Milch!\n"
        f"    [NO] 'Kokosmilch', Pflanzendrink, KEINE Milch!\n"
        f"> 'Auf Basis von' + Nüssen/Pflanzenprodukten = KEINE Milch!\n"
        f"  Beispiele (NICHT als Milch melden):\n"
        f"    [NO] 'Auf Basis von gerösteten Mandeln', KEINE Milch!\n"
        f"    [NO] 'Auf Basis von Hafer', KEINE Milch!\n"
        f"    [NO] 'Basis: Soja', KEINE Milch!\n"
        f"    [NO] 'Hergestellt aus Cashews', KEINE Milch!\n"
        f"> Vegane/pflanzliche Butter = KEINE Milch-Allergen!\n"
        f"  Beispiele (NICHT als Milch melden):\n"
        f"    [NO] 'vegane Butter', Pflanzenfett, KEINE Milch!\n"
        f"    [NO] 'pflanzliche Butter', Pflanzenfett, KEINE Milch!\n"
        f"    [NO] 'Margarine', meist pflanzlich, KEINE Milch!\n"
        f"    [NO] 'Kokosfett', Pflanzenfett, KEINE Milch!\n"
        f"    [NO] 'Kakaobutter', Pflanzenfett aus Kakao, KEINE Milch!\n"
        f"    [NO] 'Kakao-butter', Pflanzenfett aus Kakao, KEINE Milch!\n"
        f"    [NO] 'Sheabutter', Pflanzenfett, KEINE Milch!\n"
        f"> Tiermilch = Milch-Allergen melden!\n"
        f"  Beispiele (ALS Milch melden):\n"
        f"    [YES] 'VOLLMILCH', echte Milch!\n"
        f"    [YES] 'Kuhmilch', echte Milch!\n"
        f"    [YES] 'Butter' (ohne 'vegan'/'pflanzlich'/'Kakao'), echte Milch!\n\n"
        
        f"[CRITICAL] Pseudo-Getreide vs. Gluten:\n"
        f"> Pseudo-Getreide (Buchweizen, Quinoa, etc.) = KEIN Gluten!\n"
        f"  Beispiele (NICHT als Gluten melden):\n"
        f"    [NO] 'Buchweizen', Pseudo-Getreide, KEIN Gluten!\n"
        f"    [NO] 'Quinoa', Pseudo-Getreide, KEIN Gluten!\n"
        f"    [NO] 'Amaranth', Pseudo-Getreide, KEIN Gluten!\n"
        f"> N\u00dcSSE und SAMEN = KEIN Gluten!\n"
        f"  Beispiele (NICHT als Gluten melden):\n"
        f"    [NO] 'Mandeln', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Waln\u00fcsse', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Haseln\u00fcsse', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Cashewn\u00fcsse', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Paranuss', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Pekann\u00fcsse', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Macadamia', N\u00fcsse, KEIN Gluten!\n"
        f"    [NO] 'Chiasamen', Samen, KEIN Gluten!\n"
        f"    [NO] 'Leinsamen', Samen, KEIN Gluten!\n"
        f"    [NO] 'Sonnenblumenkerne', Samen, KEIN Gluten!\n"
        f"> Reis, Mais, Kartoffeln = KEIN Gluten!\n"
        f"  Beispiele (NICHT als Gluten melden):\n"
        f"    [NO] 'Reis', KEIN Gluten!\n"
        f"    [NO] 'Reismehl', KEIN Gluten!\n"
        f"    [NO] 'Mais', KEIN Gluten!\n"
        f"    [NO] 'Maismehl', KEIN Gluten!\n"
        f"    [NO] 'Kartoffelmehl', KEIN Gluten!\n"
        f"    [NO] 'Kartoffelst\u00e4rke', KEIN Gluten!\n"
        f"> Echtes Gluten-Getreide:\n"
        f"  Beispiele (ALS Gluten melden):\n"
        f"    [YES] 'Weizen', enth\u00e4lt Gluten!\n"
        f"    [YES] 'Roggen', enth\u00e4lt Gluten!\n"
        f"    [YES] 'Gerste', enth\u00e4lt Gluten!\n"
        f"    [YES] 'Dinkel', enth\u00e4lt Gluten!\n"
        f"    [YES] 'Hafer' (meist kontaminiert), enth\u00e4lt Gluten!\n\n"
        
        f"[IMPORTANT] Keine Negativ-Meldungen:\n"
        f"> Wenn ein Allergen NICHT gefunden wird, NICHT ins Array aufnehmen!\n"
        f"> NIEMALS schreiben: 'kein X gefunden', 'kein Allergen', 'nicht vorhanden'\n"
        f"> NUR ECHTE FUNDE ins JSON-Array!\n\n"
        
        f"Weitere Regeln:\n"
        f"• Spuren-Hinweise: 'kann Spuren enthalten' → ist_spur=true\n"
        f"• Zutatenlisten beginnen oft mit 'Zutaten:', 'enthält:', 'Ingredients:'\n"
        f"• Produktbeschreibungen: Marketing-Text, Nährwertangaben\n\n"
        
        f"Text:\n{text[:2000]}\n\n"
        
        f"Antworte NUR mit JSON-Array MIT ECHTEN FUNDEN:\n"
        f"[\n"
        f"  {{\n"
        f"    \"allergie\": \"Name aus [{allergien_str}]\",\n"
        f"    \"synonym\": \"gefundener Begriff (NUR echte Allergene!)\",\n"
        f"    \"fundstelle\": \"Textstelle (max 80 Zeichen)\",\n"
        f"    \"ist_spur\": true/false,\n"
        f"    \"ersatz\": [\"Ersatzprodukt1\", \"Ersatzprodukt2\"]\n"
        f"  }}\n"
        f"]\n"
        f"Wenn NICHTS gefunden: [] (leeres Array!)\n"
        f"KEINE 'kein X gefunden' Einträge!\n"
        f"Antworte NUR mit JSON, ohne Erklärung."
    )
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }, timeout=30)
        raw = r.json().get("response", "[]").strip()
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            funde = json.loads(m.group(0))
            # POST-PROCESSING: Filtere "kein X gefunden" Einträge UND False Positives
            gefilterte_funde = []
            for fund in funde:
                synonym = (fund.get("synonym") or "").lower()
                allergie = (fund.get("allergie") or "").lower()
                fundstelle = (fund.get("fundstelle") or "")
                
                # Filtere negative/informative Einträge
                if any(neg in synonym for neg in ["kein", "nicht gefunden", "nicht vorhanden", "keine"]):
                    logger.warning(f"Ollama junk filtered: '{synonym}'")
                    continue
                
                # KRITISCH: False-Positive-Filter anwenden (z.B. Vanilleschote ≠ Ei)
                if ist_false_positive(allergie, synonym, fundstelle):
                    logger.info(f"Ollama false-positive filtered: '{synonym}' for {allergie}")
                    continue
                
                gefilterte_funde.append(fund)
            return gefilterte_funde
            
    except requests.RequestException as e:
        logger.error(f"Ollama API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ollama response parsing failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in Ollama analysis: {e}")
        return []
    
    return []
