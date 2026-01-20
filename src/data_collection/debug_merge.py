import pandas as pd
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_collection.fetch_waqi import fetch_waqi_data
from src.data_collection.fetch_openaq_sdk import fetch_real_openaq_data_sdk

print("--- DEBUG FETCH WAQI ---")
waqi_df = fetch_waqi_data()
if waqi_df is not None:
    print(f"WAQI rows: {len(waqi_df)}")
    print(f"WAQI sources: {waqi_df['source'].unique() if 'source' in waqi_df.columns else 'NO SOURCE'}")

print("\n--- DEBUG FETCH OPENAQ ---")
openaq_df = fetch_real_openaq_data_sdk(country_code="IN")
if openaq_df is not None:
    print(f"OpenAQ rows: {len(openaq_df)}")
    if not openaq_df.empty:
        print(f"OpenAQ sources: {openaq_df['source'].unique() if 'source' in openaq_df.columns else 'NO SOURCE'}")
        print(f"Sample coords: {openaq_df[['latitude', 'longitude']].iloc[0].to_dict()}")

print("\n--- DEBUG MERGE ---")
datasets = [waqi_df, openaq_df]
valid = [df for df in datasets if df is not None and not df.empty]
combined = pd.concat(valid, ignore_index=True)
print(f"Combined count: {len(combined)}")
print(f"Source counts:\n{combined['source'].value_counts()}")
