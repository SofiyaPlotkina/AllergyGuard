import json

import pytest
import requests

from ollama_client import analyse_mit_ollama


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _mock_post(monkeypatch, response_text):
    """Ersetzt requests.post so, dass Ollama den gegebenen 'response'-Text liefert."""
    def fake_post(url, json, timeout):
        return _FakeResponse({"response": response_text})

    monkeypatch.setattr("ollama_client.requests.post", fake_post)


class TestAnalyseMitOllama:
    def test_valider_fund_wird_zurueckgegeben(self, monkeypatch):
        funde = [{"allergie": "Ei", "synonym": "Eier", "fundstelle": "2 Eier", "ist_spur": False}]
        _mock_post(monkeypatch, json.dumps(funde))

        result = analyse_mit_ollama("2 Eier, Mehl", ["Ei"])

        assert result == funde

    def test_leeres_array_ergibt_leere_liste(self, monkeypatch):
        _mock_post(monkeypatch, "[]")

        result = analyse_mit_ollama("Wasser, Salz", ["Ei"])

        assert result == []

    def test_keine_json_antwort_ergibt_leere_liste(self, monkeypatch):
        _mock_post(monkeypatch, "Ich habe leider nichts gefunden.")

        result = analyse_mit_ollama("Wasser", ["Ei"])

        assert result == []

    def test_negative_eintraege_werden_gefiltert(self, monkeypatch):
        funde = [{"allergie": "Ei", "synonym": "kein Ei gefunden", "fundstelle": "Text", "ist_spur": False}]
        _mock_post(monkeypatch, json.dumps(funde))

        result = analyse_mit_ollama("Text", ["Ei"])

        assert result == []

    def test_protein_kontext_wird_fuer_ei_gefiltert(self, monkeypatch):
        funde = [{
            "allergie": "Ei", "synonym": "Eiweiß",
            "fundstelle": "Nährwerte: Eiweiß 10g pro 100g", "ist_spur": False,
        }]
        _mock_post(monkeypatch, json.dumps(funde))

        result = analyse_mit_ollama("Nährwerte: Eiweiß 10g pro 100g", ["Ei"])

        assert result == []

    def test_veganer_kontext_wird_fuer_milch_gefiltert(self, monkeypatch):
        funde = [{
            "allergie": "Milch", "synonym": "Milchpulver",
            "fundstelle": "100% vegan, kein Milchpulver enthalten", "ist_spur": False,
        }]
        _mock_post(monkeypatch, json.dumps(funde))

        result = analyse_mit_ollama("100% vegan, kein Milchpulver enthalten", ["Milch"])

        assert result == []

    def test_glutenfrei_kontext_wird_fuer_gluten_gefiltert(self, monkeypatch):
        funde = [{
            "allergie": "Gluten", "synonym": "Hafer",
            "fundstelle": "glutenfrei zertifizierter Hafer", "ist_spur": False,
        }]
        _mock_post(monkeypatch, json.dumps(funde))

        result = analyse_mit_ollama("glutenfrei zertifizierter Hafer", ["Gluten"])

        assert result == []

    def test_zu_kurzes_synonym_wird_gefiltert(self, monkeypatch):
        funde = [{"allergie": "Ei", "synonym": "ei", "fundstelle": "irgendwas", "ist_spur": False}]
        _mock_post(monkeypatch, json.dumps(funde))

        result = analyse_mit_ollama("irgendwas", ["Ei"])

        assert result == []

    def test_request_exception_ergibt_leere_liste(self, monkeypatch):
        def fake_post(url, json, timeout):
            raise requests.exceptions.ConnectionError("Ollama nicht erreichbar")

        monkeypatch.setattr("ollama_client.requests.post", fake_post)

        result = analyse_mit_ollama("Text", ["Ei"])

        assert result == []

    def test_kaputtes_json_ergibt_leere_liste(self, monkeypatch):
        # Ein '[...]'-Match, der aber kein valides JSON ist.
        _mock_post(monkeypatch, "[{'allergie': 'Ei',}]")

        result = analyse_mit_ollama("Text", ["Ei"])

        assert result == []
