from pydantic import BaseModel
from typing import Optional


class RecipeRequest(BaseModel):
    ingredients: str
    source: Optional[str] = "Unbekannt"


class UserProfile(BaseModel):
    name: str
    allergy: str


class SelectionUpdate(BaseModel):
    selected: bool