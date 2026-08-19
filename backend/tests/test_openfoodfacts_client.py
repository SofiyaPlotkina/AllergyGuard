from openfoodfacts_client import off_allergene_pruefen, _markennamen_kandidaten


class TestOffAllergenePruefen:
    def test_direkter_allergen_tag_ergibt_gefahr(self):
        produkt = {
            "product_name": "Erdnussflips",
            "allergens_tags": ["en:peanuts"],
            "traces_tags": [],
        }

        funde = off_allergene_pruefen(produkt, ["Erdnuss"])

        assert len(funde) == 1
        assert funde[0]["allergie"] == "Erdnuss"
        assert funde[0]["ist_spur"] is False

    def test_spuren_tag_ergibt_warnung(self):
        produkt = {
            "product_name": "Kekse",
            "allergens_tags": [],
            "traces_tags": ["en:milk"],
        }

        funde = off_allergene_pruefen(produkt, ["Milch"])

        assert len(funde) == 1
        assert funde[0]["ist_spur"] is True

    def test_kein_passender_tag_ergibt_keinen_fund(self):
        produkt = {
            "product_name": "Wasser",
            "allergens_tags": [],
            "traces_tags": [],
        }

        funde = off_allergene_pruefen(produkt, ["Erdnuss", "Milch"])

        assert funde == []

    def test_mehrere_allergien_gleichzeitig_geprueft(self):
        produkt = {
            "product_name": "Erdnuss-Milch-Riegel",
            "allergens_tags": ["en:peanuts", "en:milk"],
            "traces_tags": [],
        }

        funde = off_allergene_pruefen(produkt, ["Erdnuss", "Milch", "Fisch"])

        gefundene_allergien = {f["allergie"] for f in funde}
        assert gefundene_allergien == {"Erdnuss", "Milch"}


class TestMarkennamenKandidaten:
    def test_einzelnes_grossgeschriebenes_wort_wird_als_kandidat_erkannt(self):
        assert _markennamen_kandidaten("Bueno") == ["Bueno"]

    def test_wenige_kandidaten_bleiben_erhalten(self):
        kandidaten = _markennamen_kandidaten("Ich habe einen Bueno Riegel gegessen")

        assert "Bueno" in kandidaten
        assert len(kandidaten) <= 3

    def test_zu_viele_kandidaten_ergeben_leere_liste(self):
        # Ganze Zutatenlisten mit vielen großgeschriebenen Begriffen (z.B.
        # Rezept-Unterüberschriften) sollen NICHT als gezielte Markennennung
        # gewertet werden - lieber gar kein Kandidat als geraten.
        text = "Ich habe einen Bueno Riegel gegessen Heute Toll Super Klasse"

        assert _markennamen_kandidaten(text) == []
