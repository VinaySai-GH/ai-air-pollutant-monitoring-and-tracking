"""
Complete FastAPI Backend - Updated for FREE Google Gemini Chatbot

Changes:
- Replaced Anthropic Claude with Google Gemini (FREE)
- All other features remain the same
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import sys
import os
# PROPER MANUAL ENV LOADER
# Because standard libraries are failing on this specific Windows environment

def manual_load_env():
    """Manually parses .env file to ensure keys are loaded."""
    try:
        # Search for .env in current and parent directories
        current = Path.cwd()
        possible_paths = [
            current / ".env",
            current.parent / ".env",
            Path(__file__).parent.parent / ".env"
        ]
        
        target_path = None
        for p in possible_paths:
            if p.exists():
                target_path = p
                break
                
        if not target_path:
            print("[CRITICAL] .env file NOT FOUND in any standard location.")
            return

        print(f"[INFO] Loading .env from: {target_path}")
        
        # Use utf-8-sig to handle Windows BOM if present
        with open(target_path, "r", encoding="utf-8-sig") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"): continue
                
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                        
                    os.environ[key] = value
                    if "API_KEY" in key or "TOKEN" in key:
                         print(f"[DEBUG] Line {line_num}: Loaded {key}")

        # Verify GROQ
        if "GROQ_API_KEY" in os.environ:
             print(f"[SUCCESS] GROQ_API_KEY loaded: {os.environ['GROQ_API_KEY'][:5]}...")
        else:
             print("[ERROR] .env loaded but GROQ_API_KEY not found in file content.")
             print(f"[DEBUG] Keys found: {[k for k in os.environ.keys() if 'API_KEY' in k]}")
             
    except Exception as e:
        print(f"[ERROR] Failed to manually load .env: {e}")

# Execute loader
manual_load_env()

# Path setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import utilities
try:
    from src.utils.gas_config import (
        get_gas_config,
        get_color_for_value,
        get_category_for_value,
        get_all_supported_gases,
        RAW_DATA_DIR
    )
    USE_GAS_CONFIG = True
except ImportError:
    print("[WARN] gas_config.py not found, using fallback")
    USE_GAS_CONFIG = False
    RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
    
    def get_all_supported_gases():
        return ["pm25", "pm10", "no2", "so2", "co", "o3"]
    
    def get_gas_config(gas):
        configs = {
            "pm25": {"name": "PM2.5", "unit": "µg/m³", "max_scale": 250},
            "pm10": {"name": "PM10", "unit": "µg/m³", "max_scale": 350},
            "no2": {"name": "NO₂", "unit": "µg/m³", "max_scale": 200},
            "so2": {"name": "SO₂", "unit": "µg/m³", "max_scale": 100},
            "co": {"name": "CO", "unit": "mg/m³", "max_scale": 10},
            "o3": {"name": "O₃", "unit": "µg/m³", "max_scale": 200},
        }
        return configs.get(gas, configs["pm25"])
    
    def get_color_for_value(gas, value):
        config = get_gas_config(gas)
        max_val = config["max_scale"]
        if value <= max_val * 0.2: return "#00E400"
        elif value <= max_val * 0.4: return "#FFFF00"
        elif value <= max_val * 0.6: return "#FF7E00"
        elif value <= max_val * 0.8: return "#FF0000"
        else: return "#8F3F97"
    
    def get_category_for_value(gas, value):
        config = get_gas_config(gas)
        max_val = config["max_scale"]
        if value <= max_val * 0.2: return "Good"
        elif value <= max_val * 0.4: return "Moderate"
        elif value <= max_val * 0.6: return "Unhealthy for Sensitive"
        elif value <= max_val * 0.8: return "Unhealthy"
        else: return "Very Unhealthy"

# Import ML models
try:
    from src.models.hotspot_detection import HotspotDetector, PollutionPredictor, get_ranked_warnings
    from src.models.forecasting import PollutionForecaster
    HAS_ML = True
except ImportError:
    print("[WARN] ML models not available")
    HAS_ML = False

# Import Google Gemini for FREE chatbot
# Check for Groq
try:
    from groq import Groq
    HAS_CHATBOT = True
    print("[INFO] ✅ Groq SDK detected")
except ImportError:
    HAS_CHATBOT = False
    print("[WARN] Groq not installed. Run: pip install groq")

# Indian cities
INDIAN_CITIES = [
    (28.61, 77.21, "Delhi"),
    (19.08, 72.88, "Mumbai"),
    (12.97, 77.59, "Bangalore"),
    (13.08, 80.27, "Chennai"),
    (22.57, 88.36, "Kolkata"),
    (17.39, 78.49, "Hyderabad"),
    (23.02, 72.57, "Ahmedabad"),
    (18.52, 73.86, "Pune"),
]

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Air Pollution Monitoring API",
    description="Real-time air quality monitoring with ML and FREE AI chatbot",
    version="4.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATA MODELS
# ============================================================================

class DataSourceInfo(BaseModel):
    gas: str
    name: str
    sources: List[str]
    measurements: int

class GasStatistics(BaseModel):
    gas: str
    name: str
    unit: str
    measurements: int
    mean: Optional[float] = None
    median: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    std: Optional[float] = None
    available: bool = True

class DataPoint(BaseModel):
    date: str
    latitude: float
    longitude: float
    value: float
    parameter: str
    location: Optional[str] = None
    color: str
    category: str

class HotspotLocation(BaseModel):
    rank: int
    city_name: str
    latitude: float
    longitude: float
    avg_value: float
    cluster: int
    color: str
    category: str
    data_points: int

class PredictionRequest(BaseModel):
    latitude: float
    longitude: float
    gas: str = "pm25"

class PredictionResponse(BaseModel):
    predicted_value: float
    gas: str
    unit: str
    city_name: str
    message: str
    color: str
    category: str

class ChatbotRequest(BaseModel):
    message: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    context: Optional[Dict[str, Any]] = None

class ChatbotResponse(BaseModel):
    response: str
    timestamp: str

class WindData(BaseModel):
    city: str
    latitude: float
    longitude: float
    wind_speed: float
    wind_direction: float
    temperature: float
    date: str


class TrackingPoint(BaseModel):
    latitude: float
    longitude: float
    angle: float
    speed: float
    color: str = "#888888"

class SourceStats(BaseModel):
    source: str
    count: int
    percentage: float

class WarningAlert(BaseModel):
    title: str
    message: str
    severity: str  # high, medium, low
    type: str     # influence, dispersion

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_nearest_city(lat: float, lon: float) -> str:
    """Find nearest Indian city"""
    min_dist = float('inf')
    nearest_city = "Unknown"
    
    for city_lat, city_lon, city_name in INDIAN_CITIES:
        dist = ((lat - city_lat)**2 + (lon - city_lon)**2)**0.5
        if dist < min_dist:
            min_dist = dist
            nearest_city = city_name
    
    return f"Near {nearest_city}" if min_dist > 0.5 else nearest_city

def load_data() -> Optional[pd.DataFrame]:
    """Load latest data"""
    data_file = RAW_DATA_DIR / "all_gases_data_latest.csv"
    
    if not data_file.exists():
        print(f"[WARN] No data at {data_file}")
        return None
    
    try:
        df = pd.read_csv(data_file, parse_dates=['date'])
        df['parameter'] = df['parameter'].str.lower()
        # Ensure date is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df
    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        return None

def load_weather_data() -> Optional[pd.DataFrame]:
    """Load weather data"""
    weather_file = RAW_DATA_DIR / "era5_weather_latest.csv"
    
    if not weather_file.exists():
        return None
    
    try:
        return pd.read_csv(weather_file)
    except Exception as e:
        print(f"[ERROR] Failed to load weather: {e}")
        return None

# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Air Pollution Monitoring API with ML & FREE AI",
        "version": "4.1.0",
        "features": [
            "Real data (OpenAQ, WAQI)",
            "ML predictions & hotspot detection",
            "FREE AI chatbot (Google Gemini)",
            "Pollution tracking with wind data"
        ],
        "supported_gases": get_all_supported_gases(),
        "chatbot": "Google Gemini (Free)" if HAS_CHATBOT else "Not configured"
    }

@app.get("/health")
def health():
    """Health check"""
    df = load_data()
    weather_df = load_weather_data()
    
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_available": df is not None,
        "data_records": len(df) if df is not None else 0,
        "weather_available": weather_df is not None,
        "ml_available": HAS_ML,
        "chatbot_available": HAS_CHATBOT,
        "chatbot_provider": "Google Gemini (Free)" if HAS_CHATBOT else None,
    }

# ============================================================================
# DATA ENDPOINTS (same as before)
# ============================================================================

@app.get("/data-sources", response_model=List[DataSourceInfo])
def get_data_sources():
    """Get data source information"""
    df = load_data()
    
    result = []
    for gas in get_all_supported_gases():
        config = get_gas_config(gas)
        
        measurements = 0
        if df is not None:
            measurements = len(df[df["parameter"] == gas])
        
        sources = ["OpenAQ", "WAQI"]
        
        result.append(
            DataSourceInfo(
                gas=gas,
                name=config["name"],
                sources=sources,
                measurements=measurements,
            )
        )
    
    return result

@app.get("/stats/all", response_model=List[GasStatistics])
def get_all_statistics():
    """Get statistics for all gases"""
    df = load_data()
    
    if df is None:
        return []
    
    result = []
    
    for gas in get_all_supported_gases():
        gas_df = df[df["parameter"] == gas]
        config = get_gas_config(gas)
        
        if gas_df.empty:
            result.append(
                GasStatistics(
                    gas=gas,
                    name=config["name"],
                    unit=config["unit"],
                    measurements=0,
                    available=False,
                )
            )
        else:
            values = gas_df["value"].dropna()
            result.append(
                GasStatistics(
                    gas=gas,
                    name=config["name"],
                    unit=config["unit"],
                    measurements=len(values),
                    mean=round(float(values.mean()), 2),
                    median=round(float(values.median()), 2),
                    min=round(float(values.min()), 2),
                    max=round(float(values.max()), 2),
                    std=round(float(values.std()), 2),
                    available=True,
                )
            )
    
    return result

@app.get("/stats/sources", response_model=List[SourceStats])
def get_source_statistics():
    """Get contribution breakdown by source"""
    df = load_data()
    if df is None or df.empty:
        return []
    
    total = len(df)
    counts = df['source'].value_counts().to_dict()
    
    result = []
    for source, count in counts.items():
        result.append(SourceStats(
            source=source,
            count=int(count),
            percentage=round((count / total) * 100, 1)
        ))
    
    # Sort by count descending
    result.sort(key=lambda x: x.count, reverse=True)
    return result

@app.get("/stats")
def get_statistics(gas: str = "pm25"):
    """Get statistics for specific gas"""
    df = load_data()
    
    if df is None:
        raise HTTPException(status_code=503, detail="No data available")
    
    gas_lower = gas.lower()
    gas_df = df[df["parameter"] == gas_lower]
    
    if gas_df.empty:
        return {"gas": gas_lower, "available": False}
    
    config = get_gas_config(gas_lower)
    values = gas_df["value"].dropna()
    
    return {
        "gas": gas_lower,
        "name": config["name"],
        "unit": config["unit"],
        "available": True,
        "measurements": int(len(values)),
        "mean": round(float(values.mean()), 2),
        "median": round(float(values.median()), 2),
        "min": round(float(values.min()), 2),
        "max": round(float(values.max()), 2),
        "std": round(float(values.std()), 2),
    }

@app.get("/data/recent", response_model=List[DataPoint])
def get_recent_data(gas: str = "pm25", limit: int = 500):
    """Get recent measurements"""
    df = load_data()
    
    if df is None:
        return []
    
    gas_df = df[df["parameter"] == gas.lower()].copy()
    
    if gas_df.empty:
        return []
    
    if 'date' in gas_df.columns:
        gas_df['date'] = pd.to_datetime(gas_df['date'], errors='coerce', format='mixed')
        gas_df = gas_df.dropna(subset=['date'])
        gas_df = gas_df.sort_values('date', ascending=False)
    
    gas_df = gas_df.head(limit)
    
    # FILTER: Remove Unknown locations (as requested)
    gas_df = gas_df[gas_df['location'] != 'Unknown']
    
    result = []
    for _, row in gas_df.iterrows():
        result.append(DataPoint(
            date=str(row.get('date', datetime.now(timezone.utc))),
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            value=float(row['value']),
            parameter=row['parameter'],
            location=row['location'] if pd.notna(row.get('location')) else 'Unknown',
            color=get_color_for_value(gas.lower(), row['value']),
            category=get_category_for_value(gas.lower(), row['value']),
        ))
    
    return result

# ============================================================================
# HOTSPOT DETECTION
# ============================================================================

@app.get("/hotspots", response_model=List[HotspotLocation])
def get_hotspots(gas: str = "pm25", top_n: int = 10):
    """Get pollution hotspots"""
    if not HAS_ML:
        return []
        
    try:
        df = load_data()
        if df is None or df.empty:
            return []
        
        # FILTER: Remove Unknown locations
        df = df[df['location'] != 'Unknown']
        
        detector = HotspotDetector(method='kmeans', n_clusters=15)
        hotspots = detector.detect_hotspots(df, parameter=gas.lower())
        
        if hotspots.empty:
            return []
        
        hotspots = hotspots.head(top_n)
        
        result = []
        for _, row in hotspots.iterrows():
            result.append(HotspotLocation(
                rank=int(row['rank']),
                city_name=row['city_name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                avg_value=round(float(row['avg_value']), 2),
                cluster=int(row['cluster']),
                color=get_color_for_value(gas.lower(), row['avg_value']),
                category=get_category_for_value(gas.lower(), row['avg_value']),
                data_points=int(row['data_points']),
            ))
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Hotspot detection failed: {e}")
        return []

# ============================================================================
# PREDICTION
# ============================================================================

@app.post("/predict", response_model=PredictionResponse)
def predict_pollution(request: PredictionRequest):
    """Predict pollution at location"""
    
    if not HAS_ML:
        raise HTTPException(status_code=503, detail="ML models not available")
    
    try:
        predictor = PollutionPredictor()
        predicted = predictor.predict(
            request.latitude,
            request.longitude,
            parameter=request.gas.lower()
        )
        
        config = get_gas_config(request.gas.lower())
        city_name = find_nearest_city(request.latitude, request.longitude)
        
        return PredictionResponse(
            predicted_value=round(predicted, 2),
            gas=request.gas.lower(),
            unit=config["unit"],
            city_name=city_name,
            message=f"ML prediction using Random Forest model",
            color=get_color_for_value(request.gas.lower(), predicted),
            category=get_category_for_value(request.gas.lower(), predicted),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predict/forecast/{city_name}")
def get_forecast(city_name: str):
    """Get 24-hour pollution forecast for a city"""
    df = load_data()
    
    if df is None:
        raise HTTPException(status_code=503, detail="No data available")
        
    try:
        forecaster = PollutionForecaster()
        result = forecaster.predict_next_24h(df, city=city_name)
        
        if not result:
            return {"error": f"Not enough data to forecast for {city_name}"}
            
        return result
        
    except Exception as e:
        print(f"[ERROR] Forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WIND & TRACKING
# ============================================================================

@app.get("/weather/current", response_model=List[WindData])
def get_current_weather():
    """Get current weather conditions"""
    weather_df = load_weather_data()
    
    if weather_df is None:
        return []
    
    weather_df['date'] = pd.to_datetime(weather_df['date'])
    latest = weather_df.sort_values('date').groupby('city').tail(1)
    
    result = []
    for _, row in latest.iterrows():
        result.append(WindData(
            city=row['city'],
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            wind_speed=round(float(row['wind_speed']), 1),
            wind_direction=round(float(row['wind_direction']), 1),
            temperature=round(float(row['temperature']), 1),
            date=str(row['date']),
        ))
    
    return result

# ============================================================================
# ADVANCED FEATURES (Arrows & Warnings)
# ============================================================================

@app.get("/tracking", response_model=List[TrackingPoint])
def get_pollution_tracking():
    """Get pollution movement vectors"""
    tracking_file = RAW_DATA_DIR / "pollution_tracking_latest.csv"
    
    if not tracking_file.exists():
        return []
        
    try:
        # Read a sample to keep it light
        df = pd.read_csv(tracking_file)
        
        # Smarter sampling: if we have too many points, sample; otherwise show all
        if len(df) > 2000:
            df = df.iloc[::10, :] 
        elif len(df) > 500:
            df = df.iloc[::5, :]
        result = []
        for _, row in df.iterrows():
                try:
                    # Use original_lat/lon for compatibility with CSV
                    lat = row.get('original_lat')
                    lon = row.get('original_lon')
                    angle = row.get('wind_direction') or 0
                    speed = row.get('wind_speed') or 0
                    
                    if pd.isna(lat) or pd.isna(lon):
                        continue

                    result.append(TrackingPoint(
                        latitude=float(lat),
                        longitude=float(lon),
                        angle=float(angle), 
                        speed=float(speed),
                        color="#888888"
                    ))
                except (ValueError, TypeError):
                    continue
        return result
    except Exception as e:
        print(f"[ERROR] Tracking failed: {e}")
        return []

@app.get("/stats/sources", response_model=List[SourceStats])
def get_source_stats():
    """Get contribution stats from each data source"""
    data_df = load_data()
    if data_df is None or data_df.empty:
        return []
        
    counts = data_df['source'].value_counts()
    total = len(data_df)
    
    stats = []
    for source, count in counts.items():
        stats.append({
            "source": source,
            "count": int(count),
            "percentage": round((count / total) * 100, 1)
        })
    return stats

@app.get("/warnings", response_model=List[WarningAlert])
def get_warnings():
    """Get influence warnings and dispersion insights"""
    alerts = []
    
    weather_df = load_weather_data()
    data_df = load_data()
    
    # 1. Weather Analysis (General Insights)
    if weather_df is not None and not weather_df.empty:
        try:
            latest_weather = weather_df.sort_values('date').tail(1).iloc[0].to_dict()
            city = latest_weather.get('city', 'the region')
            precip = latest_weather.get('total_precipitation', 0)
            ws = latest_weather.get('wind_speed', 0)
            
            # Washout Insight
            if precip > 0.05:
                 alerts.append(WarningAlert(
                    title=f"Washout: {city}", 
                    message=f"Precipitation ({precip:.2f} mm) in {city} is actively reducing particulate concentration through washout.", 
                    severity="low", 
                    type="dispersion"
                ))

            # Dispersion/Stagnation Insight
            if ws > 20.0:
                alerts.append(WarningAlert(
                    title=f"Dispersion: {city}", 
                    message=f"Strong winds ({ws:.1f} km/h) in {city} are preventing local accumulation but may transport pollutants to downwind areas.", 
                    severity="medium", 
                    type="dispersion"
                ))
            elif ws < 5.0:
                 alerts.append(WarningAlert(
                    title=f"Stagnation: {city}", 
                    message=f"Low wind speed ({ws:.1f} km/h) in {city} is trapping pollutants near sources, increasing local health risks.", 
                    severity="high", 
                    type="dispersion"
                ))
        except Exception as e:
            print(f"[WARN] Weather analysis in warnings failed: {e}")

    # 2. Regional Influence (Weighted Top 4) using new logic from hotspot_detection.py
    if data_df is not None and weather_df is not None and not weather_df.empty:
        # The new get_ranked_warnings handles the complex score and ranking
        top_warnings = get_ranked_warnings(data_df, weather_df, top_n=4)
        
        latest_weather = weather_df.sort_values('date').iloc[-1]
        wind_speed = latest_weather.get('wind_speed', 0)
        wind_dir = latest_weather.get('wind_direction', 0)
        precip = latest_weather.get('total_precipitation', 0)
        drift_dir = get_cardinal_direction(wind_dir + 180)

        for item in top_warnings:
            city = item['city']
            val = item['avg_value']
            score = item['score']
            
            msg = f"Pollution level {val:.1f} µg/m³"
            if wind_speed > 10:
                msg += f" is drifting {drift_dir} (Influence Score: {score:.1f})."
            else:
                msg += f" is stagnant (Influence Score: {score:.1f})."
                
            if precip > 0.1:
                msg += " Impact mitigated by active rainfall."

            alerts.append(WarningAlert(
                title=f"Top Alert: {city}",
                message=msg,
                severity="high" if val > 150 or score > 200 else "medium",
                type="influence"
            ))
    
    # Clean and deduplicate alerts (by title)
    unique_alerts = []
    seen_titles = set()
    for alert in alerts:
        if alert.title not in seen_titles:
            unique_alerts.append(alert)
            seen_titles.add(alert.title)
    
    return unique_alerts[:6]

def get_cardinal_direction(degrees):
    """Helper to convert degrees to text"""
    degrees = degrees % 360
    if 45 <= degrees < 135: return "East"
    if 135 <= degrees < 225: return "South"
    if 225 <= degrees < 315: return "West"
    return "North" 

# ============================================================================
# FREE AI CHATBOT (GOOGLE GEMINI)
# ============================================================================

@app.post("/chatbot", response_model=ChatbotResponse)
async def chatbot(request: ChatbotRequest):
    """FREE AI chatbot using Groq (Llama 3)"""
    
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        return ChatbotResponse(
            response="❌ Chatbot not configured. Missing GROQ_API_KEY.",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    try:
        # 1. Gather Global Context
        df = load_data()
        weather_df = load_weather_data()
        
        context_lines = []
        user_local_context = ""

        if df is not None and not df.empty:
            # National Averages
            stats = df.groupby('parameter')['value'].mean().to_dict()
            avg_str = " | ".join([f"{p.upper()}: {v:.1f}" for p, v in stats.items()])
            context_lines.append(f"National Average Levels: {avg_str}")
            
            # Hyper-local context if coordinates provided
            if request.latitude is not None and request.longitude is not None:
                # Find nearest stations within ~50km
                df['dist'] = np.sqrt((df['latitude'] - request.latitude)**2 + (df['longitude'] - request.longitude)**2)
                nearby = df[df['dist'] < 0.5].sort_values('dist').head(3)
                
                if not nearby.empty:
                    city = find_nearest_city(request.latitude, request.longitude)
                    local_vals = " | ".join([f"{row['parameter'].upper()}: {row['value']:.1f}" for _, row in nearby.iterrows()])
                    user_local_context = f"\nUSER LOCATION CONTEXT: User is in/near {city}. Local levels observed: {local_vals}"
                else:
                    user_local_context = f"\nUSER LOCATION CONTEXT: User at ({request.latitude}, {request.longitude}), but no stations found within 50km."

            # Hotspots
            hotspots = df.sort_values('value', ascending=False).head(5)
            hotspot_str = ", ".join([f"{row['location']} ({row['parameter'].upper()}: {row['value']:.1f})" for _, row in hotspots.iterrows()])
            context_lines.append(f"Current Peak Hotspots: {hotspot_str}")
            
        # Get active warnings
        try:
            active_warnings = get_warnings()
            if active_warnings:
                warning_str = " | ".join([f"{w.title}: {w.message}" for w in active_warnings[:3]])
                context_lines.append(f"Active Meteorological Warnings: {warning_str}")
        except:
            pass
            
        context_info = "\n".join(context_lines) + user_local_context

        system_prompt = f"""You are 'AirAware Pro', a premium AI Environmental Scientist and friendly project assistant.
        
        CURRENT SYSTEM DATA (Reference if relevant):
        {context_info}
        
        YOUR GUIDELINES:
        1. CONVERSATIONAL & EXPERT: You are a high-level LLM. Answer general questions normally. You don't HAVE to mention data if the user is just chatting or asking general science questions.
        2. DATA-AWARE: When asked about current conditions, locations, or trends, use the 'CURRENT SYSTEM DATA' provided above.
        3. PERSONALITY: Be professional, authoritative, but also engaging and friendly. Not robotic.
        4. BREVITY: Keep answers concise but complete. No strict sentence limits, but avoid long essays unless requested.
        5. FORMATTING: Use **bolding** for critical values or important terms.
        """

        # Initialize Groq Client
        from groq import Groq
        client = Groq(api_key=groq_key)
        
        # Generate
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": request.message,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.6,
            max_tokens=400,
            top_p=1,
            stream=False,
        )
        
        return ChatbotResponse(
            response=chat_completion.choices[0].message.content,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        print(f"[ERROR] Chatbot failed: {e}")
        return ChatbotResponse(
            response=f"Error: {str(e)}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 70)
    print("🌍 AIR POLLUTION MONITORING API")
    print("=" * 70)
    print("\n🤖 Chatbot: Google Gemini (FREE)" if HAS_CHATBOT else "\n⚠️  Chatbot: Not configured")
    if not HAS_CHATBOT:
        print("   Get FREE key: https://makersuite.google.com/app/apikey")
    print("\n🚀 Starting server...")
    print("📍 API: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("🎨 Dashboard: Open dashboard/index.html")
    print("\nPress CTRL+C to stop")
    print("=" * 70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)