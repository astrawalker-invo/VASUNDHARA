# LIMITATIONS

- POWER is a ~50 km climate cell (0.5° × 0.625°). It is not the weather on the field. Rain is the weakest of these variables. Soil wetness is a model.
- The solar series changes source in 1984. A trend fitted across that break would be misleading. The app does not fit trends yet.
- MODIS NDVI is one 231.7 m cell, every 16 days. It can be larger than the field. Cloudy and snowy composites are removed, so the chart has gaps. Those gaps are missing observations, not zero vegetation.
- The GIBS 8-day NDVI picture starts in February 2025. Earlier years have true-color imagery and the ORNL chart, not an NDVI tile.
- ORNL's date list took about 20 seconds, and each 10-date chunk took about 6 seconds. A 20-year series is on the order of a minute or more the first time. Cached repeats are much faster. There is no Earth Engine fallback yet.
- The POWER cell formula was checked around Patna, not across India.
- Nothing in the app ranks crops, predicts yield, or prices a harvest yet.
- Market prices need `DATA_GOV_IN_API_KEY` or `CEDA_API_KEY`. Those adapters are not built. Manual prices will be the fallback.
- CORS is open (`*`) until a Vercel URL exists.
