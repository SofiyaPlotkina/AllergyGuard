from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import requests

app = FastAPI()

# GANZ WICHTIG: Erlaubt dem Browser-Plugin, mit eurem Server zu sprechen (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RecipeRequest(BaseModel):
    ingredients: str

@app.post("/check-recipe")
def check_recipe(request: RecipeRequest):
    conn = sqlite3.connect('allergen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, allergy FROM users LIMIT 1')
    user = cursor.fetchone()
    conn.close()

    user_name = user[0]
    user_allergy = user[1]

    # 2. Den "Prompt" für eure lokale KI zusammenbauen (Jetzt viel strenger!)
    prompt = f"""Du bist ein strikter Assistent für Lebensmittelsicherheit. 
    Hier ist der Text einer Webseite (Zutaten): "{request.ingredients}". 
    Der Nutzer {user_name} hat eine lebensbedrohliche Allergie gegen: {user_allergy}. 
    
    Regeln:
    1. Suche akribisch nach dem Allergen. 
    2. Achte GANZ BESONDERS auf Sätze wie "Kann Spuren von ... enthalten". Wenn das Allergen dort steht, ist es NICHT sicher!
    3. Antworte immer zuerst mit einem lauten und klaren "NEIN, GEFAHR!" oder "JA, SICHER!".
    4. Erkläre danach in einem kurzen Satz, warum.
    """

    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.1",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(ollama_url, json=payload)
        response_data = response.json()
        ki_antwort = response_data.get("response", "Keine Antwort von KI")
    except Exception as e:
        ki_antwort = f"Fehler bei der KI-Verbindung. Läuft Ollama? Fehler: {e}"

    return {
        "nutzer": user_name,
        "allergie_geprueft": user_allergy,
        "ki_warnung": ki_antwort
    }