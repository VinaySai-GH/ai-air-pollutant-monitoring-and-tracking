"""
Quick test script to verify all data sources are working.
Run this to check if data collection is functioning properly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_collection.fetch_waqi import fetch_waqi_data
from src.data_collection.fetch_satellite_gee import fetch_sentinel5p_grid, fetch_modis_aod
from src.utils.config import WAQI_API_TOKEN

def test_waqi():
    """Test WAQI data collection"""
    print("\n" + "="*60)
    print("Testing WAQI Data Collection")
    print("="*60)
    
    if not WAQI_API_TOKEN:
        print("[SKIP] WAQI token not configured")
        return None
    
    try:
        df = fetch_waqi_data(limit=10)  # Test with just 10 stations
        if not df.empty:
            print(f"[OK] WAQI: {len(df)} measurements collected")
            print(f"     Gases: {df['parameter'].unique().tolist()}")
            return df
        else:
            print("[WARN] WAQI: No data collected")
            return None
    except Exception as e:
        print(f"[ERROR] WAQI: {e}")
        return None

def test_sentinel5p():
    """Test Sentinel-5P data collection"""
    print("\n" + "="*60)
    print("Testing Sentinel-5P Data Collection")
    print("="*60)
    
    try:
        df = fetch_sentinel5p_grid(["no2", "co", "so2"], num_points=9)  # Small grid for testing
        if not df.empty:
            print(f"[OK] Sentinel-5P: {len(df)} measurements collected")
            print(f"     Gases: {df['parameter'].unique().tolist()}")
            return df
        else:
            print("[WARN] Sentinel-5P: No data collected")
            return None
    except Exception as e:
        print(f"[ERROR] Sentinel-5P: {e}")
        print("     Make sure Google Earth Engine is authenticated")
        return None

def test_modis():
    """Test MODIS AOD data collection"""
    print("\n" + "="*60)
    print("Testing MODIS AOD Data Collection")
    print("="*60)
    
    try:
        df = fetch_modis_aod(num_points=9)  # Small grid for testing
        if not df.empty:
            print(f"[OK] MODIS: {len(df)} measurements collected")
            print(f"     Parameter: {df['parameter'].unique().tolist()}")
            return df
        else:
            print("[WARN] MODIS: No data collected")
            return None
    except Exception as e:
        print(f"[ERROR] MODIS: {e}")
        print("     Make sure Google Earth Engine is authenticated")
        return None

def main():
    """Run all tests"""
    print("="*60)
    print("DATA COLLECTION TEST SUITE")
    print("="*60)
    
    results = {
        "WAQI": test_waqi(),
        "Sentinel-5P": test_sentinel5p(),
        "MODIS": test_modis(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for source, df in results.items():
        status = "✅ PASS" if df is not None and not df.empty else "❌ FAIL"
        count = len(df) if df is not None else 0
        print(f"{source:15} {status:10} ({count} measurements)")
    
    successful = sum(1 for df in results.values() if df is not None and not df.empty)
    print(f"\n{successful}/{len(results)} data sources working")
    
    if successful > 0:
        print("\n✅ At least one data source is working!")
        print("   Run 'python src/data_collection/fetch_all_gases.py' for full collection")
    else:
        print("\n❌ No data sources working. Check:")
        print("   1. WAQI token configured")
        print("   2. Google Earth Engine authenticated")
        print("   3. Internet connection")

if __name__ == "__main__":
    main()
