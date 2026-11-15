"""NASA POWER daily point API (community=AG).

Verified 14 Nov 2026 (POWER Daily API v2.10.3) around Patna:
- community=AG returns all 8 variables below, including GWETTOP and GWETROOT.
- Fill value is -999. Header sources are MERRA2 and SYN1DEG.
- T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, GWETTOP, GWETROOT were valid from 1981-01-01.
  ALLSKY_SFC_SW_DWN was valid from 1984-01-01 (do not trend solar across that source change).
- Values are piecewise constant on a 0.5 deg latitude by 0.625 deg longitude grid.
  The geometry field echoes the request rounded to 3 decimals, plus the cell elevation.
  It is not a field location and it is not the cell center.
GWETTOP/GWETROOT are MODELED. This is regional climate context, not field-level weather.
"""
import math
import httpx
from common import make_meta, unavailable
import cache

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,GWETTOP,GWETROOT"
MODELED = {"GWETTOP", "GWETROOT"}
LAT_STEP = 0.5
LON_STEP = 0.625

def power_cell(lat: float, lon: float) -> tuple[float, float]:
    """Center of the POWER cell that contains this point.

    Latitude edges fall on *.25 and *.75. Longitude centers are multiples of 0.625.
    Confirmed by identical T2M inside those cells, and a change across the edges,
    for 25-26N and 84.5-86E on 2024-06-01.
    """
    lat_c = math.floor((lat + LAT_STEP / 2) / LAT_STEP) * LAT_STEP
    lon_c = math.floor((lon + LON_STEP / 2) / LON_STEP) * LON_STEP
    return round(lat_c, 6), round(lon_c, 6)

async def fetch_power(client: httpx.AsyncClient, lat: float, lon: float, y0: int, y1: int):
    lat_c, lon_c = power_cell(lat, lon)
    k = cache.key("power", lat_c, lon_c, 4, y0=y0, y1=y1)
    hit = cache.get(k, cache.TTL_HISTORY)
    if hit: return hit
    q = dict(parameters=PARAMS, community="AG", longitude=lon_c, latitude=lat_c,
             start=f"{y0}0101", end=f"{y1}1231", format="JSON")
    last = None
    for attempt in range(3):
        try:
            r = await client.get(URL, params=q, timeout=60); r.raise_for_status()
            props = r.json()["properties"]["parameter"]; break
        except Exception as e:
            last = e
    else:
        return unavailable("NASA POWER daily", f"{type(last).__name__}: {last}")
    dates = sorted(next(iter(props.values())).keys())
    cols = {p: [None if v == -999 else v for v in (props[p][d] for d in dates)] for p in props}
    out = dict(available=True, dates=dates, columns=cols,
        cell={"lat": lat_c, "lon": lon_c, "lat_size_deg": LAT_STEP, "lon_size_deg": LON_STEP},
        meta={"overall": make_meta("NASA POWER daily (AG)", "https://power.larc.nasa.gov/docs/services/api/",
              "0.5 x 0.625 deg cell (tens of km). Regional climate context, not the field. Solar is SYN1DEG.",
              dates[0], dates[-1], len(dates), "observed"),
              "sources": ["MERRA2", "SYN1DEG"],
              "modeled_vars": sorted(MODELED & set(cols)),
              "non_null_counts": {p: sum(v is not None for v in c) for p, c in cols.items()}})
    cache.put(k, out); return out
