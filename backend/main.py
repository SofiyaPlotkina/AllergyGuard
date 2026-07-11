from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .db import get_history, init_db, load_profile, save_history, save_profile
    from .models import ProfileRequest, RecipeRequest
    from .recognition import analyze_text
except ImportError:  # pragma: no cover - fallback for direct execution
    from db import get_history, init_db, load_profile, save_history, save_profile
    from models import ProfileRequest, RecipeRequest
    from recognition import analyze_text

import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.get("/profile")
def get_profile():
    profile = load_profile()
    return {"name": profile["name"], "allergy": profile["allergy"]}


@app.post("/profile")
def save_profile_endpoint(req: ProfileRequest):
    save_profile(req.name, req.allergy)
    return {"status": "ok"}


@app.get("/history")
def get_history_endpoint():
    return get_history()


@app.post("/check-recipe")
def check_recipe(request: RecipeRequest):
    profile = load_profile()
    if not profile["name"] and not profile["allergy"]:
        return {"error": "Kein Benutzerprofil gefunden. Bitte Profil anlegen."}

    user_name = profile["name"]
    user_allergy = profile["allergy"]
    allergien = [item.strip() for item in user_allergy.split(",") if item.strip()]

    result = analyze_text(request.ingredients, allergien)

    save_history(
        {
            "timestamp": datetime.datetime.now().isoformat(),
            "source": request.source or "Unbekannt",
            "urteil": result["urteil"],
            "allergie_geprueft": user_allergy,
            "gefundenes_synonym": result.get("gefundenes_synonym", ""),
            "fundstelle": result.get("fundstelle", ""),
            "grund": result.get("grund", ""),
            "methode": result.get("methode", "synonym"),
        }
    )

    return {
        "nutzer": user_name,
        "allergie_geprueft": user_allergy,
        "urteil": result["urteil"],
        "gefundenes_synonym": result.get("gefundenes_synonym", ""),
        "fundstelle": result.get("fundstelle", ""),
        "grund": result.get("grund", ""),
        "methode": result.get("methode", "synonym"),
        "alle_funde": result.get("alle_funde", []),
        "alle_ersatz_vorschlaege": result.get("alle_ersatz_vorschlaege", []),
    }
