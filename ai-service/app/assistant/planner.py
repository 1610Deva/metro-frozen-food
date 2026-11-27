"""Penyusun belanja sesuai budget. Semua hitungan di kode, bukan di LLM."""
from itertools import combinations_with_replacement

MAX_PACKS = 8
MAX_CANDIDATES = 12  # batasi kombinasi bila katalog asli berisi ratusan produk


def plan(catalog, budget, days=1, people=1, meals_per_day=2, branch_id=None, top=3):
    stock = (lambda pid: catalog.stock(branch_id, pid)) if branch_id else None
    if stock is None:  # tanpa lokasi: stok terbaik di SATU cabang (satu pesanan satu cabang)
        stock = lambda pid: max((catalog.stock(b["id"], pid) for b in catalog.branches), default=0)
    pool = [p for p in catalog.products if p.get("is_lauk", True) and p["price"] <= budget and stock(p["id"]) > 0]
    # ambil yang termurah per porsi, bergiliran antar kategori agar tetap bervariasi
    by_cat = {}
    for p in sorted(pool, key=lambda p: p["price"] / p["servings_per_pack"]):
        by_cat.setdefault(p["category_id"], []).append(p)
    queues, picked = list(by_cat.values()), []
    while any(queues) and len(picked) < MAX_CANDIDATES:
        picked += [q.pop(0) for q in queues if q]
    pool = picked[:MAX_CANDIDATES]
    target = days * people * meals_per_day
    options = []
    variety = min(3, max(1, target // 2))  # cukup sampai 3 jenis; setelah itu pilih yang lebih hemat
    if pool:
        smallest = min(p["servings_per_pack"] for p in pool)
        limit = min(MAX_PACKS, budget // min(p["price"] for p in pool), -(-target // smallest) + 1)
        for n in range(1, int(limit) + 1):
            for combo in combinations_with_replacement(pool, n):
                total = sum(p["price"] for p in combo)
                if total > budget:
                    continue
                counts = {}
                for p in combo:
                    counts[p["id"]] = counts.get(p["id"], 0) + 1
                if any(q > stock(pid) for pid, q in counts.items()):
                    continue
                if not branch_id and not any(all(catalog.stock(b["id"], i) >= q for i, q in counts.items())
                                             for b in catalog.branches):
                    continue
                portions = sum(p["servings_per_pack"] for p in combo)
                # prioritas: porsi tercukupi > variasi > lebih murah > sisa porsi
                score = (min(portions, target), min(len(counts), variety), -total, portions)
                options.append((score, counts, total, portions))
    options.sort(key=lambda o: o[0], reverse=True)
    results, seen = [], []
    for _, counts, total, portions in options:
        if set(counts) in seen:
            continue
        seen.append(set(counts))
        results.append({"items": [{"product_id": i, "sku": catalog.product_by_id[i]["sku"],
                                   "name": catalog.product_by_id[i]["name"], "quantity": q,
                                   "unit_price": catalog.product_by_id[i]["price"],
                                   "subtotal": q * catalog.product_by_id[i]["price"]} for i, q in counts.items()],
                        "total": total, "remaining": budget - total, "portions": portions,
                        "covers_target": portions >= target})
        if len(results) == top:
            break
    cheapest = min((p for p in catalog.products if p.get("is_lauk", True)), key=lambda p: p["price"], default=None)
    return {"budget": budget, "days": days, "people": people, "meals_per_day": meals_per_day,
            "target_portions": target, "options": results,
            "cheapest": {"name": cheapest["name"], "price": cheapest["price"]} if cheapest else None}
