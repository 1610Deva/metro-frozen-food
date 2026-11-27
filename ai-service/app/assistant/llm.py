"""Gemini REST (opsional). Gagal / tanpa key -> None, lalu pemanggil memakai jawaban template."""
import logging
import re
import httpx
from ..config import settings

log = logging.getLogger("llm")


def redact(s):
    """Tier gratis dapat dipakai Google untuk pengembangan produk: samarkan data pribadi."""
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", s)
    return re.sub(r"(?:\+?62|\b0)[\d\s-]{8,15}\d", "[telepon]", s)


def generate(system, user):
    if not settings.gemini_api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": redact(user)}]}],
            "generationConfig": {"maxOutputTokens": 1000}}
    try:
        r = httpx.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key}, timeout=20)
        r.raise_for_status()
        cand = r.json()["candidates"][0]
        if cand.get("finishReason") not in (None, "STOP"):
            return None
        return "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought")).strip() or None
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as e:
        log.warning("Gemini gagal: %s", type(e).__name__)
        return None
