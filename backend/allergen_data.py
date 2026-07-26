"""Allergen knowledge base: synonyms, OpenFoodFacts mappings, and replacement suggestions."""

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

# ── Ersatzvorschläge pro gefundenem Begriff ──────────────────────────────────
# Schlüssel: Substring (Kleinschreibung) der im Text gefunden wurde
# Wert: Liste von Ersatzvorschlägen (wird dem Nutzer angezeigt)
ERSATZ: dict[str, list[str]] = {
    # Erdnuss
    "erdnuss":        ["Sonnenblumenöl", "Mandelmus (falls keine Nussallergie)", "Sonnenblumenbutter"],
    "erdnussöl":      ["Sonnenblumenöl", "Rapsöl", "Avocadoöl"],
    "erdnussbutter":  ["Sonnenblumenbutter", "Reismehlpaste", "Kürbiskernmus"],
    "erdnusspaste":   ["Sonnenblumenbutter", "Kürbiskernmus"],
    "peanut":         ["Sunflower seed butter", "Sunflower oil", "Coconut oil"],
    "peanut butter":  ["Sunflower seed butter", "Pumpkin seed butter"],
    "peanut oil":     ["Sunflower oil", "Rapeseed oil", "Avocado oil"],
    "groundnut":      ["Sunflower oil", "Rapeseed oil"],
    "satay":          ["Kürbiskern-Sauce", "Tahini-Dressing (falls kein Sesam)", "Sonnenblumenbutter-Sauce"],
    "arachis":        ["Sonnenblumenöl", "Rapsöl"],

    # Milch
    "milch":          ["Hafermilch", "Mandelmilch (falls keine Nussallergie)", "Reismilch", "Kokosdrink"],
    "butter":         ["Margarine (pflanzlich)", "Kokosöl", "Avocadoöl", "Olivenöl"],
    "butterschmalz":  ["Kokosöl", "Pflanzliches Bratfett"],
    "ghee":           ["Kokosöl", "Pflanzliches Bratfett"],
    "sahne":          ["Hafersahne", "Kokosmilch (Vollfett)", "Cashewsahne"],
    "schlagsahne":    ["Kokosmilch (gekühlt, aufschlagen)", "Haferschlagsahne"],
    "creme fraiche":  ["Cashew-Crème (eingeweicht & gemixt)", "Sojajoghurt"],
    "crème fraîche":  ["Cashew-Crème (eingeweicht & gemixt)", "Sojajoghurt"],
    "schmand":        ["Sojajoghurt", "Kokosmilch-Creme"],
    "käse":           ["Hefeflocken + Cashewcreme", "Veganer Käseersatz"],
    "mozzarella":     ["Veganer Mozzarella (Cashewbasis)", "Tofu natur (abgetropft)"],
    "parmesan":       ["Hefeflocken", "Cashew-Parmesan (Cashew + Hefe + Salz gemahlen)"],
    "frischkäse":     ["Cashew-Frischkäse", "Sojafrischkäse"],
    "ricotta":        ["Tofu natur (zerkrümelt)", "Cashew-Ricotta"],
    "mascarpone":     ["Cashew-Mascarpone", "Kokoscreme"],
    "joghurt":        ["Sojajoghurt", "Kokosjoghurt", "Haferjoghurt"],
    "yogurt":         ["Soy yogurt", "Coconut yogurt", "Oat yogurt"],
    "quark":          ["Sojajoghurt (abgetropft)", "Cashew-Quark"],
    "kasein":         ["Erbsenprotein", "Reisprotein"],
    "casein":         ["Pea protein", "Rice protein"],
    "molke":          ["Erbsenprotein-Pulver", "Hanfprotein"],
    "whey":           ["Pea protein powder", "Hemp protein", "Rice protein"],
    "laktose":        ["Laktaseenzym verwenden", "Laktosefreie Alternative"],
    "lactose":        ["Lactase enzyme", "Lactose-free alternative"],
    "milk":           ["Oat milk", "Rice milk", "Coconut drink", "Almond milk"],
    "cream":          ["Oat cream", "Coconut cream", "Cashew cream"],
    "ice cream":      ["Sorbet", "Nice cream (gefrorene Banane)", "Kokoseis"],
    "eiscreme":       ["Sorbet", "Bananencreme (gefrorene Banane)", "Kokoseis"],

    # Ei
    "eigelb":         ["1 EL Leinsamengel (1 EL Leinsamen + 3 EL Wasser)", "Aquafaba (3 EL)"],
    "eiklar":         ["Aquafaba (Kichererbsenwasser, 3 EL = 1 Eiklar)", "Agar-Agar-Schaum"],
    "eiweiß":         ["Aquafaba", "Erbsenprotein"],
    "vollei":         ["Leinsamen-Ei (1 EL gemahlen + 3 EL Wasser)", "Chia-Ei", "Apfelmus (60 g = 1 Ei)"],
    "ei,":            ["Leinsamen-Ei", "Chia-Ei (1 EL + 3 EL Wasser)", "Apfelmus (60 g)"],
    " ei ":           ["Leinsamen-Ei", "Chia-Ei (1 EL + 3 EL Wasser)", "Apfelmus (60 g)"],
    "mayonnaise":     ["Vegane Mayo (Aquafaba-Basis)", "Avocadocreme", "Hummus"],
    "mayo":           ["Vegane Mayo", "Avocadocreme"],
    "aioli":          ["Veganes Aioli (Aquafaba + Knoblauch + Öl)", "Sojajoghurt + Knoblauch"],
    "hollandaise":    ["Vegane Hollandaise (Cashew- oder Silkentofubasis)"],
    "meringue":       ["Aquafaba-Baiser (Kichererbsenwasser aufschlagen)"],
    "baiser":         ["Aquafaba-Baiser"],
    "eiernudeln":     ["Glutenfreie Reisnudeln", "Buchweizennudeln", "Linsen-Pasta"],
    "egg":            ["Flax egg (1 tbsp ground flax + 3 tbsp water)", "Chia egg", "Applesauce (60g)", "Aquafaba (3 tbsp)"],
    "egg white":      ["Aquafaba (3 tbsp per egg white)", "Agar foam"],
    "egg yolk":       ["Flax egg", "Sunflower lecithin (emulsifier)"],

    # Gluten
    "weizenmehl":     ["Reismehl", "Buchweizenmehl", "Mandelmehl (falls keine Nussallergie)", "Kichererbsenmehl", "Hafermehl (glutenfrei zertifiziert)"],
    "mehl":           ["Reismehl", "Kichererbsenmehl", "Buchweizenmehl", "Maismehl"],
    "weizenstärke":   ["Maisstärke", "Tapiokastärke", "Kartoffelstärke", "Pfeilwurzelstärke"],
    "stärke":         ["Maisstärke", "Kartoffelstärke", "Tapiokastärke"],
    "semmelbrösel":   ["Glutenfreie Semmelbrösel", "Reisbrösel", "Maisgrieß", "Kichererbsenmehl"],
    "paniermehl":     ["Glutenfreies Paniermehl", "Maismehl", "Reismehl"],
    "panko":          ["Glutenfreies Panko", "Maisflakes (fein gemahlen)"],
    "nudeln":         ["Reisnudeln", "Buchweizennudeln", "Linsen-Pasta", "Erbsen-Pasta", "Glasnudeln"],
    "pasta":          ["Rice pasta", "Buckwheat pasta", "Lentil pasta", "Chickpea pasta"],
    "spaghetti":      ["Reisnudeln", "Buchweizenspaghetti", "Maisspaghetti"],
    "brot":           ["Glutenfreies Brot (Reismehl-Basis)", "Maiswrap", "Reiswaffel"],
    "toastbrot":      ["Glutenfreies Toastbrot"],
    "weizen":         ["Buchweizen (trotz Name glutenfrei)", "Hirse", "Quinoa", "Amaranth"],
    "dinkel":         ["Buchweizen", "Hirse", "Reismehl"],
    "roggen":         ["Buchweizen", "Reismehl", "Maismehl"],
    "gerste":         ["Buchweizen", "Hirse", "Quinoa"],
    "hafer":          ["Glutenfreier Hafer (zertifiziert)", "Hirse", "Buchweizen"],
    "bulgur":         ["Hirse", "Quinoa", "Buchweizen"],
    "couscous":       ["Hirsekörner", "Quinoa", "Blumenkohlreis"],
    "grieß":          ["Polenta (Maisgrieß)", "Buchweizengries", "Hirsegrieß"],
    "seitan":         ["Tofu", "Tempeh", "Jackfrucht", "Hülsenfrüchte"],
    "gluten":         ["Glutenfreie Alternative je nach Gericht"],
    "wheat flour":    ["Rice flour", "Buckwheat flour", "Chickpea flour", "Almond flour"],
    "wheat starch":   ["Cornstarch", "Tapioca starch", "Potato starch"],
    "breadcrumbs":    ["Gluten-free breadcrumbs", "Rice crumbs", "Cornmeal"],
    "malt":           ["Ahornsirup", "Reissirup", "Dattelsirup"],
    "malzextrakt":    ["Reissirup", "Ahornsirup"],

    # Soja
    "soja":           ["Kichererbsen", "Erbsenprotein", "Linsen"],
    "sojasoße":       ["Tamari (glutenfreie Sojasoße, falls nur Glutenallergie)", "Kokosaminos", "Worcestersauce (fischfrei)"],
    "soy sauce":      ["Coconut aminos", "Tamari (check label)", "Fish sauce (if no fish allergy)"],
    "sojaprotein":    ["Erbsenprotein", "Reisprotein", "Hanfprotein"],
    "sojalecithin":   ["Sonnenblumenlecithin", "Rapsöl (als Emulgator)"],
    "soy lecithin":   ["Sunflower lecithin", "Rapeseed lecithin"],
    "lecithin":       ["Sonnenblumenlecithin (E322 aus Sonnenblume)"],
    "tofu":           ["Kichererbsen-Tofu", "Weiße Bohnen (püriert)", "Jackfrucht"],
    "tempeh":         ["Kichererbsen", "Schwarze Bohnen", "Jackfrucht"],
    "miso":           ["Kichererbsen-Miso", "Hefeflocken + Salz + etwas Essig"],
    "edamame":        ["Junge Erbsen (Petits Pois)", "Dicke Bohnen"],
    "sojamilch":      ["Hafermilch", "Reismilch", "Kokosdrink", "Erbsendrink"],
    "soy milk":       ["Oat milk", "Rice milk", "Pea milk", "Coconut drink"],
    "kokosaminos":    ["Kokosaminos sind bereits Sojasoßen-Ersatz"],

    # Nüsse
    "mandel":         ["Sonnenblumenkerne", "Kürbiskerne", "Reismehl (für Mandelmehl)"],
    "haselnuss":      ["Sonnenblumenkerne", "Kürbiskernmus"],
    "walnuss":        ["Hanfsamen", "Sonnenblumenkerne", "Kürbiskerne"],
    "cashew":         ["Sonnenblumenkerne", "Kürbiskerne (für Creme)"],
    "pistazie":       ["Kürbiskerne (ähnliche Farbe)", "Sonnenblumenkerne"],
    "macadamia":      ["Sonnenblumenkerne", "Kürbiskerne"],
    "pekannuss":      ["Sonnenblumenkerne", "Hanfsamen"],
    "paranuss":       ["Sonnenblumenkerne", "Kürbiskerne"],
    "pinienkern":     ["Sonnenblumenkerne", "Kürbiskerne", "Hanfsamen"],
    "kokos":          ["Sonnenblumenkerne (geröstet)", "Haferflocken (für Kokosraspeln-Ersatz)"],
    "kokosmilch":     ["Hafersahne", "Cashewmilch (falls keine Nussallergie)", "Erbsensahne"],
    "coconut milk":   ["Oat cream", "Sunflower seed cream", "Pea cream"],
    "nougat":         ["Sonnenblumenkern-Nougat", "Kakaopaste + Agavensirup"],
    "marzipan":       ["Sonnenblumenkern-Marzipan (Sonnenblumenkerne + Zucker + Rosenwasser)"],
    "nutella":        ["Sonnenblumenkern-Aufstrich", "Kakaobutter + Reissirup"],
    "almond":         ["Sunflower seeds", "Pumpkin seeds", "Sunflower seed flour"],
    "hazelnut":       ["Sunflower seed butter", "Pumpkin seed butter"],
    "walnut":         ["Hemp seeds", "Sunflower seeds"],
    "cashew nut":     ["Sunflower seeds", "Pumpkin seeds"],
    "chestnut":       ["Kürbis (in herzhaften Gerichten)", "Kichererbsen"],
    "nut butter":     ["Sunflower seed butter", "Pumpkin seed butter"],

    # Fisch
    "fisch":          ["Tofu (geräuchert)", "Jackfrucht (in herzhaften Gerichten)", "Kichererbsen"],
    "lachs":          ["Geräucherter Tofu", "Marinierte Karotten (als Räucherlachs-Optik)", "Rote Beete"],
    "thunfisch":      ["Kichererbsen (zerkrümelt, als Thunfischersatz)", "Junger Jackfruit"],
    "sardelle":       ["Kapernsauce", "Misopaste (Umami)", "Algen-Würzsauce"],
    "anchovis":       ["Kapernsauce", "Misopaste", "Algen-Worcestersauce"],
    "worcestersauce": ["Kokosaminos + Tamarinde + Gewürze", "Vegane Worcestersauce"],
    "worcestershire": ["Coconut aminos + tamarind", "Vegan worcestershire sauce"],
    "fischöl":        ["Algenöl (DHA/EPA aus Meeresalgen)", "Leinöl (ALA)"],
    "fish oil":       ["Algae oil (DHA/EPA)", "Flaxseed oil (ALA)"],
    "fischsauce":     ["Kokosaminos", "Sojasauce (falls keine Sojaallerie)", "Algen-Würzsoße"],
    "fish sauce":     ["Coconut aminos", "Soy sauce (if tolerated)", "Seaweed seasoning"],
    "surimi":         ["Herzhafter Tofu", "Kichererbsen"],
    "caesar dressing":["Veganes Caesar-Dressing (Cashewbasis, Kapern statt Anchovis)"],

    # Sellerie
    "sellerie":       ["Fenchel", "Petersilienwurzel", "Pastinake", "Kohlrabi"],
    "selleriesalz":   ["Meersalz + getrockneter Fenchel", "Kräutersalz ohne Sellerie"],
    "celery":         ["Fennel", "Parsley root", "Kohlrabi", "Leek"],
    "celery salt":    ["Sea salt + dried fennel", "Herb salt (celery-free)"],
    "suppengrün":     ["Lauch + Möhren + Petersilie (ohne Sellerie)"],
    "gemüsebrühe":    ["Selbstgemachte Brühe ohne Sellerie", "Pilzbrühe"],

    # Senf
    "senf":           ["Meerrettich (schärfere Alternative)", "Kurkuma + Essig + etwas Honig", "Wasabi (in kleiner Menge)"],
    "senfkörner":     ["Kapern", "Kümmel", "Fenchelsamen"],
    "mustard":        ["Horseradish", "Turmeric + vinegar + honey", "Wasabi (small amount)"],
    "mustard seed":   ["Capers", "Caraway seeds", "Fennel seeds"],
    "remoulade":      ["Vegane Remoulade ohne Senf (Kapern + Kräuter + vegane Mayo)"],

    # Sesam
    "sesam":          ["Sonnenblumenkerne", "Kürbiskerne", "Hanfsamen", "Mohn"],
    "sesamsamen":     ["Sonnenblumenkerne", "Hanfsamen", "Mohn", "Leinsamen"],
    "sesam-samen":    ["Sonnenblumenkerne", "Hanfsamen", "Mohn"],
    "sesamöl":        ["Walnussöl (Röstaroma)", "Geröstetes Kürbiskernöl", "Chiliöl (für Schärfe)"],
    "tahini":         ["Sonnenblumenkern-Mus (Sunbutter)", "Kürbiskernmus"],
    "tahin":          ["Sonnenblumenkern-Mus", "Kürbiskernmus"],
    "sesame":         ["Sunflower seeds", "Pumpkin seeds", "Hemp seeds", "Poppy seeds"],
    "sesame oil":     ["Walnut oil (roasted)", "Pumpkin seed oil", "Chili oil"],
    "sesame seeds":   ["Sunflower seeds", "Hemp seeds", "Poppy seeds"],
    "hummus":         ["Sonnenblumenkern-Hummus (ohne Tahini)", "Weiße-Bohnen-Dip"],
    "halva":          ["Sonnenblumenkern-Halva", "Karamell-Konfekt"],
    "goma":           ["Sunflower seed paste", "Pumpkin seed oil"],

    # Lupine
    "lupine":         ["Erbsenprotein", "Kichererbsenmehl", "Reisprotein"],
    "lupinenmehl":    ["Kichererbsenmehl", "Reismehl", "Erbsenmehl"],
    "lupin":          ["Pea protein", "Chickpea flour", "Rice protein"],
    "lupin flour":    ["Chickpea flour", "Rice flour", "Pea flour"],

    # Krebstiere
    "garnele":        ["Herzhafter Tofu", "Shiitake-Pilze (ähnliche Textur)", "Jackfrucht"],
    "shrimp":         ["Firm tofu", "King oyster mushroom", "Jackfruit"],
    "hummer":         ["Herzhafte Pilze", "Kichererbsen", "Jackfrucht"],
    "krabbe":         ["Herzhafter Tofu", "Shiitake-Pilze", "Surimi-Ersatz aus Gemüse"],
    "crab":           ["Firm tofu", "Shiitake mushrooms", "Hearts of palm"],
    "garnelenpaste":  ["Miso-Paste", "Algen-Würzpaste"],
    "shrimp paste":   ["Miso paste", "Seaweed seasoning paste"],
    "prawn crackers": ["Reischips", "Tapioka-Chips"],

    # Weichtiere
    "muschel":        ["Herzhafte Pilze (Austernpilze)", "Artischockenherzen"],
    "mussel":         ["Oyster mushrooms", "Artichoke hearts"],
    "auster":         ["Austernpilze", "Artischocken"],
    "tintenfisch":    ["Jackfrucht", "Konjak (Shirataki)", "Herzhafte Pilze"],
    "squid":          ["Jackfruit", "Konjac", "King oyster mushroom"],
    "calamari":       ["Jackfrucht-Calamari", "Konjak-Ringe"],

    # Sulfite
    "e220":           ["Frische Zutaten statt getrockneter/konservierter", "Ascorbinsäure (E300) als Alternative"],
    "sulfit":         ["Frische Alternativen bevorzugen", "Ungeschwefelte Trockenfrüchte"],
    "schwefeldioxid": ["Frische Zutaten", "Produkte ohne Konservierungsstoffe"],
    "sulphite":       ["Fresh alternatives", "Unsulphured dried fruit"],
    "sulfite":        ["Fresh alternatives", "Preservative-free products"],
    "wein":           ["Traubensaft", "Apfelessig (für Säure in Saucen)", "Gemüsebrühe"],
    "rotwein":        ["Traubensaft (dunkel)", "Granatapfelsaft", "Rote-Bete-Saft"],
    "weißwein":       ["Heller Traubensaft", "Apfelsaft", "Gemüsebrühe mit Zitrone"],
    "trockenfrüchte": ["Frisches Obst", "Ungeschwefelte Trockenfrüchte (im Bioladen)"],
}


def ersatz_fuer(gefundener_begriff: str) -> list[str]:
    """Gibt Ersatzvorschläge für einen gefundenen Allergenbegriff zurück."""
    begriff = gefundener_begriff.lower().strip()
    # Exakter Treffer
    if begriff in ERSATZ:
        return ERSATZ[begriff]
    # Partieller Treffer: längster passender Schlüssel gewinnt
    treffer = [(k, v) for k, v in ERSATZ.items() if k in begriff or begriff in k]
    if treffer:
        bester = max(treffer, key=lambda x: len(x[0]))
        return bester[1]
    return []
