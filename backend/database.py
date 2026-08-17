import sqlite3
from config import DATABASE_PATH


def db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            allergy TEXT NOT NULL,
            selected INTEGER NOT NULL DEFAULT 0
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
    
    # Neue Tabelle für dynamisch gelernte Synonyme
    conn.execute('''
        CREATE TABLE IF NOT EXISTS learned_synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allergen TEXT NOT NULL,
            synonym TEXT NOT NULL,
            quelle TEXT NOT NULL,
            confidence INTEGER DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(allergen, synonym)
        )
    ''')
    
    # Tabelle für Allergen-Synonyme (Migration von allergen_data.py)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS allergen_synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allergen TEXT NOT NULL,
            synonym TEXT NOT NULL,
            language TEXT DEFAULT 'de',
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(allergen, synonym)
        )
    ''')
    
    # Index für schnelle Suche
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_synonym_search 
        ON allergen_synonyms(synonym, allergen)
    ''')
    
    # Tabelle für Allergen-Ersatzvorschläge
    conn.execute('''
        CREATE TABLE IF NOT EXISTS allergen_replacements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allergen_term TEXT NOT NULL UNIQUE,
            replacement_de TEXT NOT NULL,
            replacement_en TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Lokal bekannte OFF-Produkte (wächst durch Barcode-Scans & verifizierte
    # Textsuchen, statt bei jedem Scan die OFF-Volltextsuche blind zu befragen)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS off_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL UNIQUE,
            produktname TEXT NOT NULL,
            produktname_normalisiert TEXT NOT NULL,
            allergens_tags TEXT NOT NULL,
            traces_tags TEXT NOT NULL,
            quelle TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_off_products_name
        ON off_products(produktname_normalisiert)
    ''')

    cols = [r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
    if "methode" not in cols:
        conn.execute("ALTER TABLE history ADD COLUMN methode TEXT")
    if "result_snapshot" not in cols:
        conn.execute("ALTER TABLE history ADD COLUMN result_snapshot TEXT")

    user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "selected" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN selected INTEGER NOT NULL DEFAULT 0")

    if not conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        conn.execute("INSERT INTO users (name, allergy, selected) VALUES ('Demo', 'Erdnuss', 1)")
    elif not conn.execute('SELECT 1 FROM users WHERE selected=1').fetchone():
        # Migrating an older single-profile DB: keep existing behavior by selecting the first user
        first_id = conn.execute('SELECT id FROM users ORDER BY id LIMIT 1').fetchone()["id"]
        conn.execute('UPDATE users SET selected=1 WHERE id=?', (first_id,))
    conn.commit()
    conn.close()