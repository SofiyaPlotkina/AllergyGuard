import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
# allergen_data.py ist reine Migrations-Altdaten und liegt deshalb in import_data/,
# wird aber von tests/test_allergen_data.py noch direkt importiert
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "import_data"))


@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    """Verhindert, dass Code mit relativen DB-Pfaden (z.B. sqlite3.connect('allergen.db'))
    die echte Entwickler-Datenbank berührt oder Dateien im Repo hinterlässt."""
    monkeypatch.chdir(tmp_path)
