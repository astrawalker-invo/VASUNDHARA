# ROTATION IQ — SCIENTIFIC DATA SOURCE REGISTER

This document establishes the empirical traceability of all environmental data, botanical classifications, crop parameters, hydrological thresholds, and economic baselines utilized within ROTATION IQ.

## 1. Remote Sensing & Earth Observation Data Sources

| Parameter / Layer | Source Mission & Product | Institution / Publisher | Resolution (Spatial & Temporal) | Validation URL / DOI | Confidence | Limitations & Data Caveats |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Surface Temperature (T2M, T2M_MAX, T2M_MIN)** | MERRA-2 assimilation, NASA POWER Daily v2.10.3 (AG Community) | NASA Langley Research Center (LaRC) | 0.5° × 0.625° (~50 km cell); Daily (1981–present) | [https://power.larc.nasa.gov](https://power.larc.nasa.gov) | **High** | Piecewise constant regional grid. Captures meso-climate, not micro-climate variations across smallholder fields. |
| **Precipitation (PRECTOTCORR)** | Bias-corrected precipitation, NASA POWER Daily v2.10.3 | NASA LaRC / GMAO | 0.5° × 0.625°; Daily (1981–present) | [https://power.larc.nasa.gov](https://power.larc.nasa.gov) | **Medium** | Reanalysis model bias-corrected against GPCP gauge analyses; underestimates localized high-intensity convective monsoon bursts. |
| **Relative Humidity (RH2M)** | 2-meter relative humidity, NASA POWER Daily v2.10.3 | NASA LaRC | 0.5° × 0.625°; Daily (1981–present) | [https://power.larc.nasa.gov](https://power.larc.nasa.gov) | **High** | Derived from 2m specific humidity and air temperature. |
| **Solar Irradiance (ALLSKY_SFC_SW_DWN)** | SYN1DEG radiative transfer, NASA POWER Daily v2.10.3 | NASA LaRC / CERES Project | 1.0° native regridded to 0.5°; Daily (1984–present) | [https://ceres.larc.nasa.gov](https://ceres.larc.nasa.gov) | **High** | **Time series break:** Valid only from 1984-01-01. Do not calculate secular solar trends spanning across 1983-1984. |
| **Surface & Root Wetness (GWETTOP, GWETROOT)** | Catchment Land Surface Model (CLSM), NASA POWER | NASA GMAO (MERRA-2) | 0.5° × 0.625°; Daily (1981–present) | [https://gmao.gsfc.nasa.gov](https://gmao.gsfc.nasa.gov) | **Medium** | Modeled top-layer (0-5 cm) and root-zone soil moisture; indicative of hydrological drought but not equal to in-situ gravimetric soil moisture. |
| **Vegetation Indices (NDVI, EVI)** | MODIS Terra MOD13Q1 v061 (16-day Composite) | NASA LP DAAC / ORNL DAAC Subset API | 231.7 m sinusoidal grid cell; 16-day composite (2000–present) | [https://modis.ornl.gov/rst/api/v1](https://modis.ornl.gov/rst/api/v1) / [doi:10.5067/MODIS/MOD13Q1.061](https://doi.org/10.5067/MODIS/MOD13Q1.061) | **High** | Multi-field spatial aggregation: an average Bihar holding (0.39 ha) represents only ~7% of a 231.7m (5.37 ha) MODIS pixel. |
| **MODIS Pixel Quality Filtering** | `250m_16_days_pixel_reliability` | NASA LP DAAC / ORNL DAAC | Categorical quality flags (Ranks 0 to 3, Fill: -1) | [MOD13Q1 User Guide](https://lpdaac.usgs.gov/documents/103/MOD13_User_Guide_V61.pdf) | **Very High** | Strict filtering: Only Rank 0 (Good Data) and Rank 1 (Marginal Data) are retained. Ranks 2 (Snow/Ice) and 3 (Cloud Covered) are preserved as `None/null` (gaps), never 0. |

---

## 2. Agronomic & Hydrological Threshold Traceability

| Parameter / Threshold | Metric Name in Engine | Governing Scientific Authority | Reference Publication / Dataset | Role in Rotation IQ Engine |
| :--- | :--- | :--- | :--- | :--- |
| **Crop Water Demand ($ET_c$)** | `water_demand_mm` | Food and Agriculture Organization (FAO) | Allen, R. G., et al. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56. Rome: FAO. | Estimated potential crop evapotranspiration ($ET_c = K_c 	imes ET_0$). **Not net irrigation requirement**. |
| **Semi-Arid Dryland Ceiling (700 mm)** | Water score threshold | ICAR-Central Research Institute for Dryland Agriculture (CRIDA) | Srinivasarao, Ch., et al. (2014). *Climate Resilient Agronomy in Rainfed Agriculture*. ICAR-CRIDA, Hyderabad. | Evaluates maximum cumulative moisture envelope for rainfed double-cropping without supplemental irrigation. |
| **Monsoon Rainfall Envelope (1200 mm)** | Water score threshold | India Meteorological Department (IMD) | IMD Climatological Normals (1981–2010), Bihar State Meteorological Report; DES Bihar. | Represents normal annual monsoon precipitation envelope for Middle Gangetic Plain. Rotations demanding >1200 mm face severe deficit under rainfed conditions. |
| **Aquifer Sustainable Draft (350 mm)** | Rabi/Zaid irrigation ceiling | Central Ground Water Board (CGWB) | CGWB (2022). *Dynamic Ground Water Resources of India - 2022*. Ministry of Jal Shakti, New Delhi. | Sustainable seasonal shallow aquifer net draft ceiling per hectare during dry winter/summer cycles before triggering groundwater depletion warnings. |
| **Wheat Terminal Heat Stress (>32°C)** | Climate resilience score | ICAR-Indian Institute of Wheat & Barley Research (IIWBR) | Rane, J., et al. (2021). *Terminal Heat Tolerance in Wheat*, ICAR-IARI; Sengupta et al. (2018). *Current Science*, 115(7). | Critical reproductive threshold during late February/March anthesis. Triggers potential heat-risk warning when NASA March temperatures exceed 32°C. |
| **Minimum Support Price (MSP)** | `market_stability` heuristic | Commission for Agricultural Costs and Prices (CACP) | CACP Price Policy Reports for Kharif & Rabi Crops (2023–24 & 2024–25). DAC&FW, GoI. | Reference price floor benchmark used for indicative price stability heuristics. **Not guaranteed open-market procurement**. |

---

## 3. Pan-Indian Crop Database Taxonomy & Botanical Reconciliation

The database contains exactly **53 crops**, categorized into 7 mutually exclusive primary categories (`primary_category` field):
1. **Cereals & Millets (8):** Rice, Wheat, Maize, Pearl Millet, Sorghum, Finger Millet, Foxtail Millet, Barley.
2. **Pulses & Grain Legumes (9):** Chickpea, Pigeonpea, Lentil, Green Gram, Black Gram, Field Pea, Cowpea, Cluster Bean, Horse Gram.
3. **Oilseeds (8):** Soybean, Groundnut, Mustard, Sesame, Sunflower, Safflower, Linseed, Castor. *(Note: Soybean and Groundnut are botanically Fabaceae legumes with biological N-fixation).*
4. **Vegetables (11):** Potato, Onion, Tomato, Brinjal, Cauliflower, Cabbage, Okra, Bitter Gourd, Carrot, Radish, Green Chilli.
5. **Fruits (5):** Mango, Banana, Guava, Papaya, Pomegranate.
6. **Spices & Condiments (7):** Turmeric, Ginger, Garlic, Coriander, Cumin, Fennel, Fenugreek. *(Note: Fenugreek is botanically a Fabaceae legume with biological N-fixation).*
7. **Commercial & Fiber (5):** Sugarcane, Cotton, Jute, Tobacco, Betel Vine.

### Fabaceae Nitrogen Fixation Reconciliation (12 Species)
To resolve previous discrepancies between total biological fixation and net residual soil nitrogen credit:
- **Total Symbiotic BNF ($N_2$ fixed):** Total atmospheric nitrogen fixed across shoots, roots, and grain during crop development (Peoples et al. 1995 Table 2; Herridge et al. 2008 Table 2).
- **Net Residual Soil N Contribution:** Residual nitrogen credited to the soil system following economic grain harvest and stover management in Indian agro-ecosystems (Ali & Venkatesh, 2009, ICAR-IIPR Kanpur; Peoples et al. 1995 Table 4). The `nitrogen_fixation_kg_ha` database attribute records this **net residual soil credit**.

| Crop ID | Common Name | Botanical Family | Primary Category | Total Biological BNF ($kg\ N/ha$) | Net Residual Soil N Credit ($kg\ N/ha$) in Database | Primary References |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `chickpea` | Chickpea / Chana | Fabaceae | Pulses | 60 – 80 | **35** (range 25–45) | Peoples et al. (1995); Ali & Venkatesh (2009) ICAR-IIPR |
| `pigeonpea` | Pigeonpea / Arhar | Fabaceae | Pulses | 80 – 110 | **45** (range 35–60) | Peoples et al. (1995); ICAR Handbook (2021) |
| `lentil` | Lentil / Masoor | Fabaceae | Pulses | 50 – 65 | **30** (range 20–40) | Herridge et al. (2008); Ali & Venkatesh (2009) |
| `green_gram` | Green Gram / Moong | Fabaceae | Pulses | 45 – 60 | **30** (range 20–38) | Peoples et al. (1995); BAU Sabour Guide |
| `black_gram` | Black Gram / Urad | Fabaceae | Pulses | 45 – 60 | **32** (range 22–40) | Peoples et al. (1995); BAU Sabour Guide |
| `field_pea` | Field Pea / Matar | Fabaceae | Pulses | 55 – 70 | **35** (range 25–45) | Herridge et al. (2008); ICAR-IIPR |
| `cowpea` | Cowpea / Lobia | Fabaceae | Pulses | 60 – 80 | **40** (range 30–50) | Peoples et al. (1995); Ali & Venkatesh (2009) |
| `soybean` | Soybean | Fabaceae | Oilseeds | 90 – 140 | **40** (range 30–55) | Peoples et al. (1995); ICAR-IISR Indore |
| `cluster_bean`| Cluster Bean / Guar | Fabaceae | Pulses | 40 – 60 | **35** (range 25–45) | Peoples et al. (1995); CAZRI Jodhpur |
| `horse_gram` | Horse Gram / Kulthi| Fabaceae | Pulses | 35 – 45 | **25** (range 15–30) | Peoples et al. (1995); ICAR-CRIDA |
| `groundnut` | Groundnut / Peanut | Fabaceae | Oilseeds | 70 – 90 | **35** (range 25–45) | Peoples et al. (1995); ICAR-DGR Junagadh |
| `fenugreek` | Fenugreek / Methi | Fabaceae | Spices | 30 – 40 | **25** (range 15–35) | ICAR-NRCSS Ajmer Technical Reports |

**All remaining 41 non-Fabaceae crops explicitly hold `nitrogen_fixation_kg_ha: null` and serialize as `null` (displayed as `"N/A"` in UI).**
