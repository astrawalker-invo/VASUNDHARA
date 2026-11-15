"""Runtime settings. Process environment only; this app does not load a .env file."""
import os


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


# Two-sided significance level for Mann-Kendall tests.
ALPHA = _float("ANALYSIS_ALPHA", 0.05)
# A period is published only when at least this fraction of its calendar days is present and non-null.
MIN_COMPLETENESS = _float("ANALYSIS_MIN_COMPLETENESS", 0.9)
# Climatological baseline used for anomalies. 1991–2020 is the current WMO standard normal.
BASELINE_START = _int("ANALYSIS_BASELINE_START", 1991)
BASELINE_END = _int("ANALYSIS_BASELINE_END", 2020)
MIN_BASELINE_YEARS = _int("ANALYSIS_MIN_BASELINE_YEARS", 10)
MIN_TREND_YEARS = _int("ANALYSIS_MIN_TREND_YEARS", 10)
MAX_SPAN_YEARS = _int("ANALYSIS_MAX_SPAN_YEARS", 50)
POWER_MIN_YEAR = _int("POWER_MIN_YEAR", 1981)
NDVI_MIN_YEAR = _int("NDVI_MIN_YEAR", 2000)
# ALLSKY_SFC_SW_DWN is SYN1DEG and is not valid before this year. Do not trend across the break.
SOLAR_START_YEAR = _int("POWER_SOLAR_START_YEAR", 1984)
WARM_CACHE = os.getenv("ROTATION_IQ_WARM_CACHE", "1") != "0"

if not 0 < MIN_COMPLETENESS <= 1:
    raise ValueError("ANALYSIS_MIN_COMPLETENESS must be in (0, 1]")
if not 0 < ALPHA < 1:
    raise ValueError("ANALYSIS_ALPHA must be in (0, 1)")
if BASELINE_END < BASELINE_START:
    raise ValueError("ANALYSIS_BASELINE_END must be on or after ANALYSIS_BASELINE_START")
if MIN_TREND_YEARS < 4:
    raise ValueError("ANALYSIS_MIN_TREND_YEARS must be at least 4")
