import pytest

import database
from synonym_learner import (
    hole_gelernte_synonyme,
    lerne_synonym,
    lerne_von_off_ingredients,
    lerne_von_ollama_funden,
    statistik_learned_synonyms,
)


@pytest.fixture(autouse=True)
def initialized_db():
    """conftest.isolate_cwd sorgt fuer eine frische relative 'allergen.db' pro Test."""
    database.init_db()


class TestLerneSynonym:
    def test_neues_synonym_wird_gespeichert(self):
        lerne_synonym("Gluten", "glutenhaltige Cerealien", "manual")

        conn = database.db()
        row = conn.execute(
            "SELECT * FROM learned_synonyms WHERE allergen='gluten' AND synonym='glutenhaltige cerealien'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["confidence"] == 1
        assert row["quelle"] == "manual"

    def test_wiederholtes_lernen_erhoeht_confidence(self):
        lerne_synonym("Gluten", "Weizenmehl", "ollama")
        lerne_synonym("Gluten", "Weizenmehl", "ollama")
        lerne_synonym("Gluten", "weizenmehl", "openfoodfacts")  # gleiches Synonym, andere Groß/Kleinschreibung

        conn = database.db()
        row = conn.execute(
            "SELECT confidence, quelle FROM learned_synonyms WHERE allergen='gluten' AND synonym='weizenmehl'"
        ).fetchone()
        conn.close()

        assert row["confidence"] == 3
        assert row["quelle"] == "openfoodfacts"

    def test_zu_kurzes_synonym_wird_ignoriert(self):
        lerne_synonym("Ei", "ei", "manual")

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM learned_synonyms").fetchone()["c"]
        conn.close()

        assert count == 0

    def test_zu_langes_synonym_wird_ignoriert(self):
        lerne_synonym("Ei", "x" * 101, "manual")

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM learned_synonyms").fetchone()["c"]
        conn.close()

        assert count == 0

    def test_leeres_synonym_wird_ignoriert(self):
        lerne_synonym("Ei", "", "manual")

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM learned_synonyms").fetchone()["c"]
        conn.close()

        assert count == 0


class TestHoleGelernteSynonyme:
    def test_gibt_nur_synonyme_ab_confidence_zwei_zurueck(self):
        lerne_synonym("Milch", "Molkepulver", "manual")  # confidence 1
        lerne_synonym("Milch", "Laktose", "manual")
        lerne_synonym("Milch", "Laktose", "manual")  # confidence 2

        result = hole_gelernte_synonyme("Milch")

        assert result == ["laktose"]

    def test_unbekanntes_allergen_gibt_leere_liste(self):
        assert hole_gelernte_synonyme("Nichtvorhanden") == []


class TestLerneVonOllamaFunden:
    def test_extrahiert_synonyme_aus_funden(self):
        funde = [
            {"allergie": "Ei", "synonym": "Eigelbpulver"},
            {"allergie": "Milch", "synonym": "Milcheiweiß"},
        ]

        lerne_von_ollama_funden(funde)

        conn = database.db()
        allergene = {r["allergen"] for r in conn.execute("SELECT allergen FROM learned_synonyms").fetchall()}
        conn.close()
        assert allergene == {"ei", "milch"}

    def test_unvollstaendige_funde_werden_ignoriert(self):
        funde = [{"allergie": "Ei"}, {"synonym": "Eigelbpulver"}, {}]

        lerne_von_ollama_funden(funde)

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM learned_synonyms").fetchone()["c"]
        conn.close()
        assert count == 0


class TestLerneVonOffIngredients:
    def test_extrahiert_grossgeschriebene_woerter(self):
        produkt = {"ingredients_text": "Zutaten: WEIZENMEHL, Zucker, VOLLMILCHPULVER, Salz"}

        lerne_von_off_ingredients(produkt, "Gluten")

        conn = database.db()
        synonyme = {r["synonym"] for r in conn.execute(
            "SELECT synonym FROM learned_synonyms WHERE allergen='gluten'"
        ).fetchall()}
        conn.close()
        assert "weizenmehl" in synonyme
        assert "vollmilchpulver" in synonyme

    def test_ohne_ingredients_text_passiert_nichts(self):
        lerne_von_off_ingredients({}, "Gluten")

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM learned_synonyms").fetchone()["c"]
        conn.close()
        assert count == 0


class TestStatistikLearnedSynonyms:
    def test_zaehlt_gesamt_und_confident_und_pro_allergen(self):
        lerne_synonym("Ei", "Eipulver", "manual")
        lerne_synonym("Ei", "Eipulver", "manual")
        lerne_synonym("Ei", "Eipulver", "manual")  # confidence 3 -> "confident"
        lerne_synonym("Milch", "Molke", "manual")  # confidence 1

        stats = statistik_learned_synonyms()

        assert stats["gesamt"] == 2
        assert stats["confident"] == 1
        assert stats["pro_allergen"] == {"ei": 1, "milch": 1}
