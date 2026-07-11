# AllergyGuard Troubleshooting

## Problem: "SICHER" bei Sportriegel statt "WARNUNG"

### Ursache
Die automatische Zutaten-Extraktion (Scan-Tab) funktioniert möglicherweise nicht auf allen Websites. Sie holt möglicherweise nur ein Wort wie "Sportriegel" ohne die Allergie-Hinweise.

### Lösung 1: Nutze die Eingabe-Tab (Manual)
1. Navigiere zum **"Eingabe"** Tab in der Extension
2. Kopiere den kompletten Produkttext inkl. Allergie-Hinweise:
   ```
   Sportriegel mit Spuren von glutenhaltigen Cerealien 
   und glutenhaltige Cerealienerzeugnissen
   ```
3. Klicke **"Text prüfen"**
4. Ergebnis sollte jetzt **WARNUNG** mit **Spurenhinweis** sein ✓

### Lösung 2: Verbesserte automatische Extraktion
Die Extension wurde verbessert um:
- Allergie-Hinweise zu erkennen ("allergen", "spuren", "may contain")
- Mehr Text zu extrahieren wenn Allergie-Keywords gefunden werden
- Fallback auf vollständigen Body-Text

**Danach:** Extension neu laden (Browser F5 oder Cmd+R)

---

## Korrekte Ergebnisse für verschiedene Szenarien

| Text | Erwartet | Urteil | Ist Spur |
|------|----------|--------|----------|
| "10 EL Mehl, 2 Eigelb" | Hauptzutaten | GEFAHR | False |
| "Kann Spuren von Gluten enthalten" | Nur Spuren | WARNUNG | True |
| "Mit glutenhaltigen Cerealien" | Spuren-Hinweis | WARNUNG | True |
| "Äpfel, Zucker, Wasser" | Keine Allergen | SICHER | - |

---

## Debug: Text-Extraktion prüfen

Öffne die **Browser-Developer-Console** (F12) und führe aus:
```javascript
// Führe die Extraktionsfunktion aus
function extractPageText() {
    // [Code aus popup.js]
}
text = extractPageText();
console.log("Extrahierter Text:", text);
```

Wenn der Text leer oder sehr kurz ist, liegt das Problem bei der Website-Struktur.

---

## Backend-Debugging

### API direkt testen
```bash
curl -X POST http://127.0.0.1:8080/check-recipe \
  -H "Content-Type: application/json" \
  -d '{"ingredients": "Sportriegel mit Spuren von Gluten", "source": "test"}'
```

### Expected Response
```json
{
  "urteil": "WARNUNG",
  "grund": "Spurenhinweise auf: Gluten.",
  "alle_funde": [{
    "ist_spur": true,
    "ersatz": ["Reismehl", "Buchweizenmehl"]
  }]
}
```

---

## Häufige Fehler

### "Server nicht erreichbar"
- ✓ FastAPI-Server läuft auf Port 8080?
- Starte: `python backend/main.py`

### "null" als Allergen-Name
- Ollama gibt unvollständige Antworten
- Prüfe: `curl http://localhost:11434/api/tags` (Ollama-Server läuft?)

### Falsche Spur-Erkennung
- Kontexte vor und nach dem Allergen werden geprüft
- Keywords: "kann spuren enthalten", "spuren von", "-haltig"
