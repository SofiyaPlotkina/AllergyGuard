"""Tests for filter logic (false positive detection)"""

import pytest
from filters import ist_false_positive, ist_protein_kontext, filtere_funde


class TestFalsePositiveDetection:
    """Test suite for false positive detection"""
    
    def test_vanille_is_false_positive_for_ei(self):
        """Vanille/Vanilleschote should NOT be detected as Ei"""
        assert ist_false_positive("ei", "vanille", "1 Vanilleschote") == True
        assert ist_false_positive("ei", "vanilleschote", "Vanilleschote gemahlen") == True
    
    def test_real_ei_is_not_false_positive(self):
        """Real Ei mentions should pass through"""
        assert ist_false_positive("ei", "eier", "2 Eier") == False
        assert ist_false_positive("ei", "ei", "1 Ei") == False
    
    def test_protein_context_detection(self):
        """Eiweiß in protein context should be filtered"""
        text = "Nährwerte: Eiweiß 10g, Fett 5g"
        assert ist_protein_kontext(text, "Eiweiß 10g") == True
        
        # But real Eiweiss mention should pass
        text = "Zutaten: Milcheiweiß, Salz"
        assert ist_protein_kontext(text, "Milcheiweiß") == False

    def test_protein_context_new_marketing_keywords(self):
        """Neu ergänzte Protein-Marketing-Begriffe sollen Eiweiß als
        Protein-Kontext (nicht Ei-Allergen) erkennen."""
        assert ist_protein_kontext("Extra Protein Riegel mit Eiweiß", "Eiweiß") == True
        assert ist_protein_kontext("High Protein Shake mit Eiweiß", "Eiweiß") == True
        assert ist_protein_kontext("Proteinquelle: Eiweiß", "Eiweiß") == True
        assert ist_protein_kontext("Für Muskelaufbau beim Bodybuilding: Eiweiß", "Eiweiß") == True
        assert ist_protein_kontext("Kalorien und Kohlenhydrate: Eiweiß 10g", "Eiweiß") == True

    def test_eiprodukt_gilt_als_zutaten_kontext(self):
        """'Eiprodukt' wurde neu als Zutaten-Kontext-Begriff ergänzt und muss
        Eiweiß in einer Zutatenliste als echtes Ei erkennen (kein Protein-FP)."""
        text = "Zutaten: Eiprodukt, Zucker, Eiweiß"
        assert ist_protein_kontext(text, "Eiweiß") == False
    
    def test_replacement_context(self):
        """Terms in replacement context should be filtered"""
        # "ohne Ei" or "ersetzt durch" context
        assert ist_false_positive("ei", "ei", "ohne Ei hergestellt") == True
        assert ist_false_positive("milch", "milch", "kann durch Mandelmilch ersetzt werden") == True
    
    def test_empty_fundstelle(self):
        """Empty finding locations should be filtered"""
        assert ist_false_positive("ei", "eier", "") == True
        assert ist_false_positive("ei", "eier", "   ") == True


class TestFundFiltering:
    """Test the filtere_funde function"""
    
    def test_filter_empty_fundstellen(self):
        """Empty locations should be filtered out"""
        funde = [
            {"allergie": "ei", "synonym": "eier", "fundstelle": ""},
            {"allergie": "ei", "synonym": "ei", "fundstelle": "2 Eier"},
        ]
        result = filtere_funde(funde)
        assert len(result) == 1
        assert result[0]["fundstelle"] == "2 Eier"
    
    def test_filter_false_positives(self):
        """False positives should be removed"""
        funde = [
            {"allergie": "ei", "synonym": "vanille", "fundstelle": "1 Vanilleschote"},
            {"allergie": "ei", "synonym": "eier", "fundstelle": "2 Eier"},
        ]
        result = filtere_funde(funde)
        assert len(result) == 1
        assert result[0]["synonym"] == "eier"
    
    def test_filter_protein_context(self):
        """Eiweiß in nutrition table should be filtered"""
        original_text = "Zutaten: Mehl, Zucker. Nährwerte: Eiweiß 12g"
        funde = [
            {"allergie": "ei", "synonym": "eiweiß", "fundstelle": "Eiweiß 12g"},
        ]
        result = filtere_funde(funde, original_text)
        assert len(result) == 0


class TestEdgeCases:
    """Test edge cases and corner cases"""
    
    def test_mixed_case_sensitivity(self):
        """Test case-insensitive matching"""
        assert ist_false_positive("ei", "VANILLE", "VANILLESCHOTE") == True
        assert ist_false_positive("EI", "vanille", "vanilleschote") == True
    
    def test_umlauts(self):
        """Test proper handling of German umlauts"""
        assert ist_false_positive("ei", "eiweiss", "Milcheiweiss") == False
        assert ist_false_positive("ei", "eiweiß", "Milcheiweiß") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
