from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import datetime
import json
import re
import requests
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Synonyme pro Allergen ────────────────────────────────────────────────────
# Matching ist Substring-basiert (Kleinschreibung).
# Kurze Begriffe (≤3 Zeichen oder in WORTGRENZE_SYNONYME) werden nur an
# Wortgrenzen gematcht um Falschpositive zu vermeiden.
ALLERGEN_SYNONYME: dict[str, list[str]] = {
    "erdnuss": [
        # ── Deutsch ──
        "erdnuss", "erdnüsse", "erdnusskern", "erdnusskerne",
        "erdnussöl", "erdnuss-öl", "erdnussbutter", "erdnuss-butter",
        "erdnussmehl", "erdnussprotein", "erdnusspaste", "erdnussextrakt",
        "erdnussmark", "erdnusscreme", "erdnusssoße", "erdnussmus",
        "erdnussflocken", "erdnussschrot", "erdnussstückchen",
        "erdnussglasur", "erdnusskrokant", "geröstete erdnuss",
        "gesalzene erdnuss", "karamellisierte erdnuss",
        # ── Englisch ──
        "peanut", "peanuts", "peanut oil", "peanut butter",
        "peanut flour", "peanut paste", "peanut extract", "peanut protein",
        "peanut powder", "peanut sauce", "peanut cream", "peanut brittle",
        "dry roasted peanut", "roasted peanut",
        "groundnut", "groundnut oil", "groundnut paste",
        # ── Lateinisch / wissenschaftlich ──
        "arachis", "arachis hypogaea", "arachide", "arachidnuss",
        # ── Saucen & Produkte die häufig Erdnüsse enthalten ──
        "satay", "sataysauce", "satay sauce",
        "bumbu kacang",          # indonesische Erdnusssauce
        "kacang",                # Erdnuss auf Malaiisch/Indonesisch
        "nam jim satay",
        "peanut dressing",
        # ── Gemischtes ──
        "mixed nuts", "gemischte nüsse", "nussmischung",
    ],

    "milch": [
        # ── Milch selbst & Varianten ──
        "milch", "kuhmilch", "vollmilch", "magermilch", "halbfettmilch",
        "fettarme milch", "frischmilch", "rohmilch", "vorzugsmilch",
        "haltbarmilch", "h-milch", "uht-milch",
        "ziegenmilch", "schafmilch", "stutenmilch", "kamelmilch",
        "büffelmilch",
        "kondensmilch", "dosenmilch", "gezuckerte kondensmilch",
        "trockenmilch", "milchpulver", "magermilchpulver",
        "vollmilchpulver", "süßmolkenpulver",
        "laktosefreie milch",    # enthält trotzdem Milchprotein
        # ── Sahne & Rahm ──
        "sahne", "schlagsahne", "schlagrahm", "rahm", "süßrahm",
        "obers", "schlagobers",  # Österreich
        "sauerrahm", "saure sahne", "creme fraiche", "crème fraîche",
        "schmand", "kaffeesahne", "kochsahne", "konditorsahne",
        "sauersahne", "crème double", "double cream",
        # ── Butter & Fette ──
        "butter", "süßrahmbutter", "sauerrahmbutter", "salzbutter",
        "butterfett", "butteröl", "butterschmalz", "clarified butter",
        "ghee", "desi ghee",
        "buttermilch", "buttermilchpulver",
        # ── Käse (alle gängigen Sorten) ──
        "käse", "frischkäse", "weichkäse", "hartkäse", "halbhartkäse",
        "schmelzkäse", "scheibenkäse", "reibekäse", "streukäse",
        "mozzarella", "büffelmozzarella", "burrata",
        "parmesan", "parmigiano", "parmigiano reggiano", "grana padano",
        "gouda", "jung gouda", "alter gouda",
        "emmentaler", "emmental", "allgäuer emmentaler",
        "cheddar", "aged cheddar",
        "brie", "camembert", "normandie camembert",
        "feta", "schafskäse",
        "ricotta", "ricotta salata",
        "mascarpone", "gorgonzola", "pecorino", "pecorino romano",
        "gruyère", "gruyere", "comté",
        "raclette", "tilsiter", "appenzeller", "bergkäse",
        "havarti", "edam", "provolone", "asiago",
        "manchego", "halloumi",
        "cottage cheese", "cream cheese", "quark käse",
        # ── Sauermilch & Fermentiertes ──
        "joghurt", "naturjoghurt", "fruchtjoghurt",
        "yogurt", "yoghurt", "greek yogurt", "griechischer joghurt",
        "quark", "magerquark", "speisequark",
        "kefir", "skyr", "dickmilch", "sauermilch", "acidophilus",
        "crème double", "ayran", "lassi",
        # ── Eiscreme & Desserts ──
        "eiscreme", "speiseeis", "milcheis", "sahneeis",
        "ice cream", "gelato",
        "pudding", "milchpudding", "milchreis",
        "panna cotta", "mousse au chocolat",   # wenn mit Sahne
        # ── Proteine & technische Zutaten ──
        "kasein", "casein", "natriumcaseinat", "calciumcaseinat",
        "molke", "molkenprotein", "molkenpulver", "süßmolke", "sauermolke",
        "whey", "whey protein", "whey concentrate", "whey isolate",
        "lactalbumin", "laktoglobulin", "beta-lactoglobulin",
        "laktose", "lactose", "laktat", "milchsäure",   # Milchsäure ≠ Milch, aber oft verwechselt
        "milcheiweiß", "milchprotein", "milchzucker", "milchfett",
        "milchserum", "milchzubereitung",
        # ── Englisch allgemein ──
        "milk", "dairy", "cream", "cheese", "butter fat", "milk fat",
        "milk protein", "milk powder", "milk solid",
        "non-fat milk", "skim milk", "whole milk",
    ],

    "ei": [
        # ── Deutsch ──
        "hühnerei", "hühnereier", "entenei", "enteneier",
        "gänseei", "gänseeier", "wachtelei", "wachteleier",
        "vollei", "volleipulver",
        "eigelb", "eidotter", "dotter", "eigelbpulver",
        "eiklar", "eiweiß", "eiklarpulver", "eiweißpulver",
        "eipulver", "trockenei", "trockeneigelb", "trockeneiklar",
        "flüssigei", "flüssigeiklar", "flüssigeigelb",
        "pasteurisiertes ei", "pasteurisiertes vollei",
        "eiprotein", "eiextrakt", "eiprodukt",
        # ── Einzeln als Zutat (mit Kontext-Trennzeichen) ──
        " ei,", " ei ", "eier,", "ganze eier",
        # ── Proteine & technische Begriffe ──
        "ovalbumin", "ovomucin", "ovomucoid", "ovotransferrin",
        "lysozym", "conalbumin", "ovoglobulin", "ovomakroglobulin",
        "globulin", "vitellin", "livetin", "phosvitin",
        # ── Verarbeitungsprodukte ──
        "mayonnaise", "mayo", "majonäse", "aioli",
        "meringue", "baiser",
        "eiernudeln", "eierteigwaren", "eierpasta",
        "pasta all'uovo", "pasta all uovo",
        "eierlikör",
        "hollandaise", "béarnaise", "bernaise",
        "caesar sauce",          # enthält Ei
        "remoulade",
        "tartar sauce", "tartarsauce",
        "lemon curd",
        "tiramisu",              # oft rohes Eigelb
        "zabaione", "zabaglione",
        # ── Englisch ──
        "egg", "eggs", "egg white", "egg yolk", "egg powder",
        "dried egg", "egg protein", "whole egg", "liquid egg",
        "free range egg", "organic egg",
    ],

    "gluten": [
        # ── Getreidesorten (Stämme reichen da sie Komposita treffen) ──
        "weizen", "dinkel", "roggen", "gerste", "hafer", "kamut",
        "emmer", "einkorn", "triticale", "grünkern", "durum",
        "hartweizen", "durum weizen",
        # ── Weizenprodukte ──
        "weizenmehl", "weizenstärke", "weizenprotein", "weizenkeime",
        "weizenkleie", "weizengrieß", "weizengluten", "weizenextrakt",
        "weizenkeimöl", "weizenspeisekleie", "weizenkleber",
        "weizenalkohol",         # in Backwaren als Aroma
        # ── Dinkel ──
        "dinkelmehl", "dinkelgrieß", "dinkelkleie", "dinkelprotein",
        "dinkelflocken",
        # ── Roggen ──
        "roggenmehl", "roggenvollkornmehl", "roggengrieß",
        "roggenkleie", "roggenflocken",
        # ── Gerste ──
        "gerstenmehl", "gerstenflocken", "gerstenmalz", "gerstenmalzextrakt",
        "malz", "malzextrakt", "malzmehl", "malzsirup", "gerstengraupen",
        "graupen",
        # ── Hafer ──
        "hafermehl", "haferflocken", "haferkleie", "hafergrieß",
        "haferprotein", "haferstärke",
        "rolled oats", "oat flakes",
        # ── Mehlprodukte & Backzutaten ──
        "mehl", "vollkornmehl", "type 405", "type 550", "type 1050",
        "grieß", "hartweizengrieß",
        "semmelbrösel", "paniermehl", "panko", "tempuramehl",
        "backpulver",            # kann Weizenstärke enthalten
        "speisestärke",          # oft Weizenstärke
        "stärke",                # ohne Angabe oft Weizen
        # ── Brot & Backwaren ──
        "brot", "vollkornbrot", "weißbrot", "toastbrot",
        "brötchen", "semmel", "schrippe",  # Österreich/Berlin
        "baguette", "ciabatta", "focaccia", "pita", "naan",
        "tortilla", "wrap",
        "brezel", "laugenstange", "laugengebäck",
        "cracker", "knäckebrot", "zwieback", "keks",
        "croissant", "blätterteig",
        "croutons", "toast",
        # ── Teig ──
        "teig", "mürbeteig", "hefeteig", "strudelteig",
        "biskuitteig", "pizzateig",
        # ── Pasta & Nudeln ──
        "nudeln", "pasta", "spaghetti", "penne", "rigatoni",
        "tagliatelle", "linguine", "fusilli", "farfalle",
        "lasagne", "lasagna", "tortellini", "ravioli", "gnocchi",
        "spätzle", "knöpfle", "maultaschen",
        # ── Andere Getreideprodukte ──
        "bulgur", "couscous", "semolina", "farro", "freekeh",
        "seitan",                # reines Weizengluten
        "weizenkleber",
        "malzbier",              # alkoholfrei, enthält Gluten
        "bier",                  # typischerweise Gerste/Weizen
        # ── Saucen & Würzmittel ──
        "sojasoße",              # normale Sojasoße enthält Weizen
        "soy sauce",
        "teriyaki", "teriyakisauce",
        "worcestersauce", "worcestershire sauce",
        "ketjap manis",
        "miso",                  # oft mit Gerste/Weizen
        # ── Gluten direkt ──
        "gluten", "weizengluten", "vital wheat gluten",
        # ── Englisch ──
        "wheat", "wheat flour", "wheat starch", "wheat germ", "wheat bran",
        "wheat protein", "wheat gluten", "durum wheat", "wheat semolina",
        "rye", "rye flour", "rye bread",
        "barley", "barley malt", "barley extract", "pearl barley",
        "malt", "malt extract", "malt vinegar", "malted",
        "oat", "oats", "oatmeal", "oat flour", "oat bran",
        "spelt", "triticale", "kamut", "einkorn", "emmer",
        "breadcrumbs", "bread crumbs", "breading",
        "flour", "all-purpose flour", "plain flour",
    ],

    "soja": [
        # ── Deutsch ──
        "soja", "sojabohne", "sojabohnen", "sojaöl", "soja-öl",
        "sojaprotein", "sojasoße", "sojasosse", "sojasauce",
        "sojamehl", "sojalecithin", "soja-lecithin",
        "sojakeimlinge", "sojasprossen", "sojakeim",
        "sojaextrakt", "sojakäse", "sojadrink", "sojamilch",
        "sojajoghurt", "sojanudeln", "sojaflocken",
        "sojamark", "sojaschrot",
        # ── Verarbeitungsprodukte ──
        "tofu", "seidentofu", "silkentofu", "firm tofu", "räuchertofu",
        "tempeh", "natto",
        "miso",                  # oft aus Soja (auch Gerste/Weizen)
        "misopaste", "shiro miso", "aka miso",
        "edamame", "edamamebohnen",
        "okara", "kinako",       # geröstetes Sojamehl (Japan)
        "yuba",                  # Sojadrinkfolie
        "sojafleisch", "sojagranulat",
        "textured soy protein", "tsp",
        "textured vegetable protein", "tvp",
        "soy nuggets",
        # ── Lecithin (häufig aus Soja) ──
        "lecithin", "sojalecithin", "e322",
        "soy lecithin", "soya lecithin",
        # ── Saucen & Würzmittel mit Soja ──
        "sojasoße", "soy sauce", "tamari",
        "teriyakisauce", "teriyaki sauce",
        "hoisin", "hoisinsauce", "hoisin sauce",
        "ketjap", "ketjap manis",
        "ponzu",
        "doubanjiang", "gochujang",   # enthält oft Soja
        "worcestersauce",              # kann Soja enthalten
        # ── Englisch ──
        "soy", "soya", "soybean", "soy beans",
        "soy milk", "soy cream", "soy yogurt",
        "soy protein", "soy flour", "soy oil",
        "soy isolate", "soy concentrate",
    ],

    "nüsse": [
        # ── Mandel ──
        "mandel", "mandeln", "mandelkern", "mandelmehl", "mandelöl",
        "mandelmilch", "mandelpaste", "mandelmus", "mandelcreme",
        "mandelextrakt", "mandelblätter", "mandelblättchen",
        "mandelstift", "mandelkrokant", "geröstete mandel",
        "bittermandel", "bittermandelöl", "amaretto",   # Bittermandel
        "almond", "almonds", "almond flour", "almond milk",
        "almond oil", "almond paste", "almond extract",
        "almond butter", "almond meal", "ground almond",
        "flaked almond", "sliced almond",
        "marzipan", "persipan",   # Persipan aus Aprikosenkernen, aber ähnlich
        # ── Haselnuss ──
        "haselnuss", "haselnüsse", "haselnusskern", "haselnussöl",
        "haselnussmus", "haselnusspaste", "haselnusskrokant",
        "haselnussmehl", "gemahlene haselnüsse",
        "hazelnut", "hazelnuts", "hazelnut oil", "hazelnut paste",
        "hazelnut butter", "ground hazelnut",
        "nutella",                # enthält Haselnuss
        "nussnougatcreme", "nuss-nougat-creme",
        # ── Walnuss ──
        "walnuss", "walnüsse", "walnusskern", "walnussöl",
        "walnussmehl", "gehackte walnüsse",
        "walnut", "walnuts", "walnut oil", "ground walnut",
        "black walnut",
        # ── Cashew ──
        "cashew", "cashews", "cashewkern", "cashewöl", "cashewmus",
        "cashewcreme", "cashewmilch",
        "cashew nut", "cashew nuts", "cashew butter", "cashew cream",
        "cashew milk",
        # ── Pistazie ──
        "pistazie", "pistazien", "pistazienkern", "pistazienmus",
        "pistazienöl", "pistazienmehl",
        "pistachio", "pistachios", "pistachio oil", "pistachio paste",
        "pistachio butter",
        # ── Macadamia ──
        "macadamia", "macadamianuss", "macadamianüsse",
        "macadamiaöl",
        "macadamia nut", "macadamia nuts", "macadamia oil",
        # ── Pekan ──
        "pekannuss", "pekannüsse", "pekankern",
        "pekan", "pecan", "pecans", "pecan nut", "pecan oil",
        # ── Paranuss ──
        "paranuss", "paranüsse", "paranusskern",
        "brazil nut", "brazil nuts", "para nut", "castanha do pará",
        # ── Pinienkerne ──
        "pinienkern", "pinienkerne",
        "pine nut", "pine nuts", "pinoli", "pignoli",
        # ── Kokosnuss ──
        "kokosnuss", "kokos", "kokosmilch", "kokoscreme", "kokoswasser",
        "kokosraspeln", "kokosflocken", "kokosmehl", "kokosfett",
        "kokosöl", "kokosbutter", "kokosmark", "kokoscreme",
        "coconut", "coconut milk", "coconut oil", "coconut cream",
        "coconut water", "coconut flour", "coconut butter",
        "desiccated coconut", "shredded coconut", "coconut flakes",
        "coconut fat", "creamed coconut",
        # ── Maroni / Kastanie (Baumnuss) ──
        "maroni", "marone", "esskastanie", "kastanie",
        "chestnut", "chestnuts", "chestnut flour",
        # ── Allgemein ──
        "nuss", "nüsse", "nussmix", "nussmischung", "nussfüllung",
        "nussmus", "nussöl", "nussprotein", "nusscreme",
        "nut", "nuts", "mixed nuts", "tree nut", "tree nuts",
        "nut butter", "nut oil", "nut milk", "nut paste",
        "nut mix", "nut blend",
        # ── Nusshaltige Produkte ──
        "nougat", "nuss-nougat", "nussnougat",
        "praline", "praliné", "gianduja", "gianduia",
        "nussschokolade", "nussriegel",
        "trail mix",
    ],

    "fisch": [
        # ── Häufige Arten (Deutsch) ──
        "lachs", "atlantischer lachs", "pazifischer lachs",
        "räucherlachs", "graved lachs", "gravad lachs", "lachsfilet",
        "lachsforelle", "regenbogenforelle",
        "thunfisch", "gelbflossenthun", "weißer thun", "thunfischfilet",
        "kabeljau", "dorsch", "atlant. kabeljau",
        "forelle", "bachforelle",
        "sardine", "sardinelle", "sardellen", "anchovis", "acciughe",
        "hering", "bismarckhering", "matjes", "rollmops", "heringsfilet",
        "bückling", "räucherhering",
        "sprotte", "kieler sprotte",
        "makrele", "atlantische makrele", "räuchermakrele", "makrelenfilet",
        "seezunge", "scholle", "flunder", "kliesche",
        "heilbutt", "schwarzer heilbutt",
        "rotbarsch", "tiefenbarsch",
        "tilapia", "pangasius", "pangasiusfilet",
        "zander", "flussbarsch", "barsch",
        "karpfen", "karausche",
        "aal", "räucheraal",
        "wels", "waller",
        "hecht",
        "seelachs", "köhler",   # kein echter Lachs aber wird oft so genannt
        "pollack",
        "steinbeißer", "seeteufel",
        "rotzunge",
        # ── Verarbeitungsprodukte ──
        "fisch", "fischfilet", "fischstäbchen", "fischpaste",
        "fischöl", "fischprotein", "fischextrakt", "fischsoße",
        "fischsauce", "fischmehl", "fischaroma", "fischgeschmack",
        "fischbrühe", "fischfond", "fischsud",
        "fischkonserve", "fischzubereitung",
        "surimi",                # Fischeiweiß (oft Pollock)
        "krabbenfleisch-imitat", "krebsfleisch-imitat",
        "fischrogen", "kaviar", "lachskaviar",
        # ── Saucen & Würzmittel ──
        "worcestersauce", "worcestershire sauce", "worcestershire",
        "caesar dressing", "caesar sauce",
        "nuoc cham", "nuoc mam",   # vietnamesische Fischsauce
        "nam pla",                  # thai Fischsauce
        "garum",                    # antike Fischsauce
        "colatura di alici",        # ital. Sardellenöl
        # ── Englisch ──
        "fish", "fish oil", "fish sauce", "fish paste", "fish protein",
        "fish extract", "fish stock", "fish broth",
        "salmon", "smoked salmon", "gravlax",
        "tuna", "yellowfin tuna", "albacore",
        "cod", "atlantic cod",
        "trout", "rainbow trout",
        "sardine", "sardines",
        "herring", "pickled herring",
        "mackerel",
        "anchovy", "anchovies",
        "halibut",
        "sea bass", "european sea bass",
        "plaice", "sole", "flounder",
        "tilapia", "pangasius",
        "pollock", "alaska pollock",
        "surimi",
        "fish roe", "caviar",
    ],

    "sellerie": [
        # ── Deutsch ──
        "sellerie", "staudensellerie", "knollensellerie", "bleichsellerie",
        "selleriesalz", "selleriesalz",
        "sellerieöl", "selleriesamen", "selleriekörner",
        "sellerieextrakt", "sellerieblätter", "sellerieblatt",
        "selleriewurzel", "sellerieknolle",
        "selleriesaft", "selleriepulver", "selleriegewürz",
        "selleriearoma",
        "liebstöckel",           # ähnliches Aroma, botanisch verwandt
        # ── Englisch ──
        "celery", "celery salt", "celery seed", "celery seeds",
        "celery oil", "celery extract", "celery juice",
        "celery root", "celeriac", "celery powder",
        "celery leaves",
        # ── Produkte ──
        "suppengrün",            # enthält meist Sellerie
        "suppengemüse",
        "gemüsebrühe",           # oft Sellerie
        "gemüsebouillon",
        "instantbrühe",
    ],

    "senf": [
        # ── Deutsch ──
        "senf", "senfkörner", "senfkorn", "senfmehl", "senfpulver",
        "senföl", "senfextrakt", "senfsoße", "senfsauce",
        "senfzubereitung", "tafelsenf", "tafelsenfkörner",
        "dijonsenf", "dijon-senf", "dijon senf",
        "grobkörniger senf", "körniger senf", "vollkornsenf",
        "süßer senf", "bayerischer senf", "weißwurstsenf",
        "amerikanischer senf", "english mustard",
        "scharfer senf", "senfschärfe",
        "gelber senf", "brauner senf", "schwarzer senf",
        "weißer senfkorn", "gelber senfkorn",
        "senfsaat",
        # ── Englisch ──
        "mustard", "mustard seed", "mustard seeds",
        "mustard flour", "mustard oil", "mustard extract",
        "mustard powder", "mustard paste",
        "dijon mustard", "whole grain mustard", "wholegrain mustard",
        "french mustard", "american mustard", "english mustard",
        "yellow mustard", "brown mustard", "black mustard",
        "mustard greens",
        # ── Produkte die Senf enthalten ──
        "remoulade",
        "honey mustard", "honigsenf",
        "senfdressing", "mustard dressing",
        "currysauce",            # enthält oft Senf
        "curry sauce",
        "ravigote",
    ],

    "sesam": [
        # ── Deutsch ──
        "sesam", "sesamsamen", "sesam-samen", "sesam samen",
        "sesamkörner", "sesamkorn", "sesam-körner",
        "sesamöl", "sesam-öl", "geröstetes sesamöl",
        "sesammehl", "sesampaste", "sesammus",
        "sesamextrakt", "sesamprotein",
        "schwarzer sesam", "weißer sesam", "heller sesam",
        "schwarzes sesam", "gerösteter sesam",
        "ungeschälter sesam", "geschälter sesam",
        "sesambrot", "sesambrötchen", "sesamkruste",
        "sesamriegel", "sesamgebäck",
        # ── Tahini / Sesampaste ──
        "tahini", "tahin", "tahina", "sesampaste",
        # ── Englisch ──
        "sesame", "sesame seed", "sesame seeds",
        "sesame oil", "roasted sesame oil", "toasted sesame oil",
        "sesame flour", "sesame paste", "sesame butter",
        "sesame extract", "sesame protein",
        "toasted sesame", "black sesame", "white sesame",
        "roasted sesame", "hulled sesame", "unhulled sesame",
        # ── Japanisch / asiatisch (häufig in Rezepten) ──
        "goma", "neri goma", "shiro goma", "kuro goma",
        "goma dare",             # Sesamdressing
        "furikake",              # enthält oft Sesam
        # ── Produkte mit Sesam ──
        "hummus",                # enthält Tahini
        "baba ganoush", "baba ghanoush",
        "halva", "halwa",        # Sesam-Süßigkeit
        "sesamkonfekt",
    ],

    "lupine": [
        # ── Deutsch ──
        "lupine", "lupinen", "süßlupine",
        "lupinenmehl", "lupinenprotein", "lupinensamen",
        "lupinenextrakt", "lupinenkorn", "lupinenkerne",
        "lupinenflocken", "lupinendrink", "lupinenmilch",
        "lupinentofu", "lupinenschrot",
        "lupinenkaffee",         # Lupinenkaffeepulver
        # ── Englisch ──
        "lupin", "lupins", "lupin flour", "lupin protein",
        "lupin seed", "lupin bean", "lupin milk",
        "sweet lupin",
        # ── Hinweis: Lupine oft als Weizen-/Soja-Ersatz ──
        "lupinenersatz",
    ],

    "weichtiere": [
        # ── Muscheln ──
        "muschel", "miesmuschel", "grünlippmuschel", "herzmuschel",
        "venusmuschel", "jakobsmuschel", "pilgermuschel", "kammmuschel",
        "auster", "austern", "felsenauster",
        "clam", "clams", "oyster", "oysters",
        "scallop", "scallops", "queen scallop",
        "mussel", "mussels", "green lipped mussel",
        # ── Tintenfische ──
        "tintenfisch", "kalmar", "loligo",
        "squid", "squid ink", "tintenfischtinte",
        "calamari", "calamar", "calamares",
        "oktopus", "krake", "octopus",
        "sepia", "sepiatinte", "sepia-tinte",
        "cuttlefish",
        # ── Schnecken ──
        "schnecke", "weinbergschnecke", "meeresschnecke",
        "escargot", "snail",
        "abalone",               # Seeohr
        # ── Allgemein ──
        "weichtier", "weichtiere",
        "mollusc", "molluscs", "mollusk", "mollusks",
        "cephalopod", "bivalve",
        # ── Produkte ──
        "meeresfrüchte",         # kann Weichtiere enthalten
        "frutti di mare",
        "seafood mix",
        "tintenfischtuben", "calamari rings",
    ],

    "krebstiere": [
        # ── Deutsch ──
        "krebstier", "krebstiere",
        "garnele", "garnelen", "riesengarnele", "tigergarnele",
        "kaisergranat", "scampi",
        "crevette", "crevetten",
        "hummer", "amerikanischer hummer",
        "languste", "langustine",
        "krabbe", "krabben", "taschenkrebs", "königskrabbe",
        "schneekrabbe", "schwimmkrabbe",
        "flusskrebs", "edelkrebs",
        # ── Englisch ──
        "crustacean", "crustaceans",
        "shrimp", "shrimps", "prawn", "prawns",
        "tiger prawn", "king prawn",
        "lobster", "rock lobster", "spiny lobster",
        "langoustine", "norway lobster",
        "crab", "crabs", "king crab", "snow crab", "blue crab",
        "crayfish", "freshwater crayfish",
        # ── Produkte ──
        "krabbenpaste", "garnelenpaste", "shrimp paste",
        "krabbenchips", "prawn crackers", "prawn chips",
        "garnelenpulver", "shrimp powder",
        "hummerbisque", "hummersauce", "lobster bisque",
        "meeresfrüchte",
        "frutti di mare",
        "paella",                # enthält oft Krebstiere
        "bouillabaisse",
    ],

    "sulfite": [
        # ── E-Nummern ──
        "e220", "e221", "e222", "e223", "e224", "e225", "e226", "e227", "e228",
        # ── Deutsch ──
        "sulfit", "sulfite", "schwefeldioxid", "schwefel",
        "schwefelhaltig", "geschwefelt", "eingeschwefelter",
        "natriumsulfit", "natriummetabisulfit", "natriumbisulfit",
        "kaliumbisulfit", "kaliummetabisulfit", "kaliumsulfit",
        "calciumsulfit", "calciumbisulfit",
        "ammoniumsulfit",
        # ── Englisch ──
        "sulphite", "sulphites", "sulfite", "sulfites",
        "sulphur dioxide", "sulfur dioxide",
        "sodium sulphite", "sodium sulfite",
        "sodium bisulphite", "sodium bisulfite",
        "sodium metabisulphite", "sodium metabisulfite",
        "potassium bisulphite", "potassium bisulfite",
        "potassium metabisulphite", "potassium metabisulfite",
        "potassium sulphite", "potassium sulfite",
        "calcium sulphite", "calcium sulfite",
        # ── Lebensmittel mit natürlich hohem Sulfitgehalt ──
        "trockenfrüchte",        # oft geschwefelt
        "getrocknete früchte",
        "wein",                  # fast immer Sulfite
        "rotwein", "weißwein", "sekt", "champagner",
        "weinessig",
        "bier",                  # kann Sulfite enthalten
        "fruchtsaft",            # oft Sulfite als Konservierungsmittel
        "mostrich",
        # ── Hinweise auf Verpackungen ──
        "enthält sulfit", "enthält sulfite",
        "contains sulphite", "contains sulphites",
        "contains sulfite",
    ],
}

# OpenFoodFacts Allergen-Tags → unsere Allergen-Schlüssel
OFF_TAG_MAP = {
    "en:gluten":      "gluten",
    "en:wheat":       "gluten",
    "en:milk":        "milch",
    "en:eggs":        "ei",
    "en:egg":         "ei",
    "en:fish":        "fisch",
    "en:peanuts":     "erdnuss",
    "en:peanut":      "erdnuss",
    "en:soybeans":    "soja",
    "en:soy":         "soja",
    "en:nuts":        "nüsse",
    "en:almonds":     "nüsse",
    "en:hazelnuts":   "nüsse",
    "en:walnuts":     "nüsse",
    "en:cashews":     "nüsse",
    "en:pistachios":  "nüsse",
    "en:celery":      "sellerie",
    "en:mustard":     "senf",
    "en:sesame":      "sesam",
    "en:lupin":       "lupine",
    "en:molluscs":    "weichtiere",
    "en:crustaceans": "krebstiere",
    "en:sulphites":   "sulfite",
    "en:sulphur-dioxide-and-sulphites": "sulfite",
}

SPUREN_PHRASEN = [
    "kann spuren enthalten", "kann spuren von",
    "may contain", "may contain traces",
    "spuren von", "traces of",
    "nicht geeignet für personen mit allergie",
    "hergestellt in einem betrieb", "in derselben anlage",
]

OFF_CACHE_TTL_DAYS = 7
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


# ── Datenbank ─────────────────────────────────────────────────────────────────
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
            methode TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS off_cache (
            query_key TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        )
    ''')
    # Spalte methode nachrüsten falls sie noch nicht existiert (Migration)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
    if "methode" not in cols:
        conn.execute("ALTER TABLE history ADD COLUMN methode TEXT")

    if not conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        conn.execute("INSERT INTO users (name, allergy) VALUES ('Demo', 'Erdnuss')")
    conn.commit()
    conn.close()


init_db()


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def synonyme_fuer(allergen: str) -> list[str]:
    key = allergen.lower().strip()
    if key in ALLERGEN_SYNONYME:
        return ALLERGEN_SYNONYME[key]
    for k, synonyme in ALLERGEN_SYNONYME.items():
        if k in key or key in k:
            return synonyme
    return [key]


def extrahiere_produktnamen(text: str) -> list[str]:
    """Versucht Produktnamen oder Barcodes aus dem Freitext zu extrahieren."""
    kandidaten = []

    # Barcode (EAN-8, EAN-13)
    for barcode in re.findall(r'\b\d{8,13}\b', text):
        kandidaten.append(barcode)

    # Erste nicht-leere Zeile als Produktname (oft Überschrift / Seitentitel)
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if 5 < len(zeile) < 80:
            kandidaten.append(zeile)
            break

    # Zutaten-Substring (erste 120 Zeichen nach "Zutaten:" o.Ä.)
    m = re.search(r'(?:zutaten|ingredients)[:\s]+(.{10,120})', text, re.IGNORECASE)
    if m:
        kandidaten.append(m.group(1).strip())

    return kandidaten[:3]  # max 3 Versuche


def off_cache_lesen(key: str) -> Optional[dict]:
    conn = db()
    row = conn.execute(
        'SELECT response_json, cached_at FROM off_cache WHERE query_key=?', (key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    # TTL prüfen
    cached = datetime.datetime.fromisoformat(row["cached_at"])
    if (datetime.datetime.now() - cached).days >= OFF_CACHE_TTL_DAYS:
        return None
    return json.loads(row["response_json"])


def off_cache_schreiben(key: str, data: dict):
    conn = db()
    conn.execute(
        'INSERT OR REPLACE INTO off_cache (query_key, response_json, cached_at) VALUES (?,?,?)',
        (key, json.dumps(data), datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def suche_off(query: str) -> Optional[dict]:
    """Sucht ein Produkt auf OpenFoodFacts. Gibt None zurück wenn nichts gefunden."""
    cached = off_cache_lesen(query)
    if cached is not None:
        return cached

    # Barcode-Suche
    if re.fullmatch(r'\d{8,13}', query):
        url = f"https://world.openfoodfacts.org/api/v2/product/{query}.json"
        try:
            r = requests.get(url, timeout=5,
                             headers={"User-Agent": "AllergyGuard/1.0"})
            data = r.json()
            if data.get("status") == 1:
                result = data.get("product", {})
                off_cache_schreiben(query, result)
                return result
        except Exception:
            pass
        return None

    # Textsuche
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 3,
        "fields": "product_name,allergens_tags,allergens,traces_tags,ingredients_text",
    }
    try:
        r = requests.get(url, params=params, timeout=6,
                         headers={"User-Agent": "AllergyGuard/1.0"})
        data = r.json()
        products = data.get("products", [])
        # Ersten Treffer mit Allergen-Daten bevorzugen
        for p in products:
            if p.get("allergens_tags") or p.get("ingredients_text"):
                off_cache_schreiben(query, p)
                return p
    except Exception:
        pass
    return None


def off_allergene_pruefen(produkt: dict, user_allergien: list[str]) -> list[dict]:
    """Gleicht OFF-Allergen-Tags mit dem Nutzerprofil ab. Gibt Funde zurück."""
    funde = []
    allergen_tags    = produkt.get("allergens_tags", [])
    spuren_tags      = produkt.get("traces_tags", [])
    produkt_name     = produkt.get("product_name", "Unbekanntes Produkt")

    for allergie in user_allergien:
        # Prüfen ob ein OFF-Tag zu dieser Allergie passt
        for tag, schluessel in OFF_TAG_MAP.items():
            if schluessel != allergie.lower().strip() and schluessel not in allergie.lower():
                continue
            if tag in allergen_tags:
                funde.append({
                    "allergie":   allergie,
                    "synonym":    tag.replace("en:", ""),
                    "fundstelle": f"OpenFoodFacts: {produkt_name}",
                    "ist_spur":   False,
                })
                break
            if tag in spuren_tags:
                funde.append({
                    "allergie":   allergie,
                    "synonym":    tag.replace("en:", ""),
                    "fundstelle": f"OpenFoodFacts (Spur): {produkt_name}",
                    "ist_spur":   True,
                })
                break
    return funde


def analyse_mit_ollama(text: str, user_allergien: list[str]) -> list[dict]:
    """Fragt Ollama nach Allergenen im Text. Gibt Funde zurück."""
    allergien_str = ", ".join(user_allergien)
    prompt = (
        f"Du bist ein Allergie-Assistent. Analysiere folgenden Zutaten- oder Produkttext "
        f"und prüfe ob er Allergene enthält, die für jemanden mit diesen Allergien gefährlich sind: {allergien_str}.\n\n"
        f"Text:\n{text[:2000]}\n\n"
        f"Antworte NUR mit einem JSON-Array. Jedes Objekt hat die Felder: "
        f"\"allergie\" (welche Allergie betroffen), \"synonym\" (gefundener Begriff im Text), "
        f"\"fundstelle\" (genaue Textstelle, max 80 Zeichen), \"ist_spur\" (true/false, ob es ein Spurenhinweis ist).\n"
        f"Wenn nichts gefunden wurde, antworte mit: []\n"
        f"Antworte ausschliesslich mit dem JSON, ohne Erklaerung."
    )
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }, timeout=30)
        raw = r.json().get("response", "[]").strip()
        # JSON aus der Antwort extrahieren (Ollama kann manchmal Text darum schreiben)
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return []


# Kurze Begriffe die Wortgrenzen brauchen um Falschpositive zu vermeiden
# z.B. "ei" soll nicht "Zwiebel", "Eisen", "Protein" treffen
WORTGRENZE_SYNONYME = {
    "ei", "eier", "nut", "nuts", "cod", "rye", "oat", "oats", "malt",
    "crab", "bass", "clam", "aal", "feta", "brie",
}


def synonym_trifft(synonym: str, text_lower: str) -> bool:
    """Prüft ob ein Synonym im Text vorkommt; kurze Begriffe nur an Wortgrenzen."""
    if synonym in WORTGRENZE_SYNONYME or len(synonym) <= 3:
        pattern = r'(?<![a-zäöüß])' + re.escape(synonym) + r'(?![a-zäöüß])'
        return bool(re.search(pattern, text_lower))
    return synonym in text_lower


def synonym_matching(text: str, user_allergien: list[str]) -> list[dict]:
    """Lokales Synonym-Matching als letzter Fallback."""
    funde = []
    text_lower = text.lower()
    for allergie in user_allergien:
        synonyme = synonyme_fuer(allergie)
        for synonym in synonyme:
            if not synonym_trifft(synonym, text_lower):
                continue
            for zeile in text.splitlines():
                if synonym_trifft(synonym, zeile.lower()):
                    zeile_lower = zeile.lower()
                    ist_spur = any(p in zeile_lower for p in SPUREN_PHRASEN)
                    if not ist_spur:
                        pos = text_lower.find(synonym)
                        kontext = text_lower[max(0, pos - 150):pos + 150]
                        ist_spur = any(p in kontext for p in SPUREN_PHRASEN)
                    funde.append({
                        "allergie":   allergie,
                        "synonym":    synonym,
                        "fundstelle": zeile.strip(),
                        "ist_spur":   ist_spur,
                    })
                    break
            if any(f["allergie"] == allergie for f in funde):
                break
    return funde


# ── Modelle ───────────────────────────────────────────────────────────────────
class RecipeRequest(BaseModel):
    ingredients: str
    source: Optional[str] = "Unbekannt"


class ProfileRequest(BaseModel):
    name: str
    allergy: str


# ── Endpunkte ─────────────────────────────────────────────────────────────────
@app.get("/profile")
def get_profile():
    conn = db()
    user = conn.execute('SELECT name, allergy FROM users LIMIT 1').fetchone()
    conn.close()
    if not user:
        return {"name": "", "allergy": ""}
    return {"name": user["name"], "allergy": user["allergy"]}


@app.post("/profile")
def save_profile(req: ProfileRequest):
    conn = db()
    existing = conn.execute('SELECT id FROM users LIMIT 1').fetchone()
    if existing:
        conn.execute('UPDATE users SET name=?, allergy=? WHERE id=?',
                     (req.name, req.allergy, existing["id"]))
    else:
        conn.execute('INSERT INTO users (name, allergy) VALUES (?,?)', (req.name, req.allergy))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/history")
def get_history():
    conn = db()
    rows = conn.execute(
        'SELECT * FROM history ORDER BY timestamp DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/check-recipe")
def check_recipe(request: RecipeRequest):
    conn = db()
    user = conn.execute('SELECT name, allergy FROM users LIMIT 1').fetchone()
    conn.close()
    if not user:
        return {"error": "Kein Benutzerprofil gefunden. Bitte Profil anlegen."}

    user_name    = user["name"]
    user_allergy = user["allergy"]
    allergien    = [a.strip() for a in user_allergy.split(",") if a.strip()]
    text         = request.ingredients

    funde: list[dict] = []
    methode = "synonym"

    # ── 1. OpenFoodFacts — NUR bei Barcode ───────────────────────────────────
    # Freitext-Rezepte liefern auf OFF zufällige Produkte (z.B. "Biscoff"),
    # daher wird OFF ausschließlich bei erkanntem EAN-8/EAN-13-Barcode genutzt.
    barcodes = re.findall(r'\b\d{8,13}\b', text)
    for barcode in barcodes:
        produkt = suche_off(barcode)
        if produkt:
            off_funde = off_allergene_pruefen(produkt, allergien)
            if off_funde or produkt.get("allergens_tags"):
                funde = off_funde
                methode = "openfoodfacts"
                break

    # ── 2. Ollama-Fallback ────────────────────────────────────────────────────
    if methode != "openfoodfacts":
        ollama_funde = analyse_mit_ollama(text, allergien)
        if ollama_funde:
            funde = ollama_funde
            methode = "ollama"

    # ── 3. Lokales Synonym-Matching als letzter Fallback ──────────────────────
    if methode not in ("openfoodfacts", "ollama"):
        funde = synonym_matching(text, allergien)
        methode = "synonym"

    # ── Gesamturteil ──────────────────────────────────────────────────────────
    gefahr_funde = [f for f in funde if not f.get("ist_spur")]
    spuren_funde = [f for f in funde if f.get("ist_spur")]

    if gefahr_funde:
        urteil = "GEFAHR"
    elif spuren_funde:
        urteil = "WARNUNG"
    else:
        urteil = "SICHER"

    erster_fund        = (gefahr_funde or spuren_funde or [None])[0]
    gefundenes_synonym = erster_fund["synonym"] if erster_fund else ""
    gefunden_in        = erster_fund["fundstelle"] if erster_fund else ""

    if urteil == "GEFAHR":
        allergien_liste = ", ".join(f["allergie"] for f in gefahr_funde)
        grund = f'Direkt gefunden: {allergien_liste}. (via {methode})'
    elif urteil == "WARNUNG":
        allergien_liste = ", ".join(f["allergie"] for f in spuren_funde)
        grund = f'Spurenhinweise auf: {allergien_liste}. (via {methode})'
    else:
        grund = f'Keine Allergene gefunden. (via {methode})'

    # ── Verlauf speichern ─────────────────────────────────────────────────────
    conn = db()
    conn.execute(
        '''INSERT INTO history
           (timestamp, source, urteil, allergie_geprueft, gefundenes_synonym, fundstelle, grund, methode)
           VALUES (?,?,?,?,?,?,?,?)''',
        (
            datetime.datetime.now().isoformat(),
            request.source or "Unbekannt",
            urteil, user_allergy,
            gefundenes_synonym, gefunden_in, grund, methode,
        )
    )
    conn.execute('''
        DELETE FROM history WHERE id NOT IN (
            SELECT id FROM history ORDER BY timestamp DESC LIMIT 20
        )
    ''')
    conn.commit()
    conn.close()

    return {
        "nutzer":             user_name,
        "allergie_geprueft":  user_allergy,
        "urteil":             urteil,
        "gefundenes_synonym": gefundenes_synonym,
        "fundstelle":         gefunden_in,
        "grund":              grund,
        "methode":            methode,
        "alle_funde":         funde,
    }
