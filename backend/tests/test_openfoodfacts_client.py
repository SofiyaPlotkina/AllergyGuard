import pytest

import database
from openfoodfacts_client import (
    normalisiere_name,
    off_allergene_pruefen,
    off_cache_lesen,
    off_cache_schreiben,
    off_lokal_suchen,
    off_produkt_cachen,
    suche_off,
)


@pytest.fixture(autouse=True)
def initialized_db():
    database.init_db()


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


class TestNormalisiereName:
    def test_entfernt_mengenangaben_und_sonderzeichen(self):
        assert normalisiere_name("Kinder Bueno White, 39g") == "kinder bueno white"

    def test_normalisiert_mehrfache_leerzeichen(self):
        assert normalisiere_name("Nutella   Nuss-Nougat-Creme") == "nutella nuss nougat creme"


class TestOffCache:
    def test_cache_schreiben_und_lesen(self):
        off_cache_schreiben("bueno", {"product_name": "Kinder Bueno"})

        result = off_cache_lesen("bueno")

        assert result == {"product_name": "Kinder Bueno"}

    def test_cache_miss_gibt_none(self):
        assert off_cache_lesen("nicht-gecacht") is None

    def test_abgelaufener_cache_eintrag_wird_ignoriert(self, monkeypatch):
        import datetime
        import openfoodfacts_client as offc

        off_cache_schreiben("alt", {"product_name": "Altes Produkt"})

        conn = database.db()
        conn.execute(
            "UPDATE off_cache SET cached_at=? WHERE query_key='alt'",
            ((datetime.datetime.now() - datetime.timedelta(days=99)).isoformat(),),
        )
        conn.commit()
        conn.close()

        assert off_cache_lesen("alt") is None


class TestOffProduktCachenUndLokalSuchen:
    def test_gecachtes_produkt_wird_lokal_gefunden(self):
        produkt = {
            "code": "4008400123456",
            "product_name": "Erdnussflips Classic",
            "allergens_tags": ["en:peanuts"],
            "traces_tags": [],
        }
        off_produkt_cachen(produkt, quelle="barcode")

        gefunden = off_lokal_suchen("Heute gab es Erdnussflips Classic zum Snack")

        assert gefunden is not None
        assert gefunden["code"] == "4008400123456"
        assert gefunden["allergens_tags"] == ["en:peanuts"]

    def test_kein_treffer_wenn_nicht_im_text(self):
        produkt = {
            "code": "4008400123456",
            "product_name": "Erdnussflips Classic",
            "allergens_tags": [],
            "traces_tags": [],
        }
        off_produkt_cachen(produkt, quelle="barcode")

        assert off_lokal_suchen("Ein ganz anderes Produkt") is None

    def test_ohne_barcode_oder_name_wird_nichts_gecacht(self):
        off_produkt_cachen({"product_name": "Ohne Barcode"}, quelle="barcode")

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM off_products").fetchone()["c"]
        conn.close()
        assert count == 0


class TestSucheOff:
    def test_nutzt_cache_ohne_netzwerkzugriff(self, monkeypatch):
        import openfoodfacts_client as offc

        off_cache_schreiben("4008400123456", {"product_name": "Aus Cache"})
        monkeypatch.setattr(
            offc, "_off_get",
            lambda *a, **kw: (_ for _ in ()).throw(AssertionError("sollte nicht aufgerufen werden")),
        )

        result = suche_off("4008400123456")

        assert result == {"product_name": "Aus Cache"}

    def test_barcode_suche_ohne_treffer_gibt_none(self, monkeypatch):
        import openfoodfacts_client as offc

        monkeypatch.setattr(offc, "_off_get", lambda *a, **kw: {"status": 0})

        assert suche_off("4008400123456") is None

    def test_barcode_treffer_wird_gecacht(self, monkeypatch):
        import openfoodfacts_client as offc

        monkeypatch.setattr(
            offc, "_off_get",
            lambda *a, **kw: {"status": 1, "product": {
                "code": "4008400123456", "product_name": "Testprodukt",
                "allergens_tags": [], "traces_tags": [],
            }},
        )

        result = suche_off("4008400123456")

        assert result["product_name"] == "Testprodukt"
        assert off_cache_lesen("4008400123456") is not None

    def test_volltextsuche_ohne_treffer_gibt_none(self, monkeypatch):
        import openfoodfacts_client as offc

        monkeypatch.setattr(offc, "_off_get", lambda *a, **kw: {"products": []})

        assert suche_off("irgendein produkt") is None
