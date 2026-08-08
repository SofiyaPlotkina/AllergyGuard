import os

import pytest


@pytest.fixture(scope="module")
def extrahiere_produktnamen(tmp_path_factory):
    """Importiert main.extrahiere_produktnamen, ohne dass main.py beim Import
    (init_db(), FastAPI-App) die echte Entwickler-Datenbank berührt."""
    tmp_dir = tmp_path_factory.mktemp("main_import")
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    try:
        from main import extrahiere_produktnamen as fn
    finally:
        os.chdir(original_cwd)
    return fn


class TestExtrahiereProduktnamen:
    def test_erkennt_gtin_praefix(self, extrahiere_produktnamen):
        text = "GTIN: 4008400123456\nSonstiges Zeug hier"

        kandidaten = extrahiere_produktnamen(text)

        assert kandidaten[0] == "4008400123456"

    def test_erkennt_barcode_ohne_praefix(self, extrahiere_produktnamen):
        text = "Produktinfo 4008400123456 im Regal"

        kandidaten = extrahiere_produktnamen(text)

        assert "4008400123456" in kandidaten

    def test_erkennt_produktnamen_mit_marke_und_geschmack(self, extrahiere_produktnamen):
        text = "Proteinriegel Schoko Karamell Geschmack\nWeitere Zeile"

        kandidaten = extrahiere_produktnamen(text)

        assert "Proteinriegel Schoko Karamell Geschmack" in kandidaten

    def test_ignoriert_generische_ueberschriften(self, extrahiere_produktnamen):
        text = "Produktbeschreibung\nZutaten: Zucker, Mehl"

        kandidaten = extrahiere_produktnamen(text)

        assert kandidaten == []

    def test_maximal_fuenf_kandidaten(self, extrahiere_produktnamen):
        text = "\n".join(f"{i} 1234567{i}9012" for i in range(10))

        kandidaten = extrahiere_produktnamen(text)

        assert len(kandidaten) <= 5
