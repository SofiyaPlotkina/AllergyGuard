from eiweiss_filter import (
    filtere_eiweiss_funde,
    hat_veganen_oder_glutenfreien_kontext,
    ist_protein_kontext,
)


def _fund(allergie, synonym, fundstelle, ist_spur=False):
    return {
        "allergie": allergie,
        "synonym": synonym,
        "fundstelle": fundstelle,
        "ist_spur": ist_spur,
        "ersatz": [],
    }


class TestFiltereEiweissFunde:
    def test_milcheiweiss_wird_nicht_als_ei_gewertet(self):
        funde = [_fund("Ei", "Milcheiweiß", "Zutaten: 20g Milcheiweiß, Zucker")]

        result = filtere_eiweiss_funde(funde, "Zutaten: 20g Milcheiweiß, Zucker")

        assert result == []

    def test_echtes_ei_bleibt_erhalten(self):
        funde = [_fund("Ei", "Vollei", "Zutaten: 3 Vollei, Mehl")]

        result = filtere_eiweiss_funde(funde, "Zutaten: 3 Vollei, Mehl")

        assert len(result) == 1

    def test_eiweiss_im_proteinkontext_wird_gefiltert(self):
        funde = [_fund("Ei", "Eiweiß", "Proteinriegel mit hohem Eiweißgehalt")]

        result = filtere_eiweiss_funde(
            funde, "Proteinriegel mit hohem Eiweißgehalt, 34% Eiweiß"
        )

        assert result == []

    def test_eiweiss_in_zutatenliste_bleibt_erhalten(self):
        funde = [_fund("Ei", "Eiweiß", "Zutaten: Mehl, Eiweiß, Zucker")]

        result = filtere_eiweiss_funde(funde, "Zutaten: Mehl, Eiweiß, Zucker")

        assert len(result) == 1

    def test_vegane_sahne_wird_nicht_als_milch_gewertet(self):
        funde = [_fund("Milch", "Sahne", "100ml vegane Sahne")]

        result = filtere_eiweiss_funde(funde, "irrelevanter Kontext")

        assert result == []

    def test_glutenfreies_brot_wird_nicht_als_gluten_gewertet(self):
        funde = [_fund("Gluten", "Weizenmehl", "glutenfreies Brot mit Weizenmehl")]

        result = filtere_eiweiss_funde(funde, "irrelevanter Kontext")

        assert result == []

    def test_mandelmilch_wird_nicht_als_milch_gewertet(self):
        funde = [_fund("Milch", "Mandelmilch", "200ml Mandelmilch")]

        result = filtere_eiweiss_funde(funde, "irrelevanter Kontext")

        assert result == []

    def test_leere_funde_liste(self):
        assert filtere_eiweiss_funde([], "irgendein Text") == []


class TestHatVeganenOderGlutenfreienKontext:
    def test_vegan_blockiert_milch(self):
        assert hat_veganen_oder_glutenfreien_kontext("vegane Sahne", "Milch") is True

    def test_glutenfrei_blockiert_gluten(self):
        assert hat_veganen_oder_glutenfreien_kontext("glutenfreies Brot", "Gluten") is True

    def test_kein_marker_kein_block(self):
        assert hat_veganen_oder_glutenfreien_kontext("frische Sahne", "Milch") is False

    def test_vegan_wirkt_nicht_auf_gluten(self):
        assert hat_veganen_oder_glutenfreien_kontext("vegane Nudeln", "Gluten") is False


class TestIstProteinKontext:
    def test_erkennt_zutatenlisten_kontext_als_echtes_ei(self):
        text = "Zutaten: Mehl, Eiweiß, Zucker"

        assert ist_protein_kontext(text, "eiweiß") is False

    def test_erkennt_proteinkontext(self):
        text = "Proteinriegel mit hohem Eiweißgehalt, 34% Eiweiß"

        assert ist_protein_kontext(text, "eiweiß") is True

    def test_fundstelle_nicht_im_text_gilt_vorsichtshalber_als_allergen(self):
        assert ist_protein_kontext("Ganz anderer Text", "eiweiß") is False
