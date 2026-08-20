"""One-time migration script: allergen_data.py → SQLite

This script migrates allergen synonyms, replacement suggestions and the
OpenFoodFacts-Tag-Zuordnung from hardcoded Python dictionaries to the
database. allergen_data.py ist danach reine Migrations-Altdaten, nichts
davon wird zur Laufzeit noch direkt importiert.

Run once (aus backend/, nicht aus import_data/!): python import_data/migrate_allergens.py
"""

import sqlite3
from allergen_data import ALLERGEN_SYNONYME, ERSATZ, OFF_TAG_MAP


def detect_language(text: str) -> str:
    """Detect language of a term (simple heuristic)"""
    # German characters
    if any(c in text for c in ["ä", "ö", "ü", "ß"]):
        return "de"
    
    # Common English words
    english_words = [
        "butter", "milk", "egg", "wheat", "nut", "fish", "sauce",
        "flour", "oil", "seed", "protein", "cream", "cheese"
    ]
    if any(word in text.lower() for word in english_words):
        return "en"
    
    # Default to German
    return "de"


def detect_category(text: str) -> str:
    """Detect category of a term"""
    text_lower = text.lower()
    
    if any(x in text_lower for x in ["öl", "oil"]):
        return "oil"
    elif any(x in text_lower for x in ["mehl", "flour"]):
        return "flour"
    elif any(x in text_lower for x in ["sauce", "soße", "dressing"]):
        return "sauce"
    elif any(x in text_lower for x in ["brot", "bread", "brötchen"]):
        return "bread"
    elif any(x in text_lower for x in ["nudeln", "pasta", "spaghetti"]):
        return "pasta"
    elif any(x in text_lower for x in ["käse", "cheese"]):
        return "cheese"
    elif any(x in text_lower for x in ["milch", "milk"]):
        return "milk"
    elif any(x in text_lower for x in ["butter"]):
        return "butter"
    elif any(x in text_lower for x in ["sahne", "cream"]):
        return "cream"
    
    return None


def migrate_synonyms():
    """Migrate allergen synonyms from Python dict to database"""
    conn = sqlite3.connect("allergen.db")
    cursor = conn.cursor()
    
    print("[MIGRATING] Allergen synonyms to database...")
    print(f"   Source: {len(ALLERGEN_SYNONYME)} allergens")
    
    total = 0
    skipped = 0
    
    for allergen, synonyms in ALLERGEN_SYNONYME.items():
        print(f"   • {allergen}: {len(synonyms)} synonyms")
        
        for synonym in synonyms:
            # Detect language and category
            lang = detect_language(synonym)
            category = detect_category(synonym)
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO allergen_synonyms 
                    (allergen, synonym, language, category)
                    VALUES (?, ?, ?, ?)
                """, (allergen.lower(), synonym.lower(), lang, category))
                
                if cursor.rowcount > 0:
                    total += 1
                else:
                    skipped += 1
            
            except sqlite3.IntegrityError:
                skipped += 1
    
    conn.commit()
    print(f"[OK] Migrated {total} synonyms (skipped {skipped} duplicates)")
    
    return total


def migrate_replacements():
    """Migrate replacement suggestions from Python dict to database"""
    conn = sqlite3.connect("allergen.db")
    cursor = conn.cursor()
    
    print("\n[MIGRATING] Replacement suggestions...")
    print(f"   Source: {len(ERSATZ)} terms")
    
    total = 0
    skipped = 0
    
    for term, replacements in ERSATZ.items():
        # Join top 5 replacements (limit to keep it manageable)
        replacement_de = " | ".join(replacements[:5])
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO allergen_replacements
                (allergen_term, replacement_de)
                VALUES (?, ?)
            """, (term.lower(), replacement_de))
            
            if cursor.rowcount > 0:
                total += 1
            else:
                skipped += 1
        
        except sqlite3.IntegrityError:
            skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Migrated {total} replacement suggestions (skipped {skipped} duplicates)")
    
    return total


def migrate_off_tag_map():
    """Migrate OFF-Tag -> Allergie-Name Zuordnung from Python dict to database"""
    conn = sqlite3.connect("allergen.db")
    cursor = conn.cursor()

    print("\n[MIGRATING] OFF tag map...")
    print(f"   Source: {len(OFF_TAG_MAP)} tags")

    total = 0
    skipped = 0

    for off_tag, allergen in OFF_TAG_MAP.items():
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO off_tag_map (off_tag, allergen)
                VALUES (?, ?)
            """, (off_tag, allergen))

            if cursor.rowcount > 0:
                total += 1
            else:
                skipped += 1

        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    conn.close()

    print(f"[OK] Migrated {total} OFF tags (skipped {skipped} duplicates)")

    return total


def verify_migration():
    """Verify that migration was successful"""
    conn = sqlite3.connect("allergen.db")
    cursor = conn.cursor()
    
    print("\n[VERIFICATION]:")
    
    # Count synonyms per allergen
    cursor.execute("""
        SELECT allergen, COUNT(*) as count 
        FROM allergen_synonyms 
        GROUP BY allergen 
        ORDER BY allergen
    """)
    
    print("\n   Synonyms per allergen:")
    for allergen, count in cursor.fetchall():
        print(f"   • {allergen}: {count}")
    
    # Total counts
    cursor.execute("SELECT COUNT(*) FROM allergen_synonyms")
    total_synonyms = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM allergen_replacements")
    total_replacements = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM off_tag_map")
    total_off_tags = cursor.fetchone()[0]

    conn.close()

    print(f"\n   Total synonyms in DB: {total_synonyms}")
    print(f"   Total replacements in DB: {total_replacements}")
    print(f"   Total OFF tags in DB: {total_off_tags}")

    return total_synonyms > 0 and total_replacements > 0 and total_off_tags > 0


if __name__ == "__main__":
    print("=" * 60)
    print("  AllergyGuard - Allergen Data Migration")
    print("  allergen_data.py → SQLite Database")
    print("=" * 60)
    print()
    
    try:
        # Run migrations
        synonym_count = migrate_synonyms()
        replacement_count = migrate_replacements()
        off_tag_count = migrate_off_tag_map()

        # Verify
        if verify_migration():
            print("\n" + "=" * 60)
            print("[OK] Migration completed successfully!")
            print("=" * 60)
            print()
        else:
            print("\n[ERROR] Migration verification failed!")
            print("   Check database file and try again.")
    
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
