"""RAG tahap retrieval: BM25 atas FAQ, deskripsi produk, dan resep (korpus kecil, tanpa vector DB)."""
import math
import re
from collections import Counter
from .text import normalize

STOP = set("yang untuk dan di ke dari atau saya kak min ya dong sih apa apakah itu ini ada bisa mau dengan pada nya kah".split())


SYNONYM = {"bayar": "pembayaran", "transfer": "pembayaran", "tunai": "pembayaran", "cod": "pembayaran", "qris": "pembayaran",
           "simpan": "penyimpanan", "menyimpan": "penyimpanan", "disimpan": "penyimpanan", "freezer": "penyimpanan",
           "kirim": "pengiriman", "dikirim": "pengiriman", "antar": "pengiriman", "ongkir": "pengiriman"}


def tokenize(s):
    out = []
    for t in re.findall(r"[a-z0-9]+", normalize(s)):
        if t in STOP:
            continue
        t = re.sub(r"(nya|kah|lah)$", "", t) if len(t) > 5 else t
        t = re.sub(r"^(?:di|ter|ber)(?=\w{4,})", "", t)
        out.append(SYNONYM.get(t, t))
    return out


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.tf = [Counter(tokenize(d["title"] + " " + d["title"] + " " + d["text"])) for d in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / max(1, len(self.len))
        df = Counter(t for c in self.tf for t in c)
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def search(self, query, k=3):
        q, scored = tokenize(query), []
        for i, tf in enumerate(self.tf):
            s = sum(self.idf[t] * tf[t] * (self.k1 + 1) /
                    (tf[t] + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg)) for t in q if t in tf)
            if s > 0:
                scored.append((s, self.docs[i]))
        return [{**d, "score": round(s, 3)} for s, d in sorted(scored, key=lambda x: -x[0])[:k]]


def faq_docs(path):
    parts = re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.M)[1:]
    return [{"id": f"faq:{p.splitlines()[0].strip()}", "title": p.splitlines()[0].strip(),
             "text": " ".join(p.splitlines()[1:]).strip()} for p in parts]
