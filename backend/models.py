from pydantic import BaseModel
from typing import Optional


class RecipeRequest(BaseModel):
    ingredients: str
    source: Optional[str] = "Unbekannt"


class ProfileRequest(BaseModel):
    name: str
    allergy: str