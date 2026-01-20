"""
Fetch REAL air pollution data using OpenAQ Python SDK.

This uses the official OpenAQ Python library which handles the API correctly.
"""

from openaq import OpenAQ
import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.hotspot_detection import train_hotspot_model
from src.utils.gas_config import RAW_DATA_DIR, OPENAQ_API_KEY

# Country ID mapping
COUNTRY_IDS = {
    "IN": 9,   # India
    "US": 231,
    "CN": 44,
}


def fetch_real_openaq_data_sdk(
    country_code: str = "IN",
    limit: int = 500,
    parameters: list = None,
) -> pd.DataFrame:
    """
    Fetch REAL air quality measurements using OpenAQ Python SDK.
    
    Args:
        country_code: ISO country code (default: IN for India)
        limit: Maximum number of measurements to fetch
        parameters: List of parameters to fetch (default: ['pm25'])
        
    Returns:
        DataFrame with REAL air quality measurements
    """
    if parameters is None:
        parameters = ['pm25', 'pm10', 'no2', 'so2', 'o3', 'co']
    
    country_id = COUNTRY_IDS.get(country_code.upper(), 9)
    
    print(f"Fetching REAL OpenAQ data for {country_code} (ID: {country_id})...")
    print(f"Using OpenAQ Python SDK")
    print(f"Parameters: {', '.join(parameters)}")
    
    if not OPENAQ_API_KEY:
        print("\n[ERROR] OpenAQ API key not found!")
        return pd.DataFrame()
    
    try:
        # Initialize OpenAQ client with API key
        api = OpenAQ(api_key=OPENAQ_API_KEY)
        
        print(f"Fetching REAL OpenAQ data for {country_code} (ID: {country_id})...")
        
        # Step 1: Get Locations first
        print("Step 1: Fetching active locations to find sensors...")
        active_locations = []
        locs_response = api.locations.list(
            countries_id=[country_id],
            limit=50, 
            page=1
        )
        
        if not locs_response.results:
            print("[ERROR] No locations found for this country.")
            return pd.DataFrame()
            
        location_map = {}
        sensor_ids = []
        
        # Mapping parameter IDs to names
        PARAM_MAP = {
            1: "pm10",
            2: "pm25",
            3: "o3",
            4: "co",
            5: "no2",
            6: "so2"
        }
        
        # Step 2: Extract Sensors for all parameters
        print("Step 2: Processing locations and sensors...")
        for loc in locs_response.results:
            lat = None
            lon = None
            if hasattr(loc, 'coordinates'):
                lat = loc.coordinates.latitude
                lon = loc.coordinates.longitude
            
            if hasattr(loc, 'sensors') and loc.sensors:
                for sensor in loc.sensors:
                    # Check if sensor has a parameter we want
                    p_name = None
                    if hasattr(sensor, 'parameter'):
                         if isinstance(sensor.parameter, dict):
                             p_name = sensor.parameter.get('name')
                         else:
                             p_name = sensor.parameter.name if hasattr(sensor.parameter, 'name') else None
                    
                    if p_name in ["pm25", "pm10", "o3", "co", "no2", "so2"] or (hasattr(sensor, 'parameter') and sensor.parameter.id in PARAM_MAP):
                        sensor_ids.append(sensor.id)
                        location_map[sensor.id] = {
                            "name": loc.name,
                            "lat": lat,
                            "lon": lon,
                            "parameter": p_name or PARAM_MAP.get(sensor.parameter.id, "unknown")
                        }
        
        print(f"Found {len(sensor_ids)} candidate sensors.")
        
        if not sensor_ids:
            return pd.DataFrame()

        # Step 3: Fetch measurements
        # Increase lookback to 3 days to ensure we get something if stations are slow
        date_to = datetime.now()
        date_from = date_to - timedelta(days=3)
        
        datetime_from = date_from.strftime("%Y-%m-%dT%H:%M:%S")
        datetime_to = date_to.strftime("%Y-%m-%dT%H:%M:%S")
        
        all_data = []
        # Take a larger sample but still respect rate limits
        target_sensors = sensor_ids[:100] 
        
        print(f"Step 3: Fetching measurements for up to {len(target_sensors)} sensors...")
        
        session = requests.Session() # Reuse connection
        for sid in target_sensors:
            try:
                url = f"https://api.openaq.org/v3/sensors/{sid}/measurements"
                # Use a wider 7-day windows by default to ensure we capture some data
                # for stations that might be reporting with some lag
                d_to = datetime.utcnow()
                d_from = d_to - timedelta(days=14)
                
                params = {
                    "datetime_from": d_from.strftime("%Y-%m-%dT%H:%M:%S"),
                    "datetime_to": d_to.strftime("%Y-%m-%dT%H:%M:%S"),
                    "limit": 10
                }
                
                resp = session.get(url, headers={"X-API-Key": OPENAQ_API_KEY}, params=params, timeout=10)
                if resp.status_code != 200:
                    continue
                    
                data = resp.json()
                measurements = data.get('results', [])
                loc_meta = location_map.get(sid, {})
                
                if not measurements:
                    continue

                for m in measurements:
                     val = m.get('value', 0)
                     # Standardize date
                     measure_date = datetime.now().isoformat()
                     if 'period' in m and 'datetime_to' in m['period']:
                         measure_date = m['period']['datetime_to']['utc']
                     elif 'date' in m and 'utc' in m['date']:
                         measure_date = m['date']['utc']
                     
                     record = {
                        "date": measure_date,
                        "location": loc_meta.get('name'),
                        "parameter": loc_meta.get('parameter', 'unknown'),
                        "value": float(val),
                        "unit": "µg/m³" if loc_meta.get('parameter') != 'co' else "mg/m³",
                        "latitude": loc_meta.get('lat'),
                        "longitude": loc_meta.get('lon'),
                        "country": country_code,
                        "source": "OpenAQ (Live)",
                    }
                     # Basic validation
                     if record["value"] >= 0 and record["latitude"] is not None:
                        all_data.append(record)
                        
                print(f".", end="", flush=True)
                
            except Exception as inner_e:
                continue

        print(f"\nExtracted {len(all_data)} measurements.")
        
        if not all_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_data)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
        return df

    except Exception as e:
        print(f"\n[ERROR] API Loop failed: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def save_openaq_data(df: pd.DataFrame, filename: str = None) -> Path:
    """Save fetched data to CSV file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openaq_real_data_{timestamp}.csv"
    
    filepath = RAW_DATA_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"\nReal data saved to: {filepath}")
    
    # Also update ALL GASES LATEST for model training
    latest_path = RAW_DATA_DIR / "all_gases_data_latest.csv"
    if latest_path.exists():
        try:
            old_df = pd.read_csv(latest_path)
            # Merge and deduplicate
            combined_df = pd.concat([old_df, df], ignore_index=True)
            # Deduplicate by date, location, parameter to avoid doubling up
            if 'date' in combined_df.columns and 'location' in combined_df.columns:
                 combined_df = combined_df.drop_duplicates(subset=['date', 'location', 'parameter'])
            
            combined_df.to_csv(latest_path, index=False)
            print(f"Updated central data file: {latest_path}")
        except Exception as e:
            print(f"[WARN] Could not update central file: {e}")
            df.to_csv(latest_path, index=False)
    else:
        df.to_csv(latest_path, index=False)
        print(f"Created central data file: {latest_path}")
        
    return filepath


if __name__ == "__main__":
    df = fetch_real_openaq_data_sdk(country_code="IN", limit=500)
    
    if not df.empty:
        save_openaq_data(df)
        print(f"\n[SUCCESS] Fetched {len(df)} REAL measurements!")
        
        # TRIGGER MODEL TRAINING
        try:
            train_hotspot_model()
            print("[SUCCESS] Models retrained with new data!")
        except Exception as e:
             print(f"[ERROR] Auto-training failed: {e}")

        if "parameter" in df.columns:
            print(f"\nParameters: {df['parameter'].value_counts().to_dict()}")
        if 'value' in df.columns:
            unit = df['unit'].iloc[0] if 'unit' in df.columns and len(df) > 0 else ''
            print(f"\nValue range: {df['value'].min():.2f} - {df['value'].max():.2f} {unit}")
    else:
        print("\n[ERROR] No data retrieved.")
