# AllergyGuard 🛡️

Eine Browser-Extension, die Rezepte & Verpackungstexte scannt und prüft, ob gefährliche Allergene enthalten sind. Mit lokaler KI (Llama 3.1) für vollständige Privatsphäre.

## 📋 Übersicht

**AllergyGuard** ist ein Prototyp mit drei Komponenten:

1. **Browser Extension** (TypeScript/JavaScript) — Liest Text von Websites
2. **FastAPI Backend** (Python) — Verarbeitet Anfragen & koordiniert
3. **Lokale KI** (Ollama + Llama 3.1) — Allergen-Analyse

### Wie es funktioniert

1. User klickt Button in Extension
2. Website-Text wird extrahiert (max. 2000 Zeichen)
3. Backend fragt lokale KI: "Ist das Allergen drin?"
4. KI antwortet mit "NEIN, GEFAHR!" oder "JA, SICHER!"
5. Ergebnis im Popup angezeigt

---

## 🚀 Local Setup

### Voraussetzungen

Vor dem Start checken:

```bash
# Python 3.8+
python --version

# Ollama installiert
ollama --version

# Chrome/Chromium Browser
```

Falls nicht installiert:
- **Python**: https://www.python.org/downloads/
- **Ollama**: https://ollama.ai
- **Chrome**: https://www.google.com/chrome/

---

### Installation (5-10 Minuten)

#### **Terminal 1: Backend + Datenbank**

```bash
# 1. Zum Projektordner
cd ~/AllergyGuard/backend

# 2. Dependencies installieren
pip install fastapi uvicorn requests

# 3. Datenbank initialisieren
python setup_db.py
# ✓ Output: "Datenbank 'allergen.db' wurde erfolgreich erstellt!"

# 4. FastAPI Server starten
uvicorn main:app --reload --host 127.0.0.1 --port 8080
# ✓ Server läuft wenn du siehst: "Uvicorn running on http://127.0.0.1:8080"
```

**Test**: Öffne http://127.0.0.1:8080/docs im Browser → FastAPI Swagger UI sollte erscheinen

---

#### **Terminal 2: Ollama (Local KI)**

Öffne ein **neues Terminal** (das erste nicht schließen!):

```bash
ollama serve
# ✓ Server läuft wenn du siehst: "Listening on [::]:11434"
```

**Falls Llama3.1 nicht vorhanden** (größter Download ~4GB):

Öffne ein **drittes Terminal** und lade das Model:
```bash
ollama pull llama3.1
# ⏳ Das dauert 5-10 Minuten (erste Mal)
# ✓ Fertig wenn: "pulling digest" fertig ist
```

---

#### **Chrome Extension laden**

1. Chrome öffnen
2. Gehe zu `chrome://extensions/`
3. Oben rechts: **"Developer mode"** einschalten
4. Klick **"Load unpacked"**
5. Wähle den Ordner: `~/AllergyGuard/extension`
6. Extension erscheint jetzt in deiner Chrome-Leiste ✅

---

## 🧪 Test: Funktioniert es?

1. Chrome öffnen, beliebige Website mit Zutaten öffnen (z.B. [rewe.de Rezepte](https://www.rewe.de))
2. Klick das **AllergenGuard Icon** in der Chrome-Leiste
3. Klick **"🔍 Rezept prüfen"**
4. Es sollte erscheinen:

```
Nutzer: Max
Allergie: Erdnuss
KI sagt: 
NEIN, GEFAHR! Das Rezept enthält Erdnussöl...