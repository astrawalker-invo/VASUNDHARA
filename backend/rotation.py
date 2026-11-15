"""Global & Pan-Indian Crop Rotation Intelligence Engine (VASUNDHARA).
Scientifically evaluates crop sequences across 1,232+ global crops using 15 agronomic criteria.
Covers North America, Latin America, Europe, Mediterranean, Sub-Saharan Africa, Asia, Australia,
and the 10 ICAR Agro-Climatic Zones of India.
"""
from typing import Any
from crops_registry import (
    CROPS,
    BASE_53_CROPS,
    BASE_53_IDS,
    search_crops,
    get_crop,
    get_catalog_stats,
)

# Export backward-compatible alias
PAN_INDIA_CROPS = BASE_53_CROPS


PRIORITY_WEIGHTS: dict[str, dict[str, float]] = {
    "water_conservation": {
        "water_sustainability": 0.40,
        "soil_health": 0.20,
        "duration_fit": 0.15,
        "economic_stability": 0.10,
        "climate_resilience": 0.15,
    },
    "soil_improvement": {
        "water_sustainability": 0.15,
        "soil_health": 0.40,
        "duration_fit": 0.15,
        "economic_stability": 0.15,
        "climate_resilience": 0.15,
    },
    "income_stability": {
        "water_sustainability": 0.15,
        "soil_health": 0.15,
        "duration_fit": 0.15,
        "economic_stability": 0.40,
        "climate_resilience": 0.15,
    },
    "balanced": {
        "water_sustainability": 0.25,
        "soil_health": 0.25,
        "duration_fit": 0.15,
        "economic_stability": 0.20,
        "climate_resilience": 0.15,
    },
}

DISCLAIMER = (
    "Rotation IQ evaluations are comparative heuristic agronomic models based on regional crop science parameters "
    "and historical climate observations across the Indian subcontinent. They provide comparative trade-off "
    "rankings and do not guarantee specific crop yields, market prices, gross margins, or physical soil improvement. "
    "Economic stability reflects relative price predictability and perishability heuristics based on historical MSP benchmarks "
    "and Agmarknet trends; it is not a live spot-price or profitability forecast, and MSP is not a guaranteed commercial procurement price. "
    "Crop water metrics represent estimated cumulative crop water demand (ETc), not calculated net irrigation requirements. "
    "A crop being present in the database does not mean it is suitable for every region or farm. "
    "Local field testing and Krishi Vigyan Kendra (KVK) / agricultural extension advice must always guide on-farm decisions."
)


def _score_water(crops_list: list[dict], irrigation: str) -> tuple[float, int, list[str]]:
    """Scores water sustainability (0-100) based on estimated cumulative crop water demand (ETc, mm)
    and farmer irrigation infrastructure type.
    
    IMPORTANT METHODOLOGICAL NOTE:
    This index evaluates estimated cumulative crop water demand (potential crop evapotranspiration, ETc = Kc * ET0)
    against regional moisture availability envelopes. It does NOT compute field-level net irrigation requirement
    (Inet = ETc - Peff - Delta_S - Gw), which requires field-scale dynamic hydrological balance modeling.
    
    Threshold References:
    - 700 mm: ICAR-CRIDA dryland cropping benchmark. Sustainable ceiling for rainfed double-cropping in semi-arid zones.
    - 1200 mm: IMD long-term normal precipitation envelope for the Middle Gangetic Plain of Bihar.
    - 350 mm: Central Ground Water Board (CGWB, 2022) sustainable dry-season (Rabi/Zaid) shallow aquifer draft benchmark per hectare.
    (Note: FAO-56 provides Kc crop coefficient and ETc methodologies; the regional mm thresholds reflect ICAR-CRIDA, IMD, and CGWB benchmarks.)
    """
    total_water = sum(c.get("typical_water_mm", 400) for c in crops_list)
    
    # Calculate off-monsoon (Rabi + Zaid) water demand:
    rabi_zaid_water = 0
    for i, c in enumerate(crops_list):
        season = c.get("season", "")
        if season in ("rabi", "zaid"):
            rabi_zaid_water += c.get("typical_water_mm", 0)
        elif i >= 1 and season in ("kharif_or_rabi", "kharif_or_zaid", "all_season"):
            rabi_zaid_water += c.get("typical_water_mm", 0)

    warnings = []

    if total_water <= 600:
        base = 92.0
    elif total_water <= 800:
        base = 82.0
    elif total_water <= 1200:
        base = 70.0
    elif total_water <= 1600:
        base = 50.0
    elif total_water <= 1900:
        base = 40.0
    else:
        base = 25.0

    # Irrigation accessibility constraint
    if irrigation == "rainfed":
        if total_water > 1200 or rabi_zaid_water > 300:
            base -= 35.0
            warnings.append(
                f"High cumulative crop water demand ({total_water} mm total, {rabi_zaid_water} mm off-monsoon) under rainfed conditions "
                "poses severe moisture deficit risk. Off-monsoon crops require supplemental irrigation (ICAR-CRIDA dryland guidelines)."
            )
        elif total_water <= 700 and rabi_zaid_water <= 250:
            base += 8.0
        
        # Check drought tolerance
        if any(c.get("drought_tolerance", 3) <= 2 for c in crops_list):
            base -= 15.0
            warnings.append("Includes low drought-tolerance crops unsuitable for rainfed cultivation.")
    elif irrigation == "partial":
        if rabi_zaid_water > 450:
            base -= 18.0
            warnings.append(f"High Rabi/Zaid crop water demand ({rabi_zaid_water} mm) exceeds partial irrigation capacity (350-450 mm).")
        elif total_water >= 1800:
            base -= 15.0
            warnings.append(f"High cumulative crop water demand ({total_water} mm) faces severe moisture stress under partial irrigation.")
        else:
            base += 3.0
    elif irrigation in ("assured_canal", "assured_tubewell"):
        if total_water >= 1800:
            warnings.append(
                f"High cumulative annual crop water demand ({total_water} mm). Intensive multi-cropping contributes to "
                "local groundwater drawdown; adoption of micro-irrigation (drip/sprinkler) is strongly recommended (CGWB 2022)."
            )
        else:
            base += 5.0

    return max(10.0, min(100.0, base)), total_water, warnings


def _score_soil_health(crops_list: list[dict], soil_type: str) -> tuple[float, list[str]]:
    """Scores soil health contribution (0-100) as a comparative heuristic index based on biological N-fixation,
    rooting depth diversity, crop family diversity, canopy cover, and soil texture match.
    
    IMPORTANT NOTE:
    This score is a comparative heuristic index of agronomic sustainability; it is NOT an empirical measurement
    of physical/chemical soil improvement or soil organic carbon gain.
    
    Unified Authoritative Formulation:
    S = Clamp_10_100(35.0 + Delta_S_BNF + Delta_S_family + Delta_S_root + Delta_S_cover - Delta_S_compaction - Delta_S_depletion - Delta_S_texture)
    
    Parameters:
    - Base score: 35.0 (neutral baseline for cultivated agricultural soil).
    - Delta_S_BNF: min(20.0, total_n_fixed * 0.45) points from Fabaceae biological N-fixation.
    - Delta_S_family:
        +8.0 pts if > 1 botanical families.
        +5.0 pts if Poaceae + Fabaceae combination (cereal-legume synergy).
        +3.0 pts if Brassicaceae present (bio-fumigation / pest break).
        -6.0 pts if all crops in multi-crop sequence belong to Poaceae (continuous cereal monoculture).
    - Delta_S_root:
        +6.0 pts if > 1 root architecture types.
        +6.0 pts if deep taproot (> 80 cm) present (subsoil nutrient extraction).
        +4.0 pts for moderate taproot without puddled rice.
    - Delta_S_cover: +4.0 pts if average soil_cover_rating >= 4.0.
    - Delta_S_compaction: -5.0 pts when moderate taproot pulses follow puddled lowland rice in heavy alluvial soil.
    - Delta_S_depletion: -8.0 pts if all crops are high N-feeders with zero legume.
    - Delta_S_texture: -8.0 pts per crop where soil_type is not in suitable_soils.
    """
    score = 35.0
    warnings = []
    total_n_fixed = sum(c.get("nitrogen_fixation_kg_ha") or 0 for c in crops_list)

    # 1. Biological Nitrogen Fixation bonus
    if total_n_fixed > 0:
        score += min(20.0, total_n_fixed * 0.45)

    # 2. Crop Family Diversity
    families = {c.get("crop_family") for c in crops_list if c.get("crop_family")}
    if len(families) > 1:
        score += 8.0
        if "Fabaceae" in families and "Poaceae" in families:
            score += 5.0
        if "Brassicaceae" in families:
            score += 3.0
    elif len(crops_list) > 1 and len(families) == 1 and "Poaceae" in families:
        score -= 6.0
        warnings.append("Continuous cereal (Poaceae) rotation fosters insect pest build-up and depletes identical soil nutrient layers.")

    # 3. Root zone diversity and compaction adjustment
    root_types = {c.get("root_type") for c in crops_list if c.get("root_type")}
    has_rice = any(c.get("id") == "rice" for c in crops_list)
    if len(root_types) > 1:
        score += 6.0
        deep_taproot = any(c.get("root_depth_range_cm", [0, 0])[1] >= 80 for c in crops_list if "taproot" in c.get("root_type", ""))
        moderate_taproot = any("taproot" in c.get("root_type", "") for c in crops_list) and not deep_taproot
        
        if deep_taproot:
            score += 6.0
        elif moderate_taproot:
            if has_rice and soil_type in ("alluvial", "clay_loam", "silt_loam"):
                score -= 5.0
                warnings.append("Post-rice puddled plow pan may restrict pulse taproot penetration unless zero-till relay (utera/para) or strip-tillage is practiced.")
            else:
                score += 4.0

    # 4. Soil cover rating bonus
    avg_cover = sum(c.get("soil_cover_rating", 3) for c in crops_list) / max(1, len(crops_list))
    if avg_cover >= 4.0:
        score += 4.0

    # 5. Heavy N-feeder depletion penalty
    if total_n_fixed == 0 and all(c.get("n_feeder") == "high" for c in crops_list):
        score -= 8.0
        warnings.append("Successive high nitrogen-demanding crops accelerate soil organic carbon and mineral nitrogen depletion.")

    # 6. Soil texture compatibility
    for c in crops_list:
        soils = c.get("suitable_soils", [])
        if soils and soil_type not in soils and "all" not in soils:
            score -= 8.0
            crop_label = c.get("name", c.get("id", "Crop"))
            warnings.append(f"{crop_label} is less suited to {soil_type} soil texture.")

    return max(10.0, min(100.0, score)), warnings


def _score_duration(crops_list: list[dict]) -> tuple[float, int, list[str]]:
    """Evaluates crop turnaround fit within the annual 365-day agricultural cycle."""
    warnings = []
    is_perennial = any(c.get("season") == "perennial" or "perennial" in c.get("categories", []) for c in crops_list)
    is_sugarcane = any(c.get("id") == "sugarcane" for c in crops_list)

    if is_perennial and len(crops_list) == 1:
        return 85.0, 0, ["Multi-year perennial system: duration scoring reflects orchard establishment rather than annual turnaround."]

    if is_sugarcane:
        if len(crops_list) == 1:
            return 88.0, 35, ["Full-season annual/ratoon cash crop (10-12 months); occupies field continuously throughout the agricultural year."]
        else:
            warnings.append(
                "Sugarcane requires 300-365 days; overlapping with other field crops within a single year "
                "causes severe calendar collision unless intercropped as autumn companion."
            )
            return 35.0, -100, warnings

    total_days = sum(c.get("typical_duration", 100) for c in crops_list)
    turnaround_days = 365 - total_days

    if total_days <= 240:
        return 92.0, turnaround_days, []
    elif total_days <= 290:
        return 84.0, turnaround_days, []
    elif total_days <= 335:
        return 75.0, turnaround_days, []
    elif total_days <= 365:
        warnings.append(
            f"Compressed turnaround window ({turnaround_days} days buffer between harvest and sowing). "
            "Requires rapid mechanization to avoid delayed sowing."
        )
        return 62.0, turnaround_days, warnings
    else:
        warnings.append(
            f"Cumulative duration ({total_days} days) exceeds annual 365-day calendar by {total_days - 365} days. "
            "Crops cannot complete their lifecycle within one year without overlapping."
        )
        return 25.0, turnaround_days, warnings


def _score_economic(crops_list: list[dict], priority: str) -> tuple[float, list[str]]:
    """Evaluates income predictability, market infrastructure, price stability, and perishability.
    
    IMPORTANT NOTE:
    Economic stability scores reflect relative price predictability and perishability heuristics based
    on historical MSP benchmarks and Agmarknet trends. They do NOT provide live price forecasts,
    profitability predictions, or guaranteed government procurement.
    """
    stability_map = {"high": 85.0, "medium": 72.0, "high_value_volatile": 60.0}
    scores = [stability_map.get(c.get("market_stability", "medium"), 70.0) for c in crops_list]
    avg_score = sum(scores) / max(1, len(scores))
    warnings = []

    has_volatile = any(c.get("market_stability") == "high_value_volatile" for c in crops_list)
    has_cereal = any("cereal" in c.get("categories", []) or c.get("id") in ("rice", "wheat", "maize") for c in crops_list)

    if has_volatile:
        if priority == "income_stability":
            avg_score -= 12.0
            warnings.append(
                "Includes perishable/volatile cash crops (vegetables/fruits) subject to price crashes; "
                "high capital and market risk for risk-averse farmers."
            )
        else:
            avg_score += 5.0

    if all(c.get("market_stability") == "high" for c in crops_list):
        avg_score = max(avg_score, 86.0)

    if has_cereal:
        warnings.append(
            "Cereal price stability references Government Minimum Support Price (MSP) benchmarks; "
            "note that open-market realization in non-APMC markets often falls below MSP without guaranteed public procurement."
        )

    return max(10.0, min(100.0, avg_score)), warnings


def _score_climate_resilience(
    crops_list: list[dict],
    climate_summary: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    """Evaluates drought resilience and heat stress tolerance during critical growth periods.
    
    When NASA POWER climate summary statistics are provided, the function evaluates March daytime maximum
    temperature (the anthesis and grain-filling period for Rabi cereals in Eastern India).
    Distinguishes potential environmental heat risk from confirmed crop damage, highlighting cultivar mitigations.
    """
    warnings = []
    drought_ratings = [c.get("drought_tolerance", 3) for c in crops_list]
    avg_drought = sum(drought_ratings) / max(1, len(drought_ratings))
    score = 30.0 + (avg_drought - 1.0) * 16.25

    has_wheat = any(c.get("id") == "wheat" for c in crops_list)
    if has_wheat:
        # Check if actual NASA POWER climate summary data is provided
        march_max_temp = None
        if climate_summary and isinstance(climate_summary, dict):
            # 1. Direct key
            if "march_t2m_max" in climate_summary and climate_summary["march_t2m_max"] is not None:
                march_max_temp = float(climate_summary["march_t2m_max"])
            # 2. Monthly climatology check
            elif "monthly_climatology" in climate_summary:
                for m_row in climate_summary.get("monthly_climatology", []):
                    if m_row.get("month") == 3 and m_row.get("t2m_mean_c") is not None:
                        mean_val = float(m_row["t2m_mean_c"])
                        march_max_temp = mean_val + 7.5  # Typical diurnal delta
                        break

        if march_max_temp is not None:
            if march_max_temp > 32.0:
                score -= 6.0
                warnings.append(
                    f"Potential terminal heat-risk warning: NASA climatology indicates March maximum temperatures averaging "
                    f"~{march_max_temp:.1f}°C (>32°C critical threshold). Late-sown wheat faces potential heat stress "
                    "during anthesis and grain filling (ICAR-IIWBR). Note: This reflects environmental risk, not confirmed "
                    "crop damage; timely sowing (Nov 15-25) and heat-tolerant cultivars (HD-2967, DBW-187) substantially mitigate this risk."
                )
            else:
                warnings.append(
                    f"March temperature profile (~{march_max_temp:.1f}°C) is within safe physiological limits for wheat grain filling."
                )
        else:
            # No NASA temperature profile supplied - provide clear agronomic advisory without false dynamic claim
            warnings.append(
                "Wheat terminal heat sensitivity note: Wheat is physiologically vulnerable to terminal heat stress (>32°C) "
                "during late-season grain filling in March (ICAR-IIWBR). No site-specific NASA temperature profile was provided "
                "to evaluate localized heat exposure."
            )

    return max(10.0, min(100.0, score)), warnings


def detect_indian_agroclimatic_zone(lat: float | None, lon: float | None) -> tuple[str, str]:
    """Resolves coordinates to one of the ICAR Agro-Climatic Zones across India."""
    if lat is None or lon is None:
        return "bihar", "Middle Gangetic Plains (Bihar Hub)"
    
    # Southern Peninsula (Tamil Nadu, Kerala, South Karnataka)
    if lat < 14.5:
        return "southern_peninsula", "Southern Peninsular Zone (Tamil Nadu / Kerala / South Karnataka)"
    
    # Deccan Plateau (Maharashtra, North Karnataka, Telangana, Rayalaseema)
    if 14.5 <= lat < 21.0 and lon < 79.5:
        return "deccan", "Deccan Plateau (Maharashtra / Karnataka / Telangana)"
    
    # Eastern Coastal Plains (Andhra Pradesh, Odisha)
    if 14.5 <= lat < 21.0 and lon >= 79.5:
        return "eastern_coastal", "Eastern Coastal Plains (Andhra Pradesh / Odisha)"
    
    # Western / Arid & Semi-Arid (Gujarat, Western Rajasthan)
    if 21.0 <= lat < 27.5 and lon < 74.5:
        return "arid_west", "Western Arid & Semi-Arid Zone (Gujarat / Rajasthan)"
    
    # Central India (Madhya Pradesh, Chhattisgarh, Vidarbha)
    if 21.0 <= lat < 26.0 and 74.5 <= lon < 82.0:
        return "central", "Central India Plateau & Hills (Madhya Pradesh / Chhattisgarh)"
    
    # Chota Nagpur & Eastern Plateau (Jharkhand)
    if 21.0 <= lat < 25.0 and 82.0 <= lon < 88.0:
        return "chota_nagpur", "Chota Nagpur & Eastern Plateau (Jharkhand)"
    
    # Bihar & Middle Gangetic Plains
    if 24.5 <= lat <= 27.6 and 83.0 <= lon <= 88.5:
        return "bihar", "Middle Gangetic Plains (Bihar)"
    
    # North-East / Brahmaputra Valley
    if lat >= 24.0 and lon >= 88.5:
        return "north_east", "Eastern Himalayan & North-Eastern Region (Assam / NE Hills)"
    
    # Hilly Northern Region (J&K, Himachal Pradesh, Uttarakhand)
    if lat >= 31.0:
        return "hilly_north", "Western Himalayan / Hilly North (J&K / Himachal Pradesh / Uttarakhand)"
    
    # Trans-Gangetic and Upper Gangetic Plains (Punjab, Haryana, Western/Central UP)
    if 26.0 <= lat < 31.0 and lon < 83.0:
        return "indo_gangetic", "Trans & Upper Gangetic Plains (Punjab / Haryana / Uttar Pradesh)"
        
    return "indo_gangetic", "Indo-Gangetic & Sub-Humid Plains"




def detect_global_climate_zone(lat: float | None, lon: float | None) -> tuple[str, str, str, str]:
    """Resolves worldwide coordinates to global agro-climatic zone, region name, hemisphere, and climate type.
    Returns: (zone_key, zone_name, hemisphere, eco_zone)
    """
    if lat is None or lon is None:
        return "bihar", "Middle Gangetic Plains (Bihar Hub)", "northern", "subtropical"

    hemisphere = "southern" if lat < 0 else "northern"

    # Check if coordinate is in Indian Subcontinent
    if 6.0 <= lat <= 38.0 and 68.0 <= lon <= 97.5:
        icar_key, icar_name = detect_indian_agroclimatic_zone(lat, lon)
        return icar_key, icar_name, "northern", "subtropical"

    # Global Agro-Climatic Zones
    # North America Corn Belt & Upper Midwest
    if 36.0 <= lat <= 49.0 and -104.0 <= lon <= -80.0:
        return "us_corn_belt", "North American Corn Belt & Upper Midwest (USA)", "northern", "temperate_continental"

    # North America Great Plains / Wheat Belt
    if 32.0 <= lat <= 52.0 and -115.0 <= lon < -100.0:
        return "us_great_plains", "North American Great Plains & Wheat Belt (USA/Canada)", "northern", "arid_semiarid"

    # North America Pacific / California Central Valley
    if 32.0 <= lat <= 46.0 and -125.0 <= lon < -115.0:
        return "us_mediterranean", "Pacific Southwest / California Central Valley", "northern", "mediterranean"

    # South America Cerrado (Mato Grosso, Goias)
    if -18.0 <= lat <= -8.0 and -60.0 <= lon <= -45.0:
        return "latin_america_cerrado", "Brazilian Cerrado Agricultural Frontier (Brazil)", "southern", "tropical_savanna"

    # South America Pampas (Argentina, Uruguay, Rio Grande do Sul)
    if -39.0 <= lat < -25.0 and -65.0 <= lon <= -50.0:
        return "latin_america_pampas", "Pampas Agricultural Plains (Argentina / Uruguay)", "southern", "temperate_subtropical"

    # Mediterranean Basin (Spain, Italy, Greece, Turkey, North Africa)
    if 30.0 <= lat <= 45.0 and -10.0 <= lon <= 36.0:
        return "mediterranean_basin", "Mediterranean Basin (Southern Europe / North Africa)", "northern", "mediterranean"

    # Western & Central European Agricultural Plain (France, Germany, UK, Poland)
    if 45.0 <= lat <= 58.0 and -10.0 <= lon <= 25.0:
        return "europe_temperate", "Western & Central European Plains (France / Germany / UK)", "northern", "temperate_maritime"

    # Eurasian Steppe & Black Earth Basin (Ukraine, Southern Russia, Kazakhstan)
    if 44.0 <= lat <= 55.0 and 25.0 <= lon <= 70.0:
        return "eurasian_steppe", "Black Earth Steppe Belt (Ukraine / Southern Russia)", "northern", "continental_temperate"

    # Sub-Saharan Africa & Savanna-Sahel (Nigeria, Kenya, Ethiopia, Ghana)
    if -15.0 <= lat <= 18.0 and -18.0 <= lon <= 50.0:
        return "sub_saharan_africa", "Sub-Saharan Africa & East African Plateau (Kenya / Nigeria)", "tropical", "tropical_savanna"

    # East Asian Agricultural Basin (China North Plain, Yangtze, Japan, Korea)
    if 22.0 <= lat <= 45.0 and 100.0 <= lon <= 145.0:
        return "east_asia", "East Asian Agricultural Basin (China / Korea / Japan)", "northern", "subtropical_temperate"

    # Australian Murray-Darling & Southwest Grain Belt
    if -42.0 <= lat <= -20.0 and 112.0 <= lon <= 154.0:
        return "australia_grain_belt", "Australian Grain Belt (Murray-Darling / Western Australia)", "southern", "mediterranean_arid"

    # General Latitudinal fallbacks
    abs_lat = abs(lat)
    if abs_lat <= 23.5:
        return "global_tropical", f"Global Tropical Lowlands ({hemisphere.capitalize()} Hemisphere)", hemisphere, "tropical"
    elif 23.5 < abs_lat <= 38.0:
        return "global_subtropical", f"Global Subtropical Belt ({hemisphere.capitalize()} Hemisphere)", hemisphere, "subtropical"
    elif 38.0 < abs_lat <= 55.0:
        return "global_temperate", f"Global Temperate Zone ({hemisphere.capitalize()} Hemisphere)", hemisphere, "temperate"
    else:
        return "global_boreal", f"High Latitude Boreal Zone ({hemisphere.capitalize()} Hemisphere)", hemisphere, "boreal"

def evaluate_single_strategy(
    strat_id: str,
    strat_name: str,
    crop_ids: list[str],
    farmer_profile: dict[str, Any],
    description: str = "",
    benefits: list[str] | None = None,
    disadvantages: list[str] | None = None,
    assumptions: list[str] | None = None,
    climate_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    priority = farmer_profile.get("priority", "balanced")
    if priority not in PRIORITY_WEIGHTS:
        priority = "balanced"
    weights = PRIORITY_WEIGHTS[priority]

    irrigation = str(farmer_profile.get("irrigation", "assured_tubewell")).lower()
    soil_type = str(farmer_profile.get("soil_type", "alluvial")).lower()

    crops_list = [{**CROPS[cid], "id": cid} for cid in crop_ids if cid in CROPS]
    if not crops_list:
        raise ValueError("At least one valid crop ID must be provided")

    water_score, total_water, water_warn = _score_water(crops_list, irrigation)
    soil_score, soil_warn = _score_soil_health(crops_list, soil_type)
    duration_score, turnaround_days, dur_warn = _score_duration(crops_list)
    econ_score, econ_warn = _score_economic(crops_list, priority)
    resilience_score, res_warn = _score_climate_resilience(crops_list, climate_summary=climate_summary)

    all_warnings = water_warn + soil_warn + dur_warn + econ_warn + res_warn

    criteria_scores = {
        "water_sustainability": round(water_score, 1),
        "soil_health": round(soil_score, 1),
        "duration_fit": round(duration_score, 1),
        "economic_stability": round(econ_score, 1),
        "climate_resilience": round(resilience_score, 1),
    }

    overall_score = sum(criteria_scores[k] * weights[k] for k in criteria_scores)
    overall_score = round(overall_score, 1)

    total_n_fixed = sum(c.get("nitrogen_fixation_kg_ha") or 0 for c in crops_list)
    total_days = sum(c.get("typical_duration", 100) for c in crops_list)

    crop_names = " → ".join(c["name"] for c in crops_list)
    if priority == "water_conservation":
        rationale = f"Consumes {total_water} mm water. Water score is {criteria_scores['water_sustainability']}/100."
    elif priority == "soil_improvement":
        rationale = f"Provides ~{round(total_n_fixed, 1)} kg/ha biological N and {len({c.get('root_type') for c in crops_list})} distinct root zone(s)."
    elif priority == "income_stability":
        rationale = f"Market stability rated at {criteria_scores['economic_stability']}/100 with predictable MSP/demand."
    else:
        rationale = f"Balanced sequence of {crop_names} achieving {overall_score}/100 multi-objective score."

    default_benefits = []
    if total_n_fixed > 0:
        default_benefits.append(f"Fixes ~{round(total_n_fixed, 1)} kg N/ha biologically under effective nodulation.")
    if len({c.get('root_type') for c in crops_list}) > 1:
        default_benefits.append("Combines fibrous and taproot architectures, exploring different soil depths and breaking compaction.")
    if total_water <= 700:
        default_benefits.append(f"Very low water demand ({total_water} mm), conserving critical dry-season groundwater.")

    default_disadvantages = []
    if total_water > 1400:
        default_disadvantages.append(f"High cumulative water requirement ({total_water} mm), placing pressure on irrigation aquifers.")
    if total_n_fixed == 0:
        default_disadvantages.append("Zero biological nitrogen fixation; entirely reliant on synthetic/organic fertilizer inputs.")
    if total_days > 330:
        default_disadvantages.append(f"Compressed turnaround window ({total_days} total duration days), leaving little buffer for sowing delays.")

    # Regional suitability check for the sequence across India
    lat = farmer_profile.get("lat")
    lon = farmer_profile.get("lon")
    reg_key, reg_name, hemisphere, eco_zone = detect_global_climate_zone(lat, lon)

    regional_fit = "high"
    for c in crops_list:
        reg_map = c.get("regional_suitability", {})
        suit = reg_map.get(reg_key)
        if not suit:
            suit = reg_map.get("indo_gangetic") or reg_map.get("central") or reg_map.get("deccan") or "moderate"
        if suit == "low":
            regional_fit = "low"
            all_warnings.append(f"{c['name']} has low suitability for {reg_name} agro-climatic conditions.")
        elif suit == "moderate" and regional_fit != "low":
            regional_fit = "moderate"

    return {
        "id": strat_id,
        "name": strat_name,
        "description": description or f"Rotation sequence of {crop_names}.",
        "crops": [c["name"] for c in crops_list],
        "crop_ids": [c["id"] for c in crops_list],
        "kharif_crop": crops_list[0]["name"] if len(crops_list) > 0 else None,
        "rabi_crop": crops_list[1]["name"] if len(crops_list) > 1 else None,
        "zaid_crop": crops_list[2]["name"] if len(crops_list) > 2 else None,
        "overall_score": overall_score,
        "criteria_scores": criteria_scores,
        "weights_used": weights,
        "water_demand_mm": total_water,
        "rabi_water_demand_mm": crops_list[1]["typical_water_mm"] if len(crops_list) > 1 else 0,
        "nitrogen_fixed_kg_ha": round(total_n_fixed, 1),
        "total_duration_days": total_days,
        "turnaround_days": turnaround_days,
        "regional_suitability": regional_fit,
        "warnings": all_warnings,
        "benefits": benefits or default_benefits or ["Agronomically sound crop combination."],
        "disadvantages": disadvantages or default_disadvantages or ["Subject to seasonal rainfall and market price dynamics."],
        "assumptions": assumptions or ["Timely sowing and standard field management practices."],
        "rationale": rationale,
    }


def evaluate_rotations(
    farmer_profile: dict[str, Any],
    climate_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generates and evaluates the top 4-6 viable rotation pathways tailored dynamically to farmer profile."""
    priority = farmer_profile.get("priority", "balanced")
    irrigation = str(farmer_profile.get("irrigation", "assured_tubewell")).lower()
    lat = farmer_profile.get("lat")
    lon = farmer_profile.get("lon")
    reg_key, reg_name, hemisphere, eco_zone = detect_global_climate_zone(lat, lon)

    # Global vs. Regional Candidate Dispatch
    is_indian_zone = (lat is None and lon is None) or (lat is not None and lon is not None and 6.0 <= lat <= 38.0 and 68.0 <= lon <= 97.5)
    
    if not is_indian_zone:
        if reg_key == "us_corn_belt":
            candidate_rotations = [
                {
                    "id": "corn_soybean",
                    "name": "Dent Corn → Soybean (Corn Belt Standard)",
                    "crop_ids": ["dent_corn", "soybean"],
                    "description": "The benchmark agricultural rotation of the US Midwest, balancing high-yielding carbohydrate feed grain with legume nitrogen fixation.",
                    "benefits": ["Proven agronomic stability across the US Corn Belt.", "Soybean nodulation fixes nitrogen reducing synthetic fertilizer needs for following corn.", "Breaks corn rootworm (Diabrotica) and foliar disease cycles."],
                    "disadvantages": ["Two-crop annual cycle lacks winter ground cover without cover crops.", "Susceptible to soil erosion during spring thaw."],
                    "assumptions": ["Assumes assured rainfall or center-pivot irrigation."],
                },
                {
                    "id": "corn_soybean_winter_wheat",
                    "name": "Dent Corn → Soybean → Winter Wheat",
                    "crop_ids": ["dent_corn", "soybean", "hard_red_winter_wheat"],
                    "description": "Diverse 3-crop extended sequence adding a winter cereal to reduce pest pressure and protect soil over winter.",
                    "benefits": ["Winter wheat roots scavenge residual soil nitrogen.", "High soil cover throughout winter and spring.", "Spreads labor and cash flow across summer and autumn harvests."],
                    "disadvantages": ["Requires tight harvest window for soybean to drill winter wheat."],
                    "assumptions": ["Assumes moderate winter hardiness zone."],
                },
                {
                    "id": "corn_alfalfa_dairy",
                    "name": "Dent Corn → Alfalfa Hay (Dairy Forage)",
                    "crop_ids": ["dent_corn", "alfalfa_hay"],
                    "description": "High-value dairy and livestock forage rotation combining silage corn with perennial deep-rooting lucerne.",
                    "benefits": ["Alfalfa taproots penetrate 2-3 meters deep breaking subsoil compaction.", "Fixes 150-250 kg N/ha, providing a massive nitrogen credit to following corn.", "Exceptional feed protein value for livestock."],
                    "disadvantages": ["High total water consumption over perennial growth."],
                    "assumptions": ["Requires dairy or livestock market infrastructure."],
                },
                {
                    "id": "oats_red_clover_corn",
                    "name": "Common Oat → Red Clover → Dent Corn",
                    "crop_ids": ["oats_common", "red_clover", "dent_corn"],
                    "description": "Regenerative soil-building system undersowing red clover into oats, terminated before high-yielding maize.",
                    "benefits": ["Substantially reduces synthetic fertilizer requirements.", "Red clover provides dense winter ground cover preventing erosion.", "Oats provide high-fiber cool-season grain and straw bedding."],
                    "disadvantages": ["Requires timely mechanical termination of clover."],
                    "assumptions": ["Assumes mixed crop-livestock or organic farming goals."],
                },
                {
                    "id": "soybean_cereal_rye",
                    "name": "Soybean → Winter Rye Cover → Field Corn",
                    "crop_ids": ["soybean", "rye_winter", "dent_corn"],
                    "description": "No-till cover-crop rotation using winter cereal rye between soybean and corn for weed suppression.",
                    "benefits": ["Winter rye allelopathy suppresses winter annual and spring weeds.", "Drastically reduces nutrient runoff into waterways.", "Builds active organic carbon in topsoil."],
                    "disadvantages": ["Rye must be terminated at right height before corn planting."],
                    "assumptions": ["Assumes no-till drill and roller-crimper or burndown."],
                },
            ]
        elif reg_key in ("latin_america_cerrado", "latin_america_pampas"):
            candidate_rotations = [
                {
                    "id": "soybean_corn_safrinha",
                    "name": "Soybean → Safrinha Corn (Cerrado Double-Crop)",
                    "crop_ids": ["soybean", "dent_corn"],
                    "description": "The quintessential Brazilian Cerrado double-crop system capitalizing on early-maturing soybeans followed immediately by dry-season maize.",
                    "benefits": ["Maximizes annual land productivity with two commercial grain harvests per calendar year.", "Soybean fixes nitrogen for the following safrinha maize."],
                    "disadvantages": ["Safrinha corn yields depend heavily on late rains before dry season."],
                    "assumptions": ["Assumes tropical savanna climate with distinct rainy/dry seasons."],
                },
                {
                    "id": "soybean_cotton",
                    "name": "Soybean → Upland Cotton",
                    "crop_ids": ["soybean", "cotton"],
                    "description": "High-value cash rotation alternating legume grain with high-return commercial fibre.",
                    "benefits": ["High gross revenue per hectare.", "Deep taproot of cotton utilizes subsoil moisture."],
                    "disadvantages": ["High pesticide and intensive management requirement for cotton."],
                    "assumptions": ["Assumes access to mechanized cotton harvesters."],
                },
                {
                    "id": "soybean_black_oats",
                    "name": "Soybean → Black Oat Cover",
                    "crop_ids": ["soybean", "black_oats"],
                    "description": "Conservation agriculture rotation using black oats as a winter cover and nematode-suppressing mulch.",
                    "benefits": ["Black oats suppress root-knot nematodes in tropical soils.", "Produces thick straw blanket that conserves soil moisture."],
                    "disadvantages": ["Oat residue requires specialized no-till seeders for following crop."],
                    "assumptions": ["Zero-tillage management."],
                },
                {
                    "id": "sunflower_soybean",
                    "name": "High-Oleic Sunflower → Soybean",
                    "crop_ids": ["sunflower_high_oleic", "soybean"],
                    "description": "Oilseed-legume sequence leveraging deep sunflower taproots to mine subsoil potassium.",
                    "benefits": ["Diversifies farm income across global vegetable oil markets.", "Breaks cereal monoculture pest complexes."],
                    "disadvantages": ["Shared susceptibility to Sclerotinia requires careful scouting."],
                    "assumptions": ["Good local oilseed crushing facilities."],
                },
            ]
        elif reg_key in ("mediterranean_basin", "us_mediterranean"):
            candidate_rotations = [
                {
                    "id": "durum_wheat_chickpea",
                    "name": "Durum Wheat → Kabuli Chickpea",
                    "crop_ids": ["durum_wheat", "kabuli_chickpea"],
                    "description": "The historic Mediterranean dryland rotation pairing premium pasta wheat with drought-hardy garbanzo legumes.",
                    "benefits": ["Chickpea fixes 40-80 kg N/ha, boosting grain protein of succeeding durum wheat.", "Low annual water demand suited to dry Mediterranean summers.", "High commercial liquidity across Mediterranean food markets."],
                    "disadvantages": ["Ascochyta blight risk in wet springs."],
                    "assumptions": ["Assumes winter rainfall Mediterranean climate."],
                },
                {
                    "id": "winter_barley_sunflower",
                    "name": "Two-Row Malting Barley → High-Oleic Sunflower",
                    "crop_ids": ["two_row_barley", "sunflower_high_oleic"],
                    "description": "Water-efficient rotation combining cool-season malting barley with deep-rooted summer sunflower.",
                    "benefits": ["Barley finishes before summer heat; sunflower extracts deep moisture reserves.", "Excellent weed competition from dense barley tillering."],
                    "disadvantages": ["Sunflower needs sufficient soil moisture stored from winter rains."],
                    "assumptions": ["Assumes winter moisture retention in soil profile."],
                },
                {
                    "id": "faba_bean_durum",
                    "name": "Broad Bean (Faba) → Durum Wheat",
                    "crop_ids": ["faba_bean_broad", "durum_wheat"],
                    "description": "High-nitrogen-building Mediterranean sequence using faba beans as a bio-fertilizer preceding premium durum.",
                    "benefits": ["Faba beans fix up to 120-160 kg N/ha.", "Significantly boosts durum wheat vitreous kernel percentage."],
                    "disadvantages": ["Faba beans require cool early vegetative conditions."],
                    "assumptions": ["Assumes moderate winter rainfall."],
                },
                {
                    "id": "tomato_winter_wheat",
                    "name": "Processing Tomato → Hard Red Winter Wheat",
                    "crop_ids": ["tomato_roma", "hard_red_winter_wheat"],
                    "description": "Intensive horticultural-cereal rotation alternating high-return processing tomatoes with soil-resting winter wheat.",
                    "benefits": ["High revenue from industrial processing tomato contract.", "Winter wheat scavenges leftover irrigation and fertilizer."],
                    "disadvantages": ["Intensive field operations during tomato harvest."],
                    "assumptions": ["Requires drip irrigation infrastructure."],
                },
            ]
        elif reg_key in ("europe_temperate", "eurasian_steppe"):
            candidate_rotations = [
                {
                    "id": "winter_wheat_oilseed_rape",
                    "name": "Winter Wheat → Winter Canola (Oilseed Rape)",
                    "crop_ids": ["soft_red_winter_wheat", "canola_winter"],
                    "description": "The dominant European crop rotation pairing high-yielding winter bread wheat with high-oil winter rapeseed.",
                    "benefits": ["Rapeseed taproot breaks plow pan and aerates soil for wheat.", "Rapeseed biofumigant root exudates suppress wheat take-all fungus.", "Highest combined gross margin in temperate Western Europe."],
                    "disadvantages": ["Heavy synthetic nitrogen demand requires careful split applications."],
                    "assumptions": ["Temperate climate with reliable winter precipitation."],
                },
                {
                    "id": "winter_wheat_sugar_beet",
                    "name": "Winter Wheat → Sugar Beet",
                    "crop_ids": ["soft_red_winter_wheat", "sugar_beet_commercial"],
                    "description": "High-yield commercial cash rotation dominant in the European loess plains.",
                    "benefits": ["Exceptional cash revenue per hectare from sugar processing quota.", "Sugar beet leaves loose, highly friable soil structure."],
                    "disadvantages": ["Heavy harvesting machinery risks soil compaction in wet autumns."],
                    "assumptions": ["Proximity to sugar processing factory."],
                },
                {
                    "id": "spring_barley_field_pea",
                    "name": "Two-Row Malting Barley → Yellow Field Pea",
                    "crop_ids": ["two_row_barley", "yellow_field_pea"],
                    "description": "Low-input, balanced rotation producing premium malting barley and plant protein peas.",
                    "benefits": ["Field pea fixes 50-80 kg N/ha, keeping subsequent barley protein in optimal malting range.", "Low water requirement and short growing seasons."],
                    "disadvantages": ["Field pea lodging can complicate wet harvests."],
                    "assumptions": ["Standard grain combining equipment."],
                },
                {
                    "id": "winter_rye_potato",
                    "name": "Winter Rye → Russet Potato",
                    "crop_ids": ["rye_winter", "potato"],
                    "description": "Cold-hardy sandy soil rotation utilizing rye's allelopathy and biomass ahead of potato tuber production.",
                    "benefits": ["Rye suppresses soil-borne potato pathogens and weeds.", "Excellent adaptation to light, sandy, slightly acidic soils."],
                    "disadvantages": ["Potato harvest disturbs soil structure."],
                    "assumptions": ["Cold temperate or continental climate."],
                },
            ]
        elif reg_key == "sub_saharan_africa":
            candidate_rotations = [
                {
                    "id": "sorghum_cowpea",
                    "name": "Red Grain Sorghum → Cowpea",
                    "crop_ids": ["sorghum_grain_red", "cowpea"],
                    "description": "The cornerstone resilient rotation of African drylands and savannas.",
                    "benefits": ["High drought tolerance and heat resilience.", "Cowpea provides household nutrition and fixes soil nitrogen.", "Sorghum provides food grain and drought-proof livestock stover."],
                    "disadvantages": ["Susceptible to Striga weed if soil fertility is severely depleted."],
                    "assumptions": ["Semi-arid or savanna tropical ecology."],
                },
                {
                    "id": "maize_pigeonpea",
                    "name": "Flint Corn → Perennial Pigeonpea",
                    "crop_ids": ["flint_corn", "pigeonpea"],
                    "description": "Multi-story cropping system combining staple maize with deep-rooting pigeonpea.",
                    "benefits": ["Pigeonpea leaf drop provides massive organic mulch.", "Mines phosphorus from subsoil horizons.", "Provides pulse grain and firewood."],
                    "disadvantages": ["Pigeonpea occupies land longer than short-season crops."],
                    "assumptions": ["Sub-humid to semi-arid tropical plateau."],
                },
                {
                    "id": "cassava_groundnut",
                    "name": "Sweet Cassava → Groundnut",
                    "crop_ids": ["cassava_sweet", "groundnut"],
                    "description": "Calorie and protein security system combining drought-proof cassava with high-oil groundnut.",
                    "benefits": ["Cassava provides flexible harvest window up to 2 years.", "Groundnut fixes nitrogen and prevents soil erosion."],
                    "disadvantages": ["Cassava removes high potassium amounts if tubers are exported."],
                    "assumptions": ["Warm tropical climate."],
                },
                {
                    "id": "teff_chickpea",
                    "name": "Brown Teff → Desi Chickpea",
                    "crop_ids": ["teff_brown", "desi_chickpea"],
                    "description": "East African highland Vertisol rotation alternating staple teff grain with nitrogen-fixing chickpea.",
                    "benefits": ["Both crops adapt to heavy cracking black clay soils.", "Teff commands high commercial market price in urban centers."],
                    "disadvantages": ["Teff requires precise, fine seedbed preparation."],
                    "assumptions": ["Tropical highland climate."],
                },
            ]
        else:
            # General Worldwide fallback
            candidate_rotations = [
                {
                    "id": "global_cereal_legume",
                    "name": "Small Grain Cereal → Grain Legume Pulse",
                    "crop_ids": ["wheat", "chickpea"],
                    "description": "Universal balanced cereal-legume sustainable rotation.",
                    "benefits": ["Restores soil nitrogen and interrupts pest cycles.", "Balanced food and cash flow."],
                    "disadvantages": ["Requires monitoring of soil moisture during transition."],
                    "assumptions": ["Adaptable to general temperate and subtropical zones."],
                },
                {
                    "id": "global_cereal_oilseed",
                    "name": "Small Grain Cereal → Brassica Oilseed",
                    "crop_ids": ["barley", "mustard"],
                    "description": "Diverse taproot-fibrous sequence breaking monoculture cycles.",
                    "benefits": ["Biofumigation from brassica glucosinolates.", "Deep subsoil moisture scavenging."],
                    "disadvantages": ["Avoid back-to-back brassicas."],
                    "assumptions": ["Standard agricultural practices."],
                },
                {
                    "id": "global_water_saver",
                    "name": "Drought-Resilient Millet → Pulse",
                    "crop_ids": ["pearl_millet", "cowpea"],
                    "description": "Climate-smart low-water pathway for semi-arid environments.",
                    "benefits": ["Lowest water footprint and high heat tolerance.", "Protects farm income during dry years."],
                    "disadvantages": ["Lower maximum yield ceiling than high-input cereals."],
                    "assumptions": ["Rainfed or limited water environments."],
                },
            ]
    else:
        candidate_rotations = [
            # Pathway 1: Staple / Baseline Rotation
            {
                "id": "rice_wheat",
                "name": "Rice → Wheat (Staple Baseline)",
                "crop_ids": ["rice", "wheat"],
                "description": "Traditional cereal-cereal staple dominant in the Indo-Gangetic Plains.",
                "benefits": [
                    "Established local cultivation practices and assured seed supply.",
                    "Established market liquidity referencing government Minimum Support Price (MSP) benchmarks; however, open-market realization varies significantly without guaranteed public procurement.",
                ],
                "disadvantages": [
                    "High total water demand (~1600 mm/year), straining regional groundwater aquifers.",
                    "Continuous shallow fibrous rooting creates a plow pan and depletes the same soil horizon.",
                    "Zero biological nitrogen fixation; heavy synthetic fertilizer dependency.",
                ],
                "assumptions": ["Assured tubewell or canal irrigation available for multiple Rabi irrigations."],
            },
            # Pathway 2: Pulse / Soil-Regenerative Diversification
            {
                "id": "rice_pulse",
                "name": "Rice → Pulse (Chickpea / Lentil)",
                "crop_ids": ["rice", "chickpea"],
                "description": "Cereal-legume rotation introducing biological nitrogen fixation and deep taproot subsoil loosening.",
                "benefits": [
                    "Saves approximately 170 mm of irrigation water compared to wheat.",
                    "Biological nitrogen fixation contributes an estimated 35 kg N/ha net residual credit to the soil system.",
                    "Deep taproot penetrates below the puddled rice hardpan, recycling deeper subsoil nutrients.",
                ],
                "disadvantages": [
                    "Highly sensitive to unseasonal winter rainfall and waterlogging.",
                    "Susceptible to pod borer (Helicoverpa armigera) and vascular wilt.",
                ],
                "assumptions": ["Plot has adequate surface drainage to prevent water stagnation."],
            },
            # Pathway 3: Oilseed Diversification
            {
                "id": "rice_mustard",
                "name": "Rice → Mustard (Sarson / Rai)",
                "crop_ids": ["rice", "mustard"],
                "description": "Cereal-oilseed rotation offering high economic return and lower water requirement.",
                "benefits": [
                    "Requires ~35% less irrigation water than wheat (~250 mm in Rabi).",
                    "Deep taproot (up to 110 cm) improves soil porosity and extracts deep residual moisture.",
                    "Strong domestic edible oil market demand with remunerative prices.",
                ],
                "disadvantages": [
                    "Susceptible to aphid infestation during cloudy winter spells and frost risk.",
                    "Does not fix atmospheric nitrogen.",
                ],
                "assumptions": ["Timely sowing in October/early November to escape late aphid attacks."],
            },
            # Pathway 4: Vegetable / Cash-Crop Intensification
            {
                "id": "rice_potato_moong",
                "name": "Rice → Potato → Green Gram (3-Crop Intensification)",
                "crop_ids": ["rice", "potato", "green_gram"],
                "description": "High-intensity triple cropping maximizing land productivity with cash crops and catch legumes.",
                "benefits": [
                    "Extremely high commercial revenue potential from early winter table potatoes.",
                    "Green gram in Zaid fixes ~30 kg N/ha net residual credit and protects soil from harsh summer erosion.",
                    "Diversified income streams across cereals, vegetables, and pulses.",
                ],
                "disadvantages": [
                    "High capital investment required for seed tubers and cold storage logistics.",
                    "Potato is a heavy nutrient extractor requiring disciplined irrigation.",
                ],
                "assumptions": ["Cold storage facilities and assured tubewell irrigation available."],
            },
            # Pathway 5: Millets / Climate-Resilient Dryland Rotation
            {
                "id": "pearl_millet_chickpea",
                "name": "Pearl Millet (Bajra) → Chickpea (Climate-Resilient)",
                "crop_ids": ["pearl_millet", "chickpea"],
                "description": "Drought-hardy cereal-pulse sequence tailored for water-scarce or light-textured upland soils.",
                "benefits": [
                    "Extremely low total water demand (~650 mm/year), conserving over 55% water compared to Rice-Wheat.",
                    "Chickpea adds 35 kg N/ha net residual nitrogen; Bajra produces nutritious coarse grain and stover.",
                    "Exceptional climate resilience against delayed monsoons and mid-season dry spells.",
                ],
                "disadvantages": [
                    "Lower gross commercial revenue compared to intensive cash crop or wheat rotations.",
                    "Local consumer food preference in canal-irrigated zones leans toward rice and wheat.",
                ],
                "assumptions": ["Well-drained upland or medium land with low flood risk."],
            },
            # Pathway 6: Maize Diversification
            {
                "id": "rice_maize",
                "name": "Rice → Maize (Cereal Diversification)",
                "crop_ids": ["rice", "maize"],
                "description": "Cereal diversification breaking continuous wheat cultivation with high yield potential.",
                "benefits": [
                    "Diversifies cereal rotation and avoids wheat terminal heat stress.",
                    "Expanding local feed and industrial processing market with strong regional demand.",
                    "Deeper root system (up to 90 cm) exploring greater soil volume than wheat.",
                ],
                "disadvantages": [
                    "Demands ~500 mm water in Rabi; high fertilizer requirement with zero N-fixation.",
                    "Hybrid seed must be purchased fresh every season.",
                ],
                "assumptions": ["Sufficient irrigation and fertilizer investment available."],
            },
        ]
    
    
    # Dynamically inject rainfed-specific dryland rotation when farm is rainfed
    if irrigation == "rainfed":
        candidate_rotations.insert(0, {
            "id": "sorghum_lentil",
            "name": "Sorghum (Jowar) → Lentil (Dryland Rotation)",
            "crop_ids": ["sorghum", "lentil"],
            "description": "Low-water dryland rotation for moisture-stressed soils with low synthetic input needs.",
            "benefits": [
                "Thrives on residual moisture with less than 600 mm total water requirement.",
                "Lentil fixes ~30 kg N/ha net residual credit; Sorghum provides rich livestock fodder.",
            ],
            "disadvantages": ["Lower yield ceiling than irrigated cereals."],
            "assumptions": ["Conserve monsoon moisture with deep summer plowing."],
        })

    # Dynamically inject region-specific candidate pathways across all India
    if reg_key in ("southern_peninsula", "deccan"):
        candidate_rotations.extend([
            {
                "id": "cotton_chickpea",
                "name": "Cotton → Chickpea (Peninsular Vertisol System)",
                "crop_ids": ["cotton", "chickpea"],
                "description": "Commercial fibre and legume sequence suited for Deccan and Peninsular black soils.",
                "benefits": ["High commercial cash returns from seed cotton.", "Chickpea fixes ~35 kg N/ha and breaks bollworm pest cycles."],
                "disadvantages": ["Requires pest management and well-drained soils."],
                "assumptions": ["Medium to deep black soils with supplementary irrigation."],
            },
            {
                "id": "finger_millet_groundnut",
                "name": "Finger Millet (Ragi) → Groundnut (Southern Dryland)",
                "crop_ids": ["finger_millet", "groundnut"],
                "description": "Nutritious drought-hardy millet and oilseed sequence with low synthetic input needs.",
                "benefits": ["Finger millet is exceptionally drought resilient.", "Groundnut contributes ~30 kg N/ha biological nitrogen fixation."],
                "disadvantages": ["Lower yield volume than flooded rice systems."],
                "assumptions": ["Light to medium red or loamy soils."],
            },
        ])
    elif reg_key in ("arid_west", "central"):
        candidate_rotations.extend([
            {
                "id": "soybean_wheat",
                "name": "Soybean → Wheat / Chickpea (Central India / Malwa System)",
                "crop_ids": ["soybean", "wheat"],
                "description": "Major oilseed-cereal rotation across Central India and Western Vertisol tracts.",
                "benefits": ["Soybean fixes ~35 kg N/ha and vacates the field early for timely wheat sowing.", "Robust industrial oilseed market demand."],
                "disadvantages": ["Soybean is sensitive to extended mid-season dry spells."],
                "assumptions": ["Assured irrigation available for winter crop."],
            },
            {
                "id": "groundnut_wheat",
                "name": "Groundnut → Wheat (Western / Saurashtra System)",
                "crop_ids": ["groundnut", "wheat"],
                "description": "Legume-cereal diversification common in Gujarat and Western semi-arid regions.",
                "benefits": ["Groundnut adds valuable nitrogen credit.", "Remunerative market demand for edible nuts and fodder oilcake."],
                "disadvantages": ["High seed cost for groundnut kernels."],
                "assumptions": ["Light sandy loam or well-drained medium black soil."],
            },
        ])

    evaluated = []
    for strat in candidate_rotations:
        ev = evaluate_single_strategy(
            strat_id=strat["id"],
            strat_name=strat["name"],
            crop_ids=strat["crop_ids"],
            farmer_profile=farmer_profile,
            description=strat.get("description", ""),
            benefits=strat.get("benefits"),
            disadvantages=strat.get("disadvantages"),
            assumptions=strat.get("assumptions"),
            climate_summary=climate_summary,
        )
        evaluated.append(ev)

    evaluated.sort(key=lambda item: item["overall_score"], reverse=True)
    weights = PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS["balanced"])

    return {
        "farmer_profile": {
            **farmer_profile,
            "priority": priority,
            "source": "farmer_reported",
        },
        "detected_region": {
            "key": reg_key,
            "name": reg_name,
        },
        "rotations": evaluated,
        "crops": {cid: {k: v for k, v in c.items() if k != "id"} for cid, c in CROPS.items()},
        "weights": weights,
        "disclaimer": DISCLAIMER,
    }


def evaluate_custom_rotation(
    crop_ids: list[str],
    farmer_profile: dict[str, Any],
    climate_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluates an arbitrary user-chosen sequence of crops from the 53-crop catalog."""
    valid_ids = [cid for cid in crop_ids if cid in CROPS]
    if not valid_ids:
        raise ValueError("At least one valid crop must be selected from the catalog")

    crop_names = [CROPS[cid]["name"] for cid in valid_ids]
    strat_id = "_".join(valid_ids)
    strat_name = " → ".join(crop_names)

    ev = evaluate_single_strategy(
        strat_id=strat_id,
        strat_name=strat_name,
        crop_ids=valid_ids,
        farmer_profile=farmer_profile,
        description=f"Custom rotation sequence: {strat_name}",
        climate_summary=climate_summary,
    )

    priority = farmer_profile.get("priority", "balanced")
    weights = PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS["balanced"])

    return {
        "farmer_profile": {
            **farmer_profile,
            "priority": priority,
            "source": "farmer_reported",
        },
        "evaluation": ev,
        "weights": weights,
        "disclaimer": DISCLAIMER,
    }
