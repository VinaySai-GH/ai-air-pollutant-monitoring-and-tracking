"""
FastAPI Backend for Air Pollution Monitoring System
PM2.5-FIRST & HISTORY-AWARE VERSION
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
import sys
import random

# ----------------------------------------------------------------------------
# Path setup
# ----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import RAW_DATA_DIR
from src.utils.pollution_colors import (
    get_pollution_color,
    get_pollution_category,
)

# ----------------------------------------------------------------------------
# App setup
# ----------------------------------------------------------------------------

app = FastAPI(
    title="Air Pollution Monitoring API",
    description="PM2.5-first Air Pollution Monitoring API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Data models
# ----------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PredictionResponse(BaseModel):
    predicted_pm25: float
    message: str


class HotspotLocation(BaseModel):
    latitude: float
    longitude: float
    avg_pm25: float
    cluster: int
    color: Optional[str] = None
    category: Optional[str] = None


class DataPoint(BaseModel):
    date: str
    latitude: float
    longitude: float
    value: float
    parameter: str
    location: Optional[str] = None
    color: Optional[str] = None
    category: Optional[str] = None


# ----------------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------------

def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names and types across all data sources.
    """

    # Latitude / Longitude consistency
    df = df.rename(
        columns={
            "lat": "latitude",
            "lon": "longitude",
        }
    )

    # Ensure parameter column exists
    if "parameter" not in df.columns:
        df["parameter"] = "pm25"

    df["parameter"] = df["parameter"].str.lower()

    # Ensure datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


# ----------------------------------------------------------------------------
# Data loading (PM2.5-first)
# ----------------------------------------------------------------------------

def load_latest_data() -> Optional[pd.DataFrame]:
    """
    Load ALL available pollution data.
    PM2.5 history is always included if present.
    """

    datasets: List[pd.DataFrame] = []

    # 1️⃣ Combined gases dataset
    combined_files = list(RAW_DATA_DIR.glob("all_gases_data*.csv"))
    if combined_files:
        latest_file = max(combined_files, key=lambda f: f.stat().st_mtime)
        df = pd.read_csv(latest_file)
        df = _normalize_dataframe(df)
        datasets.append(df)
        print(f"[OK] Loaded combined data: {latest_file.name} ({len(df)})")

    # 2️⃣ WAQI PM2.5 history (most important)
    pm25_history_path = RAW_DATA_DIR / "waqi_pm25_history.csv"
    if pm25_history_path.exists():
        df = pd.read_csv(pm25_history_path)
        df = df.rename(columns={"pm25": "value"})
        df["parameter"] = "pm25"
        df = _normalize_dataframe(df)
        datasets.append(df)
        print(f"[OK] Loaded PM2.5 history: {len(df)}")

    # 3️⃣ MODIS PM2.5 proxy
    modis_files = list(RAW_DATA_DIR.glob("modis_aod_data*.csv"))
    if modis_files:
        latest_file = max(modis_files, key=lambda f: f.stat().st_mtime)
        df = pd.read_csv(latest_file)
        df = _normalize_dataframe(df)
        datasets.append(df)
        print(f"[OK] Loaded MODIS PM2.5: {len(df)}")

    if not datasets:
        print("[WARN] No real data found")
        return None

    combined = pd.concat(datasets, ignore_index=True)
    combined = combined.dropna(subset=["latitude", "longitude", "value"])

    print(f"[OK] Total records loaded: {len(combined)}")
    return combined


# ----------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "running",
        "message": "PM2.5-first Air Pollution Monitoring API",
        "primary_pollutant": "pm25",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ----------------------------------------------------------------------------
# Recent data (heatmap)
# ----------------------------------------------------------------------------

@app.get("/data/recent", response_model=List[DataPoint])
def get_recent_data(
    limit: int = 300,
    parameter: str = "pm25",
):
    df = load_latest_data()
    if df is None or df.empty:
        return []

    parameter = parameter.lower()
    df = df[df["parameter"] == parameter]

    if df.empty:
        return []

    # PM2.5 → spatial sampling
    if parameter == "pm25":
        df = df.sample(
            n=min(limit, len(df)),
            random_state=42,
        )
    else:
        df = df.sort_values("date", ascending=False).head(limit)

    response: List[DataPoint] = []

    for _, row in df.iterrows():
        value = float(row["value"])

        # Down-weight MODIS proxy
        if row.get("source") == "MODIS_AOD":
            value *= 0.7

        response.append(
            DataPoint(
                date=row["date"].isoformat() if pd.notna(row["date"]) else "",
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                value=value,
                parameter=parameter,
                location=row.get("location", ""),
                color=get_pollution_color(value, parameter),
                category=get_pollution_category(value, parameter),
            )
        )

    return response


# ----------------------------------------------------------------------------
# Hotspots (PM2.5-first)
# ----------------------------------------------------------------------------

@app.get("/hotspots", response_model=List[HotspotLocation])
def get_hotspots():
    df = load_latest_data()
    if df is None or df.empty:
        return []

    df = df[df["parameter"] == "pm25"]
    if df.empty:
        return []

    grouped = (
        df.groupby(["latitude", "longitude"])
        .agg(
            avg_pm25=("value", "mean"),
            count=("value", "count"),
        )
        .reset_index()
    )

    grouped = grouped[grouped["count"] >= 3]
    grouped = grouped.sort_values("avg_pm25", ascending=False).head(10)

    hotspots: List[HotspotLocation] = []

    for idx, row in enumerate(grouped.itertuples(), start=1):
        pm25 = row.avg_pm25
        hotspots.append(
            HotspotLocation(
                latitude=row.latitude,
                longitude=row.longitude,
                avg_pm25=pm25,
                cluster=((idx - 1) // 3) + 1,
                color=get_pollution_color(pm25, "pm25"),
                category=get_pollution_category(pm25, "pm25"),
            )
        )

    return hotspots


# ----------------------------------------------------------------------------
# Prediction (placeholder)
# ----------------------------------------------------------------------------

@app.post("/predict", response_model=PredictionResponse)
def predict_pm25(_: PredictionRequest):
    return PredictionResponse(
        predicted_pm25=round(random.uniform(50, 150), 2),
        message="Dummy prediction (replace with ML model later)",
    )


# ----------------------------------------------------------------------------
# Local run
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("\nStarting PM2.5-first API")
    print("http://localhost:8000")
    print("Docs: http://localhost:8000/docs\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
