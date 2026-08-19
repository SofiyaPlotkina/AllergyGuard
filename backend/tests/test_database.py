import sqlite3

import pytest

import database


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Isolierte, absolute DB-Datei fuer jeden Test (unabhaengig vom cwd)."""
    path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    return path


class TestInitDb:
    def test_erzeugt_alle_erwarteten_tabellen(self, db_path):
        database.init_db()

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        conn.close()

        for expected in (
            "users", "history", "off_cache", "learned_synonyms",
            "allergen_synonyms", "allergen_replacements", "off_products",
        ):
            assert expected in tables

    def test_seeded_demo_user_bei_leerer_db(self, db_path):
        database.init_db()

        conn = database.db()
        rows = conn.execute("SELECT name, allergy, selected FROM users").fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0]["name"] == "Demo"
        assert rows[0]["allergy"] == "Erdnuss"
        assert bool(rows[0]["selected"]) is True

    def test_ist_idempotent(self, db_path):
        database.init_db()
        database.init_db()

        conn = database.db()
        count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        conn.close()

        assert count == 1

    def test_kein_zusaetzlicher_demo_user_wenn_bereits_daten_vorhanden(self, db_path):
        # Simuliert eine bereits existierende DB mit einem eigenen Profil,
        # bevor init_db() zum ersten Mal darauf laeuft.
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                allergy TEXT NOT NULL,
                selected INTEGER NOT NULL DEFAULT 0
            )
        ''')
        conn.execute("INSERT INTO users (name, allergy, selected) VALUES ('Max', 'Milch', 1)")
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.db()
        names = {r["name"] for r in conn.execute("SELECT name FROM users").fetchall()}
        conn.close()
        assert names == {"Max"}

    def test_migriert_alte_db_ohne_selected_spalte(self, db_path):
        # Aeltere DB-Version: users ohne 'selected', mit genau einem Profil.
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                allergy TEXT NOT NULL
            )
        ''')
        conn.execute("INSERT INTO users (name, allergy) VALUES ('Altes Profil', 'Gluten')")
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.db()
        row = conn.execute("SELECT selected FROM users WHERE name='Altes Profil'").fetchone()
        conn.close()
        assert bool(row["selected"]) is True


class TestDb:
    def test_db_gibt_verbindung_mit_row_factory_zurueck(self, db_path):
        database.init_db()

        conn = database.db()
        row = conn.execute("SELECT 1 as eins").fetchone()
        conn.close()

        assert row["eins"] == 1
