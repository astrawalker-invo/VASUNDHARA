"""Global Crop Registry for VASUNDHARA.
Loads, indexes, and searches the 1,232+ global crop database.
Provides backward compatibility for the base 53 crops while unlocking 1,000+ worldwide crops.
"""
import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent / "data" / "crops_global.json"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Global crop database not found at {DATA_PATH}")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    CROPS: dict[str, dict[str, Any]] = json.load(f)

# The 53 base crops from the original pan-Indian dataset
BASE_53_IDS = {
    "banana", "barley", "betel_vine", "bitter_gourd", "black_gram", "brinjal",
    "cabbage", "carrot", "castor", "cauliflower", "chickpea", "cluster_bean",
    "coriander", "cotton", "cowpea", "cumin", "fennel", "fenugreek", "field_pea",
    "finger_millet", "foxtail_millet", "garlic", "ginger", "green_chilli",
    "green_gram", "groundnut", "guava", "horse_gram", "jute", "lentil", "linseed",
    "maize", "mango", "mustard", "okra", "onion", "papaya", "pearl_millet",
    "pigeonpea", "pomegranate", "potato", "radish", "rice", "safflower", "sesame",
    "sorghum", "soybean", "sugarcane", "sunflower", "tobacco", "tomato", "turmeric",
    "wheat"
}

BASE_53_CROPS: dict[str, dict[str, Any]] = {
    cid: c for cid, c in CROPS.items() if cid in BASE_53_IDS
}

# Fast indices
CROPS_BY_CATEGORY: dict[str, list[str]] = {}
CROPS_BY_FAMILY: dict[str, list[str]] = {}
CROPS_BY_ZONE: dict[str, list[str]] = {}
CROPS_BY_SEASON: dict[str, list[str]] = {}

for cid, c in CROPS.items():
    pcat = c.get("primary_category", "other")
    CROPS_BY_CATEGORY.setdefault(pcat, []).append(cid)
    for cat in c.get("categories", []):
        if cat != pcat:
            CROPS_BY_CATEGORY.setdefault(cat, []).append(cid)

    fam = c.get("crop_family", "Unknown")
    CROPS_BY_FAMILY.setdefault(fam, []).append(cid)

    for z in c.get("climatic_zones", []):
        CROPS_BY_ZONE.setdefault(z, []).append(cid)

    s = c.get("season", "all_season")
    CROPS_BY_SEASON.setdefault(s, []).append(cid)


def get_crop(crop_id: str) -> dict[str, Any] | None:
    return CROPS.get(crop_id)


def search_crops(
    q: str | None = None,
    category: str | None = None,
    crop_family: str | None = None,
    season: str | None = None,
    climate_zone: str | None = None,
    region: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Search and filter the global crop catalog with pagination support."""
    results = []
    q_lower = q.strip().lower() if q else None
    cat_lower = category.strip().lower() if category else None
    fam_lower = crop_family.strip().lower() if crop_family else None
    seas_lower = season.strip().lower() if season else None
    zone_lower = climate_zone.strip().lower() if climate_zone else None
    reg_lower = region.strip().lower() if region else None

    for cid, c in CROPS.items():
        if cat_lower:
            cats = [cat.lower() for cat in c.get("categories", [])] + [c.get("primary_category", "").lower()]
            if cat_lower not in cats:
                continue

        if fam_lower and c.get("crop_family", "").lower() != fam_lower:
            continue

        if seas_lower and seas_lower not in c.get("season", "").lower() and "all_season" not in c.get("season", "").lower():
            continue

        if zone_lower:
            zones = [z.lower() for z in c.get("climatic_zones", [])]
            if zone_lower not in zones:
                continue

        if reg_lower:
            suit = c.get("regional_suitability", {}).get(reg_lower, "low")
            if suit not in ("high", "moderate"):
                continue

        if q_lower:
            in_id = q_lower in cid
            in_name = q_lower in c.get("name", "").lower()
            in_sci = q_lower in c.get("scientific_name", "").lower()
            in_syns = any(q_lower in syn.lower() for syn in c.get("synonyms", []))
            in_cats = any(q_lower in cat.lower() for cat in c.get("categories", []))
            if not (in_id or in_name or in_sci or in_syns or in_cats):
                continue

        results.append(c)

    total_count = len(results)
    if offset:
        results = results[offset:]
    if limit is not None:
        results = results[:limit]

    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "crops": results,
    }


def get_catalog_stats() -> dict[str, Any]:
    """Summary statistics of the global database."""
    families = sorted(list(CROPS_BY_FAMILY.keys()))
    categories = sorted(list(CROPS_BY_CATEGORY.keys()))
    zones = sorted(list(CROPS_BY_ZONE.keys()))
    fabaceae_count = len(CROPS_BY_FAMILY.get("Fabaceae", []))

    return {
        "total_crops": len(CROPS),
        "base_53_count": len(BASE_53_CROPS),
        "fabaceae_bnf_count": fabaceae_count,
        "non_fabaceae_count": len(CROPS) - fabaceae_count,
        "unique_families": len(families),
        "families": families,
        "unique_categories": len(categories),
        "categories": categories,
        "climatic_zones": zones,
    }
