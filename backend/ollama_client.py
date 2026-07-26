"""Ollama AI client for allergen analysis."""

import json
import re
import requests

from config import OLLAMA_MODEL, OLLAMA_URL


def analyse_mit_ollama(text: str, user_allergien: list[str]) -> list[dict]:
    """Fragt Ollama nach Allergenen und Ersatzvorschlägen. Gibt Funde zurück."""
    allergien_str = ", ".join(user_allergien)
    prompt = (
        f"Du bist ein Allergie-Assistent. Analysiere den folgenden Zutaten- oder Produkttext "
        f"und prüfe ob er Allergene enthält, die für jemanden mit diesen Allergien gefährlich sind: {allergien_str}.\n\n"
        f"Text:\n{text[:2000]}\n\n"
        f"Antworte NUR mit einem JSON-Array. Jedes Objekt hat folgende Felder:\n"
        f"  \"allergie\": welche Allergie aus der Liste betroffen ist\n"
        f"  \"synonym\": der genaue gefundene Begriff im Text\n"
        f"  \"fundstelle\": die genaue Textstelle (max 80 Zeichen)\n"
        f"  \"ist_spur\": true wenn es ein Spurenhinweis ist (z.B. 'kann Spuren enthalten'), sonst false\n"
        f"  \"ersatz\": Array mit 1-3 konkreten Ersatzvorschlägen für den gefundenen Begriff (z.B. [\"Sonnenblumenöl\", \"Rapsöl\"]). Leeres Array wenn kein sinnvoller Ersatz existiert.\n"
        f"Wenn nichts gefunden wurde, antworte mit: []\n"
        f"Antworte ausschliesslich mit dem JSON-Array, ohne Erklaerung oder weiteren Text."
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
            return json.loads(m.group(0))
    except Exception:
        pass
    return []
