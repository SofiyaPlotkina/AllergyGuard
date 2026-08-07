"""Vollständiger Test mit allen Filtern (wie in main.py)"""

from synonym_matcher import synonym_matching
from ollama_client import analyse_mit_ollama
from eiweiss_filter import filtere_eiweiss_funde

text = "Cremiger Brotaufstrich mit Karamell-Keks-Geschmack Auf Basis von 60 % gerösteten Mandeln"
allergien = ["Milch", "Ei", "Gluten", "Sesam"]

print("=" * 80)
print("VOLLSTÄNDIGER TEST (mit Filtern wie in main.py)")
print("=" * 80)
print(f"Text: {text}\n")

# TIER 2: Synonym Matching
print("TIER 2 - Synonym Matching:")
print("-" * 80)
synonym_funde = synonym_matching(text, allergien)
print(f"Funde: {len(synonym_funde)}")
for f in synonym_funde:
    print(f'  - {f["allergie"]}: {f["synonym"]} in "{f["fundstelle"][:60]}..."')
print()

# TIER 3: Ollama (ROH, vor Filtern)
print("TIER 3 - Ollama KI (ROHFUNDE vor Filtern):")
print("-" * 80)
ollama_roh = analyse_mit_ollama(text, allergien)
print(f"Funde: {len(ollama_roh)}")
for f in ollama_roh:
    print(f'  - {f["allergie"]}: "{f["fundstelle"]}"')
print()

# TIER 3: Nach Filtern
print("TIER 3 - Ollama KI (NACH Filtern):")
print("-" * 80)
ollama_gefiltert = filtere_eiweiss_funde(ollama_roh, text)
print(f"Funde: {len(ollama_gefiltert)}")
if ollama_gefiltert:
    for f in ollama_gefiltert:
        print(f'  - {f["allergie"]}: "{f["fundstelle"]}"')
else:
    print("  ✅ Alle False Positives wurden gefiltert!")
print()

# GESAMT
print("=" * 80)
print("FINAL-ERGEBNIS (wie User es sieht):")
print("=" * 80)
alle_funde = synonym_funde + ollama_gefiltert
print(f"Gesamt-Funde: {len(alle_funde)}")
for f in alle_funde:
    print(f'  - {f["allergie"]}: {f["synonym"] if "synonym" in f else f["fundstelle"][:50]}')
