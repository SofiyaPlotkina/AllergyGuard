from typing import Optional
from pydantic import BaseModel


class RecipeRequest(BaseModel):
    ingredients: str
    source: Optional[str] = "Unbekannt"


class ProfileRequest(BaseModel):
    name: str
    allergy: str
