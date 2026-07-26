import sqlite3


def db():
    conn = sqlite3.connect('allergen.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            allergy TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT,
            urteil TEXT,
            allergie_geprueft TEXT,
            gefundenes_synonym TEXT,
            fundstelle TEXT,
            grund TEXT,
            methode TEXT,
            result_snapshot TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS off_cache (
            query_key TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        )
    ''')

    cols = [r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
    if "methode" not in cols:
        conn.execute("ALTER TABLE history ADD COLUMN methode TEXT")
    if "result_snapshot" not in cols:
        conn.execute("ALTER TABLE history ADD COLUMN result_snapshot TEXT")

    if not conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        conn.execute("INSERT INTO users (name, allergy) VALUES ('Demo', 'Erdnuss')")
    conn.commit()
    conn.close()