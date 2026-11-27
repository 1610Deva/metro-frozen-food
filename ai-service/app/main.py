import secrets
from typing import Literal, Optional
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from . import branches, repository, routing
from .assistant import service
from .config import settings

app = FastAPI(title="Metro AI Service", version="0.1.0",
              description="Fitur AE: cabang terdekat, AI Shopping Assistant, rute pengantaran.")


def auth(x_internal_key: str = Header(default="")):
    if settings.internal_api_key and not secrets.compare_digest(x_internal_key.encode(), settings.internal_api_key.encode()):
        raise HTTPException(401, "x-internal-key salah")


@app.exception_handler(ValueError)
def bad_value(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(repository.DataUnavailable)
def no_data(_, exc):
    return JSONResponse({"detail": "Data toko sedang tidak tersedia."}, status_code=503)


class Location(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def both_or_none(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude dan longitude harus diisi berpasangan")
        return self


class Item(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=1000)


class RecommendIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    items: list[Item] = Field(default_factory=list, max_length=50)
    method: Literal["self_pickup", "direct_delivery", "batch_delivery"] = "self_pickup"


class ChatIn(Location):
    message: str = Field(min_length=1, max_length=500)
    branch_id: Optional[str] = None
    context: dict[Literal["budget", "days", "people", "meals_per_day", "awaiting"], int | str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def clean_context(self):
        for k, v in self.context.items():
            if k != "awaiting" and (not isinstance(v, int) or not 0 < v <= 100_000_000):
                raise ValueError(f"context.{k} tidak valid")
        return self


class Stop(BaseModel):
    order_code: str = Field(min_length=1, max_length=30)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    customer_name: Optional[str] = None


class RouteIn(BaseModel):
    branch_id: str
    stops: list[Stop] = Field(min_length=1, max_length=25)
    return_to_branch: bool = False
    slot_start: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    slot_end: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    service_minutes: int = Field(5, ge=0, le=60)


@app.get("/health")
def health():
    return {"status": "ok", "data": "backend" if settings.backend_snapshot_url else "dummy",
            "llm_configured": bool(settings.gemini_api_key), "owner_whatsapp_configured": bool(settings.owner_whatsapp)}


@app.get("/v1/areas", dependencies=[Depends(auth)])
def list_areas():
    return repository.areas()


@app.post("/v1/branches/recommend", dependencies=[Depends(auth)])
def recommend(body: RecommendIn):
    return branches.recommend(repository.load_catalog(), body.latitude, body.longitude,
                              [i.model_dump() for i in body.items], body.method)


@app.get("/v1/products/search", dependencies=[Depends(auth)])
def search(q: str = Query(min_length=1, max_length=100), latitude: Optional[float] = Query(None, ge=-90, le=90),
           longitude: Optional[float] = Query(None, ge=-180, le=180), branch_id: Optional[str] = None):
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "latitude dan longitude harus berpasangan")
    return branches.search_products(repository.load_catalog(), q, latitude, longitude, branch_id)


@app.post("/v1/assistant/chat", dependencies=[Depends(auth)])
def chat(body: ChatIn):
    return service.chat(body.message, body.context, body.branch_id, body.latitude, body.longitude)


@app.post("/v1/routes/optimize", dependencies=[Depends(auth)])
def optimize(body: RouteIn):
    branch = repository.load_catalog().branch_by_id.get(body.branch_id)
    if not branch:
        raise HTTPException(404, "cabang tidak ditemukan")
    return routing.optimize(branch, [s.model_dump() for s in body.stops], body.return_to_branch,
                            body.slot_start, body.slot_end, body.service_minutes)
