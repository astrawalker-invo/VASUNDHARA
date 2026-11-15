# ROTATION IQ

Live NASA-data decision support for crop rotation. The app supports local agronomic expertise. It does not replace it.

What runs today: a map, NASA GIBS imagery, and charts of POWER climate and MODIS NDVI for a point the farmer marks. Rotation ranking, the simulator, and prices are not built yet.

## Run

From the repository root, two terminals:

```text
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --port 8000
```

```text
cd frontend
npm install
npm run dev
```

Open the Vite URL. Click the map. The first MODIS load for a new cell takes roughly half a minute because ORNL's date list is slow. The same cell and years are then cached.

Check the external APIs directly:

```text
.venv\Scripts\python.exe tests\verify_sources.py
```

## Layout

- `backend/` — FastAPI adapters for POWER and ORNL, cache, SSE progress
- `frontend/` — map and charts
- `tests/verify_sources.py` — live API check
- `docs/` — assumptions, methods, limitations
