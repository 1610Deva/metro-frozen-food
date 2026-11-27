"""Bangun data/*.json dari data/sumber/katalog_instagram.csv.

Nama, harga, ukuran, isi karton, tanggal = dari caption Instagram @ridwanfrozenfood.sby.
Kategori = kolom "kategori" di CSV (boleh diubah tangan). Jenis, porsi, is_lauk, alias = turunan/ASUMSI AE.
Stok = DUMMY (acak tetap per SKU+cabang).
Jalankan dari folder ai-service:  python tools/build_catalog.py
"""
import csv
import json
import random
import re
import uuid
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
uid = lambda k: str(uuid.uuid5(uuid.NAMESPACE_URL, "metro-dummy/" + k))

CATEGORIES = [  # urutan = prioritas pencocokan (hanya dipakai bila kolom kategori di CSV kosong)
    ("Camilan", r"toples|siap makan|cireng|basreng|churros|donat|mantau|mantou|rice bites|bombs|pisang|risoles|lumpia udang|cilor|crispy stick"),
    ("Saus & Bumbu", r"saus|^(?!.*bakso).*sambal|mayonais|kecap|bumbu|tepung|minyak|oregano|parsley|pepper|chili|dressing|hot lava|hot and hot|extra hot|cabe bubuk|^(?:euro gourmet|delmonte|mc ?lewis|kikoman|siliwangi|la fancy|belibis)"),
    ("Pelengkap", r"kulit lumpia|ricepaper|nori|kwetiau|prochiz|procis|winchez keju|roti|diary champ"),
    ("Kentang & Sayur", r"kentang|crinckle|shoestring|vegetable|jagung|kacang polong|edamame"),
    ("Seafood", r"dori fillet"),
    ("Daging & Ayam", r"^fresh|daging slice"),
    ("Dimsum", r"dimsum|siomay|dumpling"),
    ("Bakso", r"bakso|baso"),
    ("Sosis", r"sosis|bakar mini|bakar jumbo|franks|kimbo heppiii"),
    ("Nugget", r"nuget|nugget|naget"),
    ("Daging & Ayam", r"karage|katsu|wings|burger|rolade|kornet|kebab"),
    ("Seafood", r"ikan|udang|cumi|fish|crab|otak|twister|odeng|kekian|lobster|narutomaki|salmon|chikuwa|seafood|snowtrip|sakura|egg money|shrimp|ebi furai|gurita|kaki naga|scallop"),
]
ORDER = ["Nugget", "Sosis", "Bakso", "Seafood", "Saus & Bumbu", "Dimsum", "Daging & Ayam", "Kentang & Sayur",
         "Camilan", "Pelengkap", "Lainnya"]  # urutan tampil
LAUK = {"Nugget", "Sosis", "Bakso", "Seafood", "Dimsum", "Daging & Ayam"}
NOT_LAUK = r"ceker|usus|fresh kulit"

# jenis produk -> dipakai untuk resep. (jenis, kategori yang boleh, pola nama)
RECIPE_TYPES = [
    ("karaage", None, r"karage|karaage"),
    ("nugget", {"Nugget"}, r"nuget|nugget|naget"),
    ("sosis", {"Sosis"}, r"."),
    ("dimsum", {"Dimsum"}, r"."),
    ("bakso", {"Bakso"}, r"^(?!.*tahu)"),
    ("fish_roll", {"Seafood"}, r"fish ?roll|crab roll"),
    ("seafood_mix", {"Seafood"}, r"seafood plater"),
    ("ayam_fillet", {"Daging & Ayam"}, r"dada fillet|paha fillet|ayam slice"),
    ("daging_slice", {"Daging & Ayam"}, r"daging slice"),
    ("kentang", {"Kentang & Sayur"}, r"kentang|crinckle|shoestring"),
]
# kata umum yang diketik pelanggan -> pola nama produk
ALIASES = {
    "nugget": r"nuget|nugget|naget", "sosis": None, "bakso": r"bakso|baso", "tahu bakso": r"tahu bakso",
    "bakso ikan": r"(?:bakso|baso) ikan", "bakso sapi": r"(?:bakso|baso) sapi", "dimsum": r"dimsum|dim sum",
    "siomay": r"siomay", "dumpling": r"dumpling", "otak otak": r"otak", "otak-otak": r"otak",
    "fish roll": r"fish ?roll", "crabstick": r"crabstik", "crabstik": r"crabstik", "odeng": r"odeng",
    "twister": r"twister", "kentang": r"^(?!.*donat).*(?:kentang|crinckle|shoestring)", "kentang goreng": r"^(?!.*donat).*(?:kentang|crinckle|shoestring)",
    "karaage": r"karage", "karage": r"karage", "katsu": r"katsu", "burger": r"burger", "rolade": r"rolade", "kornet": r"kornet",
    "kebab": r"kebab", "mayones": r"mayonais", "mayonaise": r"mayonais", "mayonais": r"mayonais", "saus": r"saus",
    "sambal": r"sambal", "kecap": r"kecap", "keju": r"keju|cheese|cheddar", "bumbu": r"bumbu", "kulit lumpia": r"kulit lumpia",
    "cireng": r"cireng", "edamame": r"edamame", "jagung": r"jagung", "kacang polong": r"kacang polong",
    "sayur": r"vegetable", "mix vegetable": r"mix vegetable", "ceker": r"ceker", "sayap": r"sayap",
    "fillet": r"fillet", "dada fillet": r"dada fillet", "paha fillet": r"paha fillet", "dori": r"dori",
    "usus": r"usus", "daging slice": r"daging slice", "seafood": r"seafood",
}
CATEGORY_ALIASES = {"Sosis": ["sosis"], "Seafood": ["seafood"], "Saus & Bumbu": ["saus"]}
# merek yang aman dicocokkan dari chat (kata ambigu seperti home/fresh/best/okey sengaja tidak dimasukkan)
BRANDS = ["fiesta", "bernardi", "kimbo", "champ", "so nice", "sonice", "so good", "belfoods", "vitalia", "hemato", "salam",
          "pakden", "pak den", "shifudo", "giziplus", "indomina", "cedea", "umiami", "mamasuka", "delmonte", "kikoman",
          "mc lewis", "mclewis", "maestro", "mamayo", "prochiz", "goldstar", "madona", "kamil", "gebooyku", "gebooy",
          "marki", "minaku", "loligo", "goodeats", "zaitun", "jofrans", "finna", "beejay", "pronas", "mabel", "venno",
          "yona", "vigo", "sumber selera", "hygreen", "karawaci", "lekker", "moonfish", "kanzler", "joyfull", "cap koki", "bamboe",
          "la fancy", "euro gourmet", "belibis", "siliwangi", "ds supeer", "ardena", "muantap", "murateku", "goyang",
          "tip top", "wincheez", "hanzel", "horeca", "amogi", "sunfish", "larasfood", "sanjaya", "mistermax", "mister max",
          "rinjani", "abah"]
UNCLEAR_UNIT = "SATUAN PERLU DICEK"
PIECES_PER_PORTION = [(r"tahu bakso", 5), (r"bakso|baso", 10), (r"sosis|bakar", 3), (r"burger", 4), (r"dimsum|siomay", 4)]


def weight_gram(text):
    m = re.findall(r"(\d+(?:[.,]\d+)?)\s*(kg|kilo|gram|gr|g)\b", text.lower())
    if not m:
        return None
    value, unit = m[-1]
    return int(float(value.replace(",", ".")) * (1000 if unit.startswith("k") else 1))


def servings(name, grams):
    """ASUMSI: 100 g = 1 porsi; tanpa berat, pakai jumlah biji. None = tidak bisa diperkirakan."""
    if grams:
        return max(1, round(grams / 100))
    m = re.search(r"\bisi\s*(\d+)(?:\s*\+\s*(\d+))?", name)
    if m:
        for pattern, per in PIECES_PER_PORTION:
            if re.search(pattern, name):
                return max(1, round((int(m[1]) + int(m[2] or 0)) / per))
    return None


def guess_category(name):
    return next((c for c, p in CATEGORIES if re.search(p, name.lower())), "Lainnya")


def build():
    with open(DATA / "sumber" / "katalog_instagram.csv", encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if not r["digabung_ke"]]
    products = []
    for r in rows:
        low = r["nama"].lower()
        category = r["kategori"].strip() or guess_category(low)
        if category not in ORDER:
            raise ValueError(f"kategori tidak dikenal di CSV no.{r['no']}: {category!r}. Pilihan: {', '.join(ORDER)}")
        name = r["nama"]
        if r["ukuran"] and weight_gram(name) is None:
            name += " " + r["ukuran"]
        grams = weight_gram(r["ukuran"]) or weight_gram(name)
        if UNCLEAR_UNIT in r["catatan"]:
            grams = None
        portion = servings(low, grams)
        recipe_type = next((t for t, cats, p in RECIPE_TYPES
                            if (cats is None or category in cats) and re.search(p, low)), None)
        aliases = [a for a, p in ALIASES.items() if p and re.search(p, low)] + CATEGORY_ALIASES.get(category, [])
        if category == "Saus & Bumbu":  # "sosis"/"bakso" tidak boleh memunculkan saus
            aliases = [a for a in aliases if a not in ("sosis", "bakso", "nugget")]
        is_lauk = category in LAUK and not re.search(NOT_LAUK, low) and portion is not None and UNCLEAR_UNIT not in r["catatan"]
        carton = int(r["isi_karton"]) if r["isi_karton"] else None
        unit_note = " Satuan harga produk ini perlu dikonfirmasi ke toko." if UNCLEAR_UNIT in r["catatan"] else ""
        products.append({
            "id": uid("ig/" + r["sku"]), "sku": r["sku"], "category_id": uid("cat/" + category), "name": name,
            "description": f"Kategori {category}." + (f" 1 karton isi {carton}." if carton else "") + unit_note,
            "price": int(r["harga"]), "price_posted_at": r["tanggal_posting"] or None, "is_active": True,
            "weight_gram": grams, "carton_qty": carton, "servings_per_pack": portion or 1, "is_lauk": is_lauk,
            "recipe_type": recipe_type, "brand": next((b for b in BRANDS if re.search(rf"\b{b}\b", low)), None),
            "low_stock_threshold": 10, "aliases": aliases, "source": f"instagram:ridwanfrozenfood.sby#{r['no']}",
        })
    used = {p["category_id"] for p in products}
    categories = [{"id": uid("cat/" + c), "name": c} for c in ORDER if uid("cat/" + c) in used]

    branches = json.loads((DATA / "branches.json").read_text(encoding="utf-8"))
    stock = []
    for p in products:
        for b in branches:
            rnd = random.Random(f"{p['sku']}|{b['code']}")
            roll = rnd.random()
            qty = 0 if roll < 0.12 else rnd.randint(1, 10) if roll < 0.25 else rnd.randint(11, 60)
            stock.append({"branch_id": b["id"], "product_id": p["id"], "stock_quantity": qty})
    for filename, data in (("categories.json", categories), ("products.json", products), ("branch_stock.json", stock)):
        (DATA / filename).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return categories, products, stock


if __name__ == "__main__":
    c, p, s = build()
    print(f"{len(p)} produk, {len(c)} kategori, {len(s)} baris stok (dummy)")
