import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """
    Baut die FastAPI-App gegen eine isolierte, absolute Test-DB auf.

    main.py fuehrt beim Import init_db() und load_synonyms_into_cache() aus -
    ueber DATABASE_PATH als absoluten Pfad direkt auf database/allergen_db
    gepatcht (statt ueber os.environ), damit main erst NACH dem Patch
    importiert wird und der spaetere, pro-Test wechselnde cwd
    (conftest.isolate_cwd) keine Rolle mehr spielt.
    """
    mp = pytest.MonkeyPatch()
    db_path = str(tmp_path_factory.mktemp("main_db") / "test.db")

    import database
    mp.setattr(database, "DATABASE_PATH", db_path)
    import allergen_db
    mp.setattr(allergen_db, "DATABASE_PATH", db_path)

    # Tier 1 (OpenFoodFacts) macht sonst fuer grossgeschriebene Woerter im
    # Freitext (z.B. "Erdnussbutter") echte Netzwerk-Requests. Fuer isolierte,
    # schnelle Tests wird die eigentliche HTTP-Ebene hier stumm geschaltet -
    # main.py faellt dann korrekt auf Tier 2 (Synonym-Matching) zurueck.
    import openfoodfacts_client
    mp.setattr(openfoodfacts_client, "_off_get", lambda *args, **kwargs: None)

    import main  # ruft beim Import init_db() + load_synonyms_into_cache() auf

    with TestClient(main.app) as test_client:
        yield test_client

    mp.undo()


class TestUsersCrud:
    def test_list_users_enthaelt_demo_profil(self, client):
        resp = client.get("/users")

        assert resp.status_code == 200
        names = {u["name"] for u in resp.json()}
        assert "Demo" in names

    def test_create_user_ist_automatisch_selected(self, client):
        resp = client.post("/users", json={"name": "Jasmine", "allergy": "Erdnuss, Milch"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Jasmine"
        assert body["allergy"] == "Erdnuss, Milch"
        assert body["selected"] is True
        assert isinstance(body["id"], int)

        client.delete(f"/users/{body['id']}")

    def test_update_user_aendert_name_und_allergy(self, client):
        created = client.post("/users", json={"name": "Temp", "allergy": "Fisch"}).json()

        resp = client.put(f"/users/{created['id']}", json={"name": "Temp2", "allergy": "Sesam"})

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        users = client.get("/users").json()
        updated = next(u for u in users if u["id"] == created["id"])
        assert updated["name"] == "Temp2"
        assert updated["allergy"] == "Sesam"

        client.delete(f"/users/{created['id']}")

    def test_update_nichtexistenten_user_gibt_fehler(self, client):
        resp = client.put("/users/999999", json={"name": "X", "allergy": "Y"})

        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_delete_user_entfernt_profil(self, client):
        created = client.post("/users", json={"name": "ZumLoeschen", "allergy": "Soja"}).json()

        resp = client.delete(f"/users/{created['id']}")

        assert resp.status_code == 200
        ids = {u["id"] for u in client.get("/users").json()}
        assert created["id"] not in ids

    def test_set_selection_toggelt_status(self, client):
        created = client.post("/users", json={"name": "Auswahl", "allergy": "Sellerie"}).json()

        resp = client.patch(f"/users/{created['id']}/selection", json={"selected": False})
        assert resp.status_code == 200
        users = client.get("/users").json()
        assert next(u for u in users if u["id"] == created["id"])["selected"] is False

        client.patch(f"/users/{created['id']}/selection", json={"selected": True})
        users = client.get("/users").json()
        assert next(u for u in users if u["id"] == created["id"])["selected"] is True

        client.delete(f"/users/{created['id']}")


class TestHistory:
    def test_history_ist_zunaechst_leer_oder_liste(self, client):
        resp = client.get("/history")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCheckRecipe:
    def test_ohne_ausgewaehltes_profil_gibt_fehler(self, client):
        # Demo-Profil temporaer abwaehlen, um den Fehlerpfad zu testen.
        users = client.get("/users").json()
        demo = next(u for u in users if u["name"] == "Demo")

        client.patch(f"/users/{demo['id']}/selection", json={"selected": False})
        try:
            resp = client.post("/check-recipe", json={"ingredients": "Wasser, Salz"})

            assert resp.status_code == 200
            assert "error" in resp.json()
        finally:
            client.patch(f"/users/{demo['id']}/selection", json={"selected": True})

    def test_erkennt_allergen_ueber_synonym_matching(self, client):
        # Demo-Profil hat "Erdnuss" als Allergie (siehe database.init_db Seed-Daten).
        resp = client.post("/check-recipe", json={"ingredients": "200g Erdnussbutter, Zucker"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["urteil"] == "GEFAHR"
        assert "synonym" in body["methode"]
        assert len(body["alle_funde"]) >= 1

    def test_sicherer_text_ohne_allergene(self, client):
        resp = client.post("/check-recipe", json={"ingredients": "Wasser, Salz, Reis"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["urteil"] == "SICHER"
        assert body["alle_funde"] == []

    def test_check_recipe_schreibt_in_history(self, client):
        before = len(client.get("/history").json())

        client.post("/check-recipe", json={"ingredients": "Erdnussflips pur"})

        after = client.get("/history").json()
        assert len(after) == before + 1
        assert after[0]["urteil"] == "GEFAHR"
