# VASUNDHARA — Intelligent Crop Rotation & Agricultural Climate Intelligence

[![Tests](https://img.shields.io/badge/Tests-51%20Passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue)](backend/)
[![React](https://img.shields.io/badge/React-19.2.0-61dafb)](frontend/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9.0-blue)](frontend/)
[![Vite](https://img.shields.io/badge/Vite-7.2.0-646cff)](frontend/)
[![NASA POWER](https://img.shields.io/badge/NASA-POWER%20v2.10.3-red)](https://power.larc.nasa.gov)
[![MODIS](https://img.shields.io/badge/MODIS-Terra%20MOD13Q1-green)](https://modis.ornl.gov)

ROTATION IQ is a scientific agricultural decision-support system that synthesizes live **NASA Earth observations** (POWER climate reanalysis and ORNL DAAC MODIS NDVI vegetation health) with an intelligent **Pan-Indian Crop Rotation Engine** across 53 crops.

---

## Key Features

1. **Global Crop Database (1253 Crops)**:
   - Organized into 7 primary categories: Cereals & Millets (8), Pulses & Grain Legumes (9), Oilseeds (8), Vegetables (11), Fruits (5), Spices (7), Commercial & Fiber (5).
   - Strict botanical taxonomy: Exactly 12 species belonging to botanical family `Fabaceae` (including leguminous oilseeds soybean and groundnut, and spice fenugreek) have verified symbiotic BNF net soil credits ($kg\ N/ha$); all 41 non-legumes strictly output `null/N/A`.
2. **Dynamic Rotation Generation & Multi-Criteria Scoring**:
   - Generates and evaluates agronomic pathways across Kharif (Monsoon), Rabi (Winter), and Zaid (Summer) seasons.
   - Unified authoritative Soil Health Index (comparative heuristic index 0–100 evaluating base 35 + BNF + family diversity + root zone stratification - puddled rice compaction - depletion - texture mismatch).
   - Estimated cumulative crop water demand ($ET_c$) evaluated against regional thresholds (ICAR-CRIDA 700 mm dryland, IMD 1200 mm monsoon, CGWB 350 mm sustainable aquifer limit).
   - Dynamic wheat terminal heat stress evaluation against historical NASA POWER March temperatures ($>32^\circ	ext{C}$).
   - Economic stability heuristics anchored to CACP Minimum Support Prices (MSP) with clear disclaimers that MSP is not guaranteed procurement.
3. **Frontend & User Experience**:
   - Leaflet interactive map with coordinate selection across Bihar and India.
   - Side-by-side Strategy Comparison modal (compare up to 3 candidate rotations).
   - Visual 12-month Crop Rotation Gantt Timeline with turnaround buffer periods.
   - Transparent Ranking Breakdown showing explicit weighting formulas.
   - One-click Printable Farmer Summary Advisory Report.
   - Monotonic request tokens discarding out-of-order in-flight responses.

---

## Automated Verification Suite (51 Tests)

```bash
# Run all 51 backend unit, API, and E2E tests
python -m unittest discover -s tests -v

# Run frontend production build & TypeScript validation
cd frontend
npm run build
```

---

## Production Deployment

- **Backend (Render):** Configured via `render.yaml` and `backend/Procfile` using startup command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Verified from repository root.
- **Frontend (Vercel):** Configured via `frontend/vercel.json` with dynamic API base URL `VITE_API_BASE_URL`.
