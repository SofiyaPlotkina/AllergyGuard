import pytest

from synonym_matcher import ist_false_positive, synonym_matching, synonym_trifft


class TestIstFalsePositive:
    @pytest.mark.parametrize(
        "allergen, synonym, fundstelle",
        [
            ("milch", "mandelmilch", "200ml Mandelmilch"),
            ("milch", "hafermilch", "Hafermilch, ungesüßt"),
            ("milch", "vegane butter", "50g vegane Butter"),
            ("butter", "margarine", "Margarine statt Butter"),
            ("gluten", "buchweizen", "100g Buchweizenmehl"),
            ("weizen", "quinoa", "Quinoa, gekocht"),
            ("ei", "sojaeiweiß", "20g Sojaeiweiß"),
            ("ei", "erbsenprotein", "Erbsenprotein 15g"),
        ],
    )
    def test_erkennt_false_positives(self, allergen, synonym, fundstelle):
        assert ist_false_positive(allergen, synonym, fundstelle) is True

    @pytest.mark.parametrize(
        "allergen, synonym, fundstelle",
        [
            ("milch", "milch", "200ml Vollmilch"),
            ("milch", "butter", "50g Butter"),
            ("gluten", "weizenmehl", "500g Weizenmehl"),
            ("ei", "vollei", "3 Vollei"),
        ],
    )
    def test_laesst_echte_allergene_durch(self, allergen, synonym, fundstelle):
        assert ist_false_positive(allergen, synonym, fundstelle) is False


class TestSynonymTrifft:
    def test_kurzes_synonym_nur_an_wortgrenze(self):
        assert synonym_trifft("ei", "1 ei, 200g mehl") is True
        assert synonym_trifft("ei", "eisen enthalten") is False
        assert synonym_trifft("ei", "eier verquirlt") is False

    def test_langes_synonym_als_substring(self):
        assert synonym_trifft("erdnussbutter", "250g erdnussbutter, cremig") is True
        assert synonym_trifft("erdnussbutter", "kein erdnusshaltiges produkt") is False


class TestSynonymMatching:
    def test_direkter_allergen_fund(self):
        text = (
            "Produktbeschreibung: Lecker und cremig.\n\n"
            "Zutaten: Erdnussbutter, Zucker, Salz."
        )
        funde = synonym_matching(text, ["Erdnuss"])

        assert len(funde) == 1
        assert funde[0]["allergie"] == "Erdnuss"
        assert funde[0]["ist_spur"] is False

    def test_spurenhinweis_wird_als_warnung_erkannt(self):
        text = "Zutaten: Zucker, Salz. Kann Spuren von Erdnuss enthalten."
        funde = synonym_matching(text, ["Erdnuss"])

        assert len(funde) == 1
        assert funde[0]["ist_spur"] is True

    def test_pflanzenmilch_wird_nicht_als_milch_gewertet(self):
        text = "Zutaten: Mandelmilch, Zucker, Vanille."
        funde = synonym_matching(text, ["Milch"])

        assert funde == []

    def test_kein_allergen_im_text(self):
        text = "Zutaten: Zucker, Salz, Wasser."
        funde = synonym_matching(text, ["Erdnuss"])

        assert funde == []

    def test_mehrere_allergene_gleichzeitig(self):
        text = "Zutaten: Erdnussbutter, Vollmilch, Zucker."
        funde = synonym_matching(text, ["Erdnuss", "Milch"])

        gefundene_allergien = {f["allergie"] for f in funde}
        assert gefundene_allergien == {"Erdnuss", "Milch"}

    def test_naehrwerttabelle_wird_nicht_als_ei_gewertet(self):
        text = "Zutaten: Zucker, Mehl.\n\nNährwerte je 100g: Eiweiß 14 g, Fett 5 g."
        funde = synonym_matching(text, ["Ei"])

        assert funde == []

    def test_kann_enthalten_ohne_zwischenwoerter_wird_als_spur_erkannt(self):
        text = "Zutaten: Zucker, Salz. Kann Erdnuss enthalten."
        funde = synonym_matching(text, ["Erdnuss"])

        assert len(funde) == 1
        assert funde[0]["ist_spur"] is True

    def test_kann_mehrere_allergene_enthalten_wird_als_spur_erkannt(self):
        text = "Zutaten: Zucker, Salz. Kann Schalenfrüchte, Erdnuss, Lupine, Sesam enthalten."
        funde = synonym_matching(text, ["Erdnuss"])

        assert len(funde) == 1
        assert funde[0]["ist_spur"] is True

    def test_spurenhinweis_in_anderer_zeile_faerbt_zutat_nicht_als_spur_ein(self):
        # Regression: der Spuren-Kontext darf nicht mehr über ein festes
        # ±150-Zeichen-Fenster in eine andere Zeile "bleeden" - eine echte
        # Zutat wie Milchpulver bleibt GEFAHR, auch wenn nahebei (aber in
        # einer eigenen Zeile) ein allgemeiner Spurenhinweis für ein anderes
        # Allergen steht.
        text = (
            "Zutaten: Milchpulver, Zucker, Salz.\n"
            "Kann Spuren von Erdnuss enthalten."
        )
        funde = synonym_matching(text, ["Milch"])

        assert len(funde) == 1
        assert funde[0]["ist_spur"] is False

    def test_spurenhinweis_in_derselben_zeile_wird_erkannt(self):
        text = "Zutaten: Zucker, Salz. Kann Spuren von Milch enthalten."
        funde = synonym_matching(text, ["Milch"])

        assert len(funde) == 1
        assert funde[0]["ist_spur"] is True
