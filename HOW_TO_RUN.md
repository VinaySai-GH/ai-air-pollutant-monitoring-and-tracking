# 🚀 How to Run the (now richer) Air Pollution Monitoring System

## 1. Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Configure API Keys (`.env`)
```
MAPBOX_ACCESS_TOKEN=your_mapbox_token
OPENAQ_API_KEY=optional_but_nice
WAQI_API_TOKEN=6567b6d060c9b0323689e7bb3ab7027d539f3e46
WAQI_MAX_STATIONS=150
```

> ✅ WAQI token already provided above. Replace if you generate a new one.

## 3. Google Earth Engine Setup
1. `earthengine authenticate`
2. `earthengine set_project "<your-project-id>"`
3. Ensure the Earth Engine API is enabled in Google Cloud and you are logged in at https://code.earthengine.google.com/

## 4. Fetch ALL Data (WAQI + Sentinel-5P + MODIS AOD)
```bash
python src/data_collection/fetch_all_gases.py
```

This single command will:
- Call WAQI for PM₂.₅/NO₂/CO/SO₂ ground stations across India.
- Sample Sentinel-5P NO₂/SO₂/CO across a 6x6 grid.
- Sample MODIS AOD (following the GitHub workflow you shared) and convert it into PM₂.₅ proxies.
- Write `data/raw/all_gases_data_latest.csv` for the backend + individual CSVs per source.

## 5. Start the Backend
```bash
uvicorn api.main:app --reload
```
or
```bash
python start_backend.py
```

The API lives at `http://localhost:8000` (health check at `/health`, docs at `/docs`).

## 6. Open the Dashboard
Open `dashboard/index.html` in your browser (or run `python -m http.server` in the `dashboard/` folder and visit `http://localhost:8000`).

## 7. Verify the Heatmap
- Use the gas toggle (PM₂.₅, NO₂, CO, SO₂).
- Click anywhere on the map to inspect the nearest data point.
- Toggle hotspots on/off to highlight local maxima for each gas.

## Troubleshooting
- **No WAQI data?** Ensure the token is valid and not rate-limited.
- **GEE errors?** Re-run `earthengine authenticate` and confirm the project is set.
- **Map blank?** Set `MAPBOX_ACCESS_TOKEN` in `.env` *and* in `dashboard/script.js`.
- **Need more coverage?** Raise `WAQI_MAX_STATIONS` or increase the grid size constants inside `fetch_satellite_gee.py`.

## Updating Data Regularly
Create a cron/scheduled task that runs:
```
python src/data_collection/fetch_all_gases.py && \
  pkill -f "uvicorn" && \
  uvicorn api.main:app --reload
```
so the dashboard always reflects the latest data.

That's it—run step 4 whenever you want fresh data, restart the backend, and enjoy a denser, richer heatmap. ✨
