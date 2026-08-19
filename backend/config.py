import os

# .env für Umgebungsvariablen laden, wenn lokal wntwickelt wird
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # wenn kein python-dotenv, dann nicht lokal, nutze also OS Umgebungsvariablen (pass einfach erstmal)
    pass

# Verschiedene Möglichkeiten, auf SPuren zu verweisen. Evtl später raus aus config.py???
SPUREN_PHRASEN = [
    "kann spuren enthalten", "kann spuren von", "kann enthalten",
    "may contain", "may contain traces",
    "spuren von", "traces of",
    "nicht geeignet für personen mit allergie",
    "hergestellt in einem betrieb", "in derselben anlage",
]

# Erfasst zusätzlich "Kann <Allergen(e)> enthalten" mit Text dazwischen
# (z.B. "Kann Schalenfrüchte, Erdnüsse, Lupin, Sesam enthalten"), nicht nur
# die exakte Formulierung "kann enthalten" ohne Zwischenwörter 
# --> habe diesen Regex mit Claude erstellt, darauf bei "KI Nutzung" verweisen
SPUREN_MUSTER = r'kann\s+.{0,60}?enthalten'

OFF_CACHE_TTL_DAYS = int(os.getenv("OFF_CACHE_TTL_DAYS", "7"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "allergen.db")

# Server
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Kurze Begriffe die Wortgrenzen brauchen um Falschpositive zu vermeiden
# z.B. "ei" soll nicht "Zwiebel", "Eisen", "Protein" treffen
# "bier" soll nicht "Probieren" treffen, "teig" nicht "teigige"
# "brot" nicht in "Brotaufstrich" (Produkttyp, keine Zutat)
WORTGRENZE_SYNONYME = {
    "ei", "eier", "nut", "nuts", "cod", "rye", "oat", "oats", "malt",
    "crab", "bass", "clam", "aal", "feta", "brie",
    "bier", "teig", "brot",  # Neue: verhindern False Positives
}