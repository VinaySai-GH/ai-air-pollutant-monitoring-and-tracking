"""
Fetch REAL air pollution data using OpenAQ Python SDK.

This uses the official OpenAQ Python library which handles the API correctly.
"""

from openaq import OpenAQ
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.config import RAW_DATA_DIR, OPENAQ_API_KEY

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
        parameters = ['pm25']
    
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
        
        # Get recent measurements (last 7 days)
        date_to = datetime.now()
        date_from = date_to - timedelta(days=7)
        
        print(f"Fetching measurements from {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}...")
        
        all_data = []
        page = 1
        max_pages = 10  # Limit to prevent too many requests
        
        while len(all_data) < limit and page <= max_pages:
            # Fetch measurements
            results = api.measurements.get(
                country_id=country_id,
                limit=min(100, limit - len(all_data)),  # API limit is 100 per page
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat(),
                page=page,
                parameter_id=2,  # PM2.5 parameter ID
            )
            
            if results.status != 200:
                print(f"\n[ERROR] API returned status {results.status}")
                break
            
            measurements = results.body.get('results', [])
            
            if not measurements:
                break
            
            # Process measurements
            for measurement in measurements:
                location = measurement.get('location', {})
                coordinates = location.get('coordinates', {})
                parameter = measurement.get('parameter', {})
                
                record = {
                    "date": measurement.get('date', {}).get('utc', datetime.now().isoformat()),
                    "location": location.get('name', ''),
                    "parameter": parameter.get('name', '').lower(),
                    "value": float(measurement.get('value', 0)),
                    "unit": parameter.get('units', ''),
                    "latitude": float(coordinates.get('latitude', 0)),
                    "longitude": float(coordinates.get('longitude', 0)),
                }
                all_data.append(record)
            
            print(f"  Fetched page {page}: {len(measurements)} measurements (total: {len(all_data)})")
            
            if len(measurements) < 100:  # Last page
                break
            
            page += 1
        
        print(f"\nExtracted {len(all_data)} REAL measurements")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
        
        return df
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
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
    return filepath


if __name__ == "__main__":
    df = fetch_real_openaq_data_sdk(country_code="IN", limit=500)
    
    if not df.empty:
        save_openaq_data(df)
        print(f"\n[SUCCESS] Fetched {len(df)} REAL measurements!")
        if "parameter" in df.columns:
            print(f"\nParameters: {df['parameter'].value_counts().to_dict()}")
        if 'value' in df.columns:
            unit = df['unit'].iloc[0] if 'unit' in df.columns and len(df) > 0 else ''
            print(f"\nValue range: {df['value'].min():.2f} - {df['value'].max():.2f} {unit}")
    else:
        print("\n[ERROR] No data retrieved.")
