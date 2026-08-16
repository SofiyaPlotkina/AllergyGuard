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
    
    # KURZER, FOKUSSIERTER PROMPT (30 Zeilen statt 170\!)
    prompt = f"""Task: Find allergens in ingredient text.

User's allergens: {allergien_str}

Critical rules:
1. Only report allergens ACTUALLY present in text (no hallucinations\!)
2. "vegan/plant-based" products → NO dairy/egg
3. "gluten-free" products → NO gluten
4. "protein/Eiweiß" in nutrition context → NO egg allergen
5. "may contain traces" → mark ist_spur=true

Text (first 600 chars):
{text[:600]}

Return JSON array ONLY:
[{{"allergie": "name", "synonym": "found_term", "fundstelle": "context (max 80 chars)", "ist_spur": false}}]

Empty if nothing found: []
No explanations, only JSON\!"""
    
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
        # Strategie: Kurzer Prompt, aber aggressive Nachfilterung\!
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
                    logger.info(f"Ollama gluten-free-context filtered: '{synonym}' (glutenfrei\!)")
                    continue
            
            # Filter 4: Kritische False-Positive-Check mit filters.py (existierendes System\!)
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
