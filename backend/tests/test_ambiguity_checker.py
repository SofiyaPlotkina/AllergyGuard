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
