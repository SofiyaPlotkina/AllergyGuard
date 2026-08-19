from ambiguity_checker import braucht_ki_check, ist_ambig


class TestIstAmbig:
    def test_eiweiss_ist_ambig_fuer_ei(self):
        assert ist_ambig("eiweiß", "Ei") is True

    def test_eiweiss_ist_case_insensitive(self):
        assert ist_ambig("Eiweiß", "ei") is True

    def test_eiweiss_ist_nicht_ambig_fuer_andere_allergene(self):
        assert ist_ambig("eiweiß", "Milch") is False

    def test_unbekanntes_synonym_ist_nicht_ambig(self):
        assert ist_ambig("vollei", "Ei") is False


class TestBrauchtKiCheck:
    def test_eiweiss_fund_bei_ei_allergie_braucht_immer_ki_check(self):
        funde = [{"allergie": "Ei", "synonym": "Eiweiß"}]

        assert braucht_ki_check(funde, "irgendein Text") is True

    def test_eindeutiger_fund_braucht_keinen_ki_check(self):
        funde = [{"allergie": "Erdnuss", "synonym": "Erdnussbutter"}]

        assert braucht_ki_check(funde, "250g Erdnussbutter") is False

    def test_leere_funde_liste_braucht_keinen_ki_check(self):
        assert braucht_ki_check([], "irgendein Text") is False

    def test_ambiges_synonym_mit_false_positive_kontext_braucht_ki_check(self):
        # Auch bei einem anderen Allergen als "Ei" prueft braucht_ki_check() den
        # Text-Kontext um "eiweiß" herum, sobald das Synonym ueberhaupt in
        # AMBIGE_SYNONYME vorkommt.
        funde = [{"allergie": "Milch", "synonym": "eiweiß"}]
        text = "Nährwerte: Eiweiß, 10g protein pro Portion"

        assert braucht_ki_check(funde, text) is True

    def test_ambiges_synonym_ohne_false_positive_kontext_braucht_keinen_ki_check(self):
        funde = [{"allergie": "Milch", "synonym": "eiweiß"}]
        text = "Zutaten: Vollei, Eiweiß, Mehl"

        assert braucht_ki_check(funde, text) is False

    def test_synonym_nicht_im_text_wird_uebersprungen(self):
        funde = [{"allergie": "Milch", "synonym": "eiweiß"}]
        text = "Dieser Text enthält das Wort gar nicht"

        assert braucht_ki_check(funde, text) is False
