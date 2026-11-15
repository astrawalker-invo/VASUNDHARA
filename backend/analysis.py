"""Climate, trend, and NDVI summaries computed only from connector payloads.

Missing observations stay missing. They are never replaced with zero.
Aggregates are withheld when fewer than the configured fraction of calendar
days are present. Historical trends describe the sample; they are not forecasts.
"""
from __future__ import annotations

import calendar
import math
from collections import Counter
from datetime import date

import numpy as np
import pandas as pd
import pymannkendall as mk

import config

POWER_VARS = {
    "T2M": {"label": "Mean temperature at 2 m", "units": "°C", "kind": "observed"},
    "T2M_MAX": {"label": "Maximum temperature at 2 m", "units": "°C", "kind": "observed"},
    "T2M_MIN": {"label": "Minimum temperature at 2 m", "units": "°C", "kind": "observed"},
    "PRECTOTCORR": {"label": "Corrected precipitation", "units": "mm/day", "kind": "observed"},
    "RH2M": {"label": "Relative humidity at 2 m", "units": "%", "kind": "observed"},
    "ALLSKY_SFC_SW_DWN": {"label": "All-sky surface shortwave irradiance", "units": "MJ/m²/day", "kind": "observed"},
    "GWETTOP": {"label": "Top-zone soil wetness", "units": "fraction (0–1)", "kind": "modeled"},
    "GWETROOT": {"label": "Root-zone soil wetness", "units": "fraction (0–1)", "kind": "modeled"},
}

# Non-overlapping eastern-India season windows. June is kharif only so rainfall
# is not counted twice. Zaid as April–June in docs/ASSUMPTIONS.md is not used here.
SEASONS = (
    ("zaid", "Zaid (Apr–May)"),
    ("kharif", "Kharif (Jun–Oct)"),
    ("rabi", "Rabi (Nov–Mar, labeled by the year it ends)"),
)

FORECAST_DISCLAIMER = (
    "These statistics describe the historical sample only. "
    "A past trend is not a prediction of future weather."
)

NDVI_INTERPRETATION = (
    "NDVI compares red and near-infrared reflectance from MODIS. Higher values usually indicate "
    "denser or greener vegetation, but the index also responds to residual cloud, soil background, "
    "viewing geometry, and mixed land cover inside the pixel. NDVI is not a measurement of soil "
    "fertility, soil moisture, crop type, or yield."
)

ANNUAL_TREND_LIMIT = (
    "The Hamed–Rao modification adjusts the Mann–Kendall variance for autocorrelation in the annual "
    "series. Annual aggregation removes the seasonal cycle, so this test does not see within-year "
    "seasonality. Incomplete years are omitted rather than filled. With only a few decades of data the "
    "autocorrelation estimate is uncertain and the test has limited power. Sen's slope uses calendar-year "
    "spacing. This is a description of the sample, not a forecast."
)

MONTHLY_TREND_LIMIT = (
    "The correlated seasonal Mann–Kendall test compares each calendar month with the same month in other "
    "years, so the seasonal cycle is not treated as a trend, and it includes cross-month correlation. "
    "Months that fail the completeness rule are omitted with that year. Sen's slope is the median of "
    "within-month slopes divided by the calendar-year gap, in units per year. It is not a forecast."
)


def power_fetch_years(
    start_year: int,
    end_year: int,
    baseline_start: int,
    baseline_end: int,
    *,
    min_year: int,
) -> tuple[int, int]:
    """Years to request so the baseline and the first rabi season are covered."""
    fetch_start = max(min_year, min(start_year, baseline_start) - 1)
    fetch_end = max(end_year, baseline_end)
    return fetch_start, fetch_end


def analyze_climate(
    payload: dict,
    *,
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
    baseline_start: int | None = None,
    baseline_end: int | None = None,
    min_completeness: float | None = None,
) -> dict:
    if not payload.get("available"):
        return _unavailable(payload, "NASA POWER daily")
    baseline_start = config.BASELINE_START if baseline_start is None else baseline_start
    baseline_end = config.BASELINE_END if baseline_end is None else baseline_end
    min_completeness = config.MIN_COMPLETENESS if min_completeness is None else min_completeness

    frame = _power_frame(payload)
    if frame.empty:
        return {"available": False, "name": "NASA POWER daily", "reason": "POWER returned no dates"}

    annual_all = [_annual_row(frame, year, min_completeness) for year in _years_in(frame)]
    monthly_all = [
        _monthly_row(frame, year, month, min_completeness)
        for year in _years_in(frame)
        for month in range(1, 13)
    ]
    seasons_all = [
        _season_row(frame, season, label, year, min_completeness)
        for year in _years_in(frame)
        for season, label in SEASONS
    ]

    t_base, t_kind = _choose_baseline(annual_all, start_year, end_year, baseline_start, baseline_end, "t2m_complete")
    r_base, r_kind = _choose_baseline(annual_all, start_year, end_year, baseline_start, baseline_end, "rainfall_complete")
    t_mean = _mean([row["_t2m"] for row in t_base])
    r_mean = _mean([row["_rain"] for row in r_base])
    t_std = _std([row["_t2m"] for row in t_base]) if len(t_base) >= config.MIN_BASELINE_YEARS else None
    r_std = _std([row["_rain"] for row in r_base]) if len(r_base) >= config.MIN_BASELINE_YEARS else None
    anomalies_ok = len(t_base) >= 2
    rain_anomalies_ok = len(r_base) >= 2

    annual = []
    raw_annual = []
    for row in annual_all:
        if not start_year <= row["year"] <= end_year:
            continue
        item = _public_annual(row)
        item["t2m_anomaly_c"] = _anomaly(row["_t2m"], t_mean, 3) if anomalies_ok else None
        item["rainfall_anomaly_mm"] = _anomaly(row["_rain"], r_mean, 2) if rain_anomalies_ok else None
        annual.append(item)
        raw_annual.append(row)

    t_years = {row["year"] for row in t_base}
    r_years = {row["year"] for row in r_base}
    clim_t = _monthly_normal(monthly_all, t_years, "_t2m", "t2m_complete")
    clim_r = _monthly_normal(monthly_all, r_years, "_rain", "rainfall_complete")
    monthly = []
    for row in monthly_all:
        if not start_year <= row["year"] <= end_year:
            continue
        monthly.append({
            "year": row["year"],
            "month": row["month"],
            "t2m_mean_c": _round(row["_t2m"], 3),
            "t2m_complete": row["t2m_complete"],
            "rainfall_mm": _round(row["_rain"], 2),
            "rainfall_complete": row["rainfall_complete"],
            "t2m_anomaly_c": _anomaly(row["_t2m"], clim_t.get(row["month"]), 3) if anomalies_ok else None,
            "rainfall_anomaly_mm": _anomaly(row["_rain"], clim_r.get(row["month"]), 2) if rain_anomalies_ok else None,
            "missing_days": row["missing_days"],
        })

    season_normals = _season_normals(seasons_all, r_years)
    seasons = []
    for row in seasons_all:
        if not start_year <= row["year"] <= end_year:
            continue
        normal = season_normals.get(row["season"])
        seasons.append({
            "year": row["year"],
            "season": row["season"],
            "label": row["label"],
            "rainfall_mm": _round(row["_rain"], 2),
            "complete": row["complete"],
            "expected_days": row["expected_days"],
            "missing_days": row["missing_days"],
            "rainfall_anomaly_mm": _anomaly(row["_rain"], normal, 2) if rain_anomalies_ok else None,
        })

    requested = frame.loc[f"{start_year}-01-01":f"{end_year}-12-31"]
    summary = _period_summary(requested, start_year, end_year, min_completeness)
    departures = _departures(raw_annual, annual, t_mean, r_mean, t_std, r_std, anomalies_ok, rain_anomalies_ok)
    variability = _variability([row for row in annual if row["rainfall_complete"]])
    kind = t_kind if t_kind == r_kind else "mixed"
    baseline = {
        "start_year": baseline_start,
        "end_year": baseline_end,
        "kind": kind,
        "temperature_kind": t_kind,
        "rainfall_kind": r_kind,
        "temperature_years": len(t_base),
        "rainfall_years": len(r_base),
        "temperature_mean_c": _round(t_mean, 3),
        "rainfall_mean_mm": _round(r_mean, 2),
        "temperature_std_c": _round(t_std, 3),
        "rainfall_std_mm": _round(r_std, 2),
        "label": _baseline_label(t_kind, baseline_start, baseline_end, start_year, end_year),
        "note": (
            "Anomalies are the value minus this baseline mean. Missing days are not filled, "
            "and incomplete years do not enter the baseline. Years inside the baseline contribute "
            "to the mean and standard deviation they are compared with."
        ),
    }
    overall = (payload.get("meta") or {}).get("overall") or {}
    cell = payload.get("cell") or {}
    return {
        "available": True,
        "location": {"lat": lat, "lon": lon, "source": "coordinates"},
        "requested_period": {
            "start_year": start_year,
            "end_year": end_year,
            "start": f"{start_year}-01-01",
            "end": f"{end_year}-12-31",
        },
        "baseline": baseline,
        "summary": summary,
        "annual": annual,
        "monthly": monthly,
        "monthly_climatology": [
            {
                "month": month,
                "t2m_mean_c": _round(clim_t.get(month), 3),
                "rainfall_mm": _round(clim_r.get(month), 2),
                "n_years_temperature": _normal_count(monthly_all, t_years, month, "t2m_complete"),
                "n_years_rainfall": _normal_count(monthly_all, r_years, month, "rainfall_complete"),
            }
            for month in range(1, 13)
        ],
        "seasons": seasons,
        "seasonal_period_means": _period_season_means(seasons),
        "variability": variability,
        "departures": departures,
        "departure_rule": (
            "A complete year is flagged when its anomaly is larger than one sample standard deviation "
            "of the baseline. Hot and cool use temperature; dry and wet use rainfall. "
            "Flags are withheld when the baseline has fewer than "
            f"{config.MIN_BASELINE_YEARS} complete years. These are statistical departures, "
            "not a crop-stress or soil-fertility diagnosis."
        ),
        "quality": _power_quality(payload, overall, cell, requested, start_year, end_year),
        "notes": _climate_notes(cell),
    }


def analyze_trends(
    payload: dict,
    *,
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
    min_completeness: float | None = None,
    alpha: float | None = None,
    min_years: int | None = None,
) -> dict:
    if not payload.get("available"):
        return _unavailable(payload, "NASA POWER daily")
    min_completeness = config.MIN_COMPLETENESS if min_completeness is None else min_completeness
    alpha = config.ALPHA if alpha is None else alpha
    min_years = config.MIN_TREND_YEARS if min_years is None else min_years
    frame = _power_frame(payload)
    annual_all = [_annual_row(frame, year, min_completeness) for year in range(start_year, end_year + 1)]
    monthly_all = [
        _monthly_row(frame, year, month, min_completeness)
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
    ]
    series = [
        _annual_trend(annual_all, start_year, end_year, "annual_t2m_mean", "Annual mean temperature",
                      "_t2m", "t2m_complete", "°C/year", alpha, min_years, "annual"),
        _annual_trend(annual_all, start_year, end_year, "annual_t2m_max", "Annual highest daily maximum temperature",
                      "_tmax", "t2m_max_complete", "°C/year", alpha, min_years, "annual"),
        _annual_trend(annual_all, start_year, end_year, "annual_t2m_min", "Annual lowest daily minimum temperature",
                      "_tmin", "t2m_min_complete", "°C/year", alpha, min_years, "annual"),
        _annual_trend(annual_all, start_year, end_year, "annual_rainfall", "Annual rainfall total",
                      "_rain", "rainfall_complete", "mm/year", alpha, min_years, "annual"),
        _monthly_trend(monthly_all, start_year, end_year, "monthly_t2m", "Monthly mean temperature",
                       "_t2m", "t2m_complete", "°C/year", alpha, min_years),
        _monthly_trend(monthly_all, start_year, end_year, "monthly_rainfall", "Monthly rainfall total",
                       "_rain", "rainfall_complete", "mm/year", alpha, min_years),
    ]
    overall = (payload.get("meta") or {}).get("overall") or {}
    return {
        "available": True,
        "location": {"lat": lat, "lon": lon, "source": "coordinates"},
        "requested_period": {"start_year": start_year, "end_year": end_year},
        "alpha": alpha,
        "disclaimer": FORECAST_DISCLAIMER,
        "series": series,
        "limitations": [
            ANNUAL_TREND_LIMIT,
            MONTHLY_TREND_LIMIT,
            "Solar irradiance is not trended. ALLSKY_SFC_SW_DWN changes source in 1984.",
            "Soil wetness is a MERRA-2 model field and is not trended here.",
        ],
        "quality": {
            "product": "NASA POWER",
            "source": overall.get("name", "NASA POWER daily (AG)"),
            "source_url": overall.get("source_url"),
            "retrieved_at": overall.get("retrieved_at"),
            "spatial_resolution": overall.get("resolution"),
            "temporal_resolution": "daily inputs, tested as annual aggregates and as a 12-month seasonal series",
            "kind": "observed",
        },
    }


def analyze_vegetation(payload: dict, *, lat: float, lon: float, start_year: int, end_year: int) -> dict:
    if not payload.get("available"):
        return _unavailable(payload, "MODIS MOD13Q1 (ORNL)")
    dates = list(payload.get("dates") or [])
    values = list(payload.get("ndvi") or [])
    reliability = list(payload.get("reliability") or [])
    if not (len(dates) == len(values) == len(reliability)):
        return {
            "available": False,
            "name": "MODIS MOD13Q1 (ORNL)",
            "reason": "NDVI dates, values, and reliability ranks have different lengths",
        }
    parsed = pd.to_datetime(dates, errors="coerce")
    rows = []
    for stamp, raw_date, value, rank in zip(parsed, dates, values, reliability):
        if pd.isna(stamp):
            continue
        year = int(stamp.year)
        month = int(stamp.month)
        in_period = start_year <= year <= end_year
        leading_rabi = year == start_year - 1 and month in (11, 12)
        if not in_period and not leading_rabi:
            continue
        number = None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)
        rows.append({
            "date": stamp.strftime("%Y-%m-%d"),
            "year": year,
            "month": int(stamp.month),
            "ndvi": number,
            "reliability": None if rank is None else int(rank),
        })
    rows.sort(key=lambda item: item["date"])
    period_rows = [row for row in rows if start_year <= row["year"] <= end_year]
    series = [{"date": row["date"], "ndvi": _round(row["ndvi"], 4), "reliability": row["reliability"]} for row in period_rows]
    valid = [row for row in period_rows if row["ndvi"] is not None]
    missing = [row for row in period_rows if row["ndvi"] is None]
    annual = [_ndvi_annual(period_rows, year) for year in range(start_year, end_year + 1)]
    seasons = [
        _ndvi_season(rows, season, label, year)
        for year in range(start_year, end_year + 1)
        for season, label in SEASONS
    ]
    by_key = {(row["season"], row["year"]): row for row in seasons}
    changes = []
    for row in seasons:
        nxt = _next_season(row["season"], row["year"])
        if nxt is None or nxt not in by_key:
            continue
        other = by_key[nxt]
        if row["n_obs"] < 2 or other["n_obs"] < 2:
            continue
        if row["mean"] is None or other["mean"] is None:
            continue
        changes.append({
            "from_season": row["season"],
            "from_year": row["year"],
            "to_season": other["season"],
            "to_year": other["year"],
            "from_label": f"{row['label'].split(' (')[0]} {row['year']}",
            "to_label": f"{other['label'].split(' (')[0]} {other['year']}",
            "delta": _round(other["mean"] - row["mean"], 4),
        })
    meta = payload.get("meta") or {}
    latest = None
    for row in reversed(valid):
        latest = {
            "date": row["date"],
            "ndvi": _round(row["ndvi"], 4),
            "note": "Latest quality-filtered observation in the selected period. This is not a live measurement.",
        }
        break
    period_max = max(valid, key=lambda row: row["ndvi"]) if valid else None
    period_min = min(valid, key=lambda row: row["ndvi"]) if valid else None
    ranks = Counter(str(row["reliability"]) for row in period_rows)
    return {
        "available": True,
        "location": {"lat": lat, "lon": lon, "source": "coordinates"},
        "requested_period": {"start_year": start_year, "end_year": end_year},
        "interpretation": NDVI_INTERPRETATION,
        "spatial_resolution": meta.get("resolution") or "231.7 m sinusoidal cell (nominal 250 m product)",
        "temporal_resolution": "16-day composite",
        "quality_filter": (
            "Pixel reliability rank 0 (good) or 1 (marginal) is kept. "
            "Ranks 2, 3, and the fill value are stored as missing. Gaps are not zeros."
        ),
        "series": series,
        "annual": [{k: v for k, v in row.items() if k != "values"} for row in annual],
        "seasons": seasons,
        "seasonal_means": _ndvi_seasonal_means(seasons),
        "season_changes": changes,
        "latest": latest,
        "period_max": None if period_max is None else {"date": period_max["date"], "ndvi": _round(period_max["ndvi"], 4)},
        "period_min": None if period_min is None else {"date": period_min["date"], "ndvi": _round(period_min["ndvi"], 4)},
        "observation_count": len(valid),
        "missing_count": len(missing),
        "reliability_counts": {key: ranks.get(key, 0) for key in ("0", "1", "2", "3", "-1")},
        "quality": {
            "product": "MODIS",
            "source": meta.get("name", "MODIS Terra MOD13Q1 NDVI via ORNL DAAC"),
            "source_url": meta.get("source_url", "https://modis.ornl.gov/rst/ui/"),
            "retrieved_at": meta.get("retrieved_at"),
            "observation_period": {
                "start": series[0]["date"] if series else None,
                "end": series[-1]["date"] if series else None,
            },
            "units": "NDVI (dimensionless, scaled from the MOD13Q1 integer by 0.0001)",
            "spatial_resolution": meta.get("resolution") or "231.7 m sinusoidal cell (nominal 250 m product)",
            "temporal_resolution": "16-day composite",
            "missing_count": len(missing),
            "observation_count": len(valid),
            "kind": meta.get("kind", "observed"),
        },
        "limitations": [
            "The value is for the 231.7 m MODIS cell that contains the point, not for a field boundary.",
            "A 16-day composite is assigned to a season by its calendar date.",
            "Cloudy, snowy, and fill composites are gaps. They are not zero vegetation.",
            NDVI_INTERPRETATION,
        ],
        "notes": [
            "Season windows match the climate analysis: zaid April–May, kharif June–October, rabi November–March.",
            "A seasonal mean is the mean of quality-filtered composites in that window. It is omitted when none are valid. "
            "Rabi of the first year includes the previous November and December when those composites were retrieved. "
            "November and December of the last year stay in the time series and the annual mean; they belong to the following rabi season.",
            "Season-to-season change is the later mean minus the earlier mean, and only when both seasons have at least two valid composites.",
        ],
    }


def _unavailable(payload: dict, fallback: str) -> dict:
    return {
        "available": False,
        "name": payload.get("name", fallback),
        "reason": payload.get("reason", "The source did not return a usable series"),
    }


def _power_frame(payload: dict) -> pd.DataFrame:
    dates = pd.to_datetime(payload.get("dates") or [], format="%Y%m%d", errors="raise")
    columns = payload.get("columns") or {}
    data = {}
    for name in POWER_VARS:
        values = columns.get(name)
        if values is None:
            data[name] = [math.nan] * len(dates)
            continue
        if len(values) != len(dates):
            raise ValueError(f"{name} length does not match the POWER date list")
        data[name] = values
    frame = pd.DataFrame(data, index=dates)
    frame = frame.apply(pd.to_numeric, errors="coerce")
    return frame[~frame.index.duplicated(keep="first")].sort_index()


def _years_in(frame: pd.DataFrame) -> range:
    if frame.empty:
        return range(0, 0)
    return range(int(frame.index.min().year), int(frame.index.max().year) + 1)


def _covered(series: pd.Series, how: str, min_completeness: float) -> dict:
    expected = int(series.shape[0])
    valid = series.dropna()
    n_valid = int(valid.shape[0])
    missing = expected - n_valid
    complete = expected > 0 and (n_valid / expected) >= min_completeness
    if n_valid == 0:
        raw = None
    elif how == "mean":
        raw = float(valid.mean())
    elif how == "sum":
        raw = float(valid.sum())
    elif how == "max":
        raw = float(valid.max())
    elif how == "min":
        raw = float(valid.min())
    else:
        raise ValueError(how)
    return {
        "value": raw if complete else None,
        "complete": bool(complete),
        "expected_days": expected,
        "missing_days": missing,
    }


def _day_index(start: date, end: date) -> pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")


def _annual_row(frame: pd.DataFrame, year: int, min_completeness: float) -> dict:
    idx = _day_index(date(year, 1, 1), date(year, 12, 31))
    covered = {name: _covered(frame[name].reindex(idx), how, min_completeness)
               for name, how in (
                   ("T2M", "mean"), ("T2M_MAX", "max"), ("T2M_MIN", "min"),
                   ("PRECTOTCORR", "sum"), ("RH2M", "mean"),
                   ("ALLSKY_SFC_SW_DWN", "mean"), ("GWETROOT", "mean"), ("GWETTOP", "mean"),
               )}
    return {
        "year": year,
        "_t2m": covered["T2M"]["value"],
        "t2m_complete": covered["T2M"]["complete"],
        "_tmax": covered["T2M_MAX"]["value"],
        "t2m_max_complete": covered["T2M_MAX"]["complete"],
        "_tmin": covered["T2M_MIN"]["value"],
        "t2m_min_complete": covered["T2M_MIN"]["complete"],
        "_rain": covered["PRECTOTCORR"]["value"],
        "rainfall_complete": covered["PRECTOTCORR"]["complete"],
        "_humidity": covered["RH2M"]["value"],
        "humidity_complete": covered["RH2M"]["complete"],
        "_solar": covered["ALLSKY_SFC_SW_DWN"]["value"],
        "solar_complete": covered["ALLSKY_SFC_SW_DWN"]["complete"],
        "_gwetroot": covered["GWETROOT"]["value"],
        "gwetroot_complete": covered["GWETROOT"]["complete"],
        "_gwettop": covered["GWETTOP"]["value"],
        "gwettop_complete": covered["GWETTOP"]["complete"],
        "missing_days": {name: covered[name]["missing_days"] for name in covered},
    }


def _public_annual(row: dict) -> dict:
    return {
        "year": row["year"],
        "t2m_mean_c": _round(row["_t2m"], 3),
        "t2m_complete": row["t2m_complete"],
        "t2m_max_c": _round(row["_tmax"], 3),
        "t2m_max_complete": row["t2m_max_complete"],
        "t2m_min_c": _round(row["_tmin"], 3),
        "t2m_min_complete": row["t2m_min_complete"],
        "rainfall_mm": _round(row["_rain"], 2),
        "rainfall_complete": row["rainfall_complete"],
        "humidity_mean_pct": _round(row["_humidity"], 2),
        "humidity_complete": row["humidity_complete"],
        "solar_mean_mj_m2_day": _round(row["_solar"], 3),
        "solar_complete": row["solar_complete"],
        "gwetroot_mean": _round(row["_gwetroot"], 4),
        "gwetroot_complete": row["gwetroot_complete"],
        "gwettop_mean": _round(row["_gwettop"], 4),
        "gwettop_complete": row["gwettop_complete"],
        "missing_days": row["missing_days"],
    }


def _monthly_row(frame: pd.DataFrame, year: int, month: int, min_completeness: float) -> dict:
    last = calendar.monthrange(year, month)[1]
    idx = _day_index(date(year, month, 1), date(year, month, last))
    temperature = _covered(frame["T2M"].reindex(idx), "mean", min_completeness)
    rainfall = _covered(frame["PRECTOTCORR"].reindex(idx), "sum", min_completeness)
    return {
        "year": year,
        "month": month,
        "_t2m": temperature["value"],
        "t2m_complete": temperature["complete"],
        "_rain": rainfall["value"],
        "rainfall_complete": rainfall["complete"],
        "missing_days": {"T2M": temperature["missing_days"], "PRECTOTCORR": rainfall["missing_days"]},
    }


def _season_index(season: str, year: int) -> pd.DatetimeIndex:
    if season == "zaid":
        return _day_index(date(year, 4, 1), date(year, 5, 31))
    if season == "kharif":
        return _day_index(date(year, 6, 1), date(year, 10, 31))
    if season == "rabi":
        first = _day_index(date(year - 1, 11, 1), date(year - 1, 12, 31))
        second = _day_index(date(year, 1, 1), date(year, 3, 31))
        return first.append(second)
    raise ValueError(season)


def _season_row(frame: pd.DataFrame, season: str, label: str, year: int, min_completeness: float) -> dict:
    covered = _covered(frame["PRECTOTCORR"].reindex(_season_index(season, year)), "sum", min_completeness)
    return {
        "year": year,
        "season": season,
        "label": label,
        "_rain": covered["value"],
        "complete": covered["complete"],
        "expected_days": covered["expected_days"],
        "missing_days": covered["missing_days"],
    }


def _choose_baseline(rows: list[dict], start_year: int, end_year: int, baseline_start: int, baseline_end: int, flag: str):
    preferred = [row for row in rows if baseline_start <= row["year"] <= baseline_end and row[flag]]
    if len(preferred) >= config.MIN_BASELINE_YEARS:
        kind = "wmo_1991_2020" if (baseline_start, baseline_end) == (1991, 2020) else "specified"
        return preferred, kind
    fallback = [row for row in rows if start_year <= row["year"] <= end_year and row[flag]]
    return fallback, "analysis_period"


def _baseline_label(kind: str, baseline_start: int, baseline_end: int, start_year: int, end_year: int) -> str:
    if kind == "wmo_1991_2020":
        return "1991–2020 climatological baseline (WMO standard normal), complete years only"
    if kind == "specified":
        return f"{baseline_start}–{baseline_end} baseline, complete years only"
    return (
        f"Mean of complete years in {start_year}–{end_year}. "
        f"Fewer than {config.MIN_BASELINE_YEARS} complete years were available in {baseline_start}–{baseline_end}."
    )


def _monthly_normal(rows: list[dict], years: set[int], key: str, flag: str) -> dict[int, float | None]:
    grouped: dict[int, list[float]] = {month: [] for month in range(1, 13)}
    for row in rows:
        if row["year"] in years and row[flag] and row[key] is not None:
            grouped[row["month"]].append(row[key])
    return {month: _mean(values) if len(values) >= 5 else None for month, values in grouped.items()}


def _normal_count(rows: list[dict], years: set[int], month: int, flag: str) -> int:
    return sum(1 for row in rows if row["year"] in years and row["month"] == month and row[flag])


def _season_normals(rows: list[dict], years: set[int]) -> dict[str, float | None]:
    grouped: dict[str, list[float]] = {season: [] for season, _label in SEASONS}
    for row in rows:
        if row["year"] in years and row["complete"] and row["_rain"] is not None:
            grouped[row["season"]].append(row["_rain"])
    return {season: _mean(values) if len(values) >= 5 else None for season, values in grouped.items()}


def _period_season_means(seasons: list[dict]) -> list[dict]:
    output = []
    for season, label in SEASONS:
        values = [row["rainfall_mm"] for row in seasons if row["season"] == season and row["complete"] and row["rainfall_mm"] is not None]
        mean_val = _round(_mean(values), 2)
        output.append({
            "season": season,
            "label": label,
            "rainfall_mm": mean_val,
            "mean_rainfall_mm": mean_val,
            "n_seasons": len(values),
            "n_years": len(values),
        })
    return output


def _period_summary(frame: pd.DataFrame, start_year: int, end_year: int, min_completeness: float) -> dict:
    idx = _day_index(date(start_year, 1, 1), date(end_year, 12, 31))
    # Solar is reported on its valid era so a request that starts before 1984 is not discarded.
    solar_start = date(max(start_year, config.SOLAR_START_YEAR), 1, 1)
    solar_idx = _day_index(solar_start, date(end_year, 12, 31)) if solar_start.year <= end_year else idx[:0]
    blocks = {
        "temperature": _covered(frame["T2M"].reindex(idx), "mean", min_completeness) if "T2M" in frame else None,
        "rainfall": _covered(frame["PRECTOTCORR"].reindex(idx), "sum", min_completeness) if "PRECTOTCORR" in frame else None,
        "humidity": _covered(frame["RH2M"].reindex(idx), "mean", min_completeness) if "RH2M" in frame else None,
        "gwetroot": _covered(frame["GWETROOT"].reindex(idx), "mean", min_completeness) if "GWETROOT" in frame else None,
        "gwettop": _covered(frame["GWETTOP"].reindex(idx), "mean", min_completeness) if "GWETTOP" in frame else None,
    }
    solar = _covered(frame["ALLSKY_SFC_SW_DWN"].reindex(solar_idx), "mean", min_completeness) if len(solar_idx) and "ALLSKY_SFC_SW_DWN" in frame else {
        "value": None, "complete": False, "expected_days": 0, "missing_days": 0,
    }
    def pack(block: dict | None, digits: int) -> dict:
        block = block or {"value": None, "complete": False, "expected_days": 0, "missing_days": 0}
        return {
            "value": _round(block["value"], digits),
            "withheld": not block["complete"],
            "missing_days": block["missing_days"],
            "expected_days": block["expected_days"],
            "observed_days": block["expected_days"] - block["missing_days"],
        }
    temperature = pack(blocks["temperature"], 3)
    rainfall = pack(blocks["rainfall"], 2)
    humidity = pack(blocks["humidity"], 2)
    solar_pack = pack(solar, 3)
    root = pack(blocks["gwetroot"], 4)
    top = pack(blocks["gwettop"], 4)
    return {
        "temperature_mean_c": temperature["value"],
        "temperature_withheld": temperature["withheld"],
        "temperature_missing_days": temperature["missing_days"],
        "temperature_observed_days": temperature["observed_days"],
        "temperature_expected_days": temperature["expected_days"],
        "rainfall_mm": rainfall["value"],
        "rainfall_withheld": rainfall["withheld"],
        "rainfall_missing_days": rainfall["missing_days"],
        "rainfall_observed_days": rainfall["observed_days"],
        "rainfall_expected_days": rainfall["expected_days"],
        "humidity_mean_pct": humidity["value"],
        "humidity_withheld": humidity["withheld"],
        "humidity_missing_days": humidity["missing_days"],
        "solar_mean_mj_m2_day": solar_pack["value"],
        "solar_withheld": solar_pack["withheld"],
        "solar_missing_days": solar_pack["missing_days"],
        "solar_expected_days": solar_pack["expected_days"],
        "solar_period_start": solar_start.isoformat() if solar_start.year <= end_year else None,
        "gwetroot_mean": root["value"],
        "gwetroot_withheld": root["withheld"],
        "gwetroot_missing_days": root["missing_days"],
        "gwettop_mean": top["value"],
        "gwettop_withheld": top["withheld"],
        "gwettop_missing_days": top["missing_days"],
    }


def _variability(rows: list[dict]) -> dict:
    values = [row["rainfall_mm"] for row in rows if row["rainfall_mm"] is not None]
    std = _std(values)
    mean = _mean(values)
    cv = None if std is None or mean is None or abs(mean) < 1e-6 else std / mean
    return {
        "rainfall_annual_std_mm": _round(std, 2),
        "rainfall_annual_cv": _round(cv, 3),
        "n_complete_years": len(values),
        "note": (
            "Sample standard deviation and coefficient of variation of complete annual rainfall totals "
            "in the selected period. Incomplete years are omitted. Missing days are not treated as zero."
        ),
    }


def _departures(raw_rows, public_rows, t_mean, r_mean, t_std, r_std, temperature_ok: bool, rainfall_ok: bool) -> list[dict]:
    flagged = []
    for raw, public in zip(raw_rows, public_rows):
        flags = []
        t_anom = raw["_t2m"] - t_mean if temperature_ok and t_mean is not None and raw["_t2m"] is not None else None
        r_anom = raw["_rain"] - r_mean if rainfall_ok and r_mean is not None and raw["_rain"] is not None else None
        if t_std is not None and t_anom is not None:
            if t_anom > t_std:
                flags.append("hot")
            elif t_anom < -t_std:
                flags.append("cool")
        if r_std is not None and r_anom is not None:
            if r_anom < -r_std:
                flags.append("dry")
            elif r_anom > r_std:
                flags.append("wet")
        if flags:
            flagged.append({
                "year": public["year"],
                "flags": flags,
                "t2m_anomaly_c": public["t2m_anomaly_c"],
                "rainfall_anomaly_mm": public["rainfall_anomaly_mm"],
            })
    return flagged


def _power_quality(payload: dict, overall: dict, cell: dict, requested: pd.DataFrame, start_year: int, end_year: int) -> dict:
    idx = _day_index(date(start_year, 1, 1), date(end_year, 12, 31))
    variables = []
    for name, spec in POWER_VARS.items():
        if name not in requested and name not in (payload.get("columns") or {}):
            continue
        series = requested[name].reindex(idx) if name in requested.columns else pd.Series(math.nan, index=idx)
        missing = int(series.isna().sum())
        variables.append({
            "id": name,
            "label": spec["label"],
            "units": spec["units"],
            "kind": spec["kind"],
            "missing_days": missing,
            "observed_days": int(series.notna().sum()),
            "expected_days": int(len(idx)),
        })
    return {
        "product": "NASA POWER",
        "source": overall.get("name", "NASA POWER daily (AG)"),
        "source_url": overall.get("source_url", "https://power.larc.nasa.gov/docs/services/api/"),
        "retrieved_at": overall.get("retrieved_at"),
        "observation_period": {"start": f"{start_year}-01-01", "end": f"{end_year}-12-31"},
        "spatial_resolution": overall.get("resolution") or "0.5 x 0.625 deg cell",
        "temporal_resolution": "daily",
        "cell": cell or None,
        "sources": (payload.get("meta") or {}).get("sources") or [],
        "modeled_variables": (payload.get("meta") or {}).get("modeled_vars") or ["GWETTOP", "GWETROOT"],
        "variables": variables,
        "kind": "mixed",
        "note": "Temperature, rainfall, humidity, and solar are POWER observation fields. GWETTOP and GWETROOT are modeled MERRA-2 wetness.",
    }


def _climate_notes(cell: dict) -> list[str]:
    center = ""
    if cell:
        center = f" The POWER cell center used for this point is {cell.get('lat')}, {cell.get('lon')}."
    return [
        "Values are historical NASA POWER observations for the selected period, not a live weather report and not a forecast.",
        "A day with the POWER fill value is missing. It is not stored as zero and it is not interpolated.",
        "An annual or monthly total is published only when at least "
        f"{config.MIN_COMPLETENESS:.0%} of that period's calendar days are present. "
        "Up to 10% of days can still be absent from a published total; those days are omitted, not estimated.",
        "Zaid is April–May and kharif is June–October so June rainfall is counted once. Rabi is November–March, labeled by the year it ends.",
        "GWETTOP and GWETROOT are modeled MERRA-2 wetness, not soil samples. Rainfall is the weakest POWER field at field scale.",
        "ALLSKY_SFC_SW_DWN is summarized from 1984 onward because the solar source changes that year."
        + center,
    ]


def _annual_trend(rows, start_year, end_year, series_id, label, key, flag, units, alpha, min_years, _kind) -> dict:
    used = [(row["year"], row[key]) for row in rows if start_year <= row["year"] <= end_year and row[flag] and row[key] is not None]
    omitted = [row["year"] for row in rows if start_year <= row["year"] <= end_year and row["year"] not in {year for year, _value in used}]
    return _finish_trend(
        series_id, label, "hamed_rao_modified_mann_kendall",
        "Hamed–Rao modified Mann–Kendall (1998) with Sen's slope (1968)",
        "Serial correlation in the annual series. The seasonal cycle is removed by using one value per year.",
        units, ANNUAL_TREND_LIMIT, used, omitted, alpha, min_years, seasonal=False,
    )


def _monthly_trend(rows, start_year, end_year, series_id, label, key, flag, units, alpha, min_years) -> dict:
    by_year: dict[int, dict[int, float]] = {}
    for row in rows:
        if row[flag] and row[key] is not None:
            by_year.setdefault(row["year"], {})[row["month"]] = row[key]
    used = []
    matrix = []
    for year in range(start_year, end_year + 1):
        months = by_year.get(year, {})
        if all(month in months for month in range(1, 13)):
            used.append(year)
            matrix.append([months[month] for month in range(1, 13)])
    omitted = [year for year in range(start_year, end_year + 1) if year not in used]
    base = _finish_trend(
        series_id, label, "correlated_seasonal_mann_kendall",
        "Correlated seasonal Mann–Kendall (Hipel 1994) with Sen's slope within calendar months",
        "Seasonality, by testing each month against itself across years, and cross-month correlation.",
        units, MONTHLY_TREND_LIMIT,
        list(zip(used, [0] * len(used))), omitted, alpha, min_years, seasonal=True,
    )
    if len(used) >= min_years:
        slope, _intercept = _seasonal_sen(used, matrix)
        base["slope"] = _round(slope, 5)
        try:
            tested = mk.correlated_seasonal_test([value for year_row in matrix for value in year_row], period=12, alpha=alpha)
            _apply_test(base, tested, alpha)
        except Exception as exc:
            base.update(direction=None, significant=None, p_value=None, z=None, tau=None,
                        error=f"Seasonal trend test could not be computed ({type(exc).__name__}).")
    return base


def _finish_trend(series_id, label, method, method_label, accounts_for, units, limitations, used, omitted, alpha, min_years, seasonal: bool) -> dict:
    result = {
        "id": series_id,
        "label": label,
        "method": method,
        "method_label": method_label,
        "accounts_for": accounts_for,
        "n": len(used),
        "omitted_years": omitted,
        "first_year": used[0][0] if used else None,
        "last_year": used[-1][0] if used else None,
        "direction": None,
        "significant": None,
        "p_value": None,
        "z": None,
        "tau": None,
        "slope": None,
        "slope_units": units,
        "fit": [],
        "limitations": limitations,
        "error": None,
    }
    if seasonal:
        if len(used) < min_years:
            result["error"] = f"At least {min_years} complete years are required for this trend test."
        return result
    if len(used) < min_years:
        result["error"] = f"At least {min_years} complete years are required for this trend test."
        return result
    years = [year for year, _value in used]
    values = [value for _year, value in used]
    slope, intercept = _sen(years, values)
    result["slope"] = _round(slope, 5)
    result["fit"] = [{"year": year, "value": _round(intercept + slope * year, 4)} for year in years]
    try:
        tested = mk.hamed_rao_modification_test(values, alpha=alpha)
        _apply_test(result, tested, alpha)
    except Exception:
        try:
            tested = mk.original_test(values, alpha=alpha)
            result["method"] = "mann_kendall"
            result["method_label"] = "Mann–Kendall with Sen's slope. The autocorrelation correction was numerically unstable on this sample."
            result["accounts_for"] = "The seasonal cycle, via the annual aggregate. Serial correlation was not corrected for this sample."
            _apply_test(result, tested, alpha)
        except Exception as exc:
            result["error"] = f"Trend test could not be computed ({type(exc).__name__})."
            result["direction"] = None
            result["significant"] = None
    return result


def _apply_test(result: dict, tested, alpha: float) -> None:
    """Use the returned p-value with this app's alpha. pymannkendall's seasonal test ignores its alpha argument."""
    p_value = _number(getattr(tested, "p", None))
    z_value = _number(getattr(tested, "z", None))
    if p_value is None:
        result["error"] = "The trend test returned no p-value."
        result["direction"] = None
        result["significant"] = None
        return
    result["p_value"] = round(p_value, 6)
    result["z"] = _round(z_value, 3)
    result["tau"] = _round(_number(getattr(tested, "Tau", None)), 3)
    significant = p_value < alpha and z_value is not None and z_value != 0
    result["significant"] = significant
    if significant and z_value > 0:
        result["direction"] = "increasing"
    elif significant and z_value < 0:
        result["direction"] = "decreasing"
    else:
        result["direction"] = "no statistically significant trend"
        result["significant"] = False


def _sen(years: list[int], values: list[float]) -> tuple[float, float]:
    slopes = []
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            span = years[j] - years[i]
            if span > 0:
                slopes.append((values[j] - values[i]) / span)
    slope = float(np.median(slopes))
    intercept = float(np.median([value - slope * year for year, value in zip(years, values)]))
    return slope, intercept


def _seasonal_sen(years: list[int], matrix: list[list[float]]) -> tuple[float, float]:
    slopes = []
    for month in range(12):
        column = [row[month] for row in matrix]
        for i in range(len(column)):
            for j in range(i + 1, len(column)):
                span = years[j] - years[i]
                if span > 0:
                    slopes.append((column[j] - column[i]) / span)
    slope = float(np.median(slopes))
    return slope, 0.0


def _ndvi_annual(rows: list[dict], year: int) -> dict:
    chosen = [row for row in rows if row["year"] == year]
    valid = [row["ndvi"] for row in chosen if row["ndvi"] is not None]
    return {
        "year": year,
        "mean": _round(_mean(valid), 4),
        "min": _round(min(valid), 4) if valid else None,
        "max": _round(max(valid), 4) if valid else None,
        "n_obs": len(valid),
        "n_missing": sum(1 for row in chosen if row["ndvi"] is None),
    }


def _ndvi_season(rows: list[dict], season: str, label: str, year: int) -> dict:
    def inside(row: dict) -> bool:
        if season == "zaid":
            return row["year"] == year and row["month"] in (4, 5)
        if season == "kharif":
            return row["year"] == year and row["month"] in (6, 7, 8, 9, 10)
        return (row["year"] == year - 1 and row["month"] in (11, 12)) or (row["year"] == year and row["month"] in (1, 2, 3))
    chosen = [row for row in rows if inside(row)]
    valid = [row["ndvi"] for row in chosen if row["ndvi"] is not None]
    return {
        "year": year,
        "season": season,
        "label": label,
        "mean": _round(_mean(valid), 4),
        "min": _round(min(valid), 4) if valid else None,
        "max": _round(max(valid), 4) if valid else None,
        "n_obs": len(valid),
        "n_missing": sum(1 for row in chosen if row["ndvi"] is None),
    }


def _ndvi_seasonal_means(seasons: list[dict]) -> list[dict]:
    output = []
    for season, label in SEASONS:
        chosen = [row for row in seasons if row["season"] == season and row["mean"] is not None and row["n_obs"] > 0]
        output.append({
            "season": season,
            "label": label,
            "mean": _round(_mean([row["mean"] for row in chosen]), 4),
            "n_seasons": len(chosen),
            "n_obs": sum(row["n_obs"] for row in chosen),
        })
    return output


def _next_season(season: str, year: int) -> tuple[str, int] | None:
    if season == "rabi":
        return ("zaid", year)
    if season == "zaid":
        return ("kharif", year)
    if season == "kharif":
        return ("rabi", year + 1)
    return None


def _mean(values: list[float]) -> float | None:
    clean = [float(value) for value in values if value is not None and not math.isnan(float(value))]
    if not clean:
        return None
    return float(sum(clean) / len(clean))


def _std(values: list[float]) -> float | None:
    clean = [float(value) for value in values if value is not None and not math.isnan(float(value))]
    if len(clean) < 2:
        return None
    center = sum(clean) / len(clean)
    return math.sqrt(sum((value - center) ** 2 for value in clean) / (len(clean) - 1))


def _anomaly(value, baseline, digits: int = 3) -> float | None:
    if value is None or baseline is None:
        return None
    return _round(float(value) - float(baseline), digits)


def _number(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _round(value, digits: int):
    number = _number(value)
    if number is None:
        return None
    return round(number, digits)
