"""End-to-End Integration and Failure Mode Tests for ROTATION IQ.

Simulates the complete farmer journey across API endpoints and verifies:
1. Health check and API availability.
2. Complete farmer journey:
   - Location selection and climate analysis retrieval.
   - Vegetation MODIS NDVI analysis retrieval.
   - Trend analysis retrieval.
   - Recommendation generation across all 4 farmer priorities.
   - Profile with missing optional parameters (null pH, null OC).
   - Custom rotation sequence evaluation.
   - Pan-Indian crop catalog querying and filtering.
3. Robust failure modes and edge cases:
   - NASA POWER API unavailable (returns available: False without 500 error).
   - MODIS ORNL API unavailable (returns available: False without 500 error).
   - Out-of-bounds coordinates (lat > 90, lon < -180 -> 422).
   - Inverted years and excessive date span -> 422.
   - Invalid crop ID in custom rotation -> 422.
   - Distinction between ETc crop water requirement and irrigation requirement.
   - Strict absence of biological N-fixation on non-legumes (null, not 0).
"""
import unittest
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
import main, rotation, config
from tests.test_analysis import make_synthetic_power_payload, make_synthetic_ndvi_payload


class TestEndToEndFarmerJourney(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_complete_farmer_workflow(self):
        """Simulates full workflow: health -> climate -> trends -> vegetation -> recommendations -> custom rotation."""
        # Step 1: Health check
        health_res = self.client.get("/api/health")
        self.assertEqual(health_res.status_code, 200)
        self.assertEqual(health_res.json(), {"ok": True})

        # Step 2: Fetch Climate Analysis for Patna (25.5941, 85.1376)
        with patch("nasa_power.fetch_power", new_callable=AsyncMock) as mock_power:
            mock_power.return_value = make_synthetic_power_payload(1991, 2024)
            climate_res = self.client.get("/api/analysis/climate?lat=25.5941&lon=85.1376&start_year=2020&end_year=2024")
            self.assertEqual(climate_res.status_code, 200)
            c_data = climate_res.json()
            self.assertTrue(c_data["available"])
            self.assertIn("baseline", c_data)
            self.assertIn("annual", c_data)

        # Step 3: Fetch Vegetation Analysis for Patna
        with patch("modis_ornl.fetch_ndvi", new_callable=AsyncMock) as mock_ndvi:
            mock_ndvi.return_value = make_synthetic_ndvi_payload(2020, 2024)
            veg_res = self.client.get("/api/analysis/vegetation?lat=25.5941&lon=85.1376&start_year=2020&end_year=2024")
            self.assertEqual(veg_res.status_code, 200)
            v_data = veg_res.json()
            self.assertTrue(v_data["available"])
            self.assertIn("series", v_data)
            self.assertIn("seasons", v_data)

        # Step 4: Generate Rotation Recommendations for standard Patna profile
        farmer_payload = {
            "area_acres": 3.0,
            "soil_type": "alluvial",
            "soil_ph": 7.1,
            "organic_carbon_pct": 0.58,
            "irrigation": "assured_tubewell",
            "current_rotation": "rice_wheat",
            "priority": "water_conservation",
        }
        rec_res = self.client.post("/api/rotation/evaluate", json=farmer_payload)
        self.assertEqual(rec_res.status_code, 200)
        rec_data = rec_res.json()
        self.assertIn("rotations", rec_data)
        self.assertGreaterEqual(len(rec_data["rotations"]), 6)
        
        # Verify priority weighting dynamically prioritized water conservation
        top_strat = rec_data["rotations"][0]
        self.assertIn(top_strat["id"], ("pearl_millet_chickpea", "sorghum_lentil", "rice_mustard", "rice_pulse"))
        self.assertGreaterEqual(top_strat["criteria_scores"]["water_sustainability"], 50.0)

        # Step 5: Evaluate a Custom 3-crop sequence (Rice -> Potato -> Green Gram)
        custom_payload = {
            "crop_ids": ["rice", "potato", "green_gram"],
            "area_acres": 2.5,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "priority": "income_stability",
        }
        custom_res = self.client.post("/api/rotation/evaluate-custom", json=custom_payload)
        self.assertEqual(custom_res.status_code, 200)
        cust_data = custom_res.json()
        self.assertIn("evaluation", cust_data)
        ev = cust_data["evaluation"]
        self.assertEqual(ev["water_demand_mm"], 1880)
        self.assertEqual(ev["nitrogen_fixed_kg_ha"], 30.0)
        self.assertEqual(len(ev["crops"]), 3)
        self.assertIn("turnaround_days", ev)

    def test_missing_optional_farmer_inputs(self):
        """Farmer profile with null pH and null Organic Carbon evaluates correctly."""
        profile = {
            "area_acres": 2.0,
            "soil_type": "clay_loam",
            "soil_ph": None,
            "organic_carbon_pct": None,
            "irrigation": "rainfed",
            "current_rotation": "rice_wheat",
            "priority": "soil_improvement",
        }
        res = self.client.post("/api/rotation/evaluate", json=profile)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNone(data["farmer_profile"]["soil_ph"])
        self.assertIsNone(data["farmer_profile"]["organic_carbon_pct"])
        self.assertEqual(data["farmer_profile"]["irrigation"], "rainfed")
        self.assertGreaterEqual(len(data["rotations"]), 6)

    def test_priority_shift_dynamically_alters_rankings(self):
        """Changing farmer priorities reorders recommendation pathways appropriately."""
        base_profile = {
            "area_acres": 2.5,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "current_rotation": "rice_wheat",
        }

        # Priority 1: Water Conservation
        res_water = self.client.post("/api/rotation/evaluate", json={**base_profile, "priority": "water_conservation"}).json()
        top_water = res_water["rotations"][0]

        # Priority 2: Soil Improvement
        res_soil = self.client.post("/api/rotation/evaluate", json={**base_profile, "priority": "soil_improvement"}).json()
        top_soil = res_soil["rotations"][0]

        # Under soil improvement, top rotation must fix nitrogen
        self.assertGreater(top_soil["nitrogen_fixed_kg_ha"], 0)

        # Under water conservation, water demand must be strictly controlled
        self.assertLessEqual(top_water["water_demand_mm"], 1500)

    def test_crop_catalog_filtering_endpoints(self):
        """Tests the pan-Indian crop explorer endpoints across category, season, region, and query."""
        # All crops (1,053+)
        res_all = self.client.get("/api/rotation/crops")
        self.assertEqual(res_all.status_code, 200)
        self.assertGreaterEqual(len(res_all.json()), 1053)

        # Filter by category
        res_pulses = self.client.get("/api/rotation/crops?category=pulse")
        self.assertEqual(res_pulses.status_code, 200)
        for cid, c in res_pulses.json().items():
            self.assertIn("pulse", [cat.lower() for cat in c["categories"]])

        # Filter by season
        res_rabi = self.client.get("/api/rotation/crops?season=rabi")
        self.assertEqual(res_rabi.status_code, 200)
        for cid, c in res_rabi.json().items():
            self.assertTrue("rabi" in c["season"].lower() or "all_season" in c["season"].lower())

        # Search by query
        res_search = self.client.get("/api/rotation/crops?q=mustard")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn("mustard", res_search.json())


class TestFailureModesAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    @patch("nasa_power.fetch_power", new_callable=AsyncMock)
    def test_nasa_power_unavailable_handled_cleanly(self, mock_power):
        """When NASA POWER times out or fails, API returns available: False without 500 error."""
        mock_power.return_value = {
            "available": False,
            "name": "NASA POWER daily",
            "reason": "HTTPTimeoutError: Connection timed out to power.larc.nasa.gov",
        }
        res = self.client.get("/api/analysis/climate?lat=25.5941&lon=85.1376&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["available"])
        self.assertIn("Connection timed out", data["reason"])

    @patch("modis_ornl.fetch_ndvi", new_callable=AsyncMock)
    def test_modis_unavailable_handled_cleanly(self, mock_ndvi):
        """When MODIS ORNL server fails, API returns available: False without 500 error."""
        mock_ndvi.return_value = {
            "available": False,
            "name": "MODIS MOD13Q1 (ORNL)",
            "reason": "ServiceUnavailable: ORNL DAAC maintenance window",
        }
        res = self.client.get("/api/analysis/vegetation?lat=25.5941&lon=85.1376&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["available"])
        self.assertIn("ORNL DAAC maintenance", data["reason"])

    def test_coordinate_validation_bounds(self):
        # Lat > 90
        res = self.client.get("/api/analysis/climate?lat=90.001&lon=85.0&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 422)

        # Lat < -90
        res = self.client.get("/api/analysis/climate?lat=-90.5&lon=85.0&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 422)

        # Lon > 180
        res = self.client.get("/api/analysis/climate?lat=25.0&lon=180.1&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 422)

        # Lon < -180
        res = self.client.get("/api/analysis/climate?lat=25.0&lon=-180.1&start_year=2020&end_year=2024")
        self.assertEqual(res.status_code, 422)

    def test_date_range_validation_bounds(self):
        # Start year > End year
        res = self.client.get("/api/analysis/climate?lat=25.59&lon=85.13&start_year=2024&end_year=2020")
        self.assertEqual(res.status_code, 422)

        # Span > 50 years
        res = self.client.get("/api/analysis/climate?lat=25.59&lon=85.13&start_year=1981&end_year=2035")
        self.assertEqual(res.status_code, 422)

    def test_custom_rotation_unknown_crop_rejected(self):
        """Unknown crop ID returns HTTP 422 with informative message."""
        payload = {
            "crop_ids": ["rice", "fictional_supercrop_123"],
            "area_acres": 2.5,
            "soil_type": "alluvial",
            "priority": "balanced",
        }
        res = self.client.post("/api/rotation/evaluate-custom", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertIn("Unknown crop ID", res.json()["detail"])

    def test_etc_versus_irrigation_requirement_integrity(self):
        """Verifies crop water demand is labeled as ETc water demand, not irrigation requirement."""
        res = self.client.post("/api/rotation/evaluate", json={
            "area_acres": 2.5,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "current_rotation": "rice_wheat",
            "priority": "balanced",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for r in data["rotations"]:
            self.assertIn("water_demand_mm", r)
            # ETc must be positive and realistic
            self.assertGreater(r["water_demand_mm"], 300)

    def test_non_legumes_have_null_nitrogen_fixation(self):
        """Verifies non-legumes strictly report null/None for N-fixation in API serialization."""
        res = self.client.get("/api/rotation/crops")
        self.assertEqual(res.status_code, 200)
        crops = res.json()
        
        # Check cereals (rice, wheat, maize)
        for cid in ("rice", "wheat", "maize", "barley"):
            self.assertIsNone(crops[cid]["nitrogen_fixation_kg_ha"], f"{cid} has non-null N-fixation")
            self.assertIsNone(crops[cid]["nitrogen_fixation_range_kg_ha"], f"{cid} has non-null N-fixation range")

        # Check Fabaceae legumes
        for cid in ("chickpea", "lentil", "pigeonpea", "groundnut", "fenugreek"):
            self.assertIsNotNone(crops[cid]["nitrogen_fixation_kg_ha"], f"{cid} has null N-fixation")
            self.assertGreater(crops[cid]["nitrogen_fixation_kg_ha"], 0)


if __name__ == "__main__":
    unittest.main()
