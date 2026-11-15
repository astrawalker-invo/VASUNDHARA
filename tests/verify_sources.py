"""RUN LOCALLY (needs internet): python tests/verify_sources.py
Verifies each external API with a real request and prints timings + differences from spec.
Paste the output back to me."""
import asyncio, time, httpx, json
LAT, LON = 25.5941, 85.1376
async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        t = time.time()
        r = await c.get("https://power.larc.nasa.gov/api/temporal/daily/point", params=dict(
            parameters="T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,GWETTOP,GWETROOT",
            community="AG", longitude=LON, latitude=LAT, start="19810101", end="20251231", format="JSON"))
        print("POWER", r.status_code, f"{time.time()-t:.1f}s")
        if r.is_success:
            p = r.json()["properties"]["parameter"]
            for k, v in p.items():
                ok = [d for d, x in v.items() if x != -999]
                print(" ", k, "first valid:", ok[0] if ok else None, "n:", len(ok))
            print("  geometry:", r.json().get("geometry"))
        else: print(r.text[:300])
        B = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
        for path in ("bands", "dates"):
            t = time.time(); r = await c.get(f"{B}/{path}", params=dict(latitude=LAT, longitude=LON) if path=="dates" else None,
                headers={"Accept": "application/json"})
            print("ORNL", path, r.status_code, f"{time.time()-t:.1f}s", r.text[:400].replace("\n", " "))
        t = time.time(); r = await c.get(f"{B}/subset", params=dict(latitude=LAT, longitude=LON, band="250m_16_days_NDVI",
            startDate="A2020001", endDate="A2020145", kmAboveBelow=0, kmLeftRight=0), headers={"Accept": "application/json"})
        print("ORNL subset", r.status_code, f"{time.time()-t:.1f}s", r.text[:500].replace("\n", " "))
        t = time.time(); r = await c.get("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-10-01/GoogleMapsCompatible_Level9/5/13/22.jpg")
        print("GIBS tile", r.status_code, r.headers.get("content-type"), f"{time.time()-t:.1f}s")
asyncio.run(main())
