# ROTATION IQ — KNOWN LIMITATIONS & SCIENTIFIC DISCLAIMERS

ROTATION IQ is designed as a regional agro-climatic decision-support tool. To maintain scientific integrity, the following system boundaries and operational limitations are documented:

## 1. Remote Sensing & Spatial Resolution

- **Meso-Scale Climate Forcing:** NASA POWER variables are derived from the MERRA-2 global assimilation model and GEOS-5 atmospheric models on a 0.5° latitude by 0.625° longitude grid. Local micro-climates, canal-side evaporative cooling, topography, and localized convective cloudbursts are smoothed over the ~50 km grid cell.
- **Sub-Pixel Landscape Heterogeneity:** MODIS MOD13Q1 produces 231.7 m spatial resolution. In fragmented smallholder landscapes where individual field parcels average 0.39 hectares, a single pixel captures a mixture of crop types, field bunds, fallow patches, rural structures, and tree canopies. Satellite NDVI reflects the aggregate greenness of this composite patch.
- **Cloud Mask Missing Data Gaps:** During the peak South-West Monsoon (July–August), persistent convective cloud cover obscures optical satellite surface reflectance. Following scientific QA protocols, MODIS pixel reliability ranks > 1 are discarded and returned as `null` gaps. ROTATION IQ never interpolates synthetic observations or converts missing satellite data to zero.

## 2. Agronomic & Rotation Engine Boundaries

- **State Calibration Scope:** The initial rule base, phenological calendars, and agro-ecological scoring have been rigorously calibrated for the Agro-Climatic Zones of Bihar (Zone I: North-West Alluvial Plains; Zone II: North-East Alluvial Plains; Zone IIIA/IIIB: South Alluvial Plains). While the 53-crop database includes pan-Indian species, running recommendations in drastically different agro-ecosystems (e.g., arid Western Rajasthan or high-altitude Himalayas) requires regional calibration of planting dates and soil matrices.
- **Pest & Pathogen Population Dynamics:** Rotation disease-break benefits are modeled through botanical family diversification and crop residue characteristics. The engine does not dynamically simulate real-time pest outbreaks, fungal spore migration, or localized nematode densities.
- **Perennial & Long-Duration Crops:** Perennial fruit orchards (e.g., Mango, Guava, Citrus) and 12-month crops (Sugarcane) operate on multi-year lifecycles. They are accommodated in the crop database and custom rotation builder, but standard 3-season annual rotation sequencing does not force them into annual turnover.

## 3. Economic & Market Forecast Boundaries

- **Static Price Benchmarks:** Economic scoring relies on official Government of India Minimum Support Prices (MSP) and Agmarknet historical modal baselines. The engine does not forecast daily spot market volatility, post-harvest distress sale discounts, or transportation logistics costs.
- **Input Cost Variability:** Net income index scores reflect standard cost of cultivation norms (C2 cost metrics from CACP). Local variations in diesel prices, canal water cess, hybrid seed premiums, and labor wage spikes during peak harvest are not individually simulated.
