"""
ERA5 Weather Data Fetcher (via Open-Meteo Archive API)

NOTE:
- This module uses ERA5 reanalysis data served through Open-Meteo.
- Open-Meteo internally processes ERA5 / ERA5-Land datasets and exposes
  them via a free REST API.
- This is NOT a direct CDS (Copernicus) NetCDF download.

Scientific intent:
- Provide near-surface wind and weather context for air pollution analysis
- Support simplified pollution movement tracking (educational / NSS use)

Variables used (Atmosphere - surface):
- 10m wind speed & direction
- 2m temperature
- Surface pressure
- Relative humidity
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path
import sys

# -------------------------------------------------------------------
# Project paths
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.utils.gas_config import RAW_DATA_DIR
except ImportError:
    RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Open-Meteo ERA5 Archive API
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# Open-Meteo Forecast API (Real-time/Current)
# -------------------------------------------------------------------

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Representative Indian cities (sampling points)
WEATHER_STATIONS = [
    {"name": "Delhi", "lat": 28.61, "lon": 77.21},
    {"name": "Mumbai", "lat": 19.08, "lon": 72.88},
    {"name": "Bangalore", "lat": 12.97, "lon": 77.59},
    {"name": "Chennai", "lat": 13.08, "lon": 80.27},
    {"name": "Kolkata", "lat": 22.57, "lon": 88.36},
    {"name": "Hyderabad", "lat": 17.39, "lon": 78.49},
    {"name": "Ahmedabad", "lat": 23.02, "lon": 72.57},
    {"name": "Pune", "lat": 18.52, "lon": 73.86},
    {"name": "Jaipur", "lat": 26.91, "lon": 75.79},
    {"name": "Lucknow", "lat": 26.85, "lon": 80.95},
    {"name": "Kanpur", "lat": 26.45, "lon": 80.33},
    {"name": "Nagpur", "lat": 21.15, "lon": 79.08},
    {"name": "Indore", "lat": 22.72, "lon": 75.86},
    {"name": "Patna", "lat": 25.59, "lon": 85.14},
    {"name": "Bhopal", "lat": 23.26, "lon": 77.41},
    {"name": "Visakhapatnam", "lat": 17.69, "lon": 83.22},
    {"name": "Surat", "lat": 21.17, "lon": 72.83},
    {"name": "Chandigarh", "lat": 30.73, "lon": 76.78},
    {"name": "Guwahati", "lat": 26.11, "lon": 91.71},
    {"name": "Kochi", "lat": 9.93, "lon": 76.26},
    {"name": "Srinagar", "lat": 34.08, "lon": 74.79},
    {"name": "Vijayawada", "lat": 16.51, "lon": 80.65},
    {"name": "Raipur", "lat": 21.25, "lon": 81.63},
]

# -------------------------------------------------------------------
# ERA5 Fetch Logic (via Open-Meteo)
# -------------------------------------------------------------------

def fetch_era5_weather(
    lat: float,
    lon: float,
    days_back: int = 1, # Unused for forecast params, keeping signature
    city_name: str = "Unknown",
) -> Optional[pd.DataFrame]:
    """
    Fetch CURRENT weather data using Open-Meteo Forecast API.
    """

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "relative_humidity_2m",
            "precipitation"
        ],
        "hourly": [
            "wind_speed_10m",
            "wind_direction_10m",
        ],
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "UTC",
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if "current" not in payload:
            return None
            
        current = payload["current"]
        
        # Create single record for 'now'
        records = [{
            "date": pd.to_datetime(current["time"], utc=True),
            "latitude": lat,
            "longitude": lon,
            "city": city_name,
            "temperature": current["temperature_2m"],
            "pressure": current["surface_pressure"],
            "wind_speed": current["wind_speed_10m"],
            "wind_direction": current["wind_direction_10m"],
            "humidity": current["relative_humidity_2m"],
            "total_precipitation": current.get("precipitation", 0),
            "source": "Open-Meteo Forecast (Live)",
        }]

        df = pd.DataFrame(records)
        return df

    except Exception as exc:
        print(f"[ERA5] Error for {city_name}: {exc}")
        return None


def fetch_era5_all_cities(
    cities: List[Dict] = None,
    days_back: int = 7,
) -> pd.DataFrame:
    """Fetch ERA5 weather data for multiple cities."""

    if cities is None:
        cities = WEATHER_STATIONS

    print("\n" + "=" * 70)
    print("ERA5 WEATHER DATA COLLECTION (Open-Meteo)")
    print("=" * 70)

    all_data = []

    for idx, city in enumerate(cities, start=1):
        print(f"[{idx}/{len(cities)}] {city['name']}...", end=" ")

        df = fetch_era5_weather(
            lat=city["lat"],
            lon=city["lon"],
            days_back=days_back,
            city_name=city["name"],
        )

        if df is not None and not df.empty:
            all_data.append(df)
            print(f"✓ {len(df)} records")
        else:
            print("✗ No data")

    if not all_data:
        print("[ERA5] No weather data collected")
        return pd.DataFrame()

    combined = pd.concat(all_data, ignore_index=True)

    print("\nSummary:")
    print(combined.groupby("city").size())
    print("\nWind statistics:")
    print(f"  Mean wind speed: {combined['wind_speed'].mean():.2f} km/h")
    print(f"  Max wind speed: {combined['wind_speed'].max():.2f} km/h")
    print(f"  Mean temperature: {combined['temperature'].mean():.2f} °C")
    print("=" * 70)

    return combined


# -------------------------------------------------------------------
# Wind Vector Utilities
# -------------------------------------------------------------------

def calculate_wind_components(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wind speed & direction into U/V components.

    Convention:
    - U: eastward
    - V: northward
    """

    data = df.copy()
    direction_rad = np.deg2rad(data["wind_direction"])

    data["wind_u"] = -data["wind_speed"] * np.sin(direction_rad)
    data["wind_v"] = -data["wind_speed"] * np.cos(direction_rad)

    return data


# -------------------------------------------------------------------
# Simplified Pollution Movement Tracking (Educational)
# -------------------------------------------------------------------

def track_pollution_movement(
    pollution_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    hours_forward: int = 12,
) -> pd.DataFrame:
    """
    Estimate pollution movement using CURRENT wind conditions.
    Approximation: Assumes wind stays constant for the next few hours (Nowcast).
    """

    print("[Tracking] Estimating pollution movement using LIVE wind...")

    pollution_df = pollution_df.copy()
    weather_df = weather_df.copy()

    # Calculate U/V once
    weather_df = calculate_wind_components(weather_df)
    
    # We only care about the latest weather for each city
    latest_weather = weather_df.groupby('city').last().reset_index()

    tracked = []

    for _, p_row in pollution_df.iterrows():
        # Find nearest weather station
        # Simple Euclidean distance approximation for speed
        latest_weather['dist'] = (latest_weather['latitude'] - p_row['latitude'])**2 + \
                                 (latest_weather['longitude'] - p_row['longitude'])**2
        
        nearest = latest_weather.loc[latest_weather['dist'].idxmin()]
        
        # Only track if weather station is somewhat close (e.g. < 2 degrees ~ 200km)
        if nearest['dist'] > 4.0: 
            continue

        # Project movement
        for h in range(1, hours_forward + 1):
             # Scale factor tuning
            scale = 0.01 
            
            tracked.append({
                "original_lat": p_row["latitude"],
                "original_lon": p_row["longitude"],
                "predicted_lat": p_row["latitude"] + nearest["wind_v"] * h * scale,
                "predicted_lon": p_row["longitude"] + nearest["wind_u"] * h * scale,
                "hours_ahead": h,
                "value": p_row["value"],
                "parameter": p_row["parameter"],
                "wind_speed": nearest["wind_speed"],
                "wind_direction": nearest["wind_direction"],
            })

    if not tracked:
        print("[Tracking] No matches found")
        return pd.DataFrame()

    print(f"[Tracking] ✓ Generated {len(tracked)} movement points (Arrows)")
    return pd.DataFrame(tracked)


# -------------------------------------------------------------------
# Persistence
# -------------------------------------------------------------------

def save_weather_data(df: pd.DataFrame):
    """Save ERA5 weather data to raw directory."""
    if df.empty:
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    latest = RAW_DATA_DIR / "era5_weather_latest.csv"
    timestamped = RAW_DATA_DIR / f"era5_weather_{timestamp}.csv"

    df.to_csv(latest, index=False)
    df.to_csv(timestamped, index=False)

    print(f"[ERA5] Saved:")
    print(f"  {latest}")
    print(f"  {timestamped}")


# -------------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------------

def main():
    df = fetch_era5_all_cities(days_back=7)

    if df.empty:
        print("[ERA5] Failed to collect weather data")
        return

    save_weather_data(df)

    # Optional test: pollution movement
    pollution_file = RAW_DATA_DIR / "all_gases_data_latest.csv"
    if pollution_file.exists():
        pollution_df = pd.read_csv(pollution_file)
        tracked = track_pollution_movement(pollution_df, df, hours_forward=12)

        if not tracked.empty:
            out = RAW_DATA_DIR / "pollution_tracking_latest.csv"
            tracked.to_csv(out, index=False)
            print(f"[Tracking] Saved → {out}")


if __name__ == "__main__":
    main()
