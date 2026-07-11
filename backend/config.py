from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "allergen.db"

OFF_CACHE_TTL_DAYS = 7
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
