"""
FastAPI Backend for Air Pollution Monitoring System
Gas-Specific, Scientifically Honest Implementation
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import sys

# ----------------------------------------------------------------------------
# Path setup
# ----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.gas_config import RAW_DATA_DIR
from src.utils.gas_config import (
    get_gas_config,
    get_color_for_value,
    get_category_for_value,
    validate_value_range,
    get_all_supported_gases,
)

# ----------------------------------------------------------------------------
# App setup
# ----------------------------------------------------------------------------

app = FastAPI(
    title="Air Pollution Monitoring API",
    description="Gas-specific air pollution monitoring for India",
    version="2.0.0",
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
    latitude: float
    longitude: float
    gas: str = "pm25"


class PredictionResponse(BaseModel):
    predicted_value: float
    gas: str
    unit: str
    message: str


class HotspotLocation(BaseModel):
    latitude: float
    longitude: float
    avg_value: float
    cluster: int
    color: str
    category: str
    data_points: int  # Number of measurements in this hotspot


class DataPoint(BaseModel):
    date: str
    latitude: float
    longitude: float
    value: float
    parameter: str
    location: Optional[str] = None
    color: str
    category: str


class DataCoverage(BaseModel):
    gas: str
    total_points: int
    unique_locations: int
    date_range: Dict[str, str]
    coverage_quality: str  # "good", "moderate", "sparse", "insufficient"
    geographic_bounds: Dict[str, float]


class GasInfo(BaseModel):
    parameter: str
    name: str
    unit: str
    description: str
    max_scale: float
    available: bool
    data_points: int


# ----------------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------------

def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and types."""
    df = df.rename(columns={"lat": "latitude", "lon": "longitude"})
    
    if "parameter" not in df.columns:
        df["parameter"] = "pm25"
    
    df["parameter"] = df["parameter"].str.lower()
    
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    return df


def _load_all_data() -> Optional[pd.DataFrame]:
    """Load all available pollution data."""
    datasets: List[pd.DataFrame] = []
    
    # Combined gases dataset
    combined_files = list(RAW_DATA_DIR.glob("all_gases_data*.csv"))
    if combined_files:
        latest_file = max(combined_files, key=lambda f: f.stat().st_mtime)
        try:
            df = pd.read_csv(latest_file)
            df = _normalize_dataframe(df)
            datasets.append(df)
            print(f"[OK] Loaded: {latest_file.name} ({len(df)} rows)")
        except Exception as e:
            print(f"[ERROR] Failed to load {latest_file.name}: {e}")
    
    # Individual gas files
    for pattern in ["waqi_*.csv", "sentinel_*.csv", "modis_*.csv"]:
        for file in RAW_DATA_DIR.glob(pattern):
            try:
                df = pd.read_csv(file)
                df = _normalize_dataframe(df)
                datasets.append(df)
                print(f"[OK] Loaded: {file.name} ({len(df)} rows)")
            except Exception as e:
                print(f"[ERROR] Failed to load {file.name}: {e}")
    
    if not datasets:
        print("[WARN] No data files found")
        return None
    
    combined = pd.concat(datasets, ignore_index=True)
    combined = combined.dropna(subset=["latitude", "longitude", "value"])
    
    # Validate ranges
    valid_rows = []
    for _, row in combined.iterrows():
        gas = row["parameter"]
        value = row["value"]
        if validate_value_range(gas, value):
            valid_rows.append(row)
        else:
            print(f"[WARN] Invalid value for {gas}: {value} (skipped)")
    
    if not valid_rows:
        return None
    
    result = pd.DataFrame(valid_rows)
    print(f"[OK] Total valid records: {len(result)}")
    return result


def _grid_coordinates(lat: float, lon: float, grid_size: float = 0.05) -> tuple:
    """Round coordinates to grid cell (0.05° ≈ 5km in India)."""
    lat_grid = round(lat / grid_size) * grid_size
    lon_grid = round(lon / grid_size) * grid_size
    return lat_grid, lon_grid


# ----------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Air Pollution Monitoring API for India",
        "version": "2.0.0",
        "supported_gases": get_all_supported_gases(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/gases", response_model=List[GasInfo])
def list_available_gases():
    """List all supported gases and their availability."""
    df = _load_all_data()
    
    result = []
    for gas in get_all_supported_gases():
        config = get_gas_config(gas)
        
        if df is not None:
            gas_data = df[df["parameter"] == gas]
            available = len(gas_data) > 0
            data_points = len(gas_data)
        else:
            available = False
            data_points = 0
        
        result.append(
            GasInfo(
                parameter=gas,
                name=config["name"],
                unit=config["unit"],
                description=config["description"],
                max_scale=config["max_scale"],
                available=available,
                data_points=data_points,
            )
        )
    
    return result


@app.get("/coverage")
def get_data_coverage(gas: str = "pm25"):
    """Get data coverage statistics for a specific gas."""
    df = _load_all_data()
    
    if df is None:
        raise HTTPException(status_code=503, detail="No data available")
    
    gas_lower = gas.lower()
    gas_df = df[df["parameter"] == gas_lower]
    
    if gas_df.empty:
        return DataCoverage(
            gas=gas_lower,
            total_points=0,
            unique_locations=0,
            date_range={"start": "N/A", "end": "N/A"},
            coverage_quality="insufficient",
            geographic_bounds={"min_lat": 0, "max_lat": 0, "min_lon": 0, "max_lon": 0},
        )
    
    # Calculate coverage quality
    total_points = len(gas_df)
    unique_locations = len(gas_df.groupby(["latitude", "longitude"]))
    
    if total_points < 10:
        quality = "insufficient"
    elif total_points < 50:
        quality = "sparse"
    elif total_points < 200:
        quality = "moderate"
    else:
        quality = "good"
    
    # Date range
    dates = gas_df["date"].dropna()
    date_range = {
        "start": dates.min().isoformat() if len(dates) > 0 else "N/A",
        "end": dates.max().isoformat() if len(dates) > 0 else "N/A",
    }
    
    # Geographic bounds
    bounds = {
        "min_lat": float(gas_df["latitude"].min()),
        "max_lat": float(gas_df["latitude"].max()),
        "min_lon": float(gas_df["longitude"].min()),
        "max_lon": float(gas_df["longitude"].max()),
    }
    
    return DataCoverage(
        gas=gas_lower,
        total_points=total_points,
        unique_locations=unique_locations,
        date_range=date_range,
        coverage_quality=quality,
        geographic_bounds=bounds,
    )


@app.get("/data/recent", response_model=List[DataPoint])
def get_recent_data(gas: str = "pm25", limit: int = 500):
    """Get recent data points for a specific gas."""
    df = _load_all_data()
    
    if df is None:
        return []
    
    gas_lower = gas.lower()
    gas_df = df[df["parameter"] == gas_lower].copy()
    
    if gas_df.empty:
        return []
    
    # Sort by date (most recent first) and limit
    gas_df = gas_df.sort_values("date", ascending=False, na_position="last")
    gas_df = gas_df.head(limit)
    
    response: List[DataPoint] = []
    
    for _, row in gas_df.iterrows():
        value = float(row["value"])
        
        response.append(
            DataPoint(
                date=row["date"].isoformat() if pd.notna(row["date"]) else datetime.utcnow().isoformat(),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                value=value,
                parameter=gas_lower,
                location=row.get("location", ""),
                color=get_color_for_value(gas_lower, value),
                category=get_category_for_value(gas_lower, value),
            )
        )
    
    return response


@app.get("/hotspots", response_model=List[HotspotLocation])
def get_hotspots(gas: str = "pm25", min_points: int = 3, top_n: int = 15):
    """
    Identify pollution hotspots using grid-based aggregation.
    Returns top N grid cells with highest average pollution.
    """
    df = _load_all_data()
    
    if df is None:
        return []
    
    gas_lower = gas.lower()
    gas_df = df[df["parameter"] == gas_lower].copy()
    
    if gas_df.empty:
        return []
    
    # Grid-based aggregation (0.05° ≈ 5km)
    gas_df["lat_grid"], gas_df["lon_grid"] = zip(
        *gas_df.apply(lambda row: _grid_coordinates(row["latitude"], row["longitude"]), axis=1)
    )
    
    # Group by grid cell
    grouped = (
        gas_df.groupby(["lat_grid", "lon_grid"])
        .agg(
            avg_value=("value", "mean"),
            count=("value", "count"),
        )
        .reset_index()
    )
    
    # Filter by minimum points
    grouped = grouped[grouped["count"] >= min_points]
    
    if grouped.empty:
        return []
    
    # Sort by average value (descending) and take top N
    grouped = grouped.sort_values("avg_value", ascending=False).head(top_n)
    
    hotspots: List[HotspotLocation] = []
    
    for idx, row in enumerate(grouped.itertuples(), start=1):
        avg_val = row.avg_value
        
        hotspots.append(
            HotspotLocation(
                latitude=row.lat_grid,
                longitude=row.lon_grid,
                avg_value=round(avg_val, 2),
                cluster=((idx - 1) // 5) + 1,  # Group into clusters of 5
                color=get_color_for_value(gas_lower, avg_val),
                category=get_category_for_value(gas_lower, avg_val),
                data_points=int(row.count),
            )
        )
    
    return hotspots


@app.get("/stats")
def get_statistics(gas: str = "pm25"):
    """Get statistical summary for a specific gas."""
    df = _load_all_data()
    
    if df is None:
        raise HTTPException(status_code=503, detail="No data available")
    
    gas_lower = gas.lower()
    gas_df = df[df["parameter"] == gas_lower]
    
    if gas_df.empty:
        return {
            "gas": gas_lower,
            "available": False,
            "message": f"No data available for {gas_lower}",
        }
    
    config = get_gas_config(gas_lower)
    values = gas_df["value"].dropna()
    
    return {
        "gas": gas_lower,
        "name": config["name"],
        "unit": config["unit"],
        "available": True,
        "count": int(len(values)),
        "mean": round(float(values.mean()), 2),
        "median": round(float(values.median()), 2),
        "min": round(float(values.min()), 2),
        "max": round(float(values.max()), 2),
        "std": round(float(values.std()), 2),
        "category_distribution": {
            "good": int((values <= config["thresholds"]["good"]).sum()),
            "moderate": int(
                ((values > config["thresholds"]["good"]) & (values <= config["thresholds"]["moderate"])).sum()
            ),
            "unhealthy": int((values > config["thresholds"]["moderate"]).sum()),
        },
    }


@app.post("/predict", response_model=PredictionResponse)
def predict_value(request: PredictionRequest):
    """
    Placeholder for ML prediction.
    Currently returns nearest neighbor average.
    """
    df = _load_all_data()
    
    if df is None:
        raise HTTPException(status_code=503, detail="No data available for prediction")
    
    gas_lower = request.gas.lower()
    gas_df = df[df["parameter"] == gas_lower]
    
    if gas_df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {gas_lower}")
    
    # Simple nearest neighbor (within 0.1° ≈ 10km)
    nearby = gas_df[
        (abs(gas_df["latitude"] - request.latitude) < 0.1)
        & (abs(gas_df["longitude"] - request.longitude) < 0.1)
    ]
    
    if nearby.empty:
        # Fallback: use overall average
        predicted = float(gas_df["value"].mean())
        message = "No nearby data. Using regional average."
    else:
        predicted = float(nearby["value"].mean())
        message = f"Based on {len(nearby)} nearby measurements"
    
    config = get_gas_config(gas_lower)
    
    return PredictionResponse(
        predicted_value=round(predicted, 2),
        gas=gas_lower,
        unit=config["unit"],
        message=message,
    )


# ----------------------------------------------------------------------------
# Startup
# ----------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 60)
    print("Air Pollution Monitoring API - Starting")
    print("=" * 60)
    
    # Check data availability
    df = _load_all_data()
    if df is not None:
        gases = df["parameter"].unique()
        print(f"\n✓ Data loaded successfully")
        print(f"  Available gases: {', '.join(gases)}")
        print(f"  Total records: {len(df)}")
    else:
        print("\n⚠ WARNING: No data files found!")
        print("  Place CSV files in:", RAW_DATA_DIR)
    
    print("\n" + "=" * 60)
    print("API ready at: http://localhost:8000")
    print("Documentation: http://localhost:8000/docs")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")