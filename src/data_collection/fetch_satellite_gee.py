"""
Robust Sentinel-5P and MODIS data collection using Google Earth Engine
"""

import os
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Optional

import ee
import pandas as pd
import numpy as np

from src.utils.gas_config import WAQI_BOUNDS, RAW_DATA_DIR, GAS_UNITS


# ===============================
# EARTH ENGINE INIT
# ===============================
def initialize_earth_engine():
    try:
        ee.Initialize()
    except Exception:
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            ee.Initialize()
        else:
            raise RuntimeError("Earth Engine not authenticated")


# ===============================
# GRID CREATION
# ===============================
def create_grid(bounds: Dict, num_points: int = 25):
    grid_size = int(num_points ** 0.5)

    lons = np.linspace(bounds["min_lon"], bounds["max_lon"], grid_size + 1)
    lats = np.linspace(bounds["min_lat"], bounds["max_lat"], grid_size + 1)

    grid = []
    for i in range(grid_size):
        for j in range(grid_size):
            grid.append({
                "min_lon": lons[i],
                "max_lon": lons[i + 1],
                "min_lat": lats[j],
                "max_lat": lats[j + 1],
                "lon": (lons[i] + lons[i + 1]) / 2,
                "lat": (lats[j] + lats[j + 1]) / 2,
            })
    return grid


# ===============================
# SENTINEL-5P
# ===============================
def fetch_sentinel5p_grid(
    parameters: List[str],
    days_back: int = 14,
    num_points: Optional[int] = None,
):
    initialize_earth_engine()

    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days_back)

    grid = create_grid(WAQI_BOUNDS, num_points or 25)

    dataset_map = {
        "no2": ("COPERNICUS/S5P/OFFL/L3_NO2", "NO2_column_number_density"),
        "so2": ("COPERNICUS/S5P/OFFL/L3_SO2", "SO2_column_number_density"),
        "co": ("COPERNICUS/S5P/OFFL/L3_CO", "CO_column_number_density"),
    }

    rows = []

    for param in parameters:
        if param not in dataset_map:
            continue

        dataset, band = dataset_map[param]

        collection = (
            ee.ImageCollection(dataset)
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .select(band)
        )

        image = collection.mean()

        for cell in grid:
            region = ee.Geometry.Rectangle(
                [cell["min_lon"], cell["min_lat"], cell["max_lon"], cell["max_lat"]]
            )

            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=10000,
                maxPixels=1e9,
            )

            stats_dict = stats.getInfo()
            if not stats_dict:
                continue

            value = stats_dict.get(band)
            if value is None:
                continue

            rows.append({
                "date": end_date,
                "latitude": cell["lat"],
                "longitude": cell["lon"],
                "parameter": param,
                "value": float(value),
                "unit": "mol/m² (column)",
                "source": "Sentinel-5P",
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(RAW_DATA_DIR / "sentinel5p_data_latest.csv", index=False)

    return df


# ===============================
# MODIS AOD
# ===============================
def fetch_modis_aod(
    months_back: int = 6,
    num_points: Optional[int] = None,
):
    initialize_earth_engine()

    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=months_back * 30)

    grid = create_grid(WAQI_BOUNDS, num_points or 25)

    collection = (
        ee.ImageCollection("MODIS/061/MOD08_M3")
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        .select("Aerosol_Optical_Depth_Land_Ocean_Mean_Mean")
    )

    image = collection.mean()
    rows = []

    for cell in grid:
        region = ee.Geometry.Rectangle(
            [cell["min_lon"], cell["min_lat"], cell["max_lon"], cell["max_lat"]]
        )

        stats = image.reduceRegion(
            ee.Reducer.mean(),
            region,
            scale=20000,
            maxPixels=1e9,
        )

        stats_dict = stats.getInfo()
        if not stats_dict:
            continue

        value = stats_dict.get("Aerosol_Optical_Depth_Land_Ocean_Mean_Mean")
        if value is None:
            continue

        pm25_proxy = float(value) * 120.0

        rows.append({
            "date": end_date,
            "latitude": cell["lat"],
            "longitude": cell["lon"],
            "parameter": "pm25",
            "value": pm25_proxy,
            "unit": GAS_UNITS["pm25"],
            "source": "MODIS_AOD",
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(RAW_DATA_DIR / "modis_aod_data_latest.csv", index=False)

    return df
