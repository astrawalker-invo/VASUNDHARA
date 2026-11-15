# ROTATION IQ — SCIENTIFIC METHODOLOGY & ASSUMPTIONS REGISTER

This document defines the authoritative scientific formulations, hydrological models, and assumptions governing ROTATION IQ.

---

## 1. Authoritative Soil Health Index Formulation

The soil health score is a **comparative heuristic index (0–100)** of relative agronomic sustainability, NOT an empirical measurement of physical/chemical soil improvement or soil organic carbon gain.

$$\text{Soil Health Index} = \text{Clamp}_{10}^{100}\left( 35.0 + \Delta S_{\text{BNF}} + \Delta S_{\text{family}} + \Delta S_{\text{root}} + \Delta S_{\text{cover}} - \Delta S_{\text{compaction}} - \Delta S_{\text{depletion}} - \Delta S_{\text{texture}} \right)$$

### Formula Components:
1. **Baseline ($S_{\text{base}} = 35.0$):** Neutral starting score for continuously cultivated arable soils in the Indo-Gangetic Plains.
2. **Biological Nitrogen Fixation Bonus ($\Delta S_{\text{BNF}}$):**
   $$\Delta S_{\text{BNF}} = \min(20.0, \sum N_{\text{fix}} \times 0.45)$$
   Credits net residual symbiotic nitrogen fixed by Fabaceae root nodules (e.g., 35 kg N/ha yields $+15.75\text{ pts}$, capped at $+20.0\text{ pts}$).
3. **Crop Family Diversity ($\Delta S_{\text{family}}$):**
   - $+8.0\text{ pts}$ if $>1$ distinct botanical families are present in sequence.
   - $+5.0\text{ pts}$ synergy bonus for Poaceae (cereals) + Fabaceae (legumes) rotations.
   - $+3.0\text{ pts}$ bio-fumigation / pest-break bonus if Brassicaceae (mustard/radish) is included.
   - $-6.0\text{ pts}$ continuous cereal penalty if all crops in a multi-crop sequence belong to Poaceae.
4. **Root Zone Stratification ($\Delta S_{\text{root}}$):**
   - $+6.0\text{ pts}$ if $>1$ root architecture types (e.g., fibrous + taproot).
   - $+6.0\text{ pts}$ if deep taproot ($>80\text{ cm}$) is present (subsoil nutrient extraction).
   - $+4.0\text{ pts}$ for moderate taproot without puddled rice.
5. **Canopy Ground Cover ($\Delta S_{\text{cover}}$):**
   - $+4.0\text{ pts}$ if average `soil_cover_rating` $\ge 4.0$.
6. **Puddled Rice Hardpan Compaction Penalty ($\Delta S_{\text{compaction}}$):**
   - $-5.0\text{ pts}$ when moderate taproot pulses follow puddled lowland rice in heavy alluvial/clay soils due to the restrictive sub-surface plough pan (unless deep taproot or conservation relay is used).
7. **Heavy Nutrient Depletion Penalty ($\Delta S_{\text{depletion}}$):**
   - $-8.0\text{ pts}$ if all crops in sequence are high nitrogen extractors (`n_feeder == "high"`) with zero legume.
8. **Soil Texture Mismatch Penalty ($\Delta S_{\text{texture}}$):**
   - $-8.0\text{ pts}$ for each crop where the farmer's soil texture is not listed in `suitable_soils`.

---

## 2. Crop Water Demand ($ET_c$) versus Net Irrigation Requirement

ROTATION IQ strictly distinguishes between:
1. **Estimated Cumulative Crop Water Demand ($ET_c$):**
   The total potential crop evapotranspiration ($ET_c = K_c \times ET_0$) under unstressed conditions across the growing cycle per FAO-56.
2. **Net Irrigation Requirement ($I_{net}$):**
   $$I_{net} = ET_c - P_{\text{eff}} - \Delta S_{\text{soil}} - G_w$$
   Calculating $I_{net}$ requires dynamic field-level soil water balance simulation. Therefore, ROTATION IQ explicitly presents `water_demand_mm` as **estimated cumulative crop water demand ($ET_c$)**, not calculated net irrigation.

### Hydrological Threshold Justifications:
- **700 mm (ICAR-CRIDA):** Dryland cropping benchmark. Rainfed rotations demanding $>700\text{ mm}$ trigger water stress warnings.
- **1200 mm (IMD Bihar Climatology):** Mean annual monsoon rainfall envelope. Rainfed rotations exceeding $1200\text{ mm}$ receive severe feasibility penalties (-35.0 pts).
- **350 mm (CGWB 2022):** Sustainable seasonal shallow aquifer net draft ceiling per hectare during dry winter/summer cycles without long-term water table drawdown.

---

## 3. Dynamic Wheat Terminal Heat Stress Evaluation

When NASA POWER climate summary statistics are provided, ROTATION IQ dynamically evaluates March daytime temperatures during the anthesis and grain-filling period:
- **Agronomic Threshold:** Daily maximum temperature exceeding $32.0^\circ\text{C}$ causes premature senescence and reduced 1000-grain weight in late-sown wheat (ICAR-IIWBR).
- **Risk Indicator, Not Confirmed Damage:** The warning explicitly indicates environmental temperature risk, not guaranteed crop failure. Timely planting (Nov 15–25) and heat-tolerant cultivars (e.g., HD-2967, DBW-187) substantially mitigate this risk.
- **Missing Data Protocol:** When no NASA temperature summary is supplied, the engine outputs an informative advisory note without score deduction or false dynamic claims.

---

## 4. Economic Stability & Regional Suitability Boundaries

- **MSP Baseline Reference:** Economic stability scores evaluate relative price volatility and perishability heuristics based on historical MSP benchmarks and Agmarknet trends. The engine does NOT guarantee government procurement or forecast live spot prices.
- **Regional Suitability as Advisory Flag:** Regional suitability warnings inform the user of agro-climatic adaptation in Bihar without artificially altering multi-objective index points.
