"""
Clean up Unknown and invalid location data from all gas data files
"""

import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.gas_config import RAW_DATA_DIR, SUPPORTED_GASES

def clean_unknown_data():
    """Remove Unknown locations and invalid data"""
    
    total_removed = 0
    
    for gas in SUPPORTED_GASES:
        file_path = RAW_DATA_DIR / f"{gas}_data.csv"
        
        if not file_path.exists():
            print(f"[SKIP] {file_path} doesn't exist")
            continue
            
        print(f"\n[CLEAN] Processing {gas}_data.csv...")
        
        df = pd.read_csv(file_path)
        original_count = len(df)
        
        # Remove rows with Unknown location
        df = df[df['location'] != 'Unknown']
        
        # Also remove rows where location is NaN
        df = df[df['location'].notna()]
        
        # Remove extremely high outlier values (likely sensor errors)
        # PM2.5 > 500 is basically unlivable, likely error
        if gas == 'pm25':
            df = df[df['value'] < 500]
        elif gas == 'pm10':
            df = df[df['value'] < 600]
        
        removed = original_count - len(df)
        total_removed += removed
        
        # Save cleaned data
        df.to_csv(file_path, index=False)
        
        print(f"  ✓ Removed {removed} invalid rows")
        print(f"  ✓ Kept {len(df)} valid rows")
    
    print(f"\n[DONE] Total removed: {total_removed} invalid data points")
    return total_removed

if __name__ == "__main__":
    clean_unknown_data()
