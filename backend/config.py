SPUREN_PHRASEN = [
    "kann spuren enthalten", "kann spuren von",
    "may contain", "may contain traces",
    "spuren von", "traces of",
    "nicht geeignet für personen mit allergie",
    "hergestellt in einem betrieb", "in derselben anlage",
]

OFF_CACHE_TTL_DAYS = 7
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral:latest"  # Mistral: schneller, weniger Halluzinationen
# OLLAMA_MODEL = "llama3.1:latest"  # Backup: llama3.1 (falls Mistral schlechter)

# Kurze Begriffe die Wortgrenzen brauchen um Falschpositive zu vermeiden
# z.B. "ei" soll nicht "Zwiebel", "Eisen", "Protein" treffen
# "bier" soll nicht "Probieren" treffen, "teig" nicht "teigige"
# "brot" nicht in "Brotaufstrich" (Produkttyp, keine Zutat)
WORTGRENZE_SYNONYME = {
    "ei", "eier", "nut", "nuts", "cod", "rye", "oat", "oats", "malt",
    "crab", "bass", "clam", "aal", "feta", "brie",
    "bier", "teig", "brot",  # Neue: verhindern False Positives
}