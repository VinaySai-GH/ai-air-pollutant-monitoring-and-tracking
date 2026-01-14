"""
Orchestrate all data sources and produce unified dataset.
PM2.5 history is automatically included.
"""

from datetime import datetime
import pandas as pd

from src.data_collection.fetch_satellite_gee import (
    fetch_sentinel5p_grid,
    fetch_modis_aod,
)
from src.data_collection.fetch_waqi import fetch_waqi_data
from src.utils.config import RAW_DATA_DIR, SUPPORTED_GASES


def consolidate_dataframes(dfs):
    valid = [df for df in dfs if df is not None and not df.empty]
    if not valid:
        return pd.DataFrame()

    combined = pd.concat(valid, ignore_index=True)
    combined["parameter"] = combined["parameter"].str.lower()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    return combined


def save_combined_data(df: pd.DataFrame):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    latest_path = RAW_DATA_DIR / "all_gases_data_latest.csv"
    df.to_csv(latest_path, index=False)
    print(f"[OK] Saved combined dataset ({len(df)} rows) to {latest_path}")


def fetch_all_sources():
    waqi_df = fetch_waqi_data()
    sentinel_df = fetch_sentinel5p_grid(["no2", "so2", "co"])
    modis_df = fetch_modis_aod()

    # Include PM2.5 history if exists
    pm25_history = RAW_DATA_DIR / "waqi_pm25_history.csv"
    if pm25_history.exists():
        pm25_hist_df = pd.read_csv(pm25_history, parse_dates=["date"])
        waqi_df = pd.concat([waqi_df, pm25_hist_df], ignore_index=True)

    return consolidate_dataframes([waqi_df, sentinel_df, modis_df])


def summarize(df: pd.DataFrame):
    if df.empty:
        print("[WARN] Combined dataframe is empty.")
        return

    print("\nSummary by gas:")
    print(df.groupby("parameter")["value"].agg(["count", "mean", "min", "max"]))


def main():
    df = fetch_all_sources()
    if df.empty:
        print("[ERROR] No data gathered.")
        return

    save_combined_data(df)
    summarize(df[df["parameter"].isin(SUPPORTED_GASES)])


if __name__ == "__main__":
    main()
