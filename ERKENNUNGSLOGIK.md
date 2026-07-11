# Architektur – Erkennungslogik und Entscheidungen

## Erkennung: 4-stufiges Fallback-System

1. **OpenFoodFacts (Datenbank)**
   - Priorisiert: Barcode-Suche
   - Alternativ: Produktnamen aus Zutaten
   - Status: Strukturierte Daten von OpenFoodFacts API

2. **Ollama (KI)**
   - Fallback, wenn OFF kein Ergebnis liefert
   - Lokales LLM mit Prompt für Allergen-Erkennung
   - Status: Intelligente Analyse ohne externe API

3. **Synonym-Matching (Regelwerk)**
   - Finaler Fallback
   - Lokale Python-Listen mit bekannten Allergenen
   - Status: Robuster Fallback auch offline

## Gefahr vs. Spuren: Die Logik

### GEFAHR (Urteil: "GEFAHR")
- Ein Allergen ist direkt als **Hauptzutat** in der Liste vorhanden
- Beispiele:
  - "10 EL **Mehl**" → GEFAHR (nicht: "kann Spuren enthalten")
  - "2 **Eier**" → GEFAHR
  - Vollständige Zutaten sind immer Gefahr, nie Spuren

### WARNUNG (Urteil: "WARNUNG")
- Nur echte **Spurenhinweise**, z.B.:
  - "Kann Spuren von Erdnüssen enthalten"
  - "Hergestellt in derselben Anlage"
  - "Nicht geeignet für Personen mit dieser Allergie"

### SICHER (Urteil: "SICHER")
- Keine Allergene gefunden

## Spuren-Detektion: Die genaue Logik

Im Synonym-Matching wird eine Zutat nur als "Spur" markiert, wenn:
1. Das Allergen wird gefunden
2. **In den 100 Zeichen NACH dem Fund** taucht eine Spurenphrase auf

Das verhindert False-Positives: "Paniermehl" gefolgt von "kann Spuren von Nüssen enthalten" wird **nicht** als Nusspuren, sondern das korrekt als Gluten-Gefahr erkannt.

## Ersatzvorschläge

Jeder Fund hat eine `ersatz` Liste mit Alternativen:
- Wird auf API zurückgegeben unter `alle_ersatz_vorschlaege`
- Dedupliziert automatisch
- Nutzer-freundlich in der Extension anzeigbar

