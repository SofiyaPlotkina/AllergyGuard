# AllergyGuard – Ticket-Übersicht

Stand: 2026-07-06, Branch `prototyp_jasmine` (Repo: SofiyaPlotkina/AllergyGuard)

Hinweis zu Ordnern: Der eigentliche Code liegt im Ordner `AllergyGuard` (Backend + Extension). Der Ordner `AllergenGuard` enthält aktuell keinen Code (nur einen Lebenslauf).

---

## Anforderungs-Check (Original-Idee #8 + Paar's Hinweis)

| Anforderung | Status | Kommentar |
|---|---|---|
| Plugin liest Rezeptseite aus | ✅ erledigt | `popup.js` extrahiert Zutaten über schema.org-Microdata, JSON-LD, CSS-Heuristik, Fallback Body-Text |
| Warnung vor Allergenen (Ei, Nüsse, Milch, etc.) | ✅ erledigt | 14 Allergenkategorien mit umfangreichen Synonymlisten (DE/EN) hinterlegt |
| Backend prüft gegen Allergenliste | ✅ erledigt | FastAPI-Endpunkt `/check-recipe`, SQLite für Profil & Verlauf |
| Ergebnis im Popup | ✅ erledigt | Ampel-Anzeige GEFAHR/WARNUNG/SICHER inkl. Fundstelle |
| Optional: Alternativen vorschlagen | ❌ offen | Keine Ersatzzutaten-Logik im Code vorhanden |
| **Paar's Hinweis: LLM zur Allergenerkennung** | ✅ erledigt | Lokales Llama 3.1 über Ollama (`analyse_mit_ollama`) |
| **Paar's Hinweis: zusätzlich spezielle API verwenden** | ⚠️ teilweise | OpenFoodFacts-API ist eingebaut, greift aber nur bei erkanntem Barcode (EAN-8/13) – nicht für die eigentlichen Rezeptseiten-Zutaten, die den Kern-Use-Case bilden |
| **"Beide Ansätze umsetzen"** | ⚠️ teilweise | Beide Bausteine existieren technisch, laufen aber nacheinander als Fallback-Kette (OFF → Ollama → Synonym-Matching) statt als kombinierte/vergleichende Prüfung pro Zutat |

Kurz: Das MVP aus der Idee ist im Kern umgesetzt. Die Alternativen-Vorschläge fehlen komplett, und der "beide Ansätze"-Hinweis ist nur für Barcode-Produkte vollständig gelöst, nicht für Freitext-Rezepte (der Hauptfall).

---

## Erledigt

### T-01 Browser-Extension Grundgerüst
Manifest V3, Popup mit vier Tabs (Scan, Eingabe, Verlauf, Profil). `extension/manifest.json`, `popup.html`.

### T-02 Automatische Zutaten-Extraktion von Webseiten
Erkennt schema.org `Recipe`-Markup, JSON-LD-Rezeptdaten, gängige CSS-Klassen (`ingredient`, `zutat`, `recipe`, …), Fallback auf Seitentext. `popup.js::extractPageText`.

### T-03 Manuelle Texteingabe
Zweiter Tab zum Einfügen von Zutaten-/Verpackungstext ohne Live-Seite.

### T-04 FastAPI-Backend mit SQLite
Tabellen `users`, `history`, `off_cache`. Endpunkte `/profile` (GET/POST), `/history`, `/check-recipe`. `backend/main.py`.

### T-05 Allergenprofil mit 14 Kategorien
Erdnuss, Milch, Ei, Gluten, Soja, Nüsse, Fisch, Sesam, Sellerie, Senf, Lupine, Krebstiere, Weichtiere, Sulfite – jeweils mit ausführlichen DE/EN/wissenschaftlichen Synonymen inkl. Produktnamen (z. B. Nutella, Tiramisu, Worcestersauce).

### T-06 Profil-UI mit Schnellauswahl & Suche
Top-8-Buttons, durchsuchbare Volltextliste, Freitextfeld synchron gehalten. `popup.js::buildPicker`.

### T-07 Drei-stufige Analyse-Pipeline
1. OpenFoodFacts-API bei erkanntem Barcode (mit 7-Tage-Cache in `off_cache`)
2. Lokales LLM (Ollama/Llama 3.1) als Haupt-Fallback für Freitext
3. Regelbasiertes Synonym-Matching (mit Wortgrenzen-Schutz gegen Falschpositive wie "Ei" in "Eisen") als letzter Fallback

### T-08 Verlaufsanzeige
Letzte 20 Prüfungen mit Zeitstempel, Quelle, Urteil, verwendeter Methode. Automatisches Aufräumen alter Einträge in der DB.

### T-09 Spuren-Erkennung
Unterscheidung zwischen direktem Allergen-Fund (GEFAHR) und "kann Spuren enthalten"-Hinweisen (WARNUNG) über Phrasenliste `SPUREN_PHRASEN`.

---

## Offen

### T-10 Alternativen-Vorschläge (aus Originalidee, "optional")
Backend/LLM sollen bei erkanntem Allergen einen Ersatz vorschlagen (z. B. "Erdnussöl → Sonnenblumenöl"). Bisher nicht implementiert, weder im Ollama-Prompt noch als eigener Endpunkt.

### T-11 Spezielle API auch für Freitext-Rezepte nutzen
Laut Hinweis sollen LLM-Ansatz **und** API-Ansatz für die eigentliche "welche Allergene pro Zutat"-Erkennung eingesetzt werden. Aktuell prüft OpenFoodFacts nur Barcodes. Zu klären: welche API ist gemeint (OpenFoodFacts Ingredient-Parsing, Edamam, Spoonacular o. Ä.) und wie sie mit Freitext-Zutatenlisten (nicht nur Produktnamen) arbeitet.

### T-12 Pro-Zutat-Aufschlüsselung statt Gesamttext-Prompt
Ollama bekommt aktuell den kompletten Text auf einmal; es gibt keine strukturierte Zerlegung "Zutat 1 → Allergen X, Zutat 2 → kein Allergen". Für Nachvollziehbarkeit und um beide Ansätze (LLM + API) pro einzelner Zutat vergleichbar zu machen, wäre eine Zutatenliste als Zwischenschritt sinnvoll.

### T-13 Tests
Keine Unit- oder Integrationstests vorhanden (weder Backend noch Extension).

### T-14 Multi-User-Fähigkeit
`users`-Tabelle unterstützt nur ein Profil (`LIMIT 1` im Code). Für mehrere Nutzer (z. B. Familie) müsste die Profilverwaltung erweitert werden.

### T-15 Fehlerbehandlung Ollama/Backend nicht erreichbar
Aktuell nur generische try/except-Blöcke; kein klares Nutzer-Feedback im Popup, wenn Ollama nicht läuft oder das Modell fehlt (nur "Server nicht erreichbar" für Backend-Verbindung selbst).

### T-16 Browser-Kompatibilität
Nur Chrome/Chromium (Manifest V3) unterstützt; Firefox/Safari nicht getestet oder vorbereitet.

### T-17 Deployment / Produktivbetrieb
Reines Localhost-Setup (Backend `127.0.0.1:8080`, Ollama `localhost:11434`). Kein Konzept für gehostetes Backend, Icons/Branding fehlen im Manifest.

### T-18 Uncommitted Changes sichern
`backend/main.py`, `extension/popup.html`, `extension/popup.js` sind im Arbeitsverzeichnis geändert, aber noch nicht committet (letzter Commit: "update README", 24.06.2026). Der aktuelle Funktionsstand (Synonymlisten, OFF-Integration, Verlauf, Profil-Picker) ist damit noch nicht im Repo gesichert.

---

## Zusammenfassung

Kernfunktionalität des MVP steht (Extraktion → Backend-Prüfung → Popup-Ergebnis) und übertrifft das Original-MVP bereits deutlich (Barcode-Support, Verlauf, Profilverwaltung, umfangreiche Synonymlisten). Die zwei offenen Punkte mit größter Priorität sind: T-18 (Arbeit committen, sonst geht sie verloren) und T-11 (spezielle API auch für Rezepttexte statt nur Barcodes einbinden, wie von Paar gefordert). T-10 (Alternativen) war laut Idee ohnehin nur optional.
