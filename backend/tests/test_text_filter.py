from text_filter import extrahiere_zutaten_sektion


class TestExtrahiereZutatenSektion:
    def test_extrahiert_nur_zutaten_ignoriert_marketing_und_verwendung(self):
        text = (
            "Produktbeschreibung: Toll und lecker.\n\n"
            "Zutaten: Zucker, Mehl, Salz.\n\n"
            "Verwendung: Ideal auf Brot."
        )

        result = extrahiere_zutaten_sektion(text)

        assert "Zucker, Mehl, Salz" in result
        assert "Ideal auf Brot" not in result
        assert "Toll und lecker" not in result

    def test_erfasst_allergenhinweise_zusaetzlich_zu_zutaten(self):
        text = "Zutaten: Mehl, Zucker.\n\nAllergene: Kann Spuren von Nüssen enthalten."

        result = extrahiere_zutaten_sektion(text)

        assert "Nüssen" in result

    def test_kurzer_text_ohne_marker_wird_komplett_zurueckgegeben(self):
        text = "Erdnussbutter, Zucker, Salz"

        assert extrahiere_zutaten_sektion(text) == text

    def test_langer_text_ohne_marker_wird_verworfen(self):
        text = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 20

        assert extrahiere_zutaten_sektion(text) == ""

    def test_naehrwerttabelle_wird_ignoriert(self):
        text = (
            "Zutaten: Zucker, Mehl.\n\n"
            "Brennwert: 250 kcal, Kohlenhydrate: 30g, davon Zucker: 10g."
        )

        result = extrahiere_zutaten_sektion(text)

        assert "Brennwert" not in result
        assert "Kohlenhydrate" not in result
