import sqlite3
from pathlib import Path

try:
    from .config import DB_PATH
except ImportError:  # pragma: no cover - fallback for direct execution
    from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            allergy TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT,
            urteil TEXT,
            allergie_geprueft TEXT,
            gefundenes_synonym TEXT,
            fundstelle TEXT,
            grund TEXT,
            methode TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS off_cache (
            query_key TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        )
        """
    )

    cols = [row[1] for row in conn.execute("PRAGMA table_info(history)").fetchall()]
    if "methode" not in cols:
        conn.execute("ALTER TABLE history ADD COLUMN methode TEXT")

    if not conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        conn.execute("INSERT INTO users (name, allergy) VALUES (?, ?)", ("Demo", "Erdnuss"))

    conn.commit()
    conn.close()


def load_profile() -> dict:
    conn = get_connection()
    user = conn.execute("SELECT name, allergy FROM users LIMIT 1").fetchone()
    conn.close()
    if not user:
        return {"name": "", "allergy": ""}
    return {"name": user["name"], "allergy": user["allergy"]}


def save_profile(name: str, allergy: str) -> None:
    conn = get_connection()
    existing = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
    if existing:
        conn.execute("UPDATE users SET name=?, allergy=? WHERE id=?", (name, allergy, existing["id"]))
    else:
        conn.execute("INSERT INTO users (name, allergy) VALUES (?, ?)", (name, allergy))
    conn.commit()
    conn.close()


def get_history(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM history ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_history(entry: dict) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO history (timestamp, source, urteil, allergie_geprueft, gefundenes_synonym, fundstelle, grund, methode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry["timestamp"],
            entry.get("source", "Unbekannt"),
            entry["urteil"],
            entry["allergie_geprueft"],
            entry.get("gefundenes_synonym", ""),
            entry.get("fundstelle", ""),
            entry.get("grund", ""),
            entry.get("methode", "synonym"),
        ),
    )
    conn.execute(
        "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY timestamp DESC LIMIT 20)"
    )
    conn.commit()
    conn.close()
