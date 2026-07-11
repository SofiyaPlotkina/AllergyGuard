# AllergyGuard Architektur

## Ziel

Die Anwendung soll Rezepte und Produkttexte analysieren und Allergene erkennen. Dabei soll die Erkennung gleichzeitig:

1. eine lokale KI (Ollama) nutzen,
2. eine strukturierte Allergen-Datenbank bzw. Regeln verwenden,
3. einen Fallback über lokales Synonym-Matching haben.

## Aktueller Aufbau

- backend/main.py
  - FastAPI-Entry-Point
  - kümmert sich nur um API und Request/Response
- backend/recognition.py
  - zentrale Erkennungsschicht
  - orchestriert: OpenFoodFacts, Ollama, Synonym-Matching
- backend/db.py
  - Datenbankzugriff für Nutzer, Verlauf und Cache
- backend/models.py
  - Pydantic-Modelle für Requests
- backend/config.py
  - zentrale Konfiguration für DB-Pfad und Ollama

## Entscheidungsprinzip

Die Architektur ist bewusst in drei Schichten aufgebaut:

- API-Schicht: Eingaben und Ausgaben
- Service-Schicht: Erkennung und Entscheidung
- Daten-Schicht: Persistenz und Cache

Dadurch ist die Logik nicht mehr in einer einzigen Datei versteckt, sondern kann später erweitert oder ersetzt werden.

## Erweiterungspfade

- Später können zusätzliche Erkennungsanbieter wie ein lokaler Rule-Engine oder ein eigenes Modell ergänzt werden.
- Die Synonyme bleiben als Datenstruktur separat von der eigentlichen API.
- Die mehrstufige Verarbeitung (OFF -> Ollama -> Synonym-Matching) macht das System robust und nachvollziehbar.
