import itertools
import random
import pytest
from fastapi.testclient import TestClient

from app import branches, repository, routing
from app.assistant import planner, service, text as T
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for k, v in dict(routing_provider="haversine", gemini_api_key="", internal_api_key="",
                     backend_snapshot_url="", owner_whatsapp="081200000000").items():
        monkeypatch.setattr(settings, k, v)


def cat():
    return repository.load_catalog()


def pick(condition):
    """Produk pertama yang stok dummy-nya memenuhi syarat (tes tidak bergantung pada angka tertentu)."""
    c = cat()
    for p in c.products:
        stock = {b["name"].split()[-1]: c.stock(b["id"], p["id"]) for b in c.branches}
        if condition(stock):
            return p, stock
    raise AssertionError("tidak ada produk yang memenuhi syarat tes")


def br(name):
    return next(b for b in cat().branches if name in b["name"])


def reco(at, items, method="self_pickup"):
    b = br(at)
    return branches.recommend(cat(), b["latitude"], b["longitude"], items, method)


def test_nearest_with_stock():
    p, _ = pick(lambda s: s["Gubeng"] >= 2)
    r = reco("Gubeng", [{"product_id": p["id"], "quantity": 2}])
    assert r["status"] == "NEAREST_AVAILABLE" and "Gubeng" in r["recommended"]["name"]


def test_empty_stock_moves_to_other_branch_with_fee():
    p, _ = pick(lambda s: s["Sukolilo"] == 0 and max(s.values()) > 0)
    r = reco("Sukolilo", [{"product_id": p["id"], "quantity": 1}], "direct_delivery")
    assert r["status"] == "ALTERNATIVE_BRANCH" and r["requires_confirmation"]
    assert r["recommended"]["extra_fee"] > 0 and "Sukolilo" not in r["recommended"]["name"]


def test_pickup_has_no_fee_and_duplicate_items_are_summed():
    need = lambda s: s["Kenjeran"] // 2 + 1  # satu baris cukup, dua baris melebihi stok Kenjeran
    p, stock = pick(lambda s: s["Kenjeran"] >= 2 and max(s.values()) >= 2 * need(s))
    item = {"product_id": p["id"], "quantity": need(stock)}
    assert reco("Kenjeran", [item])["status"] == "NEAREST_AVAILABLE"
    r = reco("Kenjeran", [item, item])
    assert r["status"] == "ALTERNATIVE_BRANCH" and r["recommended"]["shipping_fee_estimate"] == 0


def test_unavailable_and_unknown_product():
    assert reco("Gubeng", [{"product_id": cat().products[0]["id"], "quantity": 500}])["status"] == "UNAVAILABLE"
    with pytest.raises(ValueError):
        reco("Gubeng", [{"product_id": "x", "quantity": 1}])


def test_out_of_range():
    r = branches.recommend(cat(), -7.98, 112.63, [], "direct_delivery")  # Malang
    assert r["status"] == "OUT_OF_RANGE"


def test_search_other_branch_only():
    p, _ = pick(lambda s: s["Sukolilo"] == 0 and max(s.values()) > 0)
    r = branches.search_products(cat(), p["name"], branch_id=br("Sukolilo")["id"])
    hit = next(x for x in r["results"] if x["product_id"] == p["id"])
    assert hit["availability"] == "OTHER_BRANCH_ONLY" and hit["other_branches"]


@pytest.mark.parametrize("msg,value", [("budget 50 ribu", 50000), ("modal 50rb", 50000), ("uang rp 75.000", 75000),
                                       ("budget 1,5 juta", 1500000), ("budget 100k 3 hari", 100000),
                                       ("budget 50 untuk 3 hari", 50000), ("untuk 3 hari", None), ("goban aja", 50000)])
def test_parse_budget(msg, value):
    assert T.parse_budget(T.normalize(msg)) == value


@pytest.mark.parametrize("budget", [0, 31999, 32000, 50000, 150000, 400000, 999999])
@pytest.mark.parametrize("days", [1, 7, 30])
def test_plan_never_exceeds_budget_or_stock(budget, days):
    c = cat()
    for b in c.branches:
        for o in planner.plan(c, budget, days, 2, 2, b["id"])["options"]:
            assert o["total"] == sum(i["subtotal"] for i in o["items"]) <= budget
            assert all(i["quantity"] <= c.stock(b["id"], i["product_id"]) for i in o["items"])


def test_chat_example_from_requirement():
    r = service.chat("saya ada budget 50 ribu, buat makan 3 hari, kirakira beli produk apa yg cocok")
    assert r["intent"] == "rekomendasi_budget" and r["plan"]["options"][0]["total"] <= 50000 and r["recipes"]
    follow = service.chat("kalau untuk 2 orang?", r["context"])
    assert follow["context"]["people"] == 2 and follow["context"]["budget"] == 50000


@pytest.mark.parametrize("msg", ["permisi semisal saya mau pesan untuk jumlah banyak untuk bisnis saya bagaimana",
                                 "saya mau pesan 50 bungkus nugget", "pesanan saya belum sampai", "baksonya halal ga?"])
def test_escalates_to_whatsapp(msg):
    r = service.chat(msg)
    assert r["intent"] == "eskalasi_owner" and r["handoff"]["url"].startswith("https://wa.me/6281200000000?text=")


def test_unknown_fact_is_not_invented():
    r = service.chat("toko libur lebaran ga, tutup tanggal berapa?")
    assert r["intent"] == "eskalasi_owner" and r["handoff"]["reason"] == "tidak_terjawab"


@pytest.mark.parametrize("msg,doc", [("apa pilihan pengirimannya?", "faq:Pilihan pengiriman"),
                                     ("bagaimana cara pesan?", "faq:Cara pesan"),
                                     ("toko buka jam berapa?", "faq:Jam buka"),
                                     ("sabtu tutup jam berapa", "faq:Jam buka"),
                                     ("bisa kirim ke luar kota?", "faq:Jangkauan pengiriman"),
                                     ("cara nyimpen sosisnya gimana", "faq:Penyimpanan frozen food")])
def test_faq(msg, doc):
    assert service.chat(msg)["sources"] == [doc]


def test_llm_invented_price_is_rejected(monkeypatch):
    monkeypatch.setattr(service.llm, "generate", lambda *_: "Ongkirnya cuma Rp1.000 saja, Kak!")
    r = service.chat("apa pilihan pengirimannya?")
    assert "1.000" not in r["answer"] and not r["used_llm"]


@pytest.mark.parametrize("n", [1, 2, 5, 7])
@pytest.mark.parametrize("back", [False, True])
def test_route_exact_matches_brute_force_on_asymmetric_matrix(n, back):
    rnd = random.Random(n * 10 + back)
    m = [[0 if i == j else rnd.uniform(1, 20) for j in range(n + 1)] for i in range(n + 1)]
    order, algo = routing.solve(m, back)
    best = min(routing._cost(list(p), m, back) for p in itertools.permutations(range(1, n + 1)))
    assert algo == "held_karp_exact" and routing._cost(order, m, back) == pytest.approx(best)


def test_route_heuristic_visits_all():
    rnd = random.Random(1)
    m = [[0 if i == j else rnd.uniform(1, 20) for j in range(21)] for i in range(21)]
    order, algo = routing.solve(m)
    assert sorted(order) == list(range(1, 21)) and algo == "nearest_neighbour_2opt"


@pytest.mark.parametrize("stops", [1, 3, 4, 5, 8, 9, 25])
def test_maps_links_cover_all_points_within_limit(stops):
    from urllib.parse import parse_qs, urlparse
    pts = [(-7.3, 112.7 + i / 1000) for i in range(stops + 1)]
    seen = []
    for url in routing.maps_links(pts):
        q = parse_qs(urlparse(url).query)
        way = q.get("waypoints", [""])[0]
        way = way.split("|") if way else []
        assert len(way) <= 3
        seen += way + q["destination"]
    assert len(seen) == stops


def test_api_endpoints_and_validation(monkeypatch):
    b = br("Rungkut")
    stops = repository._read("orders_sample.json")["stops"]
    r = client.post("/v1/routes/optimize", json={"branch_id": b["id"], "stops": stops, "slot_start": "15:00", "slot_end": "17:00"})
    assert r.status_code == 200 and sorted(s["sequence"] for s in r.json()["stops"]) == [1, 2, 3, 4, 5]
    assert client.post("/v1/routes/optimize", json={"branch_id": b["id"], "stops": [stops[0], stops[0]]}).status_code == 422
    assert client.post("/v1/assistant/chat", json={"message": "x" * 501}).status_code == 422
    assert client.post("/v1/assistant/chat", json={"message": "halo", "latitude": -7.3}).status_code == 422
    assert client.post("/v1/assistant/chat", json={"message": "halo", "context": {"budget": "abc"}}).status_code == 422
    assert client.get("/v1/products/search", params={"q": "sosis"}).status_code == 200
    assert client.get("/health").json()["data"] == "dummy"
    monkeypatch.setattr(settings, "internal_api_key", "rahasia")
    assert client.get("/v1/areas").status_code == 401
    assert client.get("/v1/areas", headers={"x-internal-key": "rahasia"}).status_code == 200


def test_backend_down_returns_503_not_dummy(monkeypatch):
    monkeypatch.setattr(settings, "backend_snapshot_url", "http://127.0.0.1:9/none")
    repository._cache.update(at=0.0, data=None)
    assert client.post("/v1/assistant/chat", json={"message": "harga sosis"}).status_code == 503


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_osrm_request_uses_lon_lat_and_converts_units(monkeypatch):
    from app import geo
    seen = {}
    monkeypatch.setattr(settings, "routing_provider", "osrm")

    def fake(url, **kw):
        seen["url"] = url
        return FakeResponse({"code": "Ok", "distances": [[0, 2000], [2500, 0]], "durations": [[0, 300], [360, 0]]})

    monkeypatch.setattr(geo.httpx, "get", fake)
    km, mins, source = geo.distance_matrix([(-7.1, 112.1), (-7.2, 112.2)])
    assert seen["url"].endswith("112.100000,-7.100000;112.200000,-7.200000")
    assert km[1][0] == 2.5 and mins[0][1] == 5 and source == "osrm_jarak_jalan"
    monkeypatch.setattr(geo.httpx, "get", lambda *a, **k: FakeResponse({"code": "Ok", "distances": [[0, None], [1, 0]], "durations": [[0, None], [1, 0]]}))
    assert geo.distance_matrix([(-7.1, 112.1), (-7.2, 112.2)])[2] == "estimasi_garis_lurus"


def test_llm_receives_redacted_text_and_grounded_answer_is_used(monkeypatch):
    sent = {}
    monkeypatch.setattr(settings, "gemini_api_key", "kunci-tes")

    def fake(url, json, headers, timeout):
        sent.update(url=url, body=json)
        return FakeResponse({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "Ada tiga pilihan pengiriman, Kak."}]}}]})

    monkeypatch.setattr(service.llm.httpx, "post", fake)
    r = service.chat("apa pilihan pengirimannya? wa saya 081234567890")
    assert r["used_llm"] and ":generateContent" in sent["url"] and "kunci-tes" not in sent["url"]
    assert "081234567890" not in str(sent["body"]) and "[telepon]" in str(sent["body"])


def test_large_catalog_stays_fast():
    import time
    base = repository.load_catalog()
    data = {"categories": [{"id": "c", "name": "c"}], "branches": base.branches,
            "products": [{**base.products[0], "id": f"p{i}", "category_id": "c", "price": 10000 + i * 100} for i in range(300)],
            "branch_stock": [{"branch_id": b["id"], "product_id": f"p{i}", "stock_quantity": 50} for b in base.branches for i in range(300)]}
    start = time.time()
    assert planner.plan(repository.Catalog(data), 900000, 30, 5, 3)["options"]
    assert time.time() - start < 5


def test_catalog_matches_instagram_source():
    import csv
    with open(settings.data_dir / "sumber" / "katalog_instagram.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    kept = {r["sku"]: r for r in rows if not r["digabung_ke"]}
    c = cat()
    assert len(rows) == 348 and len(c.products) == len(kept) == len({p["id"] for p in c.products})
    assert all(p["price"] == int(kept[p["sku"]]["harga"]) for p in c.products)
    assert all(r["digabung_ke"] in kept for r in rows if r["digabung_ke"])


def test_generated_files_are_in_sync_with_builder():
    """products.json tidak boleh diedit tangan: harus sama dengan hasil tools/build_catalog.py."""
    import json, subprocess, sys, shutil, tempfile, pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as d:
        shutil.copytree(root / "tools", pathlib.Path(d) / "tools")
        shutil.copytree(root / "data", pathlib.Path(d) / "data")
        subprocess.run([sys.executable, str(pathlib.Path(d) / "tools" / "build_catalog.py")], check=True, capture_output=True)
        for name in ("products.json", "categories.json", "branch_stock.json"):
            assert json.loads((pathlib.Path(d) / "data" / name).read_text()) == json.loads((root / "data" / name).read_text()), name


def test_budget_plan_only_uses_meal_products():
    c = cat()
    for budget in (10000, 50000, 200000):
        for o in planner.plan(c, budget, 3, 2, 2, c.branches[0]["id"])["options"]:
            for item in o["items"]:
                p = c.product_by_id[item["product_id"]]
                assert p["is_lauk"] and c.categories[p["category_id"]] not in ("Saus & Bumbu", "Camilan", "Kentang & Sayur", "Pelengkap")
                assert "perlu dikonfirmasi" not in p["description"]


@pytest.mark.parametrize("msg,expected", [
    ("harga mayonaise mamayo 1kg", ["MAMAYO MAYONAIS ORIGINAL 1kg"]),
    ("1 karton isi berapa sosis lekker 1 kg", ["LEKKER Sosis Ayam 1kg"]),
    ("stok dada fillet", ["FRESH DADA FILLET 500gr"])])
def test_find_specific_product(msg, expected):
    assert [p["name"] for p in T.find_products(T.normalize(msg), cat().products)] == expected


def test_sauce_is_not_returned_for_sausage():
    c = cat()
    hits = T.find_products("sosis", c.products)
    assert hits and all(c.categories[p["category_id"]] != "Saus & Bumbu" for p in hits)


def test_long_product_list_is_capped_and_brand_gap_is_said():
    r = service.chat("harga nugget fiesta")
    assert len(r["products"]) == service.MAX_LISTED and "belum ada untuk merek Fiesta" in r["answer"]


def test_every_recipe_is_reachable():
    types = {p["recipe_type"] for p in cat().products}
    assert all(set(r["product_types"]) <= types for r in repository.recipes())


def test_backend_without_meal_fields_never_plans(monkeypatch):
    data = {"categories": [], "branches": [{"id": "b", "name": "B", "latitude": "-7.3", "longitude": "112.7"}],
            "products": [{"id": "saus", "name": "Saus", "price": "5000"}],
            "branch_stock": [{"branch_id": "b", "product_id": "saus", "stock_quantity": 9}]}
    monkeypatch.setattr(settings, "backend_snapshot_url", "http://contoh/snapshot")
    monkeypatch.setattr(repository.httpx, "get", lambda *a, **k: FakeResponse(data))
    repository._cache.update(at=0.0, data=None)
    try:
        assert planner.plan(repository.load_catalog(), 50000)["options"] == []
    finally:
        repository._cache.update(at=0.0, data=None)


@pytest.mark.parametrize("query,category", [("saos", "Saus & Bumbu"), ("saus", "Saus & Bumbu"), ("sausage", "Sosis")])
def test_sauce_and_sausage_search_do_not_mix(query, category):
    c = cat()
    found = [c.categories[c.product_by_id[r["product_id"]]["category_id"]]
             for r in branches.search_products(c, query)["results"]]
    assert category in found
    assert ("Sosis" if category == "Saus & Bumbu" else "Saus & Bumbu") not in found
