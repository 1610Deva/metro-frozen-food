"""Sumber data. Default: JSON dummy. Produksi: satu endpoint snapshot dari backend Express."""
import json
import time
import httpx
from .config import settings

SNAPSHOT_KEYS = ("categories", "products", "branches", "branch_stock")
_cache = {"at": 0.0, "data": None}


class DataUnavailable(Exception):
    pass


def _read(name):
    return json.loads((settings.data_dir / name).read_text(encoding="utf-8"))


def _from_backend():
    if _cache["data"] and time.time() - _cache["at"] < 15:
        return _cache["data"]
    try:
        r = httpx.get(settings.backend_snapshot_url, timeout=5,
                      headers={"x-internal-key": settings.internal_api_key})
        r.raise_for_status()
        data = r.json()
        for p in data["products"]:
            p["price"] = int(float(p["price"]))  # NUMERIC bisa datang sebagai string
            p.setdefault("sku", p["id"])
            p.setdefault("aliases", [])
            # tanpa is_lauk + porsi, produk tidak dipakai penyusun budget (saus jangan jadi "lauk")
            p["is_lauk"] = bool(p.get("is_lauk")) and bool(p.get("servings_per_pack"))
            p["servings_per_pack"] = p.get("servings_per_pack") or 1
            p.setdefault("low_stock_threshold", 10)
        for b in data["branches"]:
            b["latitude"], b["longitude"] = float(b["latitude"]), float(b["longitude"])
        missing = [k for k in SNAPSHOT_KEYS if k not in data]
        if missing:
            raise KeyError(missing)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        # Sengaja TIDAK jatuh ke data dummy: stok palsu lebih berbahaya daripada error.
        raise DataUnavailable(f"snapshot backend gagal: {type(e).__name__}") from e
    _cache.update(at=time.time(), data=data)
    return data


class Catalog:
    def __init__(self, data):
        self.categories = {c["id"]: c["name"] for c in data["categories"]}
        self.products = [p for p in data["products"] if p.get("is_active", True)]
        self.branches = [b for b in data["branches"] if b.get("is_active", True)]
        self.product_by_id = {p["id"]: p for p in self.products}
        self.branch_by_id = {b["id"]: b for b in self.branches}
        self._stock = {(r["branch_id"], r["product_id"]): int(r["stock_quantity"]) for r in data["branch_stock"]}

    def stock(self, branch_id, product_id):
        return self._stock.get((branch_id, product_id), 0)

    def total_stock(self, product_id):
        return sum(self.stock(b["id"], product_id) for b in self.branches)


def load_catalog() -> Catalog:
    if settings.backend_snapshot_url:
        return Catalog(_from_backend())
    return Catalog({k: _read(f"{k}.json") for k in SNAPSHOT_KEYS})


def recipes():
    return _read("recipes.json")


def areas():
    return _read("areas.json")


def delivery_rules():
    return _read("delivery_rules.json")
