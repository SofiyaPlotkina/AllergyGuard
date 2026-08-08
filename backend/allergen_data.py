"""Allergen configuration - OpenFoodFacts mappings.

NOTE: Allergen synonyms and replacement suggestions are now stored in the database\!
See allergen_db.py for database access layer.
Run migrate_allergens.py to populate the database from the old hardcoded data.
"""

# OpenFoodFacts Allergen-Tags → unsere Allergen-Schlüssel
# Diese Mapping-Konfiguration bleibt in dieser Datei (ist keine Datenstruktur, sondern Config)
OFF_TAG_MAP = {
    "en:gluten":      "gluten",
    "en:wheat":       "gluten",
    "en:milk":        "milch",
    "en:eggs":        "ei",
    "en:egg":         "ei",
    "en:fish":        "fisch",
    "en:peanuts":     "erdnuss",
    "en:peanut":      "erdnuss",
    "en:soybeans":    "soja",
    "en:soy":         "soja",
    "en:nuts":        "nüsse",
    "en:almonds":     "nüsse",
    "en:hazelnuts":   "nüsse",
    "en:walnuts":     "nüsse",
    "en:cashews":     "nüsse",
    "en:pistachios":  "nüsse",
    "en:celery":      "sellerie",
    "en:mustard":     "senf",
    "en:sesame":      "sesam",
    "en:lupin":       "lupine",
    "en:molluscs":    "weichtiere",
    "en:crustaceans": "krebstiere",
    "en:sulphites":   "sulfite",
    "en:sulphur-dioxide-and-sulphites": "sulfite",
}
