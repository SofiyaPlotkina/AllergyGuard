import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    """Verhindert, dass Code mit relativen DB-Pfaden (z.B. sqlite3.connect('allergen.db'))
    die echte Entwickler-Datenbank berührt oder Dateien im Repo hinterlässt."""
    monkeypatch.chdir(tmp_path)
