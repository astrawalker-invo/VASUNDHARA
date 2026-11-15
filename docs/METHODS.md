# METHODS

Rotation IQ reads live NASA data and shows it with the resolution of the source. It does not invent values when a source fails.

## Climate

NASA POWER daily point API, `community=AG`, one request per grid cell for the full variable list. Variables: 2 m temperature (mean, max, min), corrected precipitation, 2 m relative humidity, all-sky surface shortwave irradiance, and top- and root-zone soil wetness.

Wetness is modeled. Solar comes from SYN1DEG and starts later than the MERRA-2 variables. The point request returns the same value anywhere inside a 0.5° × 0.625° cell. The app labels this as regional climate context for that cell.

## Vegetation

MODIS Terra MOD13Q1 through the ORNL DAAC subset API. The request asks for the single cell containing the point (`kmAboveBelow=0`, `kmLeftRight=0`). NDVI is scaled by 0.0001. Fill -3000 and pixel-reliability ranks other than 0 or 1 are stored as null and shown as gaps.

The cell is 231.7 m on the sinusoidal grid. A small field can be mixed with its surroundings.

## Map imagery

NASA GIBS WMTS, Web Mercator, `GoogleMapsCompatible_Level9` (zoom 0–9):

- `MODIS_Terra_CorrectedReflectance_TrueColor` (JPEG)
- `MODIS_Terra_NDVI_8Day` (PNG), available in GIBS from 2025-02-12

Imagery is a picture. The numbers in the charts come from POWER and ORNL.

## Not built yet

Trends, bare-soil days, vulnerability, the field model, water balance, rotation scoring, the simulator, and market prices. Those methods will be added here when the code exists. No Earth Engine path is connected.
