"""Debug: Warum meldet Mistral bei 'geröstete Mandeln' → Milch?"""

from synonym_matcher import synonym_matching
from ollama_client import analyse_mit_ollama

text = "Cremiger Brotaufstrich mit Karamell-Keks-Geschmack Auf Basis von 60 % gerösteten Mandeln"
allergien = ["Milch", "Ei", "Gluten", "Sesam"]

print("=" * 80)
print("TEST: Geröstete Mandeln")
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

# TIER 3: Ollama
print("TIER 3 - Ollama KI:")
print("-" * 80)
ollama_funde = analyse_mit_ollama(text, allergien)
print(f"Funde: {len(ollama_funde)}")
for f in ollama_funde:
    allergie = f.get("allergie", "?")
    fundstelle = f.get("fundstelle", "")
    print(f'  - {allergie}: "{fundstelle}"')
