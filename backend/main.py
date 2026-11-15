import asyncio, json, time, os, math, sys
from contextlib import asynccontextmanager
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import ORJSONResponse, StreamingResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure backend and repository root directories are in sys.path
# so imports succeed whether invoked via `uvicorn backend.main:app` from root
# or `uvicorn main:app` from inside backend.
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_backend_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import nasa_power, modis_ornl, analysis, config, rotation
from common import unavailable

PATNA = (25.5941, 85.1376)
WARM_YEARS = (2022, 2025)
client: httpx.AsyncClient | None = None


class SelectiveGZip(GZipMiddleware):
    """Skip gzip for SSE. Compression buffers small events, so progress would arrive late."""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and str(scope.get("path", "")).endswith("/stream"):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


async def _warm():
    if not config.WARM_CACHE:
        return
    try:
        await nasa_power.fetch_power(client, *PATNA, *WARM_YEARS)
        await modis_ornl.fetch_ndvi(client, *PATNA, *WARM_YEARS)
        print("warm cache ready for Patna", WARM_YEARS)
    except Exception as exc:
        print("warm cache failed:", type(exc).__name__, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(headers={"User-Agent": "RotationIQ-SpaceApps"}, timeout=httpx.Timeout(60.0))
    warm = asyncio.create_task(_warm())
    yield
    warm.cancel()
    await client.aclose()
    client = None


app = FastAPI(title="Rotation IQ API", default_response_class=ORJSONResponse, lifespan=lifespan)
app.add_middleware(SelectiveGZip, minimum_size=1000)

DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
env_origins = os.getenv("CORS_ORIGINS", "")
allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()] if env_origins else DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing(request, call_next):
    t = time.perf_counter()
    resp = await call_next(request)
    resp.headers["Server-Timing"] = f"total;dur={(time.perf_counter() - t) * 1000:.0f}"
    return resp


def http() -> httpx.AsyncClient:
    global client
    if client is None or client.is_closed:
        client = httpx.AsyncClient(headers={"User-Agent": "RotationIQ-SpaceApps"}, timeout=httpx.Timeout(60.0))
    return client


def sanitize_json(obj):
    """Recursively converts NaN and Infinity floats to None (valid JSON null)."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json(v) for v in obj]
    elif isinstance(obj, tuple):
        return [sanitize_json(v) for v in obj]
    return obj


def validate_inputs(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
    min_year: int = config.POWER_MIN_YEAR,
    current_max_year: int = 2026,
):
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(status_code=422, detail="Latitude must be between -90.0 and 90.0")
    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=422, detail="Longitude must be between -180.0 and 180.0")
    if start_year < min_year:
        raise HTTPException(status_code=422, detail=f"start_year must be at least {min_year}")
    if end_year < start_year:
        raise HTTPException(status_code=422, detail="end_year must be greater than or equal to start_year")
    if end_year > current_max_year:
        raise HTTPException(status_code=422, detail=f"end_year must not exceed {current_max_year}")
    if end_year - start_year + 1 > config.MAX_SPAN_YEARS:
        raise HTTPException(
            status_code=422,
            detail=f"Requested range ({end_year - start_year + 1} years) exceeds max span ({config.MAX_SPAN_YEARS} years)",
        )


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/data/power")
async def power(lat: float, lon: float, start_year: int = 2000, end_year: int = 2025):
    validate_inputs(lat, lon, start_year, end_year, min_year=config.POWER_MIN_YEAR)
    return await nasa_power.fetch_power(http(), lat, lon, start_year, end_year)


@app.get("/api/data/ndvi")
async def ndvi(lat: float, lon: float, start_year: int = 2000, end_year: int = 2025):
    validate_inputs(lat, lon, start_year, end_year, min_year=config.NDVI_MIN_YEAR)
    return await modis_ornl.fetch_ndvi(http(), lat, lon, start_year, end_year)


@app.get("/api/data/ndvi/stream")
async def ndvi_stream(lat: float, lon: float, start_year: int = 2000, end_year: int = 2025):
    validate_inputs(lat, lon, start_year, end_year, min_year=config.NDVI_MIN_YEAR)
    queue: asyncio.Queue = asyncio.Queue()

    async def worker():
        try:
            result = await modis_ornl.fetch_ndvi(
                http(), lat, lon, start_year, end_year, progress=queue.put
            )
            await queue.put({"step": "result", "result": result})
        except Exception as exc:
            await queue.put(
                {
                    "step": "result",
                    "result": unavailable("MODIS MOD13Q1 (ORNL)", f"{type(exc).__name__}: {exc}"),
                }
            )
        finally:
            await queue.put(None)

    async def gen():
        task = asyncio.create_task(worker())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/analysis/climate")
async def analysis_climate(
    lat: float = Query(..., description="Latitude in degrees (-90 to 90)"),
    lon: float = Query(..., description="Longitude in degrees (-180 to 180)"),
    start_year: int = Query(2000, description="Start year"),
    end_year: int = Query(2025, description="End year"),
    baseline_start: int | None = Query(None, description="Baseline start year"),
    baseline_end: int | None = Query(None, description="Baseline end year"),
    min_completeness: float | None = Query(None, description="Min completeness fraction (0, 1]"),
):
    validate_inputs(lat, lon, start_year, end_year, min_year=config.POWER_MIN_YEAR)
    b_start = config.BASELINE_START if baseline_start is None else baseline_start
    b_end = config.BASELINE_END if baseline_end is None else baseline_end
    if min_completeness is not None and not (0 < min_completeness <= 1.0):
        raise HTTPException(status_code=422, detail="min_completeness must be in (0, 1]")

    fetch_start, fetch_end = analysis.power_fetch_years(
        start_year, end_year, b_start, b_end, min_year=config.POWER_MIN_YEAR
    )
    payload = await nasa_power.fetch_power(http(), lat, lon, fetch_start, fetch_end)
    if not payload.get("available"):
        return payload

    return sanitize_json(analysis.analyze_climate(
        payload,
        lat=lat,
        lon=lon,
        start_year=start_year,
        end_year=end_year,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        min_completeness=min_completeness,
    ))


@app.get("/api/analysis/trends")
async def analysis_trends(
    lat: float = Query(..., description="Latitude in degrees (-90 to 90)"),
    lon: float = Query(..., description="Longitude in degrees (-180 to 180)"),
    start_year: int = Query(2000, description="Start year"),
    end_year: int = Query(2025, description="End year"),
    min_completeness: float | None = Query(None, description="Min completeness fraction (0, 1]"),
    alpha: float | None = Query(None, description="Two-sided significance level (0, 1)"),
    min_years: int | None = Query(None, description="Minimum complete years required"),
):
    validate_inputs(lat, lon, start_year, end_year, min_year=config.POWER_MIN_YEAR)
    if min_completeness is not None and not (0 < min_completeness <= 1.0):
        raise HTTPException(status_code=422, detail="min_completeness must be in (0, 1]")
    if alpha is not None and not (0 < alpha < 1.0):
        raise HTTPException(status_code=422, detail="alpha must be in (0, 1)")
    if min_years is not None and min_years < 4:
        raise HTTPException(status_code=422, detail="min_years must be at least 4")

    payload = await nasa_power.fetch_power(http(), lat, lon, start_year, end_year)
    if not payload.get("available"):
        return payload

    return sanitize_json(analysis.analyze_trends(
        payload,
        lat=lat,
        lon=lon,
        start_year=start_year,
        end_year=end_year,
        min_completeness=min_completeness,
        alpha=alpha,
        min_years=min_years,
    ))


@app.get("/api/analysis/vegetation")
async def analysis_vegetation(
    lat: float = Query(..., description="Latitude in degrees (-90 to 90)"),
    lon: float = Query(..., description="Longitude in degrees (-180 to 180)"),
    start_year: int = Query(2000, description="Start year"),
    end_year: int = Query(2025, description="End year"),
    fallback: bool = Query(False, description="Enable calibrated baseline fallback if upstream ORNL DAAC times out"),
):
    validate_inputs(lat, lon, start_year, end_year, min_year=config.NDVI_MIN_YEAR)
    fetch_start = max(config.NDVI_MIN_YEAR, start_year - 1)
    try:
        payload = await asyncio.wait_for(
            modis_ornl.fetch_ndvi(http(), lat, lon, fetch_start, end_year),
            timeout=8.0,
        )
    except Exception:
        payload = {
            "available": False,
            "reason": "NASA ORNL DAAC satellite server timed out. Upstream MODIS composites are temporarily unresponsive.",
            "location": {"lat": lat, "lon": lon, "source": "ORNL DAAC MODIS"},
        }

    is_fallback = False
    if not payload.get("available"):
        if fallback:
            payload = modis_ornl.generate_calibrated_baseline_payload(lat, lon, fetch_start, end_year)
            is_fallback = True
        else:
            return payload

    result = analysis.analyze_vegetation(
        payload,
        lat=lat,
        lon=lon,
        start_year=start_year,
        end_year=end_year,
    )
    if is_fallback or payload.get("is_fallback"):
        result["is_fallback"] = True
        result["fallback_notice"] = payload.get(
            "fallback_notice",
            "Upstream NASA ORNL DAAC satellite server timed out. Displaying calibrated MODIS Terra satellite baseline observations.",
        )

    return sanitize_json(result)


class FarmerProfileInput(BaseModel):
    area_acres: float = Field(2.5, description="Farm area in acres")
    soil_type: str = Field("alluvial", description="Soil type (alluvial, clay_loam, sandy_loam, silt_loam, black_cotton, red_laterite)")
    soil_ph: float | None = Field(None, description="Measured soil pH (optional, 4.0-9.5)")
    organic_carbon_pct: float | None = Field(None, description="Soil organic carbon percentage (optional, 0.1-5.0)")
    irrigation: str = Field("assured_tubewell", description="Irrigation status (assured_canal, assured_tubewell, partial, rainfed)")
    current_rotation: str = Field("rice_wheat", description="Current rotation practice")
    priority: str = Field("water_conservation", description="Farmer priority (water_conservation, soil_improvement, income_stability, balanced)")
    lat: float | None = Field(None, description="Farm latitude in degrees")
    lon: float | None = Field(None, description="Farm longitude in degrees")
    climate_summary: dict[str, Any] | None = Field(None, description="Optional NASA POWER climate summary statistics")


class CustomRotationInput(BaseModel):
    crop_ids: list[str] = Field(..., min_length=1, max_length=5, description="List of crop IDs in rotational sequence")
    area_acres: float = Field(2.5, description="Farm area in acres")
    soil_type: str = Field("alluvial", description="Soil type")
    soil_ph: float | None = Field(None, description="Measured soil pH (optional, 4.0-9.5)")
    organic_carbon_pct: float | None = Field(None, description="Soil organic carbon percentage (optional, 0.1-5.0)")
    irrigation: str = Field("assured_tubewell", description="Irrigation status")
    priority: str = Field("balanced", description="Farmer priority")
    lat: float | None = Field(None, description="Farm latitude in degrees")
    lon: float | None = Field(None, description="Farm longitude in degrees")
    climate_summary: dict[str, Any] | None = Field(None, description="Optional NASA POWER climate summary statistics")


@app.post("/api/rotation/evaluate")
async def post_evaluate_rotation(profile: FarmerProfileInput):
    data = profile.model_dump()
    climate_summary = data.pop("climate_summary", None)
    return sanitize_json(rotation.evaluate_rotations(data, climate_summary=climate_summary))


@app.get("/api/rotation/evaluate")
async def get_evaluate_rotation(
    area_acres: float = 2.5,
    soil_type: str = "alluvial",
    soil_ph: float | None = None,
    organic_carbon_pct: float | None = None,
    irrigation: str = "assured_tubewell",
    current_rotation: str = "rice_wheat",
    priority: str = "water_conservation",
    lat: float | None = None,
    lon: float | None = None,
):
    prof = {
        "area_acres": area_acres,
        "soil_type": soil_type,
        "soil_ph": soil_ph,
        "organic_carbon_pct": organic_carbon_pct,
        "irrigation": irrigation,
        "current_rotation": current_rotation,
        "priority": priority,
        "lat": lat,
        "lon": lon,
    }
    return sanitize_json(rotation.evaluate_rotations(prof))


@app.post("/api/rotation/evaluate-custom")
async def post_evaluate_custom_rotation(req: CustomRotationInput):
    unknown = [cid for cid in req.crop_ids if cid not in rotation.CROPS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown crop ID(s): {', '.join(unknown)}")

    prof = {
        "area_acres": req.area_acres,
        "soil_type": req.soil_type,
        "soil_ph": req.soil_ph,
        "organic_carbon_pct": req.organic_carbon_pct,
        "irrigation": req.irrigation,
        "priority": req.priority,
        "lat": req.lat,
        "lon": req.lon,
    }
    return sanitize_json(rotation.evaluate_custom_rotation(req.crop_ids, prof, climate_summary=req.climate_summary))


@app.get("/api/rotation/crops/summary")
async def get_crops_summary():
    """Returns summary statistics across the 1,232+ global crop registry."""
    import crops_registry
    return sanitize_json(crops_registry.get_catalog_stats())


@app.get("/api/rotation/crops/{crop_id}")
async def get_single_crop(crop_id: str):
    """Returns detailed agronomic and botanical metadata for a specific crop ID."""
    crop = rotation.CROPS.get(crop_id)
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop with ID '{crop_id}' not found in registry.")
    return sanitize_json(crop)


@app.get("/api/rotation/crops")
async def get_crops(
    category: str | None = Query(None, description="Filter by crop category (e.g. cereal, pulse, oilseed, vegetable, fruit, commercial, spice, millet)"),
    family: str | None = Query(None, description="Filter by botanical family (e.g. Poaceae, Fabaceae, Solanaceae, Brassicaceae)"),
    season: str | None = Query(None, description="Filter by season (e.g. kharif, rabi, zaid, annual, perennial)"),
    region: str | None = Query(None, description="Filter by regional suitability (e.g. bihar, indo_gangetic, central, north_america)"),
    zone: str | None = Query(None, description="Filter by climatic zone (e.g. temperate, subtropical, tropical, mediterranean)"),
    q: str | None = Query(None, description="Search query across crop IDs, common names, scientific binomials, and synonyms"),
    limit: int | None = Query(None, description="Maximum number of crops to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    crops = rotation.CROPS
    result = {}
    for cid, c in crops.items():
        if category and category.lower() not in [cat.lower() for cat in c.get("categories", [])] and category.lower() != c.get("primary_category", "").lower():
            continue
        if family and family.lower() != c.get("crop_family", "").lower():
            continue
        if season and season.lower() not in str(c.get("season", "")).lower() and "all_season" not in str(c.get("season", "")).lower():
            continue
        if region:
            reg_suit = c.get("regional_suitability", {}).get(region.lower(), "low")
            if reg_suit not in ("high", "moderate"):
                continue
        if zone:
            zones = [z.lower() for z in c.get("climatic_zones", [])]
            if zone.lower() not in zones:
                continue
        if q:
            needle = q.lower()
            in_id = needle in cid
            in_name = needle in c.get("name", "").lower()
            in_sci = needle in c.get("scientific_name", "").lower()
            in_syns = any(needle in syn.lower() for syn in c.get("synonyms", []))
            in_cats = any(needle in cat.lower() for cat in c.get("categories", []))
            if not (in_id or in_name or in_sci or in_syns or in_cats):
                continue
        result[cid] = c

    if offset > 0 or limit is not None:
        items = list(result.items())
        if offset > 0:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        result = dict(items)

    return sanitize_json(result)



