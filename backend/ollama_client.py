"""Ollama AI client for allergen analysis."""

import json
import re
import requests

from config import OLLAMA_MODEL, OLLAMA_URL


def analyse_mit_ollama(text: str, user_allergien: list[str]) -> list[dict]:
    """Fragt Ollama nach Allergenen und Ersatzvorschlägen. Gibt Funde zurück."""
    allergien_str = ", ".join(user_allergien)
    prompt = (
        f"Du bist ein Allergie-Assistent. Analysiere den folgenden Text und finde ALLERGENE für: {allergien_str}.\n\n"
        
        f"🚨 KRITISCH - Unterscheide Nährstoffe von Allergenen:\n"
        f"▶ 'Eiweiß' in Produktbeschreibungen = Nährstoff (PROTEIN) → KEIN Ei-Allergen!\n"
        f"  Beispiele (NICHT als Ei melden):\n"
        f"    ❌ 'Riegel mit Eiweiß' → Protein, KEIN Ei!\n"
        f"    ❌ 'hoher Eiweißgehalt' → Protein, KEIN Ei!\n"
        f"    ❌ '34% Protein / Eiweiß' → Nährstoffangabe, KEIN Ei!\n"
        f"    ❌ 'reich an Eiweiß' → Protein, KEIN Ei!\n"
        f"    ❌ 'MILCHEIWEISS' → Milch-Protein, KEIN Ei!\n"
        f"    ❌ 'Molkeneiweiss' → Molken-Protein, KEIN Ei!\n"
        f"    ❌ 'Sojaeiweiß' → Soja-Protein, KEIN Ei!\n"
        f"▶ 'Eiweiß' in ZUTATENLISTEN = Ei-Produkt → Allergen melden!\n"
        f"  Beispiele (ALS Ei melden):\n"
        f"    ✅ 'Zutaten: Mehl, Eiweiß, Zucker' → echtes Ei-Allergen!\n"
        f"    ✅ 'enthält: Eiklar, Eiweiß' → echtes Ei-Allergen!\n\n"
        
        f"🚨 WICHTIG - Keine Negativ-Meldungen:\n"
        f"▶ Wenn ein Allergen NICHT gefunden wird → NICHT ins Array aufnehmen!\n"
        f"▶ NIEMALS schreiben: 'kein X gefunden', 'kein Allergen', 'nicht vorhanden'\n"
        f"▶ NUR ECHTE FUNDE ins JSON-Array!\n\n"
        
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
            # POST-PROCESSING: Filtere "kein X gefunden" Einträge
            gefilterte_funde = []
            for fund in funde:
                synonym = (fund.get("synonym") or "").lower()
                # Filtere negative/informative Einträge
                if any(neg in synonym for neg in ["kein", "nicht gefunden", "nicht vorhanden", "keine"]):
                    print(f"⚠️ Ollama-Müll gefiltert: '{synonym}'")
                    continue
                gefilterte_funde.append(fund)
            return gefilterte_funde
    except Exception:
        pass
    return []
