import os
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env")


class Settings:
    data_dir = BASE / "data"
    backend_snapshot_url = os.getenv("BACKEND_SNAPSHOT_URL", "")
    internal_api_key = os.getenv("INTERNAL_API_KEY", "")
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    owner_whatsapp = os.getenv("OWNER_WHATSAPP", "")
    routing_provider = os.getenv("ROUTING_PROVIDER", "osrm")  # osrm | haversine
    osrm_base_url = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
    bulk_pack_threshold = int(os.getenv("BULK_PACK_THRESHOLD", "20"))
    bulk_budget_threshold = int(os.getenv("BULK_BUDGET_THRESHOLD", "1000000"))


settings = Settings()
