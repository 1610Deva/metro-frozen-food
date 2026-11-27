"""Fitur 1: rekomendasi cabang terdekat sesuai stok."""
from math import ceil
from . import geo, repository
from .assistant.text import words

DELIVERY_METHODS = {"direct_delivery", "batch_delivery"}


def rank_branches(catalog, lat, lon):
    pts = [(lat, lon)] + [(b["latitude"], b["longitude"]) for b in catalog.branches]
    km, mins, source = geo.distance_matrix(pts)
    rows = [{"branch": b, "distance_km": km[0][i], "duration_min": mins[0][i]}
            for i, b in enumerate(catalog.branches, 1)]
    return sorted(rows, key=lambda r: r["distance_km"]), source


def _public(branch):
    return {k: branch.get(k) for k in ("id", "name", "address", "latitude", "longitude")}


def recommend(catalog, lat, lon, items, method="self_pickup"):
    """items: [{product_id, quantity}]. Aturan MVP: satu pesanan dipenuhi satu cabang."""
    need = {}
    for it in items:
        if it["product_id"] not in catalog.product_by_id:
            raise ValueError(f"produk tidak dikenal: {it['product_id']}")
        need[it["product_id"]] = need.get(it["product_id"], 0) + it["quantity"]
    ranked, source = rank_branches(catalog, lat, lon)
    if not ranked:
        raise ValueError("belum ada cabang aktif")
    rules = repository.delivery_rules()
    is_delivery = method in DELIVERY_METHODS
    nearest_km = ranked[0]["distance_km"]
    base = rules["direct_base_fee"] if method == "direct_delivery" else rules["batch_base_fee"]

    out = []
    for pos, row in enumerate(ranked):
        b = row["branch"]
        missing = [{"product_id": pid, "name": catalog.product_by_id[pid]["name"],
                    "requested": q, "available": catalog.stock(b["id"], pid)}
                   for pid, q in need.items() if catalog.stock(b["id"], pid) < q]
        extra = 0
        if is_delivery and pos > 0:
            extra = ceil(max(0.0, row["distance_km"] - nearest_km)) * rules["other_branch_fee_per_km"]
        out.append({**_public(b), "distance_km": round(row["distance_km"], 2),
                    "duration_min": round(row["duration_min"]), "is_nearest": pos == 0,
                    "can_fulfill": not missing, "missing_items": missing,
                    "in_delivery_range": (not is_delivery) or row["distance_km"] <= rules["max_delivery_km"],
                    "shipping_fee_estimate": (base + extra) if is_delivery else 0,
                    "extra_fee": extra})

    stocked = [c for c in out if c["can_fulfill"]]
    chosen = next((c for c in stocked if c["in_delivery_range"]), None)
    if chosen is None and stocked:
        status, msg = "OUT_OF_RANGE", "Alamat di luar jangkauan pengiriman. Pilih ambil di toko atau hubungi owner."
    elif chosen is None:
        status, msg = "UNAVAILABLE", ("Belum ada satu cabang yang stoknya cukup untuk semua produk. "
                                      "Kurangi jumlah, pisahkan pesanan, atau hubungi owner.")
    elif chosen["is_nearest"]:
        status, msg = "NEAREST_AVAILABLE", f"{chosen['name']} terdekat dan stoknya tersedia."
    else:
        status = "ALTERNATIVE_BRANCH"
        msg = f"Stok di {out[0]['name']} tidak cukup. Tersedia di {chosen['name']} ({chosen['distance_km']} km)."
        if chosen["extra_fee"]:
            msg += f" Perkiraan tambahan ongkir Rp{chosen['extra_fee']:,}".replace(",", ".") + "."
    return {"status": status, "message": msg, "recommended": chosen,
            "requires_confirmation": status == "ALTERNATIVE_BRANCH" and is_delivery,
            "branches": out, "distance_source": source, "fee_is_dummy": rules.get("is_dummy", False)}


def search_products(catalog, query, lat=None, lon=None, branch_id=None):
    """Search bar: tampilkan produk, tandai bila hanya tersedia di cabang lain."""
    if lat is not None and lon is not None:
        ordered = [r["branch"] for r in rank_branches(catalog, lat, lon)[0]]
    else:
        ordered = catalog.branches
    selected = catalog.branch_by_id.get(branch_id) if branch_id else (ordered[0] if lat is not None and ordered else None)
    if branch_id and not selected:
        raise ValueError("cabang tidak dikenal")
    q = words(query)
    results = []
    for p in catalog.products:
        hay = words(" ".join([p["name"], p.get("brand") or "", catalog.categories.get(p["category_id"], ""), *p.get("aliases", [])]))
        if not q or not all(tok in hay for tok in q.split()):
            continue
        here = catalog.stock(selected["id"], p["id"]) if selected else None
        others = [{"branch_id": b["id"], "name": b["name"], "stock_quantity": catalog.stock(b["id"], p["id"])}
                  for b in ordered if (not selected or b["id"] != selected["id"]) and catalog.stock(b["id"], p["id"]) > 0]
        if here:
            availability = "AVAILABLE_HERE"
        else:
            availability = "OTHER_BRANCH_ONLY" if others and selected else ("AVAILABLE" if others else "OUT_OF_STOCK")
        results.append({"product_id": p["id"], "name": p["name"], "price": p["price"], "availability": availability,
                        "stock_selected_branch": here, "other_branches": others})
    return {"selected_branch": _public(selected) if selected else None, "results": results}
