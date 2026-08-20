import pandas as pd
import re
from collections import OrderedDict
from deep_translator import GoogleTranslator

# Define allergen mapping
ALLERGEN_MAPPING = {
    'dairy': 'milch',
    'eggs': 'ei',
    'gluten': 'gluten',
    'wheat': 'gluten',
    'soybeans': 'soja',
    'peanuts': 'erdnuss',
    'tree nuts': 'nüsse',
    'sesame': 'sesam',
    'fish': 'fisch',
    'shellfish': 'krebstiere',
    'mollusks': 'weichtiere',
    'mustard': 'senf',
    'celery': 'sellerie',
    'lupin': 'lupine',
    'sulphur dioxide': 'sulfite',
    'sulphites': 'sulfite'
}

def clean_name(name):
    """Remove content in round brackets and double asterisks, clean up multiple spaces and strip"""
    name = re.sub(r'$[^)]*$', '', name)
    name = name.replace('**', '')
    name = ' '.join(name.split()).strip()
    return name

def translate_to_german(text):
    try:
        translator = GoogleTranslator(source='en', target='de')
        return translator.translate(text)
    except Exception as e:
        print(f"Translation error for '{text}': {e}")
        return text

def has_allergens(allergens_str):
    """Check if the allergen string contains actual allergens"""
    if not allergens_str.strip():
        return False
    if allergens_str.strip() == '[]':
        return False
    if allergens_str.strip().lower() == "'[]'":
        return False
    return True

def process_row(row):
    id_, name, allergens_str = row

    # Skip if no allergens
    if not has_allergens(allergens_str):
        return []

    # Clean name first (before translation)
    name = clean_name(name)

    # Process allergens
    try:
        allergens = eval(allergens_str)
    except:
        allergens = []

    # Create rows for each allergen
    rows = []
    for allergen in allergens:
        # Clean and map allergen
        clean_allergen = allergen.replace('**', '').strip().lower()

        # Handle special cases
        if clean_allergen == 'molluscan shellfish':
            clean_allergen = 'mollusks'
        elif clean_allergen == 'mustard flour':
            clean_allergen = 'mustard'

        euro_allergen = ALLERGEN_MAPPING.get(clean_allergen, clean_allergen)

        # Only include if we have a valid mapping
        if euro_allergen in ALLERGEN_MAPPING.values():
            # Translate name to German (only once per unique name)
            if name not in translation_cache:
                translation_cache[name] = translate_to_german(name)

            # Create new row
            new_row = [
                '',  # ID will be generated during import
                euro_allergen,
                translation_cache[name],
                'de',
                '',  # Empty category
                'USDA'
                # Timestamp will be generated during import
            ]
            rows.append(new_row)

    return rows

def clean_ingredients(input_file, output_file):
    # Load CSV
    df = pd.read_csv(input_file, header=None, names=["id", "allergen", "name", "language", "source", "category"])

    # Step 1: Remove empty/placeholder names
    df = df[df["name"].str.strip() != ""]

    # Step 2: Length filter (2-80 chars)
    df = df[(df["name"].str.len() >= 2) & (df["name"].str.len() <= 80)]

    # Step 3: Remove generic descriptors
    blacklist = [
        "Zutaten", "enthält", "Belag", "Füllung", "Gewürze", "Soße", "Kruste", "Aroma",
        "Mischung", "Teig", "Überzug", "Stücke", "Pulver", "Extrakt", "Basis", "Sauce",
        "Dressing", "Geschmack", "Gewürzmischung", "Käse-", "Fleisch-", "Fisch-",
        "Hühner-", "Rindfleisch-", "Schweinefleisch-"
    ]
    df = df[~df["name"].str.contains("|".join(blacklist), case=False, regex=True)]

    # Step 4: Remove brackets/parentheses
    df = df[~df["name"].str.contains(r'[$$$$]', regex=True)]

    # Step 5: Remove trailing special characters
    df = df[~df["name"].str.contains(r'[,:;]\s*$', regex=True)]

    # Save to CSV
    df.to_csv(output_file, index=False, header=False)

def process_csv(input_file, output_file):
    seen = OrderedDict()

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Write header
        writer.writerow(['id', 'allergen', 'name', 'language', 'source', 'category'])

        # Process rows
        for row in reader:
            if not row or len(row) < 6:
                continue

            # Clean fields
            id_ = row[0]
            allergen = clean_field(row[1])
            name = clean_field(row[2])
            language = row[3] if row[3] else 'de'
            source = row[5] if row[5] else 'USDA'
            category = clean_field(row[4])

            # Create new row with correct column order
            new_row = [id_, allergen, name, language, source, category]

            # Remove duplicates
            row_key = tuple(new_row)
            if row_key not in seen:
                seen[row_key] = None
                writer.writerow(new_row)

def clean_field(field):
    """Remove square brackets and their contents from a field"""
    return re.sub(r'$[^]]*$', '', field)

def main():
    input_file = 'import_allergies.csv'
    output_file = 'short_allergies.csv'

    # Clean ingredients
    clean_ingredients(input_file, 'filtered_ingredients.csv')

    # Process CSV to remove duplicates and clean fields
    process_csv('filtered_ingredients.csv', output_file)

    # Further clean and process if needed
    # For example, to remove trailing special characters from name and allergen
    with open(output_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Write header
        writer.writerow(['id', 'allergen', 'name', 'language', 'source', 'category'])

        # Process each row
        for row in reader:
            if not row or len(row) < 6:
                continue

            # Clean fields again
            id_, allergen, name, language, source, category = row

            # Remove trailing special characters
            name = name.rstrip('.,;:[]()')
            allergen = allergen.rstrip('.,;:[]()')

            # Write cleaned row
            writer.writerow([id_, allergen, name, language, source, category])

if __name__ == '__main__':
    main()
