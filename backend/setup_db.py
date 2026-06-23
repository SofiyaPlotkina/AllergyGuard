import sqlite3

# 1. Verbindung herstellen - (erstellt automatisch die Datei 'allergen.db' in dem Ordner)
conn = sqlite3.connect('allergen.db')
cursor = conn.cursor()

# 2. Eine basic Tabelle für die Nutzer erstellen
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    allergy TEXT NOT NULL
)
''')

# NUR PROTOTYP: Wir leeren die Tabelle kurz, damit wir "Max" nicht 10-mal anlegen, wenn wir das Skript öfter testen)
cursor.execute('DELETE FROM users')

# 3. Test-Nutzer "Max" und seine Erdnussallergie
cursor.execute("INSERT INTO users (name, allergy) VALUES ('Max', 'Erdnuss')")

# 4. Änderungen speichern
conn.commit()

# 5. Tabelle auslesen und ins Terminal printen
cursor.execute('SELECT * FROM users')
test_user = cursor.fetchall()

print("Datenbank 'allergen.db' wurde erfolgreich erstellt!")
print(f"Eingetragener Nutzer: {test_user}")

# 6. Verbindung sauber schließen
conn.close()