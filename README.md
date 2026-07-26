# AllergyGuard 🛡️

Eine intelligente Browser-Extension, die Rezepte & Lebensmittel auf Allergene prüft. Mit **5-stufiger Extraktionskaskade**, **3-Tier-Analysepipeline** und **lokaler KI** für vollständige Privatsphäre.

---

## 📋 Übersicht

**AllergyGuard** kombiniert moderne Web-Technologien mit lokaler KI-Analyse, um Allergiker beim sicheren Einkaufen und Kochen zu unterstützen.

### 🏗️ Architektur (4 Komponenten)

1. **🌐 Chrome Extension** (Manifest V3) — Intelligente Textextraktion von Webseiten
2. **⚡ FastAPI Backend** (Python) — 3-Tier-Analysepipeline mit Caching
3. **🗄️ OpenFoodFacts API** — Allergen-Datenbank für Barcode-Produkte
4. **🤖 Ollama + Llama 3** — Lokale KI für AI-gestützte Analyse

### ✨ Key Features

- **🎯 Intelligente Extraktion**: 5-stufige Kaskade (JSON-LD → Microdata → CSS-Selektoren → Heading-Search → Fallback)
- **🔬 Multi-Methoden-Analyse**: OpenFoodFacts (Barcodes) → Ollama (KI) → Synonym-Matching (Fallback)
- **📊 14 Allergene**: Erdnuss, Milch, Ei, Gluten, Soja, Nüsse, Fisch, Sellerie, Senf, Sesam, Lupine, Weichtiere, Krebstiere, Sulfite
- **💡 Smart Suggestions**: ~200 Ersatzvorschläge für gefundene Allergene
- **📝 History**: Letzte 20 Prüfungen mit vollständigem Snapshot
- **🔒 Privacy First**: Alle Daten bleiben lokal (nur Barcodes gehen zu OpenFoodFacts)
- **⚡ Performance**: 7-Tage-Cache für OpenFoodFacts-Anfragen

---

## 🚀 Installation & Setup

### Voraussetzungen

```bash
# Python 3.8+
python --version

# Ollama installiert
ollama --version

# Chrome/Chromium Browser
```

**Installation:**
- **Python**: https://www.python.org/downloads/
- **Ollama**: https://ollama.ai
- **Chrome**: https://www.google.com/chrome/

---

### 1️⃣ Backend Setup (Terminal 1)

```bash
# In den Backend-Ordner wechseln
cd backend

# Virtual Environment erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install fastapi uvicorn requests

# FastAPI Server starten
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

**✅ Erfolg**: Server läuft auf `http://127.0.0.1:8080` — API-Docs unter `/docs` verfügbar

> **Hinweis**: Die Datenbank (`allergen.db`) wird beim ersten Start automatisch initialisiert.

---

### 2️⃣ Ollama Setup (Terminal 2)

```bash
# Ollama Server starten
ollama serve
```

**✅ Erfolg**: Server lauscht auf `[::]:11434`

```bash
# Llama 3 Model herunterladen (einmalig, ~4GB)
ollama pull llama3
```

> **Tipp**: Der erste Download dauert 5-10 Minuten. Danach ist das Modell lokal verfügbar.

---

### 3️⃣ Extension laden

1. Chrome öffnen → `chrome://extensions/`
2. **"Developer mode"** (oben rechts) aktivieren
3. **"Load unpacked"** klicken
4. Ordner `extension/` auswählen
5. ✅ AllergyGuard erscheint in der Chrome-Toolbar

---

## 🧪 Benutzung

### Profil einrichten

1. Extension-Icon klicken
2. Tab **"Profil"** öffnen
3. Name eingeben
4. Allergien auswählen (8 häufigste als Quick-Buttons, weitere in Liste)
5. **"Speichern"** klicken

### Rezept prüfen (2 Methoden)

#### **Methode 1: Automatischer Scan**
1. Rezept-Website öffnen (z.B. Chefkoch.de, Rewe Rezepte)
2. Extension-Icon klicken → Tab **"Scan"**
3. **"🔍 Rezept prüfen"** klicken
4. ⏳ Extension extrahiert automatisch Zutaten
5. 📊 Ergebnis wird angezeigt

#### **Methode 2: Manuelle Eingabe**
1. Extension-Icon klicken → Tab **"Eingabe"**
2. Zutatenliste ins Textfeld kopieren
3. **"Prüfen"** klicken
4. 📊 Ergebnis wird angezeigt

### Ergebnis verstehen

**🚫 GEFAHR** (Rot)
- Allergen wurde direkt gefunden
- **Nicht sicher** für dein Profil
- Zeigt: Synonym, Fundstelle, Ersatzvorschläge

**⚠️ WARNUNG** (Gelb)
- Spurenhinweise gefunden ("kann Spuren enthalten")
- **Vorsicht geboten**

**✅ SICHER** (Grün)
- Keine Allergene gefunden
- **Sicher** für dein Profil

### Verlauf anzeigen

- Tab **"Verlauf"** öffnet die letzten 20 Prüfungen
- **Klick auf Eintrag** zeigt Details (expandierbar)
- Farb-Dots zeigen Urteil (🔴 Gefahr, 🟡 Warnung, 🟢 Sicher)

---

## 🏛️ Architektur-Details

### Extension: 5-Stufen-Extraktionskaskade

Die Extension versucht in dieser Reihenfolge, Zutaten zu extrahieren:

1. **JSON-LD**: Strukturierte Recipe-Daten (`<script type="application/ld+json">`)
2. **Microdata**: HTML5 Microdata mit `itemtype="http://schema.org/Recipe"`
3. **Bekannte Selektoren**: 40+ CSS-Selektoren für populäre Rezept-Sites
4. **Heading-basiert**: Suche nach "Zutaten"-Überschriften + folgende Listen
5. **Fallback**: Titel + alle Listen + erste 5.000 Zeichen Body-Text

**Nachverarbeitung**: Bereinigung, Deduplizierung, Kürzung auf 6.000 Zeichen

### Backend: 3-Tier-Analysepipeline

```
1. OpenFoodFacts (Barcode-Suche)
   ├─ Barcode im Text? → API-Call
   ├─ Cache prüfen (7 Tage TTL)
   ├─ allergen_tags & traces_tags abgleichen
   └─ ❌ Kein Barcode → weiter zu 2.

2. Ollama (KI-Analyse)
   ├─ Prompt mit User-Allergenen
   ├─ LLM antwortet mit JSON-Array
   ├─ Enthält: allergie, synonym, fundstelle, ist_spur, ersatz
   └─ ❌ Ollama nicht erreichbar → weiter zu 3.

3. Synonym-Matching (Fallback)
   ├─ ~900 Synonyme in 14 Sprachen/Varianten
   ├─ Wortgrenzen-bewusste Suche
   ├─ Spuren-Erkennung (±150 Zeichen Kontext)
   └─ ✅ Immer verfügbar (keine externe Abhängigkeit)
```

### Datenbank (SQLite)

**3 Tabellen:**

- `users`: Nutzer-Profile (Name + Allergien)
- `history`: Letzte 20 Prüfungen + vollständiger JSON-Snapshot
- `off_cache`: OpenFoodFacts-Responses (7 Tage TTL)

---

## 📁 Projektstruktur

```
AllergyGuard/
├── backend/
│   ├── allergen.db              # SQLite Datenbank
│   ├── allergen_data.py         # 832 Zeilen: Synonyme, Tags, Ersatz
│   ├── synonym_matcher.py       # 55 Zeilen: Lokales Matching
│   ├── openfoodfacts_client.py  # 119 Zeilen: OFF API + Cache
│   ├── ollama_client.py         # 38 Zeilen: KI-Client
│   ├── main.py                  # 186 Zeilen: FastAPI Routes
│   ├── config.py                # 17 Zeilen: Konstanten
│   ├── database.py              # 48 Zeilen: DB-Init + Helfer
│   └── models.py                # 11 Zeilen: Pydantic Models
│
├── extension/
│   ├── manifest.json            # Extension Config (Manifest V3)
│   ├── popup.html               # UI mit Tabs + CSS
│   ├── popup.js                 # Bootstrap + Event-Handler
│   └── scripts/
│       ├── namespace.js         # Globaler AllergyGuard-Namespace
│       ├── extract.js           # 5-Stufen-Extraktionskaskade
│       ├── render.js            # Result-Rendering (Banner, Funde)
│       ├── api.js               # Backend-Kommunikation
│       ├── history.js           # Verlauf mit Expand-Details
│       └── profile.js           # Allergen-Picker (14 Allergene)
│
├── docs/
│   └── refactor-contract.md    # Refactor-Spezifikation
│
└── README.md                    # Diese Datei
```

---

## 🔬 Technische Details

### Wissensbasis (832 Zeilen)

**ALLERGEN_SYNONYME**: 14 Allergene × ~60 Synonyme
- Deutsch, Englisch, Lateinisch
- Versteckte Quellen (z.B. "Satay" bei Erdnuss, "Worcestersauce" bei Fisch)

**OFF_TAG_MAP**: Übersetzt OpenFoodFacts-Tags
- `en:peanuts` → `erdnuss`
- `en:milk` → `milch`
- etc.

**ERSATZ**: ~200 Ersatzvorschläge
- `Eigelb` → Leinsamengel, Aquafaba, Apfelmus
- `Butter` → Margarine, Kokosöl, Avocado
- etc.

### Spuren-Erkennung

**SPUREN_PHRASEN**: 7 Formulierungen
- "kann Spuren enthalten"
- "kann Spuren von ... enthalten"
- "möglicherweise ... enthalten"
- etc.

**Kontext-Analyse**: ±150 Zeichen um Fund herum prüfen

### Performance-Optimierungen

- **OpenFoodFacts Cache**: 7 Tage TTL, reduziert API-Calls
- **History-Limit**: Max. 20 Einträge, älteste werden gelöscht
- **Text-Limit**: 6.000 Zeichen pro Analyse
- **Wortgrenzen-Matching**: Verhindert False Positives (z.B. "Ei" in "Eisen")

---

## 🛠️ Entwicklung

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Module-Import testen
python -c "import main; print('✅ Backend OK')"

# Syntax-Checks
python -m py_compile *.py
```

### Extension Tests

```bash
cd extension/scripts

# JavaScript-Syntax prüfen
for f in *.js; do node --check "$f"; done
```

---

## 📝 API-Endpunkte

### `GET /profile`
Lädt gespeichertes Profil (erster User)

**Response**: `{"name": "Max", "allergy": "Erdnuss,Milch"}`

### `POST /profile`
Speichert Profil

**Body**: `{"name": "Max", "allergy": "Erdnuss,Milch"}`

### `GET /history`
Lädt letzte 20 Prüfungen

**Response**: `[{...}, {...}]` (mit `result_snapshot` für Details)

### `POST /check-recipe`
Analysiert Rezept/Zutaten

**Body**: `{"ingredients": "250g Erdnussbutter...", "source": "chefkoch.de"}`

**Response**:
```json
{
  "nutzer": "Max",
  "allergie_geprueft": "Erdnuss",
  "urteil": "GEFAHR",
  "gefundenes_synonym": "Erdnussbutter",
  "fundstelle": "250g Erdnussbutter, cremig",
  "grund": "Direkte Allergene: Erdnuss. (via synonym)",
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

## 🤝 Contributing

Dies ist ein Prototyp für das Modul "Serverseitige Technologien". Verbesserungsvorschläge willkommen!

### Roadmap-Ideen
- [ ] Browser-kompatibilität (Firefox, Edge)
- [ ] Mehr Sprachen (EN, FR, IT)
- [ ] Offline-Modus (alle Daten lokal)
- [ ] Mobile App Version
- [ ] Export/Import von Profilen

---

## 📄 Lizenz

MIT License — Projekt entwickelt im Rahmen des Studiums.

---

## 🙏 Credits

- **OpenFoodFacts**: https://world.openfoodfacts.org
- **Ollama**: https://ollama.ai
- **Llama 3**: Meta AI
- **FastAPI**: https://fastapi.tiangolo.com

---

**Made with 💚 for Allergiker**