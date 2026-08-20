# AllergyGuard

Eine Chrome-Extension mit FastAPI-Backend, die Rezepte und Lebensmittel-Produktseiten auf Allergene prüft. Die Analyse läuft in einer 3-Tier-Pipeline aus OpenFoodFacts-Abgleich, lokalem Synonym-Matching und lokaler KI (Ollama) als Fallback.

---

## Übersicht

**AllergyGuard** kombiniert eine Browser-Extension zur Textextraktion mit einem Python-Backend, das Zutatentexte gegen die Allergien eines oder mehrerer Nutzerprofile prüft.

### Architektur (4 Komponenten)

1. **Chrome Extension** (Manifest V3) — Textextraktion von Rezept- und Produktseiten, Anzeige der Ergebnisse
2. **FastAPI Backend** (Python) — 3-Tier-Analysepipeline, Nutzerverwaltung, Verlauf
3. **OpenFoodFacts API** — Allergen-Daten für Produkte per Barcode oder Produktname
4. **Ollama** (lokale KI, Default-Modell `mistral`) — Fallback-Analyse, falls OpenFoodFacts und Synonym-Matching nichts finden

### Key Features

- **Extraktions-Kaskade**: JSON-LD → Microdata → bekannte CSS-Selektoren → Heading-Suche → Fallback (kompletter Seitentext)
- **3-Tier-Analyse**: OpenFoodFacts (Barcode/Produktname) und lokales Synonym-Matching laufen immer; Ollama greift nur, wenn beide nichts finden
- **14 Allergene**: Erdnuss, Milch, Ei, Gluten, Soja, Nüsse, Fisch, Sellerie, Senf, Sesam, Lupine, Weichtiere, Krebstiere, Sulfite
- **Über 1.200 Synonyme** in der lokalen Allergen-Datenbank, plus ~180 Ersatzvorschläge für gefundene Allergene
- **Mehrere Profile gleichzeitig**: Beliebig viele Nutzerprofile anlegen, mehrere davon gleichzeitig aktivieren — ihre Allergien werden für die Prüfung kombiniert
- **Verlauf**: Letzte 20 Prüfungen inkl. vollständigem Ergebnis-Snapshot
- **Privacy**: Zutatentexte werden nur lokal (Backend + Ollama) verarbeitet; nur erkannte Barcodes/Produktnamen gehen an die OpenFoodFacts-API
- **Caching**: OpenFoodFacts-Antworten werden 7 Tage lokal gecacht

---

## Installation & Setup

### Voraussetzungen

```bash
# Python 3.8+
python --version

# Ollama installiert
ollama --version

# Chrome/Chromium Browser
```

- **Python**: https://www.python.org/downloads/
- **Ollama**: https://ollama.ai
- **Chrome**: https://www.google.com/chrome/

---

### 1. Backend Setup (Terminal 1)

```bash
cd backend

# Virtual Environment erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# FastAPI Server starten
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

**Erfolg**: Server läuft auf `http://127.0.0.1:8080` — API-Docs unter `/docs`.

> Die Datenbank (`allergen.db`) sowie alle Tabellen werden beim ersten Start automatisch angelegt/migriert. Beim allerersten Start wird zudem ein Demo-Profil ("Demo", Allergie: Erdnuss) erstellt.

Optional lässt sich das Verhalten über eine `.env`-Datei anpassen (siehe `backend/.env.example`), u. a. das verwendete Ollama-Modell, der Server-Port oder das OpenFoodFacts-Cache-TTL.

---

### 2. Ollama Setup (Terminal 2)

```bash
ollama serve
```

**Erfolg**: Server lauscht auf `[::]:11434`.

```bash
# Standardmodell herunterladen (einmalig, ~4GB)
ollama pull mistral
```

> Das Backend nutzt standardmäßig `mistral:latest` (konfigurierbar über die Umgebungsvariable `OLLAMA_MODEL` in `backend/.env`).

---

### 3. Extension laden

1. Chrome öffnen → `chrome://extensions/`
2. **"Developer mode"** (oben rechts) aktivieren
3. **"Load unpacked"** klicken
4. Ordner `extension/` auswählen
5. AllergyGuard erscheint in der Chrome-Toolbar

---

## Benutzung

### Profil(e) einrichten

1. Extension-Icon klicken → Tab **"Profil"**
2. **"+ Neues Profil"** klicken, Name eingeben
3. Allergien auswählen (aktuell per Klick auswählbar: Gluten, Milch, Erdnuss, Ei)
4. Speichern
5. Über die Checkbox neben jedem Profil festlegen, welche(s) Profil(e) aktuell für die Prüfung berücksichtigt werden sollen — bei mehreren aktiven Profilen werden deren Allergien kombiniert geprüft

### Rezept/Produkt prüfen (2 Methoden)

**Methode 1: Automatischer Scan**
1. Rezept- oder Produkt-Website öffnen
2. Extension-Icon klicken → Tab **"Scan"** → **"Rezept prüfen"**
3. Die Extension extrahiert automatisch den relevanten Text und zeigt das Ergebnis an

**Methode 2: Manuelle Eingabe**
1. Extension-Icon klicken → Tab **"Eingabe"**
2. Zutatenliste ins Textfeld einfügen → **"Prüfen"**

### Ergebnis verstehen

- **GEFAHR** (Rot) — Allergen wurde direkt in den Zutaten gefunden, nicht sicher für das geprüfte Profil; zeigt Synonym, Fundstelle und Ersatzvorschläge
- **WARNUNG** (Gelb) — Nur Spurenhinweise gefunden ("kann Spuren enthalten" o. ä.), Vorsicht geboten
- **SICHER** (Grün) — Keine Allergene gefunden

### Verlauf anzeigen

- Tab **"Verlauf"** zeigt die letzten 20 Prüfungen
- Klick auf einen Eintrag zeigt die vollständigen Details

---

## Architektur-Details

### Extension: Extraktions-Kaskade

Die Extension versucht in dieser Reihenfolge, den relevanten Text zu extrahieren (`extension/scripts/extract.js`):

1. **JSON-LD**: Strukturierte Recipe-Daten (`<script type="application/ld+json">`)
2. **Microdata**: HTML5 Microdata mit `itemtype="...Recipe"`
3. **Bekannte Selektoren**: CSS-Selektoren für Zutaten-, Allergen- und Produktbeschreibungs-Bereiche
4. **Heading-basiert**: Sucht nach Überschriften wie "Zutaten"/"Allergene" und liest die folgenden Elemente
5. **Fallback**: kompletter sichtbarer Seitentext

Nachverarbeitung: Zeilen-Deduplizierung, Kürzung auf 6.000 (bzw. bis zu 10.000 im Fallback) Zeichen.

### Backend: 3-Tier-Analysepipeline

```
1. OpenFoodFacts (Tier 1)
   ├─ Barcode im Text gefunden? → OFF-API-Abfrage
   ├─ Sonst: Versuch, Produktnamen im Freitext zu erkennen
   ├─ Cache prüfen (7 Tage TTL)
   └─ allergens_tags gegen Nutzerallergien abgleichen

2. Lokales Synonym-Matching (Tier 2)
   ├─ Läuft immer, unabhängig vom Ergebnis aus Tier 1
   ├─ 14 Allergene, 1.200+ Synonyme aus der lokalen DB
   ├─ Wortgrenzen-bewusstes Matching, False-Positive-Filter
   │  (z. B. "Ei" in "Eisen", "Eiweiß" im Nährwert- statt Zutatenkontext)
   └─ Spuren-Erkennung anhand von Formulierungen wie "kann Spuren enthalten"

3. Ollama-KI (Tier 3, Fallback)
   ├─ Wird nur angefragt, wenn Tier 1 UND Tier 2 nichts gefunden haben
   ├─ Kurzer Prompt mit den Nutzerallergien + Zutatentext
   └─ Ergebnis wird nachträglich gegen dieselben False-Positive-Filter geprüft
```

### Datenbank (SQLite, `backend/allergen.db`)

- `users` — Profile (Name, Allergien als kommaseparierte Liste, `selected`-Flag für die aktive Prüfung)
- `history` — letzte 20 Prüfungen inkl. vollständigem JSON-Snapshot
- `allergen_synonyms` — Allergen ↔ Synonym-Zuordnungen (Wissensbasis für Tier 2)
- `allergen_replacements` — Ersatzvorschläge je gefundenem Begriff
- `off_tag_map` — Übersetzung von OpenFoodFacts-Tags (z. B. `en:peanuts`) auf interne Allergie-Namen
- `off_products` — lokal bekannte OFF-Produkte (aus Barcode-Scans/Textsuchen)
- `off_cache` — gecachte OpenFoodFacts-Antworten (7 Tage TTL)

---

## Projektstruktur

```
AllergyGuard/
├── backend/
│   ├── allergen.db                # SQLite-Datenbank
│   ├── main.py                    # FastAPI-Routen, 3-Tier-Pipeline
│   ├── config.py                  # Konstanten & Umgebungsvariablen
│   ├── database.py                # DB-Init/Migration + Verbindungs-Helfer
│   ├── models.py                  # Pydantic-Models
│   ├── allergen_db.py             # DB-Zugriff auf Synonyme/Ersatz/OFF-Tag-Map (In-Memory-Cache)
│   ├── synonym_matcher.py         # Tier 2: lokales Synonym-Matching
│   ├── text_filter.py             # Extrahiert Zutaten-Sektion aus Rohtext
│   ├── filters.py                 # False-Positive-/Kontext-Filter
│   ├── openfoodfacts_client.py    # Tier 1: OFF-API-Client + Cache
│   ├── ollama_client.py           # Tier 3: Ollama-Client + Post-Filter
│   ├── synonym_learner.py         # Optionales dynamisches Synonym-Lernen
│   ├── import_data/                # Einmalige Import-/Migrationsskripte für die Synonym-DB (USDA-Quelldaten)
│   └── tests/                     # pytest-Suite
│
├── extension/
│   ├── manifest.json              # Extension-Konfiguration (Manifest V3)
│   ├── popup.html                 # UI mit Tabs (Scan, Eingabe, Verlauf, Profil)
│   ├── popup.js                   # Bootstrap + Event-Handler
│   └── scripts/
│       ├── namespace.js           # Globaler AllergyGuard-Namespace + API-Basis-URL
│       ├── extract.js             # Extraktions-Kaskade
│       ├── api.js                 # Backend-Kommunikation
│       ├── render.js              # Ergebnis-Rendering
│       └── profile.js             # Profil-/Allergien-Verwaltung (Mehrfachauswahl)
│
└── README.md
```

---

## API-Endpunkte

### `GET /users`
Alle Profile inkl. `selected`-Status (welche gerade für die Prüfung aktiv sind).

### `POST /users`
Legt ein neues Profil an (standardmäßig aktiv).
**Body**: `{"name": "Max", "allergy": "Erdnuss,Milch"}`

### `PUT /users/{user_id}`
Aktualisiert Name/Allergien eines Profils.

### `DELETE /users/{user_id}`
Löscht ein Profil.

### `PATCH /users/{user_id}/selection`
Aktiviert/deaktiviert ein Profil für die Prüfung.
**Body**: `{"selected": true}`

### `GET /history`
Lädt die letzten 20 Prüfungen.

### `POST /check-recipe`
Analysiert einen Zutatentext gegen die Allergien aller aktuell aktiven Profile.

**Body**: `{"ingredients": "250g Erdnussbutter...", "source": "chefkoch.de"}`

**Response**:
```json
{
  "nutzer": "Max",
  "allergie_geprueft": "Erdnuss",
  "urteil": "GEFAHR",
  "gefundenes_synonym": "Erdnussbutter",
  "fundstelle": "250g Erdnussbutter, cremig",
  "grund": "Direkt gefunden: Erdnuss. (via synonym)",
  "methode": "synonym",
  "alle_funde": [
    {
      "allergie": "Erdnuss",
      "synonym": "Erdnussbutter",
      "fundstelle": "250g Erdnussbutter, cremig",
      "ist_spur": false,
      "ersatz": ["Mandelbutter", "Cashewbutter", "Sonnenblumenkernmus"]
    }
  ]
}
```

---

## Data Sources & Licenses

This project uses foundational data sourced from the **USDA Food Data Central** database to power the local synonym matching.

- **Source:** USDA Food Database (~10,000 categorized ingredients)
- **License:** [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- **Modifications:** The original dataset was cleaned, filtered for 16 major allergen categories, and adapted specifically for local allergen detection in this prototype.

In addition, product/barcode lookups at runtime are powered by the **OpenFoodFacts** database (https://world.openfoodfacts.org), queried live via their public API and cached locally for 7 days. OpenFoodFacts data is community-contributed and licensed under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/).

---

## Entwicklung

### Backend Tests

```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

### Extension Syntax-Check

```bash
cd extension/scripts
for f in *.js; do node --check "$f"; done
```

CI führt beide Checks bei jedem Push/PR auf `main` aus (`.github/workflows/tests.yml`).

---

## Lizenz

Prototyp, entwickelt im Rahmen des Studiums (Modul "Serverseitige Technologien"). Für die verwendeten Fremddaten gelten die oben genannten Lizenzen (USDA/Apache 2.0, OpenFoodFacts/ODbL).

## Credits

- **OpenFoodFacts**: https://world.openfoodfacts.org
- **USDA Food Data Central**: https://fdc.nal.usda.gov
- **Ollama**: https://ollama.ai
- **FastAPI**: https://fastapi.tiangolo.com
