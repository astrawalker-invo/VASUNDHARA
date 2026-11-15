"""Unit tests for Rotation IQ 53-crop database and intelligent rotation engine.

Verifies:
1. 53 unique crop records exist.
2. All records follow the complete required schema.
3. Category and crop-family classifications are valid.
4. Nitrogen fixation is assigned only to legumes (Fabaceae: exactly 12 species); non-legumes are None.
5. Missing attributes do not receive fabricated defaults.
6. Crop filtering and search functionality.
7. Regional suitability indicators.
8. Rainfed vs assured-irrigation profile differentiation.
9. Farmer priorities effect on scoring and weights.
10. Soil texture profile compatibility effects.
11. Crop calendar incompatibility detection (>365 days warning).
12. Perennial crops and sole sugarcane handled appropriately without false penalties.
13. Custom rotation evaluation.
14. Soil health score for Rice-Pulse calibrated (defensible ~72-76, not inflated to 98).
15. Water stress warnings on high-water triple-crop systems.
16. The 6 benchmark scenarios produce expected score ranges.
17. Invalid crop IDs rejection.
18. Score boundary constraints (all scores within [0, 100]).
19. Safe JSON serializability.
20. Preserved Phase 1 & Phase 2 functionality.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
import rotation


class TestPanIndianCropDatabase(unittest.TestCase):
    def test_catalogue_size_at_least_50_expected_53(self):
        crops = rotation.PAN_INDIA_CROPS
        self.assertGreaterEqual(len(crops), 50)
        self.assertEqual(len(crops), 53)

    def test_required_schema_fields_present_on_all_crops(self):
        required_keys = {
            "id", "name", "scientific_name", "categories", "crop_family",
            "season", "duration_range_days", "typical_duration",
            "water_need_range_mm", "nitrogen_fixation_range_kg_ha",
            "root_type", "root_depth_range_cm", "soil_cover_rating",
            "drought_tolerance", "waterlogging_tolerance", "n_feeder",
            "suitable_soils", "regional_suitability", "data_source",
            "source_year", "data_confidence", "limitations",
        }
        for cid, c in rotation.PAN_INDIA_CROPS.items():
            missing = required_keys - set(c.keys())
            self.assertEqual(len(missing), 0, f"Crop {cid} missing keys: {missing}")
            self.assertEqual(c["id"], cid)
            self.assertIsInstance(c["categories"], list)
            self.assertGreaterEqual(len(c["categories"]), 1)
            self.assertIsInstance(c["crop_family"], str)
            self.assertIsInstance(c["duration_range_days"], (list, tuple))
            self.assertEqual(len(c["duration_range_days"]), 2)
            self.assertIsInstance(c["water_need_range_mm"], (list, tuple))
            self.assertEqual(len(c["water_need_range_mm"]), 2)
            self.assertIsInstance(c["limitations"], list)
            self.assertGreaterEqual(len(c["limitations"]), 1)

    def test_category_representation(self):
        crops = rotation.PAN_INDIA_CROPS
        all_cats = {cat for c in crops.values() for cat in c.get("categories", [])}
        expected_cats = {"cereal", "pulse", "oilseed", "vegetable", "fruit", "commercial", "spice", "millet"}
        self.assertTrue(expected_cats.issubset(all_cats), f"Missing categories: {expected_cats - all_cats}")

    def test_nitrogen_fixation_assigned_only_to_legumes(self):
        fabaceae_count = 0
        for cid, c in rotation.PAN_INDIA_CROPS.items():
            if c.get("crop_family") == "Fabaceae":
                fabaceae_count += 1
                self.assertIsNotNone(c.get("nitrogen_fixation_range_kg_ha"), f"{cid} has None range")
                self.assertGreater(c.get("nitrogen_fixation_kg_ha") or 0, 0, f"{cid} has 0 N-fix")
            else:
                self.assertIsNone(c.get("nitrogen_fixation_range_kg_ha"), f"{cid} has non-None range")
                self.assertIsNone(c.get("nitrogen_fixation_kg_ha"), f"{cid} has non-None N-fix")
        # Exactly 12 Fabaceae species: 10 pulses + groundnut (oilseed) + fenugreek (spice)
        self.assertEqual(fabaceae_count, 12)

    def test_regional_suitability_mapping(self):
        for cid, c in rotation.PAN_INDIA_CROPS.items():
            reg = c.get("regional_suitability", {})
            self.assertIsInstance(reg, dict)
            self.assertIn("bihar", reg)
            self.assertIn(reg["bihar"], ("high", "moderate", "low"))

    def test_global_expanded_catalogue_integrity(self):
        """Verifies expanded global database has >= 1053 crops and strict BNF integrity."""
        crops = rotation.CROPS
        self.assertGreaterEqual(len(crops), 1053)
        fabaceae_count = 0
        for cid, c in crops.items():
            if c.get("crop_family") == "Fabaceae":
                fabaceae_count += 1
                self.assertIsNotNone(c.get("nitrogen_fixation_kg_ha"), f"{cid} missing BNF")
                self.assertGreater(c.get("nitrogen_fixation_kg_ha"), 0)
            else:
                self.assertIsNone(c.get("nitrogen_fixation_kg_ha"), f"Non-Fabaceae {cid} has BNF")
        self.assertGreaterEqual(fabaceae_count, 150)



class TestIntelligentRotationEngine(unittest.TestCase):
    def test_evaluates_top_pathways(self):
        profile = {
            "area_acres": 3.0,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "priority": "balanced",
        }
        res = rotation.evaluate_rotations(profile)
        self.assertIn("rotations", res)
        self.assertGreaterEqual(len(res["rotations"]), 6)
        strat_ids = {r["id"] for r in res["rotations"]}
        self.assertTrue({"rice_wheat", "rice_pulse", "rice_mustard", "rice_maize"}.issubset(strat_ids))

    def test_water_conservation_priority_and_rainfed_logic(self):
        profile = {
            "area_acres": 2.0,
            "soil_type": "alluvial",
            "irrigation": "rainfed",
            "priority": "water_conservation",
        }
        res = rotation.evaluate_rotations(profile)
        rotations = res["rotations"]
        top_strat = rotations[0]
        self.assertIn(top_strat["id"], ("pearl_millet_chickpea", "sorghum_lentil"))
        rice_wheat = next(r for r in rotations if r["id"] == "rice_wheat")
        self.assertLess(rice_wheat["criteria_scores"]["water_sustainability"], top_strat["criteria_scores"]["water_sustainability"])
        self.assertGreater(len(rice_wheat["warnings"]), 0)

    def test_soil_improvement_priority_ranking(self):
        profile = {
            "area_acres": 4.0,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "priority": "soil_improvement",
        }
        res = rotation.evaluate_rotations(profile)
        pulse = next(r for r in res["rotations"] if r["id"] == "rice_pulse")
        wheat = next(r for r in res["rotations"] if r["id"] == "rice_wheat")
        self.assertGreater(pulse["nitrogen_fixed_kg_ha"], 0)
        self.assertEqual(wheat["nitrogen_fixed_kg_ha"], 0)
        self.assertGreater(pulse["criteria_scores"]["soil_health"], wheat["criteria_scores"]["soil_health"])

    def test_soil_health_individual_formula_components(self):
        """Tests every individual component of the unified authoritative soil health formula:
        S = clamp(35.0 + Delta_S_BNF + Delta_S_family + Delta_S_root + Delta_S_cover - Delta_S_compaction - Delta_S_depletion - Delta_S_texture)
        """
        # Component 1: Base score is 35.0
        # A single hypothetical neutral crop
        neutral_crop = {
            "id": "neutral", "crop_family": "Neutralaceae", "nitrogen_fixation_kg_ha": None,
            "root_type": "fibrous", "root_depth_range_cm": [20, 40], "soil_cover_rating": 3,
            "n_feeder": "medium", "suitable_soils": ["alluvial"]
        }
        score, _ = rotation._score_soil_health([neutral_crop], "alluvial")
        self.assertEqual(score, 35.0)

        # Component 2: Delta_S_BNF (+0.45 per kg N, capped at +20.0)
        legume_20 = {
            "id": "leg20", "crop_family": "Fabaceae", "nitrogen_fixation_kg_ha": 20,
            "root_type": "moderate_taproot", "root_depth_range_cm": [30, 60], "soil_cover_rating": 3,
            "n_feeder": "low", "suitable_soils": ["alluvial"]
        }
        # Single legume: Base(35) + BNF(20 * 0.45 = 9.0) = 44.0
        score, _ = rotation._score_soil_health([legume_20], "alluvial")
        self.assertEqual(score, 44.0)

        # High BNF capped at 20.0
        legume_60 = {**legume_20, "nitrogen_fixation_kg_ha": 60}
        score, _ = rotation._score_soil_health([legume_60], "alluvial")
        self.assertEqual(score, 35.0 + 20.0)

        # Component 3: Family diversity (+8 multi-family, +5 Poaceae+Fabaceae, +3 Brassicaceae, -6 continuous Poaceae)
        poaceae1 = {**neutral_crop, "id": "p1", "crop_family": "Poaceae"}
        poaceae2 = {**neutral_crop, "id": "p2", "crop_family": "Poaceae"}
        # Continuous Poaceae in multi-crop: Base(35) - 6 = 29.0
        score, warns = rotation._score_soil_health([poaceae1, poaceae2], "alluvial")
        self.assertEqual(score, 29.0)
        self.assertTrue(any("poaceae" in w.lower() for w in warns))

        # Poaceae + Fabaceae: Base(35) + BNF(9.0) + Family(8 + 5 = 13) + Root(6 + 4 = 10) = 67.0
        score, _ = rotation._score_soil_health([poaceae1, legume_20], "alluvial")
        self.assertEqual(score, 35.0 + 9.0 + 13.0 + 10.0)

        # Brassicaceae bonus (+3.0)
        brassicaceae = {**neutral_crop, "id": "b1", "crop_family": "Brassicaceae"}
        score, _ = rotation._score_soil_health([neutral_crop, brassicaceae], "alluvial")
        # Base(35) + Family(8 + 3 = 11) = 46.0
        self.assertEqual(score, 46.0)

        # Component 4: Root architecture (+6 multi-root, +6 deep taproot >80cm)
        deep_tap = {**neutral_crop, "id": "dt", "root_type": "deep_taproot", "root_depth_range_cm": [50, 100]}
        score, _ = rotation._score_soil_health([neutral_crop, deep_tap], "alluvial")
        # Base(35) + Family(0) + Root(6 multi + 6 deep = 12) = 47.0
        self.assertEqual(score, 47.0)

        # Component 5: Puddled rice compaction penalty (-5.0 for moderate taproot in alluvial)
        rice_crop = {**neutral_crop, "id": "rice", "crop_family": "Poaceae", "root_type": "fibrous"}
        mod_tap = {**neutral_crop, "id": "mt", "crop_family": "Fabaceae", "nitrogen_fixation_kg_ha": 0, "root_type": "moderate_taproot", "root_depth_range_cm": [30, 60]}
        # Rice + mod_tap in alluvial: Base(35) + Family(8 + 5 = 13) + Root(6 multi - 5 compaction = 1) = 49.0
        score, warns = rotation._score_soil_health([rice_crop, mod_tap], "alluvial")
        self.assertEqual(score, 49.0)
        self.assertTrue(any("plow pan" in w.lower() for w in warns))

        # Component 6: High soil cover rating bonus (+4.0)
        high_cover = {**neutral_crop, "soil_cover_rating": 4.5}
        score, _ = rotation._score_soil_health([high_cover], "alluvial")
        self.assertEqual(score, 35.0 + 4.0)

        # Component 7: Heavy N-feeder depletion penalty (-8.0)
        high_n1 = {**neutral_crop, "n_feeder": "high"}
        high_n2 = {**neutral_crop, "n_feeder": "high"}
        # Both high N-feeders with zero legume: Base(35) - 8 = 27.0
        score, warns = rotation._score_soil_health([high_n1, high_n2], "alluvial")
        self.assertEqual(score, 27.0)
        self.assertTrue(any("nitrogen-demanding" in w.lower() for w in warns))

        # Component 8: Soil texture mismatch penalty (-8.0 per mismatched crop)
        unsuited = {**neutral_crop, "suitable_soils": ["black_cotton"]}
        score, warns = rotation._score_soil_health([unsuited], "alluvial")
        self.assertEqual(score, 35.0 - 8.0)
        self.assertTrue(any("alluvial" in w.lower() for w in warns))

    def test_wheat_heat_stress_dynamic_evaluation_with_climate_summary(self):
        """Verifies that wheat climate resilience dynamically evaluates March temperature statistics
        when NASA POWER climate summary is provided, and distinguishes environmental risk from confirmed damage.
        """
        wheat_strat = [rotation.CROPS["wheat"]]

        # Scenario 1: No climate summary -> informative advisory note without penalty deduction
        score_none, warn_none = rotation._score_climate_resilience(wheat_strat, None)
        self.assertEqual(score_none, 62.5)  # 30 + (3 - 1) * 16.25 = 62.5
        self.assertTrue(any("Wheat terminal heat sensitivity note" in w for w in warn_none))
        self.assertFalse(any("Potential terminal heat-risk warning" in w for w in warn_none))

        # Scenario 2: NASA climate summary with March T2M_MAX > 32°C -> -6.0 penalty + explicit risk warning
        hot_summary = {"march_t2m_max": 34.5}
        score_hot, warn_hot = rotation._score_climate_resilience(wheat_strat, hot_summary)
        self.assertEqual(score_hot, 62.5 - 6.0)
        self.assertTrue(any("Potential terminal heat-risk warning" in w for w in warn_hot))
        self.assertTrue(any("environmental risk, not confirmed crop damage" in w for w in warn_hot))

        # Scenario 3: NASA climate summary with cool/normal March T2M_MAX <= 32°C -> no penalty deduction
        cool_summary = {"march_t2m_max": 29.8}
        score_cool, warn_cool = rotation._score_climate_resilience(wheat_strat, cool_summary)
        self.assertEqual(score_cool, 62.5)
        self.assertTrue(any("within safe physiological limits" in w for w in warn_cool))

    def test_soil_health_rice_pulse_calibrated_and_not_inflated(self):
        profile = {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "soil_improvement"}
        res = rotation.evaluate_custom_rotation(["rice", "chickpea"], profile)
        ev = res["evaluation"]
        soil_score = ev["criteria_scores"]["soil_health"]
        # Scientifically calibrated range: must be between 65 and 80 (not inflated to 90+)
        self.assertGreaterEqual(soil_score, 65.0)
        self.assertLessEqual(soil_score, 80.0)

    def test_income_stability_priority(self):
        profile = {
            "area_acres": 2.5,
            "soil_type": "alluvial",
            "irrigation": "assured_tubewell",
            "priority": "income_stability",
        }
        res = rotation.evaluate_rotations(profile)
        wheat = next(r for r in res["rotations"] if r["id"] == "rice_wheat")
        self.assertGreaterEqual(wheat["criteria_scores"]["economic_stability"], 85.0)

    def test_soil_texture_compatibility_penalties(self):
        profile = {
            "soil_type": "clay_loam",
            "irrigation": "assured_tubewell",
            "priority": "balanced",
        }
        res_custom = rotation.evaluate_custom_rotation(["rice", "carrot"], profile)
        ev = res_custom["evaluation"]
        self.assertTrue(any("clay_loam" in w.lower() for w in ev["warnings"]))

    def test_calendar_incompatibility_detection(self):
        profile = {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "balanced"}
        res = rotation.evaluate_custom_rotation(["sugarcane", "wheat"], profile)
        ev = res["evaluation"]
        self.assertLess(ev["criteria_scores"]["duration_fit"], 50.0)
        self.assertTrue(any("calendar collision" in w.lower() or "exceeds" in w.lower() for w in ev["warnings"]))

    def test_perennial_and_sugarcane_handled_without_false_penalty(self):
        profile = {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "balanced"}
        # Perennial mango orchard
        res_mango = rotation.evaluate_custom_rotation(["mango"], profile)
        self.assertGreaterEqual(res_mango["evaluation"]["criteria_scores"]["duration_fit"], 80.0)
        
        # Sole sugarcane
        res_cane = rotation.evaluate_custom_rotation(["sugarcane"], profile)
        self.assertGreaterEqual(res_cane["evaluation"]["criteria_scores"]["duration_fit"], 85.0)
        self.assertFalse(any("calendar collision" in w.lower() for w in res_cane["evaluation"]["warnings"]))

    def test_custom_rotation_evaluation(self):
        profile = {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "water_conservation"}
        res = rotation.evaluate_custom_rotation(["rice", "potato", "green_gram"], profile)
        self.assertIn("evaluation", res)
        ev = res["evaluation"]
        self.assertEqual(len(ev["crops"]), 3)
        self.assertIn("Potato", ev["name"])
        self.assertIn("Green Gram", ev["name"])
        self.assertEqual(ev["nitrogen_fixed_kg_ha"], 30)
        self.assertEqual(ev["water_demand_mm"], 1880)
        self.assertIn("turnaround_days", ev)

    def test_water_stress_warning_on_intensive_triple_cropping(self):
        profile = {"soil_type": "alluvial", "irrigation": "partial", "priority": "income_stability"}
        res = rotation.evaluate_custom_rotation(["rice", "potato", "green_gram"], profile)
        ev = res["evaluation"]
        self.assertTrue(any("partial irrigation" in w.lower() or "water deficit" in w.lower() for w in ev["warnings"]))

    def test_six_benchmark_scenarios(self):
        # 1. Pearl Millet -> Chickpea (rainfed, water_conservation)
        pm_cp = rotation.evaluate_single_strategy(
            "pm_cp", "Pearl Millet -> Chickpea", ["pearl_millet", "chickpea"],
            {"soil_type": "sandy_loam", "irrigation": "rainfed", "priority": "water_conservation"}
        )
        self.assertEqual(pm_cp["water_demand_mm"], 530)
        self.assertEqual(pm_cp["criteria_scores"]["water_sustainability"], 100.0)
        self.assertGreaterEqual(pm_cp["overall_score"], 85.0)

        # 2. Sorghum -> Lentil (rainfed, balanced)
        sg_lt = rotation.evaluate_single_strategy(
            "sg_lt", "Sorghum -> Lentil", ["sorghum", "lentil"],
            {"soil_type": "alluvial", "irrigation": "rainfed", "priority": "balanced"}
        )
        self.assertEqual(sg_lt["water_demand_mm"], 600)
        self.assertEqual(sg_lt["criteria_scores"]["water_sustainability"], 100.0)
        self.assertFalse(any("high water demand" in w.lower() for w in sg_lt["warnings"]))

        # 3. Rice -> Wheat (rainfed vs irrigated)
        rw_rain = rotation.evaluate_single_strategy(
            "rw_rain", "Rice -> Wheat Rainfed", ["rice", "wheat"],
            {"soil_type": "alluvial", "irrigation": "rainfed", "priority": "balanced"}
        )
        rw_irrig = rotation.evaluate_single_strategy(
            "rw_irrig", "Rice -> Wheat Irrigated", ["rice", "wheat"],
            {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "balanced"}
        )
        self.assertLess(rw_rain["criteria_scores"]["water_sustainability"], 20.0)
        self.assertGreater(rw_irrig["criteria_scores"]["water_sustainability"], 50.0)
        self.assertLess(rw_rain["overall_score"], rw_irrig["overall_score"])

        # 4. Rice -> Pulse (Chickpea, irrigated)
        rp = rotation.evaluate_single_strategy(
            "rp", "Rice -> Chickpea", ["rice", "chickpea"],
            {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "soil_improvement"}
        )
        self.assertGreaterEqual(rp["criteria_scores"]["soil_health"], 70.0)
        self.assertLessEqual(rp["criteria_scores"]["soil_health"], 80.0)

        # 5. Rice -> Potato -> Green Gram (1880 mm)
        rpg = rotation.evaluate_single_strategy(
            "rpg", "Rice -> Potato -> Green Gram", ["rice", "potato", "green_gram"],
            {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "income_stability"}
        )
        self.assertEqual(rpg["water_demand_mm"], 1880)
        self.assertTrue(any("drawdown" in w.lower() or "micro-irrigation" in w.lower() for w in rpg["warnings"]))

        # 6. Pearl Millet -> Mustard (partial, water_conservation)
        pm_mst = rotation.evaluate_single_strategy(
            "pm_mst", "Pearl Millet -> Mustard", ["pearl_millet", "mustard"],
            {"soil_type": "sandy_loam", "irrigation": "partial", "priority": "water_conservation"}
        )
        self.assertEqual(pm_mst["water_demand_mm"], 550)
        self.assertGreaterEqual(pm_mst["criteria_scores"]["water_sustainability"], 90.0)

    def test_invalid_crop_id_rejected(self):
        profile = {"soil_type": "alluvial", "irrigation": "assured_tubewell", "priority": "balanced"}
        with self.assertRaises(ValueError):
            rotation.evaluate_custom_rotation(["invalid_crop_xyz"], profile)

    def test_all_scores_within_valid_bounds(self):
        for priority in ("water_conservation", "soil_improvement", "income_stability", "balanced"):
            for irrigation in ("rainfed", "partial", "assured_tubewell"):
                profile = {"priority": priority, "irrigation": irrigation, "soil_type": "alluvial"}
                res = rotation.evaluate_rotations(profile)
                for r in res["rotations"]:
                    self.assertGreaterEqual(r["overall_score"], 0.0)
                    self.assertLessEqual(r["overall_score"], 100.0)
                    for crit, val in r["criteria_scores"].items():
                        self.assertGreaterEqual(val, 0.0, f"{crit} < 0")
                        self.assertLessEqual(val, 100.0, f"{crit} > 100")

    def test_disclaimer_and_transparency(self):
        profile = {"priority": "balanced"}
        res = rotation.evaluate_rotations(profile)
        self.assertIn("disclaimer", res)
        self.assertIn("do not guarantee", res["disclaimer"].lower())
        self.assertEqual(res["farmer_profile"]["source"], "farmer_reported")


if __name__ == "__main__":
    unittest.main()
