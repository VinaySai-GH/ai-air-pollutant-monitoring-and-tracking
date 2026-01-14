"""
Script to fetch real air pollution data and prepare it for the backend.

This script:
1. Fetches ALL gases (PM2.5, NO2, CO, SO2)
2. Uses WAQI + Sentinel-5P + MODIS
3. Saves data in a format the backend already expects

Run:
    python scripts/fetch_data.py
"""

import sys
from pathlib import Path
import traceback

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_collection.fetch_all_gases import fetch_all_sources
from src.utils.config import RAW_DATA_DIR


def main():
    print("=" * 60)
    print("Fetching REAL Air Pollution Data (ALL GASES)")
    print("=" * 60)

    try:
        df = fetch_all_sources()

        if df is None or df.empty:
            print("[WARN] No data collected from any source.")
            return 1

        print("\n[OK] Data collection completed successfully")
        print(f"[OK] Total rows collected: {len(df)}")

        if "parameter" in df.columns:
            print("\nGases collected:")
            print(df["parameter"].value_counts())

        print("\nFiles updated:")
        print(f" - {RAW_DATA_DIR / 'all_gases_data_latest.csv'}")
        print(f" - {RAW_DATA_DIR / 'waqi_pm25_history.csv'} (PM2.5 accumulation)")

        print("\nNext steps:")
        print("1. Restart backend:")
        print("   uvicorn api.main:app --reload")
        print("2. Query API with different gases:")
        print("   /data/recent?parameter=no2")
        print("   /data/recent?parameter=co")
        print("   /data/recent?parameter=so2")

        return 0

    except Exception:
        print("\n[ERROR] Data fetch failed")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
