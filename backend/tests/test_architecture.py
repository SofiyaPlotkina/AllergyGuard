import unittest

from backend.recognition import analyze_text


class RecognitionArchitectureTest(unittest.TestCase):
    def test_synonym_fallback_detects_known_allergen(self):
        result = analyze_text("Dieses Rezept enthält Erdnussöl und Sahne.", ["Erdnuss", "Milch"])

        self.assertEqual(result["urteil"], "GEFAHR")
        self.assertGreaterEqual(len(result["alle_funde"]), 1)
        self.assertIn("erdnuss", result["grund"].lower())


if __name__ == "__main__":
    unittest.main()
