"""
Fetch pollution data from the World Air Quality Index (WAQI) API.

PM2.5 is treated specially:
- PM2.5 is APPENDED over time to build dense coverage
- Other gases remain snapshot-based
"""

import time
from datetime import datetime, timezone
from typing import List, Dict, Optional

import pandas as pd
import requests

from src.utils.gas_config import (
    WAQI_API_TOKEN,
    WAQI_BOUNDS,
    RAW_DATA_DIR,
    GAS_UNITS,
)

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

WAQI_MAP_BOUNDS_URL = "https://api.waqi.info/map/bounds/"
WAQI_FEED_URL = "https://api.waqi.info/feed/@{uid}/"

TARGET_PARAMETERS = ["pm25", "no2", "co", "so2", "pm10", "o3"]
DEFAULT_STATION_LIMIT = 150

PM25_HISTORY_FILE = RAW_DATA_DIR / "waqi_pm25_history.csv"


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def fetch_station_list(limit: int = DEFAULT_STATION_LIMIT) -> List[Dict]:
    """Fetch list of WAQI stations within geographic bounds"""
    params = {
        "token": WAQI_API_TOKEN,
        "latlng": (
            f"{WAQI_BOUNDS['min_lat']},{WAQI_BOUNDS['min_lon']},"
            f"{WAQI_BOUNDS['max_lat']},{WAQI_BOUNDS['max_lon']}"
        ),
    }

    response = requests.get(
        WAQI_MAP_BOUNDS_URL,
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(f"WAQI bounds API error: {payload}")

    stations = payload.get("data", [])
    
    # --- Priority City Logic ---
    # Major cities to ensure coverage even if AQI is low
    PRIORITY_CITIES = ['Hyderabad', 'Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Ahmedabad', 'Pune']
    priority_list = []
    other_list = []
    
    seen_cities = set()
    for s in stations:
        name = s.get('station', {}).get('name', '').lower()
        is_priority = any(p.lower() in name for p in PRIORITY_CITIES)
        
        # Extract city if possible to avoid duplicates for the same city in priority
        city_match = next((p for p in PRIORITY_CITIES if p.lower() in name), None)
        
        if is_priority and city_match not in seen_cities:
            priority_list.append(s)
            if city_match: seen_cities.add(city_match)
        else:
            other_list.append(s)
            
    # Sort remaining by AQI
    other_list = sorted(other_list, key=lambda s: s.get("aqi", 0), reverse=True)
    
    # Combine (Priority first, then top polluted)
    final_stations = priority_list + other_list
    return final_stations[:limit]


def fetch_station_measurements(uid: int) -> Optional[Dict]:
    """Fetch detailed data for a single WAQI station"""
    params = {"token": WAQI_API_TOKEN}

    response = requests.get(
        WAQI_FEED_URL.format(uid=uid),
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("status") != "ok":
        return None

    return payload.get("data")


def _parse_timestamp(data: Dict) -> datetime:
    """
    Robust timestamp parsing:
    - Handles ISO strings with or without timezone
    - Always returns UTC datetime
    """
    raw = data.get("time", {}).get("iso") or data.get("time", {}).get("s")

    if not raw:
        return datetime.utcnow()

    try:
        # Normalize Z → +00:00
        raw = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
    except Exception:
        return datetime.utcnow()

    # Ensure UTC & tz-naive consistency
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt


def parse_station_data(data: Dict) -> List[Dict]:
    """Convert WAQI station payload to row records"""
    rows = []

    iaqi = data.get("iaqi", {})
    station = data.get("city", {})
    lat, lon = station.get("geo", [None, None])

    timestamp = _parse_timestamp(data)

    for param in TARGET_PARAMETERS:
        pdata = iaqi.get(param)
        if not pdata or pdata.get("v") is None:
            continue

        rows.append(
            {
                "date": timestamp,
                "latitude": lat,
                "longitude": lon,
                "parameter": param,
                "value": float(pdata["v"]),
                "unit": GAS_UNITS.get(param, "index"),
                "location": station.get("name", ""),
                "source": "WAQI",
                "station_uid": data.get("idx"),
            }
        )

    return rows


# -------------------------------------------------------------------
# Main Fetch Logic
# -------------------------------------------------------------------

def fetch_waqi_data(
    limit: int = DEFAULT_STATION_LIMIT,
    sleep_seconds: float = 0.5,
) -> pd.DataFrame:
    if not WAQI_API_TOKEN:
        print("[WARN] WAQI token missing.")
        return pd.DataFrame()

    print(f"[INFO] Fetching WAQI data (limit={limit})")

    stations = fetch_station_list(limit)
    all_rows: List[Dict] = []

    for index, station in enumerate(stations, start=1):
        uid = station.get("uid")
        if uid is None:
            continue

        try:
            data = fetch_station_measurements(uid)
            if data:
                all_rows.extend(parse_station_data(data))
        except Exception as exc:
            print(f"[WARN] Failed station {uid}: {exc}")

        time.sleep(sleep_seconds)

        if index % 25 == 0:
            print(f"  Processed {index}/{len(stations)} stations")

    df = pd.DataFrame(all_rows)

    if df.empty:
        print("[WARN] No WAQI measurements collected")
        return df

    # ✅ CRITICAL FIX: normalize datetimes safely
    df["date"] = pd.to_datetime(
        df["date"],
        utc=True,
        errors="coerce",
    )
    df = df.dropna(subset=["date"])

    # ----------------------------------------------------------------
    # PM2.5 APPEND LOGIC (PRESERVED)
    # ----------------------------------------------------------------

    pm25_df = df[df["parameter"] == "pm25"]
    other_df = df[df["parameter"] != "pm25"]

    if not pm25_df.empty:
        if PM25_HISTORY_FILE.exists():
            old = pd.read_csv(PM25_HISTORY_FILE, parse_dates=["date"])
            pm25_df = pd.concat([old, pm25_df], ignore_index=True)

        pm25_df.drop_duplicates(
            subset=["station_uid", "date"],
            inplace=True,
        )

        pm25_df.to_csv(PM25_HISTORY_FILE, index=False)
        print(f"[OK] PM2.5 history size: {len(pm25_df)}")

    # Snapshot file (unchanged behavior)
    output_path = RAW_DATA_DIR / "waqi_data_latest.csv"
    other_df.to_csv(output_path, index=False)
    print(f"[OK] Saved {len(other_df)} WAQI snapshot measurements to {output_path}")

    # Combined view for pipeline
    combined = pd.concat([pm25_df, other_df], ignore_index=True)
    return combined


if __name__ == "__main__":
    fetch_waqi_data()
