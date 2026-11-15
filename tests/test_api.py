"""Automated API integration and validation tests for Rotation IQ."""
import unittest
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
import main, config
from tests.test_analysis import make_synthetic_power_payload, make_synthetic_ndvi_payload


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_production_asgi_import_and_uvicorn_startup(self):
        """Verifies that the exact production startup target 'backend.main:app' loads cleanly via uvicorn from root."""
        import uvicorn
        cfg = uvicorn.Config("backend.main:app", host="0.0.0.0", port=8000)
        cfg.load()
        loaded = cfg.loaded_app
        self.assertIsNotNone(loaded)
        app_obj = getattr(loaded, "app", loaded)
        self.assertEqual(getattr(app_obj, "title", None), "Rotation IQ API")

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"ok": True})

    def test_coordinate_validation(self):
        # Invalid latitude (> 90)
        res = self.client.get("/api/analysis/climate?lat=95.0&lon=85.1376&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 422)

        # Invalid longitude (< -180)
        res = self.client.get("/api/analysis/climate?lat=25.59&lon=-185.0&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 422)

    def test_year_validation(self):
        # Inverted years (end < start)
        res = self.client.get("/api/analysis/climate?lat=25.59&lon=85.14&start_year=2024&end_year=2020")
        self.assertEqual(res.status_code, 422)

        # Year before 1981
        res = self.client.get("/api/analysis/climate?lat=25.59&lon=85.14&start_year=1975&end_year=2020")
        self.assertEqual(res.status_code, 422)

        # Exceeds max span (50 years)
        res = self.client.get("/api/analysis/climate?lat=25.59&lon=85.14&start_year=1981&end_year=2035")
        self.assertEqual(res.status_code, 422)

    @patch("nasa_power.fetch_power", new_callable=AsyncMock)
    def test_climate_analysis_response_structure(self, mock_power):
        mock_power.return_value = make_synthetic_power_payload(1991, 2024)
        res = self.client.get("/api/analysis/climate?lat=25.5941&lon=85.1376&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["available"])
        self.assertIn("baseline", data)
        self.assertEqual(data["baseline"]["start_year"], config.BASELINE_START)
        self.assertEqual(data["baseline"]["end_year"], config.BASELINE_END)
        self.assertIn("quality", data)
        self.assertIn("source", data["quality"])
        self.assertIn("observation_period", data["quality"])
        self.assertIn("annual", data)
        self.assertIn("seasons", data)

    @patch("nasa_power.fetch_power", new_callable=AsyncMock)
    def test_trends_analysis_response_structure(self, mock_power):
        mock_power.return_value = make_synthetic_power_payload(2000, 2024, trend_slope=0.08)
        res = self.client.get("/api/analysis/trends?lat=25.5941&lon=85.1376&start_year=2000&end_year=2024")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["available"])
        self.assertIn("series", data)
        self.assertIn("disclaimer", data)
        self.assertIn("quality", data)
        t2m_series = next(s for s in data["series"] if s["id"] == "annual_t2m_mean")
        self.assertIn("slope", t2m_series)
        self.assertIn("slope_units", t2m_series)
        self.assertIn("p_value", t2m_series)
        self.assertIn("direction", t2m_series)

    @patch("modis_ornl.fetch_ndvi", new_callable=AsyncMock)
    def test_vegetation_analysis_response_structure(self, mock_ndvi):
        mock_ndvi.return_value = make_synthetic_ndvi_payload(2020, 2024)
        res = self.client.get("/api/analysis/vegetation?lat=25.5941&lon=85.1376&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["available"])
        self.assertIn("series", data)
        self.assertIn("seasons", data)
        self.assertIn("seasonal_means", data)
        self.assertIn("quality", data)
        self.assertIn("units", data["quality"])
        self.assertIn("observation_period", data["quality"])

    def test_rotation_evaluate_endpoints(self):
        # Test GET
        res_get = self.client.get("/api/rotation/evaluate?priority=water_conservation&irrigation=partial")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertIn("rotations", data_get)
        self.assertGreaterEqual(len(data_get["rotations"]), 4)
        self.assertEqual(data_get["farmer_profile"]["source"], "farmer_reported")

        # Test POST
        payload = {
            "area_acres": 4.5,
            "soil_type": "clay_loam",
            "soil_ph": 6.8,
            "organic_carbon_pct": 0.45,
            "irrigation": "assured_canal",
            "current_rotation": "rice_wheat",
            "priority": "soil_improvement",
        }
        res_post = self.client.post("/api/rotation/evaluate", json=payload)
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.json()
        self.assertIn("rotations", data_post)
        self.assertGreaterEqual(len(data_post["rotations"]), 4)
        self.assertEqual(data_post["farmer_profile"]["soil_ph"], 6.8)

    def test_rotation_crops_endpoint_and_filtering(self):
        # All crops (1,053+)
        res = self.client.get("/api/rotation/crops")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 1053)
        self.assertIn("rice", data)
        self.assertIn("wheat", data)
        self.assertIn("chickpea", data)

        # Filter by category = pulse
        res_pulse = self.client.get("/api/rotation/crops?category=pulse")
        self.assertEqual(res_pulse.status_code, 200)
        data_pulse = res_pulse.json()
        self.assertGreaterEqual(len(data_pulse), 9)
        self.assertIn("chickpea", data_pulse)
        self.assertNotIn("wheat", data_pulse)

        # Search by query
        res_search = self.client.get("/api/rotation/crops?q=paddy")
        self.assertEqual(res_search.status_code, 200)
        data_search = res_search.json()
        self.assertIn("rice", data_search)

    def test_rotation_evaluate_custom_endpoint(self):
        # Valid custom sequence: Rice -> Potato -> Green Gram
        custom_payload = {
            "crop_ids": ["rice", "potato", "green_gram"],
            "area_acres": 2.0,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "priority": "balanced",
        }
        res = self.client.post("/api/rotation/evaluate-custom", json=custom_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("evaluation", data)
        ev = data["evaluation"]
        self.assertEqual(ev["crop_ids"], ["rice", "potato", "green_gram"])
        self.assertEqual(ev["nitrogen_fixed_kg_ha"], 30)
        self.assertGreaterEqual(ev["overall_score"], 0.0)

        # Invalid crop ID rejected with 422
        bad_payload = {
            "crop_ids": ["non_existent_crop"],
            "area_acres": 2.0,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "priority": "balanced",
        }
        res_bad = self.client.post("/api/rotation/evaluate-custom", json=bad_payload)
        self.assertEqual(res_bad.status_code, 422)


if __name__ == '__main__':
    unittest.main()

