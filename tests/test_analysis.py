"""Automated analytical tests for Rotation IQ using synthetic datasets."""
import math
import unittest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
import analysis, config, modis_ornl


def make_synthetic_power_payload(start_year: int = 2000, end_year: int = 2020, missing_fraction: float = 0.0, trend_slope: float = 0.05):
    dates = []
    t2m_vals = []
    t2m_max_vals = []
    t2m_min_vals = []
    rain_vals = []
    rh2m_vals = []
    solar_vals = []
    gwettop_vals = []
    gwetroot_vals = []

    rng = np.random.RandomState(42)
    cur = pd.Timestamp(f'{start_year}-01-01')
    end = pd.Timestamp(f'{end_year}-12-31')

    while cur <= end:
        ds = cur.strftime('%Y%m%d')
        dates.append(ds)
        year_offset = cur.year - start_year
        doy = cur.day_of_year
        seasonal_temp = 10.0 * np.sin(2 * np.pi * (doy - 100) / 365.0)
        # Add slight variation so identical-value lags don't produce division-by-zero warnings in autocorrelation
        noise = rng.normal(0, 0.01)
        mean_t = 24.0 + trend_slope * year_offset + seasonal_temp + noise

        if missing_fraction > 0 and rng.rand() < missing_fraction:
            t2m_vals.append(None)
            t2m_max_vals.append(None)
            t2m_min_vals.append(None)
            rain_vals.append(None)
        else:
            t2m_vals.append(round(float(mean_t), 2))
            t2m_max_vals.append(round(float(mean_t + 5.0), 2))
            t2m_min_vals.append(round(float(mean_t - 5.0), 2))
            rain = 15.0 if cur.month in (6, 7, 8, 9) else 0.5
            rain_vals.append(round(float(rain), 2))

        rh2m_vals.append(60.0)
        solar_vals.append(18.0)
        gwettop_vals.append(0.5)
        gwetroot_vals.append(0.5)

        cur += pd.Timedelta(days=1)

    return {
        'available': True,
        'dates': dates,
        'columns': {
            'T2M': t2m_vals,
            'T2M_MAX': t2m_max_vals,
            'T2M_MIN': t2m_min_vals,
            'PRECTOTCORR': rain_vals,
            'RH2M': rh2m_vals,
            'ALLSKY_SFC_SW_DWN': solar_vals,
            'GWETTOP': gwettop_vals,
            'GWETROOT': gwetroot_vals,
        },
        'cell': {'lat': 25.5, 'lon': 85.0, 'lat_size_deg': 0.5, 'lon_size_deg': 0.625},
        'meta': {
            'overall': {
                'name': 'NASA POWER daily (AG)',
                'source_url': 'https://power.larc.nasa.gov',
                'resolution': '0.5 x 0.625 deg',
                'period_start': dates[0],
                'period_end': dates[-1],
                'n_obs': len(dates),
                'kind': 'observed',
                'retrieved_at': '2026-11-14T00:00:00Z',
            },
            'sources': ['MERRA2', 'SYN1DEG'],
            'modeled_vars': ['GWETTOP', 'GWETROOT'],
            'non_null_counts': {'T2M': sum(v is not None for v in t2m_vals)},
        },
    }


def make_synthetic_ndvi_payload(start_year: int = 2020, end_year: int = 2022):
    dates = []
    ndvi_raw = []
    rel_raw = []

    cur = pd.Timestamp(f'{start_year - 1}-11-01')
    end = pd.Timestamp(f'{end_year}-12-31')

    while cur <= end:
        dates.append(cur.strftime('%Y-%m-%d'))
        month = cur.month
        if 6 <= month <= 10:
            val = 7000
        elif month in (11, 12, 1, 2, 3):
            val = 5000
        else:
            val = 3000

        # Inject cloudy composite
        if cur.month == 7 and cur.day < 15:
            ndvi_raw.append(None)
            rel_raw.append(3)
        else:
            ndvi_raw.append(val * 0.0001)
            rel_raw.append(0)

        cur += pd.Timedelta(days=16)

    col, row = modis_ornl.modis_sinusoidal_pixel(25.5941, 85.1376)
    return {
        'available': True,
        'dates': dates,
        'ndvi': ndvi_raw,
        'reliability': rel_raw,
        'pixel': {'col': col, 'row': row, 'cellsize_m': 231.656},
        'meta': {
            'name': 'MODIS Terra MOD13Q1 NDVI via ORNL DAAC',
            'source_url': 'https://modis.ornl.gov',
            'resolution': '231.7 m sinusoidal cell',
            'period_start': dates[0],
            'period_end': dates[-1],
            'n_obs': sum(v is not None for v in ndvi_raw),
            'kind': 'observed',
            'retrieved_at': '2026-11-14T00:00:00Z',
        },
    }


class TestClimateAnalysis(unittest.TestCase):
    def test_missing_values_never_replaced_with_zero(self):
        payload = make_synthetic_power_payload(2010, 2015, missing_fraction=0.3)
        res = analysis.analyze_climate(payload, lat=25.59, lon=85.14, start_year=2010, end_year=2015, min_completeness=0.9)
        self.assertTrue(res['available'])
        for yr in res['annual']:
            if not yr['t2m_complete']:
                self.assertIsNone(yr['t2m_mean_c'])
            if not yr['rainfall_complete']:
                self.assertIsNone(yr['rainfall_mm'])

    def test_baseline_and_anomalies_calculated(self):
        payload = make_synthetic_power_payload(1995, 2020, missing_fraction=0.0)
        res = analysis.analyze_climate(payload, lat=25.59, lon=85.14, start_year=2000, end_year=2010, baseline_start=1995, baseline_end=2010)
        self.assertTrue(res['available'])
        self.assertIn('baseline', res)
        self.assertIsNotNone(res['baseline']['temperature_mean_c'])
        self.assertIsNotNone(res['baseline']['rainfall_mean_mm'])
        for yr in res['annual']:
            if yr['t2m_complete'] and res['baseline']['temperature_mean_c'] is not None:
                expected_anom = round(yr['t2m_mean_c'] - res['baseline']['temperature_mean_c'], 3)
                self.assertAlmostEqual(yr['t2m_anomaly_c'], expected_anom, places=2)

    def test_rabi_season_spans_previous_nov_dec(self):
        payload = make_synthetic_power_payload(2018, 2020)
        res = analysis.analyze_climate(payload, lat=25.59, lon=85.14, start_year=2019, end_year=2020)
        rabi_2019 = next(s for s in res['seasons'] if s['season'] == 'rabi' and s['year'] == 2019)
        self.assertEqual(rabi_2019['expected_days'], 151)


class TestTrendAnalysis(unittest.TestCase):
    def test_mann_kendall_known_increasing_trend(self):
        payload = make_synthetic_power_payload(2000, 2020, missing_fraction=0.0, trend_slope=0.1)
        res = analysis.analyze_trends(payload, lat=25.59, lon=85.14, start_year=2000, end_year=2020, min_years=10)
        t2m_trend = next(s for s in res['series'] if s['id'] == 'annual_t2m_mean')
        self.assertIsNone(t2m_trend['error'])
        self.assertGreater(t2m_trend['slope'], 0.0)
        self.assertIn('°C', t2m_trend['slope_units'])
        self.assertEqual(t2m_trend['direction'], 'increasing')
        self.assertTrue(t2m_trend['significant'])

    def test_mann_kendall_known_decreasing_trend(self):
        payload = make_synthetic_power_payload(2000, 2020, missing_fraction=0.0, trend_slope=-0.1)
        res = analysis.analyze_trends(payload, lat=25.59, lon=85.14, start_year=2000, end_year=2020, min_years=10)
        t2m_trend = next(s for s in res['series'] if s['id'] == 'annual_t2m_mean')
        self.assertIsNone(t2m_trend['error'])
        self.assertLess(t2m_trend['slope'], 0.0)
        self.assertEqual(t2m_trend['direction'], 'decreasing')
        self.assertTrue(t2m_trend['significant'])

    def test_mann_kendall_known_no_trend(self):
        payload = make_synthetic_power_payload(2000, 2020, missing_fraction=0.0, trend_slope=0.0)
        res = analysis.analyze_trends(payload, lat=25.59, lon=85.14, start_year=2000, end_year=2020, min_years=10)
        t2m_trend = next(s for s in res['series'] if s['id'] == 'annual_t2m_mean')
        self.assertIsNone(t2m_trend['error'])
        self.assertAlmostEqual(t2m_trend['slope'], 0.0, places=2)
        self.assertEqual(t2m_trend['direction'], 'no statistically significant trend')


class TestVegetationAnalysis(unittest.TestCase):
    def test_vegetation_analysis_includes_leading_rabi(self):
        payload = make_synthetic_ndvi_payload(2020, 2022)
        res = analysis.analyze_vegetation(payload, lat=25.5941, lon=85.1376, start_year=2020, end_year=2022)
        self.assertTrue(res['available'])
        rabi_2020 = next(s for s in res['seasons'] if s['season'] == 'rabi' and s['year'] == 2020)
        self.assertGreater(rabi_2020['n_obs'], 0)
        self.assertIsNotNone(rabi_2020['mean'])

    def test_cloudy_composites_filtered(self):
        payload = make_synthetic_ndvi_payload(2020, 2022)
        res = analysis.analyze_vegetation(payload, lat=25.5941, lon=85.1376, start_year=2020, end_year=2022)
        cloudy_dates = [s for s in res['series'] if s['reliability'] == 3]
        for c in cloudy_dates:
            self.assertIsNone(c['ndvi'])

    def test_modis_sinusoidal_pixel_determinism(self):
        col1, row1 = modis_ornl.modis_sinusoidal_pixel(25.5941, 85.1376)
        col2, row2 = modis_ornl.modis_sinusoidal_pixel(25.59414, 85.13764)
        self.assertEqual((col1, row1), (col2, row2))


if __name__ == '__main__':
    unittest.main()
