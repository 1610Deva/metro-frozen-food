"""Normalisasi bahasa chat Indonesia dan pembacaan angka (budget, hari, orang, jumlah)."""
import re

SLANG = {"brp": "berapa", "brapa": "berapa", "hrg": "harga", "gmn": "bagaimana", "gimana": "bagaimana",
         "gmna": "bagaimana", "bgmn": "bagaimana", "sy": "saya", "gk": "tidak", "ga": "tidak", "gak": "tidak",
         "nggak": "tidak", "yg": "yang", "utk": "untuk", "buat": "untuk", "bwt": "untuk", "mkn": "makan",
         "dgn": "dengan", "bsa": "bisa", "bs": "bisa", "pesen": "pesan", "mesen": "pesan", "tlg": "tolong",
         "org": "orang", "nyimpen": "menyimpan", "nyimpan": "menyimpan", "hr": "hari", "bli": "beli", "anter": "antar", "ongkirnya": "ongkir",
         # ejaan nama produk yang berbeda-beda di caption maupun chat
         "nuget": "nugget", "naget": "nugget", "baso": "bakso", "mayonaise": "mayonais", "mayones": "mayonais",
         "mayo": "mayonais", "crinckle": "crinkle", "crabstick": "crabstik", "sachet": "saset", "saos": "saus", "sauce": "saus", "sossis": "sosis", "sausage": "sosis"}
WORDNUM = {"satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5, "enam": 6, "tujuh": 7,
           "delapan": 8, "sembilan": 9, "sepuluh": 10}
MONEY_SLANG = {"ceban": 10000, "goceng": 5000, "goban": 50000, "gocap": 50000, "cepek": 100000,
               "seratus ribu": 100000, "lima puluh ribu": 50000, "setengah juta": 500000, "sejuta": 1000000}


def normalize(s):
    s = s.lower()
    return " ".join(SLANG.get(t, t) for t in re.findall(r"[a-z]+|\d+(?:[.,]\d+)*|[^\sa-z\d]", s))


def _num(raw, unit):
    if unit:
        return int(float(raw.replace(",", ".")) * {"juta": 1e6, "jt": 1e6}.get(unit, 1e3))
    return int(re.sub(r"[.,]", "", raw))


def parse_budget(t):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(ribu|rb|rban|k|juta|jt)\b", t)
    if m:
        return _num(*m.groups())
    m = re.search(r"\b(?:rp|idr)\s*\.?\s*(\d+(?:[.,]\d{3})*)", t) or re.search(r"\b(\d{1,3}(?:\.\d{3})+|\d{4,8})\b", t)
    if m:
        v = _num(m.group(1), None)
        return v if v >= 1000 else None
    for k, v in MONEY_SLANG.items():
        if k in t:
            return v
    m = re.search(r"\b(?:budget|bujet|modal|duit|uang)\D{0,12}?(\d{2,3})\b(?!\s*(?:hari|orang|pack|bungkus|pcs))", t)
    return int(m.group(1)) * 1000 if m else None


def _count(t, unit):
    m = re.search(r"\b(\d+|" + "|".join(WORDNUM) + r")\s*(?:" + unit + r")\b", t)
    return None if not m else (WORDNUM.get(m.group(1)) or int(m.group(1)))


def parse_days(t):
    if re.search(r"\bseminggu\b|\bsepekan\b", t):
        return 7
    weeks = _count(t, "minggu|pekan")
    if weeks:
        return weeks * 7
    return 1 if re.search(r"\bsehari\b(?!\s*\d)", t) and not _count(t, "hari") else _count(t, "hari")


def parse_people(t):
    for word, n in (("sendiri", 1), ("sendirian", 1), ("berdua", 2), ("bertiga", 3), ("berempat", 4), ("berlima", 5)):
        if re.search(rf"\b{word}\b", t):
            return n
    return _count(t, "orang")


def parse_meals_per_day(t):
    m = re.search(r"(\d)\s*(?:x|kali)\s*(?:makan\s*)?(?:sehari|per\s*hari)|(?:sehari|per\s*hari)\s*(\d)\s*(?:x|kali)", t)
    return int(m.group(1) or m.group(2)) if m else None


def parse_pack_qty(t):
    found = re.findall(r"\b(\d{1,5})\s*(?:pack|pak|pax|bungkus|bks|pcs|dus|karton|box|porsi|kg)\b", t)
    return max(map(int, found), default=None)


def words(s):
    """Bentuk baku untuk mencocokkan nama produk: huruf kecil, ejaan diseragamkan, tanpa tanda baca."""
    out = " ".join(w for w in normalize(s).split() if w.isalnum())
    out = re.sub(r"\b(\d+) (?:gram|gr|g)\b", r"\1g", out)  # ukuran jadi satu kata: "500 gr" -> "500g"
    return re.sub(r"\b(\d+) (?:kilo|kg)\b", r"\1kg", out)


# kata yang tidak membedakan produk
NOT_SPECIFIC = set("isi harga berapa ada stok karton dus 1 yang untuk apa tidak saya mau beli di ke dan".split())


def _has(q, phrase):
    return bool(phrase) and re.search(rf"\b{re.escape(phrase)}(?:nya)?\b", q) is not None


def find_products(t, products):
    """Cocokkan lewat nama lengkap, alias (jenis) atau merek; hasil disaring ke yang paling spesifik."""
    q = words(t)
    exact = [p for p in products if _has(q, words(p["name"]))]
    if exact:
        return exact
    typed = [p for p in products if any(_has(q, words(a)) for a in p.get("aliases", []))]
    brands = {words(p["brand"]) for p in products if p.get("brand") and _has(q, words(p["brand"]))}
    branded = [p for p in products if p.get("brand") and words(p["brand"]) in brands]
    if typed and branded:
        ids = {p["id"] for p in branded}
        hits = [p for p in typed if p["id"] in ids] or typed
    else:
        hits = typed or branded
    if not hits:
        return []
    asked = set(q.split()) - NOT_SPECIFIC
    scores = [len(asked & set(words(p["name"]).split())) for p in hits]
    return [p for p, s in zip(hits, scores) if s == max(scores)]
