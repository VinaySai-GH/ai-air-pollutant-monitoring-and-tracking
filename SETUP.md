# 🌍 Air Pollution Monitoring System - Quick Setup

## Get REAL Pollution Data (Worldwide)

### Step 1: Install Google Earth Engine

```bash
pip install earthengine-api
```

### Step 2: Set Up Google Earth Engine

**2a. Visit Earth Engine website:**
- Go to: https://code.earthengine.google.com/
- Sign in with your Google account
- Accept the terms of service when prompted
- This creates a free Earth Engine project for you

**2b. Authenticate:**
```bash
earthengine authenticate
```

This opens your browser - allow all permissions when asked.

### Step 3: Get Real Satellite Data

```bash
python src\data_collection\fetch_satellite_gee.py
```

(Note: Use backslashes `\` on Windows, forward slashes `/` on Mac/Linux)

This downloads REAL pollution data (NO2, SO2, CO) from satellites.

### Step 4: Start Backend

```bash
uvicorn api.main:app --reload
```

### Step 5: Open Dashboard

Open `dashboard/index.html` in your browser or:

```bash
cd dashboard
python -m http.server 8080
```

Visit: http://localhost:8080

---

## 🌎 Change Coverage Area

Edit `src/utils/config.py` (line 46):

**Worldwide**:
```python
AREA_OF_INTEREST = {
    "min_lon": -180.0,
    "min_lat": -90.0,
    "max_lon": 180.0,
    "max_lat": 90.0,
}
```

**India**:
```python
AREA_OF_INTEREST = {
    "min_lon": 68.0,
    "min_lat": 8.0,
    "max_lon": 97.0,
    "max_lat": 37.0,
}
```

Then run step 3 again to fetch data for that region.

---

## What You'll See

✅ REAL pollution heatmap with color-coded intensity
✅ Worldwide coverage (or any region you choose)
✅ Multiple pollutants: NO2, SO2, CO
✅ Weather data: temperature, wind speed

**NO sample data - everything is REAL!**
