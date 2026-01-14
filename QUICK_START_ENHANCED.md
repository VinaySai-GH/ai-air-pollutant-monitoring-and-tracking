# 🚀 Quick Start - Enhanced Multi-Source System

## ✅ What's New

Your system now uses **4 data sources** for maximum coverage:
1. **WAQI API** - ~150 ground stations (PM₂.₅, NO₂, CO, SO₂)
2. **Sentinel-5P** - Satellite data (NO₂, CO, SO₂)
3. **MODIS AOD** - Satellite PM₂.₅ proxy
4. **OpenAQ** - Optional fallback

---

## 🎯 Quick Setup (3 Steps)

### Step 1: Verify Configuration

Your WAQI token is already configured! Check `.env` has:
```env
WAQI_API_TOKEN=6567b6d060c9b0323689e7bb3ab7027d539f3e46
MAPBOX_ACCESS_TOKEN=your_mapbox_token
```

### Step 2: Test Data Collection (Optional)

Test if all sources work:
```bash
python test_data_collection.py
```

This will quickly test each data source with small samples.

### Step 3: Fetch All Data

Run the unified collection script:
```bash
python src/data_collection/fetch_all_gases.py
```

**Expected output:**
- WAQI: ~150-600 measurements (4 gases × stations)
- Sentinel-5P: ~108 measurements (3 gases × grid)
- MODIS: ~49 measurements (PM₂.₅ proxy × grid)
- **Total: ~300-750 data points**

**Time:** 5-15 minutes (WAQI API rate limits)

---

## 🖥️ Start the System

### Backend
```bash
python api/main.py
```

### Dashboard
Open `dashboard/index.html` in your browser

---

## 📊 What You'll See

### Heatmap
- **All data sources** contribute to the heatmap
- Ground stations + satellite grid = full coverage
- Click anywhere to see pollution values

### Hotspots
- **Per-gas hotspots** from all sources
- Top pollution locations identified
- Toggle on/off in dashboard

### Statistics
- **Averages** from all sources combined
- **Station counts** (ground + grid points)
- Updates when switching gases

---

## 🎯 Data Sources Summary

| Gas | WAQI | Sentinel-5P | MODIS | Total Coverage |
|-----|------|-------------|-------|----------------|
| PM₂.₅ | ✅ ~150 stations | ❌ | ✅ ~49 grid | **Excellent** |
| NO₂ | ✅ ~150 stations | ✅ ~36 grid | ❌ | **Excellent** |
| CO | ✅ ~150 stations | ✅ ~36 grid | ❌ | **Excellent** |
| SO₂ | ✅ ~150 stations | ✅ ~36 grid | ❌ | **Excellent** |

---

## 🔧 Troubleshooting

### "WAQI token missing"
- Token is already in config, but check `.env` if needed

### "Google Earth Engine not initialized"
```bash
earthengine authenticate
earthengine set_project "your-project-id"
```

### "No data collected"
- Check internet connection
- Verify API tokens
- Run `test_data_collection.py` to diagnose

### Slow WAQI fetching
- Normal! Rate limits require 0.5s delay between stations
- ~150 stations = ~75 seconds minimum
- Progress shown every 25 stations

---

## 📈 Expected Results

After running `fetch_all_gases.py`:

```
Summary by gas:
           count      mean       min       max
pm25       200+     45.2      12.0      180.0
no2        180+     28.5       5.0       95.0
co         150+      2.1       0.5       8.5
so2        120+     15.3       2.0       65.0
```

**All data saved to:** `data/raw/all_gases_data_latest.csv`

---

## 🎉 You're Ready!

Your system now has:
- ✅ **Maximum data coverage** (4 sources)
- ✅ **All 4 gases** (PM₂.₅, NO₂, CO, SO₂)
- ✅ **Ground + satellite** data
- ✅ **Full India coverage**
- ✅ **No data wasted** - everything used for visualization

**See `DATA_SOURCES_SUMMARY.md` for complete details!**
