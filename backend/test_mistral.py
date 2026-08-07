"""Test-Script für Mistral vs. llama3.1 Vergleich."""

import requests
import time

# Kritische Test-Fälle (llama3.1 hatte Probleme)
TESTS = [
    {
        "name": "❌ LLAMA PROBLEM: Vegane Sahne → Kuhmilch halluziniert",
        "text": "Zutaten: 600 g vegane Sahne, 150 g veganer Frischkäse, Mehl",
        "should_find": [],  # Keine Milch!
        "check": "milch"
    },
    {
        "name": "❌ LLAMA PROBLEM: Haferdrink → Kuhmilch halluziniert",
        "text": "Zutaten: 300 ml Haferdrink, 50 g vegane Butter, Mehl",
        "should_find": [],  # Keine Milch!
        "check": "milch"
    },
    {
        "name": "❌ LLAMA PROBLEM: Glutenfreies Brot → MILCHEIWEISS halluziniert",
        "text": "Zutaten: glutenfreies Brot, glutenfreie Nudeln, Salz",
        "should_find": [],  # Kein Milch!
        "check": "milch"
    },
    {
        "name": "✅ SOLL FINDEN: Carbonara mit echten Eiern",
        "text": "Zutaten: Spaghetti, Speck, Käse, 2 Ei(er), Sahne",
        "should_find": ["ei", "milch"],
        "check": ["ei", "milch"]
    },
    {
        "name": "✅ SOLL FINDEN: Kuchen mit echter Milch",
        "text": "Zutaten: Mehl, Zucker, 200ml frische Sahne, 100ml Vollmilch",
        "should_find": ["milch"],
        "check": "milch"
    }
]

def run_tests():
    print("=" * 80)
    print("🤖 MISTRAL TEST-SUITE")
    print("=" * 80)
    
    results = {"passed": 0, "failed": 0, "total_time": 0}
    
    for i, test in enumerate(TESTS, 1):
        print(f"\n{i}. {test['name']}")
        print("-" * 80)
        print(f"Text: {test['text'][:70]}...")
        
        start = time.time()
        try:
            r = requests.post("http://127.0.0.1:8080/check-recipe", 
                             json={"ingredients": test['text'], "source": "test"}, 
                             timeout=30)
            duration = time.time() - start
            results["total_time"] += duration
            
            result = r.json()
            funde = result['alle_funde']
            
            # Prüfe relevante Funde
            checks = [test['check']] if isinstance(test['check'], str) else test['check']
            relevante_funde = [
                f for f in funde 
                if any(check in f['allergie'].lower() for check in checks)
            ]
            
            # Bewertung
            soll_finden = len(test['should_find']) > 0
            hat_gefunden = len(relevante_funde) > 0
            
            if soll_finden and hat_gefunden:
                print(f"✅ RICHTIG! {len(relevante_funde)} Fund(e) erkannt ({duration:.2f}s)")
                results["passed"] += 1
            elif not soll_finden and not hat_gefunden:
                print(f"✅ RICHTIG! 0 Funde (korrekt gefiltert) ({duration:.2f}s)")
                results["passed"] += 1
            else:
                print(f"❌ FEHLER! ({duration:.2f}s)")
                if soll_finden:
                    print(f"   Erwartet: {test['should_find']}, Gefunden: {len(relevante_funde)}")
                else:
                    print(f"   Sollte 0 sein, aber {len(relevante_funde)} gefunden:")
                    for f in relevante_funde:
                        print(f"   - {f['allergie']}: '{f.get('synonym')}'")
                results["failed"] += 1
            
            print(f"Methode: {result['methode']}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results["failed"] += 1
    
    # Zusammenfassung
    print("\n" + "=" * 80)
    print("📊 ERGEBNIS:")
    print("=" * 80)
    print(f"✅ Bestanden: {results['passed']}/{len(TESTS)}")
    print(f"❌ Fehlgeschlagen: {results['failed']}/{len(TESTS)}")
    print(f"⏱️  Gesamt: {results['total_time']:.2f}s")
    print(f"⏱️  Durchschnitt: {results['total_time']/len(TESTS):.2f}s pro Test")
    
    if results['passed'] == len(TESTS):
        print("\n🎉 ALLE TESTS BESTANDEN! Mistral funktioniert perfekt!")
    elif results['passed'] >= len(TESTS) * 0.8:
        print("\n👍 MEISTE TESTS bestanden, aber noch Optimierung möglich")
    else:
        print("\n⚠️  VIELE FEHLER! Vielleicht doch bei llama3.1 bleiben?")

if __name__ == "__main__":
    run_tests()
