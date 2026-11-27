"""Fitur 3: urutan pengantaran. Pengelompokan batch adalah tugas DS; modul ini hanya mengurutkan."""
from datetime import datetime, timedelta
from urllib.parse import urlencode
from . import geo

EXACT_LIMIT = 12  # Held-Karp: pasti optimal terhadap matriks, cepat sampai ~12 titik


def _cost(order, m, back):
    path = [0, *order, 0] if back else [0, *order]
    return sum(m[a][b] for a, b in zip(path, path[1:]))


def _held_karp(m, back):
    n = len(m) - 1
    best = {(1 << (i - 1), i): (m[0][i], 0) for i in range(1, n + 1)}
    for mask in range(1, 1 << n):
        for last in range(1, n + 1):
            if (mask, last) not in best:
                continue
            cost = best[(mask, last)][0]
            for nxt in range(1, n + 1):
                bit = 1 << (nxt - 1)
                if mask & bit:
                    continue
                key, c = (mask | bit, nxt), cost + m[last][nxt]
                if key not in best or c < best[key][0]:
                    best[key] = (c, last)
    full = (1 << n) - 1
    last = min(range(1, n + 1), key=lambda i: best[(full, i)][0] + (m[i][0] if back else 0))
    order, mask = [], full
    while last:
        order.append(last)
        prev = best[(mask, last)][1]
        mask ^= 1 << (last - 1)
        last = prev
    return order[::-1]


def _heuristic(m, back):
    left, order, cur = set(range(1, len(m))), [], 0
    while left:  # nearest neighbour
        cur = min(left, key=lambda j: m[cur][j])
        order.append(cur)
        left.remove(cur)
    improved = True
    while improved:  # 2-opt; biaya dihitung utuh karena matriks jalan bisa asimetris
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 2, len(order) + 1):
                cand = order[:i] + order[i:j][::-1] + order[j:]
                if _cost(cand, m, back) < _cost(order, m, back) - 1e-9:
                    order, improved = cand, True
    return order


def solve(matrix, back=False):
    if len(matrix) <= 1:
        return [], "none"
    if len(matrix) - 1 <= EXACT_LIMIT:
        return _held_karp(matrix, back), "held_karp_exact"
    return _heuristic(matrix, back), "nearest_neighbour_2opt"


def _maps_url(points):
    fmt = lambda p: f"{p[0]:.6f},{p[1]:.6f}"
    q = {"api": 1, "origin": fmt(points[0]), "destination": fmt(points[-1]), "travelmode": "driving"}
    if len(points) > 2:
        q["waypoints"] = "|".join(fmt(p) for p in points[1:-1])
    return "https://www.google.com/maps/dir/?" + urlencode(q)


def maps_links(points, per_link=4):
    """Dipecah agar tiap link maksimal 3 waypoint (batas browser HP untuk Maps URLs)."""
    step = per_link
    return [_maps_url(points[i:i + step + 1]) for i in range(0, len(points) - 1, step)]


def optimize(branch, stops, return_to_branch=False, slot_start=None, slot_end=None, service_minutes=5):
    codes = [s["order_code"] for s in stops]
    if len(set(codes)) != len(codes):
        raise ValueError("order_code duplikat")
    pts = [(branch["latitude"], branch["longitude"])] + [(s["latitude"], s["longitude"]) for s in stops]
    km, mins, source = geo.distance_matrix(pts)
    order, algo = solve(km, return_to_branch)
    clock = datetime.strptime(slot_start, "%H:%M") if slot_start else None
    end = datetime.strptime(slot_end, "%H:%M") if slot_end else None
    prev, total_km, total_min, route, late = 0, 0.0, 0.0, [], []
    for seq, idx in enumerate(order, 1):
        total_km += km[prev][idx]
        total_min += mins[prev][idx]
        item = {**stops[idx - 1], "sequence": seq, "leg_km": round(km[prev][idx], 2),
                "leg_min": round(mins[prev][idx]), "cumulative_km": round(total_km, 2), "eta": None}
        if clock:
            clock += timedelta(minutes=mins[prev][idx])
            item["eta"] = clock.strftime("%H:%M")
            if end and clock > end:
                late.append(item["order_code"])
            clock += timedelta(minutes=service_minutes)
        total_min += service_minutes
        route.append(item)
        prev = idx
    if return_to_branch:
        total_km += km[prev][0]
        total_min += mins[prev][0]
    input_km = _cost(list(range(1, len(pts))), km, return_to_branch)
    path = [pts[0]] + [pts[i] for i in order] + ([pts[0]] if return_to_branch else [])
    warnings = []
    if late:
        warnings.append(f"ETA melewati slot {slot_end}: {', '.join(late)}")
    if source != "osrm_jarak_jalan":
        warnings.append("Jarak berupa estimasi garis lurus, bukan jarak jalan.")
    return {"origin": {"branch_id": branch["id"], "name": branch["name"]}, "stops": route,
            "total_distance_km": round(total_km, 2), "total_duration_min": round(total_min),
            "input_order_distance_km": round(input_km, 2), "saved_km": round(input_km - total_km, 2),
            "algorithm": algo, "distance_source": source, "google_maps_links": maps_links(path),
            "warnings": warnings, "note": "Rekomendasi. Urutan final dapat disesuaikan petugas; lalu lintas real-time tidak dihitung."}
