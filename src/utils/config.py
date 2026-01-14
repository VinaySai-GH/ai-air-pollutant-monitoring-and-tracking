"""
Configuration for PM2.5 Monitoring System
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ===============================
# API TOKENS
# ===============================
WAQI_API_TOKEN = os.getenv("WAQI_API_TOKEN", "")

# ===============================
# INDIA AOI
# ===============================
AREA_OF_INTEREST = {
    "min_lon": 68.0,
    "min_lat": 6.0,
    "max_lon": 97.0,
    "max_lat": 37.0,
}

WAQI_BOUNDS = AREA_OF_INTEREST

# ===============================
# UNITS
# ===============================
# ===============================
# GAS UNITS (BACKWARD COMPATIBLE)
# ===============================
GAS_UNITS = {
    "pm25": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "co": "mg/m³",
}
SUPPORTED_GASES = ["pm25", "no2", "co", "so2"]
