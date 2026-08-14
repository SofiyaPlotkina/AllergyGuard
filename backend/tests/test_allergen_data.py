from allergen_data import ALLERGEN_SYNONYME, ERSATZ, OFF_TAG_MAP, ersatz_fuer


class TestErsatzFuer:
    def test_exakter_treffer(self):
        assert ersatz_fuer("Eigelb") == ERSATZ["eigelb"]

    def test_ist_case_insensitive(self):
        assert ersatz_fuer("BUTTER") == ERSATZ["butter"]

    def test_partieller_treffer_waehlt_laengsten_schluessel(self):
        result = ersatz_fuer("Bio-Erdnussöl")

        assert result == ERSATZ["erdnussöl"]

    def test_unbekannter_begriff_gibt_leere_liste(self):
        assert ersatz_fuer("xyzzyzzy-unbekannt") == []


class TestDatenintegritaet:
    def test_alle_allergene_haben_synonyme(self):
        for allergen, synonyme in ALLERGEN_SYNONYME.items():
            assert isinstance(synonyme, list)
            assert len(synonyme) > 0, f"'{allergen}' hat keine Synonyme"

    def test_off_tag_map_zeigt_auf_bekannte_allergene(self):
        for tag, allergen in OFF_TAG_MAP.items():
            assert allergen in ALLERGEN_SYNONYME, (
                f"OFF-Tag '{tag}' zeigt auf unbekanntes Allergen '{allergen}'"
            )

    def test_alle_ersatz_eintraege_haben_vorschlaege(self):
        for begriff, vorschlaege in ERSATZ.items():
            assert isinstance(vorschlaege, list)
            assert len(vorschlaege) > 0, f"'{begriff}' hat keine Ersatzvorschläge"
