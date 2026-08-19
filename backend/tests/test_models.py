import pytest
from pydantic import ValidationError

from models import RecipeRequest, SelectionUpdate, UserProfile


class TestRecipeRequest:
    def test_source_ist_optional_mit_default(self):
        req = RecipeRequest(ingredients="Mehl, Eier")

        assert req.ingredients == "Mehl, Eier"
        assert req.source == "Unbekannt"

    def test_source_kann_explizit_gesetzt_werden(self):
        req = RecipeRequest(ingredients="Mehl", source="Barcode-Scan")

        assert req.source == "Barcode-Scan"

    def test_ingredients_ist_pflichtfeld(self):
        with pytest.raises(ValidationError):
            RecipeRequest()


class TestUserProfile:
    def test_name_und_allergy_sind_pflichtfelder(self):
        profile = UserProfile(name="Jasmine", allergy="Erdnuss, Milch")

        assert profile.name == "Jasmine"
        assert profile.allergy == "Erdnuss, Milch"

    def test_fehlender_name_wirft_validation_error(self):
        with pytest.raises(ValidationError):
            UserProfile(allergy="Erdnuss")

    def test_fehlende_allergy_wirft_validation_error(self):
        with pytest.raises(ValidationError):
            UserProfile(name="Jasmine")


class TestSelectionUpdate:
    def test_selected_true(self):
        assert SelectionUpdate(selected=True).selected is True

    def test_selected_false(self):
        assert SelectionUpdate(selected=False).selected is False

    def test_selected_ist_pflichtfeld(self):
        with pytest.raises(ValidationError):
            SelectionUpdate()
