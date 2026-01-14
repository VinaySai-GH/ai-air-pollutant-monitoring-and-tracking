# 📊 Data Sources Overview (Updated)

The system now aggregates **three** independent sources to maximize coverage and data quality:

| Source | Parameters | Coverage | Notes |
| --- | --- | --- | --- |
| WAQI (World Air Quality Index) | PM₂.₅, NO₂, CO, SO₂ | Ground stations across India | Uses your token `6567...` to pull up to 150 stations |
| Sentinel-5P (Google Earth Engine) | NO₂, SO₂, CO | Satellite grid over India | 5 km sampling grid averaged over the last 7 days |
| MODIS AOD (Google Earth Engine) | PM₂.₅ (estimated) | Satellite grid over India | Based on the workflow from the [MODIS AOD analysis repo](https://github.com/DIVYA-ctrl-dot/Air-Pollution-Aerosol-Optical-Depth-Analysis) |

## WAQI Details
- Endpoint: `map/bounds` to list stations, `feed/@uid` for pollutant breakdown.
- File generated: `data/raw/waqi_data_latest.csv`.
- Provides live ground truth for all four gases.

## Sentinel-5P Details
- Datasets: `COPERNICUS/S5P/OFFL/L3_NO2`, `L3_SO2`, `L3_CO`.
- We sample a 6x6 grid covering India for better spatial granularity.
- File generated: `data/raw/sentinel5p_data_latest.csv`.

## MODIS AOD ➝ PM₂.₅
- Dataset: `MODIS/006/MOD08_M3` monthly AOD composite.
- Inspired by the MODIS how-to shared in the referenced GitHub repo.
- We approximate PM₂.₅ as `AOD * 120` (scaling factor can be tuned) and store the raw AOD for transparency.
- File generated: `data/raw/modis_aod_data_latest.csv` with both AOD and PM₂.₅.

## Unified Dataset
Running `python src/data_collection/fetch_all_gases.py` now:
1. Pulls WAQI station data.
2. Samples Sentinel-5P gases across the grid.
3. Samples MODIS AOD and converts it to PM₂.₅ proxy.
4. Writes `data/raw/all_gases_data_latest.csv`, which the backend loads first.

## When Data is Missing
- If a source fails (e.g., GEE auth), the script continues with the remaining sources so you always have something to visualize.
- The backend will automatically pick up any parameters present in the combined file.

## Next Ideas
- Increase `WAQI_MAX_STATIONS` in `.env` for denser ground coverage.
- Adjust the MODIS scaling factor once you calibrate it against WAQI PM₂.₅.
- Extend the GEE grid size (increase `num_points`) for finer heatmaps.

Feel free to ask if you'd like to plug in additional APIs (e.g., CPCB official feed) or expand beyond India.
