# ROTATION IQ — DEPLOYMENT & PRODUCTION OPERATIONS MANUAL

This guide details the procedure for deploying ROTATION IQ as a decoupled, production-grade cloud architecture.

```
                      +-----------------------------+
                      |   Vercel Edge Network       |
                      |   (React 18 + Vite SPA)     |
                      |   https://rotation-iq.app   |
                      +--------------+--------------+
                                     |
                         HTTPS REST  |  CORS Enabled
                                     v
                      +-----------------------------+
                      |   Render Web Service        |
                      |   (FastAPI + Uvicorn)       |
                      |   https://api.rotation-iq   |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                                           |
               v                                           v
   +-----------------------+                   +-----------------------+
   |   NASA POWER API      |                   |   ORNL DAAC MODIS     |
   |   v2.10.3 (MERRA-2)   |                   |   MOD13Q1 Subsets     |
   +-----------------------+                   +-----------------------+
```

---

## 1. Backend Deployment (Render)

The backend is configured as a Render Python Web Service using `render.yaml` and `backend/Procfile`.

### Render Setup Steps:
1. Connect your Git repository to Render.
2. Create a new **Web Service** from the repo root.
3. Configure the following build settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Set Environment Variables:
   - `PYTHON_VERSION`: `3.11.9` (or `3.12`)
   - `CORS_ORIGINS`: `https://<your-vercel-domain>.vercel.app,http://localhost:5173`
   - `ROTATION_IQ_WARM_CACHE`: `1` (Pre-caches Patna benchmark climate data on startup)
   - `ENVIRONMENT`: `production`
5. Deploy the service. Verify deployment via:
   ```bash
   curl -s https://<your-render-url>/api/health
   # Expected response: {"status":"healthy","service":"rotation-iq-api"}
   ```

---

## 2. Frontend Deployment (Vercel)

The frontend is a React 18 + TypeScript SPA built with Vite, configured via `frontend/vercel.json`.

### Vercel Setup Steps:
1. Connect the Git repository to Vercel.
2. Set the **Root Directory** to `frontend`.
3. Vercel will automatically detect the Vite framework preset:
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Configure Environment Variables in Vercel project settings:
   - `VITE_API_BASE_URL`: `https://<your-render-url>` (Your deployed FastAPI backend URL, without trailing slash)
5. Deploy. The `vercel.json` rewrite rule ensures all client-side routing routes back to `index.html`.

---

## 3. Local Development

To run the full stack locally:

### Terminal 1: Backend
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.
