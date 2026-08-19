import pytest

import allergen_db
import database
from allergen_db import (
    add_synonym_to_db,
    get_all_allergen_synonyms,
    get_replacement_for_term,
    get_synonyms_for_allergen,
    load_synonyms_into_cache,
)


@pytest.fixture(autouse=True)
def initialized_db_and_fresh_cache(monkeypatch):
    """Frische DB (via conftest.isolate_cwd) + zurueckgesetzte In-Memory-Caches,
    da _SYNONYM_CACHE/_REPLACEMENT_CACHE Modul-globale Singletons sind."""
    database.init_db()
    monkeypatch.setattr(allergen_db, "_SYNONYM_CACHE", {})
    monkeypatch.setattr(allergen_db, "_REPLACEMENT_CACHE", {})


def _insert_synonym(allergen, synonym, language="de"):
    conn = database.db()
    conn.execute(
        "INSERT INTO allergen_synonyms (allergen, synonym, language) VALUES (?, ?, ?)",
        (allergen, synonym, language),
    )
    conn.commit()
    conn.close()


def _insert_replacement(term, replacement_de):
    conn = database.db()
    conn.execute(
        "INSERT INTO allergen_replacements (allergen_term, replacement_de) VALUES (?, ?)",
        (term, replacement_de),
    )
    conn.commit()
    conn.close()


class TestLoadSynonymsIntoCache:
    def test_laedt_synonyme_aus_db(self):
        _insert_synonym("ei", "eier")
        _insert_synonym("ei", "eiklar")
        _insert_synonym("milch", "laktose")

        load_synonyms_into_cache()

        cache = get_all_allergen_synonyms()
        assert set(cache["ei"]) == {"eier", "eiklar"}
        assert cache["milch"] == ["laktose"]

    def test_leere_db_ergibt_leeren_cache(self):
        load_synonyms_into_cache()

        assert get_all_allergen_synonyms() == {}


class TestGetSynonymsForAllergen:
    def test_gibt_synonyme_fuer_bekanntes_allergen(self):
        _insert_synonym("ei", "eigelb")

        assert get_synonyms_for_allergen("Ei") == ["eigelb"]

    def test_ist_case_insensitive(self):
        _insert_synonym("erdnuss", "erdnussbutter")

        assert get_synonyms_for_allergen("  ERDNUSS  ") == ["erdnussbutter"]

    def test_unbekanntes_allergen_gibt_sich_selbst_zurueck(self):
        load_synonyms_into_cache()

        assert get_synonyms_for_allergen("Sellerie") == ["sellerie"]

    def test_laedt_cache_automatisch_falls_leer(self):
        _insert_synonym("soja", "sojalecithin")

        # Kein expliziter load_synonyms_into_cache()-Aufruf vorher.
        assert get_synonyms_for_allergen("soja") == ["sojalecithin"]


class TestGetReplacementForTerm:
    def test_exakter_treffer(self):
        _insert_replacement("eigelb", "Leinsamen, Apfelmus")

        assert get_replacement_for_term("eigelb") == ["Leinsamen", "Apfelmus"]

    def test_ist_case_insensitive(self):
        _insert_replacement("butter", "Margarine")

        assert get_replacement_for_term("BUTTER") == ["Margarine"]

    def test_partieller_treffer(self):
        _insert_replacement("erdnussöl", "Sonnenblumenöl")

        assert get_replacement_for_term("Bio-Erdnussöl") == ["Sonnenblumenöl"]

    def test_kein_treffer_gibt_leere_liste(self):
        load_synonyms_into_cache()

        assert get_replacement_for_term("xyz-unbekannt") == []


class TestAddSynonymToDb:
    def test_fuegt_synonym_in_db_und_cache_ein(self):
        # Hinweis: add_synonym_to_db() cached unter dem exakten `allergen`-Arg
        # (nicht lowercased), get_synonyms_for_allergen() lowercased dagegen
        # immer beim Lookup - fuer den Cache-Hit muss der Aufrufer daher
        # bereits kleingeschrieben uebergeben (wie es main.py/synonym_learner
        # ueberall tun).
        result = add_synonym_to_db("ei", "Vollei")

        assert result is True

        conn = database.db()
        row = conn.execute(
            "SELECT * FROM allergen_synonyms WHERE allergen='ei' AND synonym='vollei'"
        ).fetchone()
        conn.close()
        assert row is not None
        # Hinweis: add_synonym_to_db() haengt den Cache-Eintrag in der
        # UNVERAENDERTEN Schreibweise an (nicht lowercased wie der DB-Insert).
        assert "Vollei" in get_synonyms_for_allergen("ei")

    def test_duplikat_wird_ignoriert_ohne_fehler(self):
        add_synonym_to_db("ei", "Vollei")
        result = add_synonym_to_db("ei", "Vollei")

        assert result is True

        conn = database.db()
        count = conn.execute(
            "SELECT COUNT(*) as c FROM allergen_synonyms WHERE allergen='ei' AND synonym='vollei'"
        ).fetchone()["c"]
        conn.close()
        assert count == 1
