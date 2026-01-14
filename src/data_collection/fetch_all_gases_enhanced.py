"""
Enhanced data orchestration with mock data fallback.
If no real data is available, generates realistic sample data for testing.
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.gas_config import RAW_DATA_DIR, SUPPORTED_GASES
from src.data_collection.fetch_waqi import fetch_waqi_data
from src.data_collection.fetch_satellite_gee import fetch_sentinel5p_grid, fetch_modis_aod

try:
    from src.utils.gas_config import validate_value_range
except ImportError:
    def validate_value_range(gas, value):
        return 0 <= value <= 1000  # Fallback validation


def generate_mock_data_for_india(num_points=200):
    """
    Generate realistic mock data for India when real data unavailable.
    Covers major Indian cities with realistic pollution patterns.
    """
    print("[INFO] Generating mock data for testing...")
    
    # Major Indian cities (lat, lon, typical PM2.5 range)
    indian_cities = [
        (28.6139, 77.2090, 80, 200, "Delhi"),          # Delhi (high pollution)
        (19.0760, 72.8777, 60, 150, "Mumbai"),         # Mumbai
        (12.9716, 77.5946, 50, 120, "Bangalore"),      # Bangalore
        (22.5726, 88.3639, 70, 180, "Kolkata"),        # Kolkata
        (13.0827, 80.2707, 55, 130, "Chennai"),        # Chennai
        (17.3850, 78.4867, 65, 160, "Hyderabad"),      # Hyderabad
        (23.0225, 72.5714, 75, 190, "Ahmedabad"),      # Ahmedabad
        (18.5204, 73.8567, 50, 110, "Pune"),           # Pune
        (26.9124, 75.7873, 85, 210, "Jaipur"),         # Jaipur
        (30.7333, 76.7794, 90, 220, "Chandigarh"),     # Chandigarh
    ]
    
    data_rows = []
    
    # Generate data for each city
    for lat, lon, min_pm25, max_pm25, city_name in indian_cities:
        # PM2.5 (primary pollutant)
        for _ in range(num_points // 10):
            pm25_value = np.random.uniform(min_pm25, max_pm25)
            
            # Add spatial variation (±0.1° ≈ 10km)
            lat_offset = np.random.uniform(-0.1, 0.1)
            lon_offset = np.random.uniform(-0.1, 0.1)
            
            # Recent date (last 24 hours)
            hours_ago = np.random.randint(0, 24)
            timestamp = datetime.utcnow() - timedelta(hours=hours_ago)
            
            data_rows.append({
                "date": timestamp,
                "latitude": lat + lat_offset,
                "longitude": lon + lon_offset,
                "parameter": "pm25",
                "value": pm25_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # NO2 (correlated with traffic)
        for _ in range(num_points // 20):
            no2_value = np.random.uniform(20, 100)  # µg/m³
            
            lat_offset = np.random.uniform(-0.1, 0.1)
            lon_offset = np.random.uniform(-0.1, 0.1)
            hours_ago = np.random.randint(0, 24)
            timestamp = datetime.utcnow() - timedelta(hours=hours_ago)
            
            data_rows.append({
                "date": timestamp,
                "latitude": lat + lat_offset,
                "longitude": lon + lon_offset,
                "parameter": "no2",
                "value": no2_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
        
        # SO2 (industrial areas)
        for _ in range(num_points // 30):
            so2_value = np.random.uniform(10, 60)  # µg/m³
            
            lat_offset = np.random.uniform(-0.1, 0.1)
            lon_offset = np.random.uniform(-0.1, 0.1)
            hours_ago = np.random.randint(0, 24)
            timestamp = datetime.utcnow() - timedelta(hours=hours_ago)
            
            data_rows.append({
                "date": timestamp,
                "latitude": lat + lat_offset,
                "longitude": lon + lon_offset,
                "parameter": "so2",
                "value": so2_value,
                "location": city_name,
                "source": "MOCK_DATA",
            })
    
    df = pd.DataFrame(data_rows)
    print(f"[OK] Generated {len(df)} mock data points")
    return df


def consolidate_dataframes(dfs):
    """Consolidate multiple dataframes."""
    valid = [df for df in dfs if df is not None and not df.empty]
    if not valid:
        return pd.DataFrame()

    combined = pd.concat(valid, ignore_index=True)
    combined["parameter"] = combined["parameter"].str.lower()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    
    # Validate ranges
    valid_rows = []
    for _, row in combined.iterrows():
        if validate_value_range(row["parameter"], row["value"]):
            valid_rows.append(row)
    
    if valid_rows:
        return pd.DataFrame(valid_rows)
    return pd.DataFrame()


def save_combined_data(df: pd.DataFrame):
    """Save consolidated dataset."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Save with timestamp
    timestamped_path = RAW_DATA_DIR / f"all_gases_data_{timestamp}.csv"
    df.to_csv(timestamped_path, index=False)
    
    # Save as latest
    latest_path = RAW_DATA_DIR / "all_gases_data_latest.csv"
    df.to_csv(latest_path, index=False)
    
    print(f"[OK] Saved {len(df)} rows to {latest_path}")


def fetch_all_sources(use_mock_if_needed=True):
    """
    Fetch from all sources. If no data available, use mock data.
    """
    datasets = []
    
    # Try real data sources
    try:
        print("[INFO] Attempting to fetch WAQI data...")
        waqi_df = fetch_waqi_data()
        if waqi_df is not None and not waqi_df.empty:
            datasets.append(waqi_df)
            print(f"[OK] WAQI: {len(waqi_df)} rows")
    except Exception as e:
        print(f"[WARN] WAQI fetch failed: {e}")
    
    try:
        print("[INFO] Attempting to fetch Sentinel-5P data...")
        sentinel_df = fetch_sentinel5p_grid(["no2", "so2", "co"])
        if sentinel_df is not None and not sentinel_df.empty:
            datasets.append(sentinel_df)
            print(f"[OK] Sentinel-5P: {len(sentinel_df)} rows")
    except Exception as e:
        print(f"[WARN] Sentinel-5P fetch failed: {e}")
    
    try:
        print("[INFO] Attempting to fetch MODIS data...")
        modis_df = fetch_modis_aod()
        if modis_df is not None and not modis_df.empty:
            datasets.append(modis_df)
            print(f"[OK] MODIS: {len(modis_df)} rows")
    except Exception as e:
        print(f"[WARN] MODIS fetch failed: {e}")
    
    # If no real data and mock requested
    if not datasets and use_mock_if_needed:
        print("\n[WARN] No real data sources available!")
        print("[INFO] Generating mock data for testing...")
        mock_df = generate_mock_data_for_india()
        datasets.append(mock_df)
    
    if not datasets:
        print("[ERROR] No data available")
        return pd.DataFrame()
    
    return consolidate_dataframes(datasets)


def summarize(df: pd.DataFrame):
    """Print summary statistics."""
    if df.empty:
        print("[WARN] Empty dataframe")
        return
    
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    
    for gas in df["parameter"].unique():
        gas_df = df[df["parameter"] == gas]
        values = gas_df["value"]
        
        print(f"\n{gas.upper()}:")
        print(f"  Count: {len(values)}")
        print(f"  Mean:  {values.mean():.2f}")
        print(f"  Min:   {values.min():.2f}")
        print(f"  Max:   {values.max():.2f}")
    
    print("\n" + "=" * 60)


def main():
    """Main execution."""
    print("\n" + "=" * 60)
    print("AIR POLLUTION DATA COLLECTION")
    print("=" * 60 + "\n")
    
    # Create data directory if needed
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Fetch data (with mock fallback)
    df = fetch_all_sources(use_mock_if_needed=True)
    
    if df.empty:
        print("[ERROR] No data gathered")
        return
    
    # Save
    save_combined_data(df)
    
    # Summarize
    summarize(df[df["parameter"].isin(SUPPORTED_GASES)])
    
    print("\n[SUCCESS] Data collection complete")
    print(f"[INFO] Run the API server: python main.py")


if __name__ == "__main__":
    main()