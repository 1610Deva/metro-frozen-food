"""Matriks jarak: OSRM (jarak jalan, data OpenStreetMap) dengan cadangan garis lurus."""
from math import asin, cos, radians, sin, sqrt
import httpx
from .config import settings

DETOUR_FACTOR = 1.3   # asumsi: jarak jalan ~1,3x garis lurus
AVG_SPEED_KMH = 25.0  # asumsi kecepatan rata-rata dalam kota


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(h))


def _estimate(points):
    km = [[haversine_km(a, b) * DETOUR_FACTOR for b in points] for a in points]
    mins = [[d / AVG_SPEED_KMH * 60 for d in row] for row in km]
    return km, mins, "estimasi_garis_lurus"


def distance_matrix(points):
    """points: [(lat, lon)] -> (km[i][j], menit[i][j], sumber)"""
    if settings.routing_provider != "osrm" or len(points) < 2:
        return _estimate(points)
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)  # OSRM: lon,lat
    try:
        r = httpx.get(f"{settings.osrm_base_url}/table/v1/driving/{coords}",
                      params={"annotations": "distance,duration"}, timeout=6,
                      headers={"User-Agent": "metro-capstone-ai-service"})
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok":
            return _estimate(points)
        km = [[d / 1000 for d in row] for row in j["distances"]]
        mins = [[t / 60 for t in row] for row in j["durations"]]
        return km, mins, "osrm_jarak_jalan"
    except (httpx.HTTPError, ValueError, KeyError, TypeError):  # TypeError: ada nilai null
        return _estimate(points)
