"""
Data collection orchestrator with automatic mock data generation
Ensures data is always available for testing
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.utils.gas_config import RAW_DATA_DIR, SUPPORTED_GASES
except ImportError:
    RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUPPORTED_GASES = ["pm25", "pm10", "no2", "so2", "co", "o3"]

try:
    from src.data_collection.fetch_waqi import fetch_waqi_data
    from src.data_collection.fetch_satellite_gee import fetch_sentinel5p_grid, fetch_modis_aod
    from src.data_collection.fetch_openaq_sdk import fetch_real_openaq_data_sdk
    REAL_SOURCES_AVAILABLE = True
except ImportError:
    print("[WARN] Data collection modules not found - will use mock data only")
    REAL_SOURCES_AVAILABLE = False


# Indian cities with realistic pollution patterns
INDIAN_CITIES = [
    (28.61, 77.21, "Delhi", 100, 220),           # High pollution
    (28.70, 77.10, "Delhi NCR", 95, 210),
    (19.08, 72.88, "Mumbai", 70, 150),
    (13.08, 80.27, "Chennai", 60, 130),
    (22.57, 88.36, "Kolkata", 80, 180),
    (12.97, 77.59, "Bangalore", 55, 120),
    (17.39, 78.49, "Hyderabad", 70, 160),
    (23.02, 72.57, "Ahmedabad", 85, 190),
    (18.52, 73.86, "Pune", 55, 110),
    (26.91, 75.79, "Jaipur", 90, 210),
    (30.73, 76.78, "Chandigarh", 95, 220),
    (21.15, 79.08, "Nagpur", 65, 140),
    (23.26, 77.41, "Bhopal", 70, 150),
    (25.59, 85.14, "Patna", 95, 220),
    (26.85, 80.95, "Lucknow", 100, 230),
]


def generate_realistic_mock_data(num_points_per_city: int = 25) -> pd.DataFrame:
    """
    Generate realistic mock data for Indian cities
    Covers all supported gases with realistic pollution patterns
    """
    print("\n" + "=" * 70)
    print("GENERATING MOCK DATA FOR TESTING")
    print("=" * 70)
    
    data_rows = []
    
    for city_lat, city_lon, city_name, min_pm25, max_pm25 in INDIAN_CITIES:
        # PM2.5 (primary pollutant)
        for _ in range(num_points_per_city):
            pm25_value = np.random.uniform(min_pm25, max_pm25)
            lat_offset = np.random.uniform(-0.15, 0.15)  # ~15km radius
            lon_offset = np.random.uniform(-0.15, 0.15)
            hours_ago = np.random.randint(0, 72)  # Last 3 days
            
            data_rows.append({
                "date": datetime.utcnow() - timedelta(hours=hours_ago),
                "latitude": city_lat + lat_offset,
                "longitude": city_lon + lon_offset,
                "parameter": "pm25",
                "value": pm25_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # PM10 (coarse particles)
        for _ in range(num_points_per_city // 2):
            pm10_value = np.random.uniform(min_pm25 * 1.5, max_pm25 * 1.5)
            lat_offset = np.random.uniform(-0.15, 0.15)
            lon_offset = np.random.uniform(-0.15, 0.15)
            hours_ago = np.random.randint(0, 72)
            
            data_rows.append({
                "date": datetime.utcnow() - timedelta(hours=hours_ago),
                "latitude": city_lat + lat_offset,
                "longitude": city_lon + lon_offset,
                "parameter": "pm10",
                "value": pm10_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # NO2 (traffic-related)
        for _ in range(num_points_per_city // 3):
            no2_value = np.random.uniform(30, 120)
            lat_offset = np.random.uniform(-0.15, 0.15)
            lon_offset = np.random.uniform(-0.15, 0.15)
            hours_ago = np.random.randint(0, 72)
            
            data_rows.append({
                "date": datetime.utcnow() - timedelta(hours=hours_ago),
                "latitude": city_lat + lat_offset,
                "longitude": city_lon + lon_offset,
                "parameter": "no2",
                "value": no2_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # SO2 (industrial)
        for _ in range(num_points_per_city // 4):
            so2_value = np.random.uniform(15, 60)
            lat_offset = np.random.uniform(-0.15, 0.15)
            lon_offset = np.random.uniform(-0.15, 0.15)
            hours_ago = np.random.randint(0, 72)
            
            data_rows.append({
                "date": datetime.utcnow() - timedelta(hours=hours_ago),
                "latitude": city_lat + lat_offset,
                "longitude": city_lon + lon_offset,
                "parameter": "so2",
                "value": so2_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # CO (combustion)
        for _ in range(num_points_per_city // 5):
            co_value = np.random.uniform(0.5, 5.0)
            lat_offset = np.random.uniform(-0.15, 0.15)
            lon_offset = np.random.uniform(-0.15, 0.15)
            hours_ago = np.random.randint(0, 72)
            
            data_rows.append({
                "date": datetime.utcnow() - timedelta(hours=hours_ago),
                "latitude": city_lat + lat_offset,
                "longitude": city_lon + lon_offset,
                "parameter": "co",
                "value": co_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # O3 (ozone)
        for _ in range(num_points_per_city // 4):
            o3_value = np.random.uniform(40, 120)
            lat_offset = np.random.uniform(-0.15, 0.15)
            lon_offset = np.random.uniform(-0.15, 0.15)
            hours_ago = np.random.randint(0, 72)
            
            data_rows.append({
                "date": datetime.utcnow() - timedelta(hours=hours_ago),
                "latitude": city_lat + lat_offset,
                "longitude": city_lon + lon_offset,
                "parameter": "o3",
                "value": o3_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
    
    df = pd.DataFrame(data_rows)
    
    print(f"\n✓ Generated {len(df)} mock data points")
    print(f"  Cities covered: {len(INDIAN_CITIES)}")
    print(f"  Gases: {', '.join(df['parameter'].unique())}")
    print("\nData distribution:")
    print(df.groupby('parameter')['value'].agg(['count', 'mean', 'min', 'max']))
    
    return df


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and validate dataframe"""
    # Ensure column names
    df = df.rename(columns={"lat": "latitude", "lon": "longitude"})
    
    if "parameter" not in df.columns:
        df["parameter"] = "pm25"
    
    # CRITICAL: Force lowercase
    df["parameter"] = df["parameter"].str.lower()
    
    # Ensure dates
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    # Filter to India bounds (8°N to 37°N, 68°E to 97°E)
    df = df[
        (df["latitude"] >= 8.0) &
        (df["latitude"] <= 37.0) &
        (df["longitude"] >= 68.0) &
        (df["longitude"] <= 97.0)
    ]
    
    # Remove invalid values
    df = df[df["value"] > 0]
    df = df.dropna(subset=["latitude", "longitude", "value"])
    
    return df


def consolidate_dataframes(dfs: list) -> pd.DataFrame:
    """Consolidate multiple dataframes"""
    valid = [df for df in dfs if df is not None and not df.empty]
    if not valid:
        return pd.DataFrame()

    combined = pd.concat(valid, ignore_index=True)
    combined = normalize_dataframe(combined)
    
    return combined


def save_combined_data(df: pd.DataFrame):
    """Save data to CSV"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Save with timestamp
    timestamped_path = RAW_DATA_DIR / f"all_gases_data_{timestamp}.csv"
    df.to_csv(timestamped_path, index=False)
    
    # Save as latest
    latest_path = RAW_DATA_DIR / "all_gases_data_latest.csv"
    df.to_csv(latest_path, index=False)
    
    print(f"\n✓ Saved {len(df)} rows to:")
    print(f"  {latest_path}")
    print(f"  {timestamped_path}")


def fetch_all_sources(use_mock_if_needed: bool = True) -> pd.DataFrame:
    """
    Fetch from all sources, with automatic fallback to mock data
    """
    datasets = []
    
    if REAL_SOURCES_AVAILABLE:
        # Try WAQI
        try:
            print("\n[INFO] Fetching WAQI data...")
            waqi_df = fetch_waqi_data()
            if waqi_df is not None and not waqi_df.empty:
                datasets.append(waqi_df)
                print(f"✓ WAQI: {len(waqi_df)} rows")
        except Exception as e:
            print(f"✗ WAQI failed: {e}")
        
        # Try Sentinel-5P
        try:
            print("\n[INFO] Fetching Sentinel-5P data...")
            sentinel_df = fetch_sentinel5p_grid(["no2", "so2", "co"])
            if sentinel_df is not None and not sentinel_df.empty:
                datasets.append(sentinel_df)
                print(f"✓ Sentinel-5P: {len(sentinel_df)} rows")
        except Exception as e:
            print(f"✗ Sentinel-5P failed: {e}")
        
        # Try MODIS
        try:
            print("\n[INFO] Fetching MODIS data...")
            modis_df = fetch_modis_aod()
            if modis_df is not None and not modis_df.empty:
                datasets.append(modis_df)
                print(f"✓ MODIS: {len(modis_df)} rows")
        except Exception as e:
            print(f"✗ MODIS failed: {e}")

        # Try OpenAQ (New Integration)
        try:
            print("\n[INFO] Fetching OpenAQ data...")
            openaq_df = fetch_real_openaq_data_sdk(country_code="IN")
            if openaq_df is not None and not openaq_df.empty:
                datasets.append(openaq_df)
                print(f"✓ OpenAQ: {len(openaq_df)} rows")
        except Exception as e:
            print(f"✗ OpenAQ failed: {e}")
    
    # If no real data and mock requested
    if not datasets and use_mock_if_needed:
        print("\n⚠ WARNING: No real data sources available!")
        print("Generating mock data for testing...")
        mock_df = generate_realistic_mock_data()
        datasets.append(mock_df)
    
    if not datasets:
        print("\n✗ ERROR: No data available")
        return pd.DataFrame()
    
    return consolidate_dataframes(datasets)


def summarize(df: pd.DataFrame):
    """Print summary"""
    if df.empty:
        print("\n✗ Empty dataframe")
        return
    
    print("\n" + "=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)
    
    print(f"\nTotal records: {len(df)}")
    print(f"Geographic coverage: {df['latitude'].min():.1f}°N to {df['latitude'].max():.1f}°N")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    print("\nBy Gas:")
    summary = df.groupby("parameter")["value"].agg(["count", "mean", "min", "max"])
    print(summary)
    
    print("\nBy Source:")
    if "source" in df.columns:
        print(df.groupby("source").size())


def main():
    """Main execution"""
    print("\n" + "=" * 70)
    print("AIR POLLUTION DATA COLLECTION")
    print("=" * 70)
    
    # Ensure directory exists
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Fetch data
    df = fetch_all_sources(use_mock_if_needed=True)
    
    if df.empty:
        print("\n✗ ERROR: No data gathered")
        return
    
    # Save
    save_combined_data(df)
    
    # Summarize
    summarize(df)
    
    # --- AUTOMATED PIPELINE TRIGGERS ---
    print("\n" + "=" * 70)
    print("TRIGGERING AUTOMATED PIPELINE STEPS")
    print("=" * 70)
    
    # 1. Weather & Tracking
    try:
        from src.data_collection.fetch_era5_weather import fetch_era5_all_cities, track_pollution_movement, save_weather_data
        print("[PIPELINE] Fetching weather and generating tracking arrows...")
        weather_df = fetch_era5_all_cities()
        if not weather_df.empty:
            save_weather_data(weather_df)
            tracked_df = track_pollution_movement(df, weather_df)
            if not tracked_df.empty:
                tracked_path = RAW_DATA_DIR / "pollution_tracking_latest.csv"
                tracked_df.to_csv(tracked_path, index=False)
                print(f"✓ Tracking arrows generated: {tracked_path}")
    except Exception as e:
        print(f"✗ Tracking trigger failed: {e}")

    # 2. ML Retraining
    try:
        from src.models.hotspot_detection import train_hotspot_model
        print("[PIPELINE] Triggering Hotspot Model retraining...")
        train_hotspot_model()
        print("✓ Models retrained.")
    except Exception as e:
        print(f"✗ Model retraining failed: {e}")

    print("\n" + "=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Start backend: python main.py")
    print("2. Open frontend: http://localhost:8080")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()