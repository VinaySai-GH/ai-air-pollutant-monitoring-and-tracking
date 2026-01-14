"""
Fetch pollution data from the World Air Quality Index (WAQI) API.

PM2.5 is treated specially:
- PM2.5 is APPENDED over time to build dense coverage
- Other gases remain snapshot-based
"""

import time
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import requests

from src.utils.config import WAQI_API_TOKEN, WAQI_BOUNDS, RAW_DATA_DIR, GAS_UNITS

WAQI_MAP_BOUNDS_URL = "https://api.waqi.info/map/bounds/"
WAQI_FEED_URL = "https://api.waqi.info/feed/@{uid}/"
TARGET_PARAMETERS = ["pm25", "no2", "co", "so2"]
DEFAULT_STATION_LIMIT = 150

PM25_HISTORY_FILE = RAW_DATA_DIR / "waqi_pm25_history.csv"


def fetch_station_list(limit: int = DEFAULT_STATION_LIMIT) -> List[Dict]:
    params = {
        "token": WAQI_API_TOKEN,
        "latlng": f"{WAQI_BOUNDS['min_lat']},{WAQI_BOUNDS['min_lon']},"
        f"{WAQI_BOUNDS['max_lat']},{WAQI_BOUNDS['max_lon']}",
    }
    response = requests.get(WAQI_MAP_BOUNDS_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(f"WAQI bounds API error: {payload}")
    stations = payload.get("data", [])
    stations = sorted(stations, key=lambda s: s.get("aqi", 0), reverse=True)
    return stations[:limit]


def fetch_station_measurements(uid: int) -> Optional[Dict]:
    params = {"token": WAQI_API_TOKEN}
    response = requests.get(WAQI_FEED_URL.format(uid=uid), params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "ok":
        return None
    return payload.get("data")


def parse_station_data(data: Dict) -> List[Dict]:
    rows = []

    iaqi = data.get("iaqi", {})
    station = data.get("city", {})
    lat, lon = station.get("geo", [None, None])

    timestamp = data.get("time", {}).get("iso") or data.get("time", {}).get("s")
    if timestamp:
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        timestamp = datetime.utcnow()

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


def fetch_waqi_data(limit: int = DEFAULT_STATION_LIMIT, sleep_seconds: float = 0.5) -> pd.DataFrame:
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
            if not data:
                continue
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

    df["date"] = pd.to_datetime(df["date"])

    # ===============================
    # PM2.5 APPEND LOGIC (NEW)
    # ===============================
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

    # Return combined view (important for pipeline)
    combined = pd.concat([pm25_df, other_df], ignore_index=True)
    return combined


if __name__ == "__main__":
    fetch_waqi_data()
