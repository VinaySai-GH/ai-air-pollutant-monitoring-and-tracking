"""
Central configuration for air pollution monitoring system.

Includes:
- Gas metadata (units, thresholds, colors)
- API configuration
- Paths
- Geographic regions
- Helper functions used by FastAPI
"""

from typing import Dict, Any
from pathlib import Path
import os
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------

load_dotenv()

# -------------------------------------------------------------------
# Project paths
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Geographic configuration
# -------------------------------------------------------------------

AREA_OF_INTEREST = {
    "type": "Polygon",
    "coordinates": [[
        [68.0, 6.5],
        [97.5, 6.5],
        [97.5, 37.5],
        [68.0, 37.5],
        [68.0, 6.5],
    ]]
}

WAQI_BOUNDS = {
    "india": {
        "lat_min": 6.5,
        "lat_max": 37.5,
        "lon_min": 68.0,
        "lon_max": 97.5,
    }
}

# -------------------------------------------------------------------
# WAQI API configuration
# -------------------------------------------------------------------

WAQI_API_TOKEN = os.getenv("WAQI_API_TOKEN")

if not WAQI_API_TOKEN:
    raise RuntimeError(
        "WAQI_API_TOKEN not found. Add it to .env file:\n"
        "WAQI_API_TOKEN=your_token_here"
    )

# -------------------------------------------------------------------
# Gas-specific configuration
# -------------------------------------------------------------------

GAS_CONFIG: Dict[str, Dict[str, Any]] = {
    "pm25": {
        "name": "PM2.5",
        "unit": "µg/m³",
        "max_scale": 250,
        "min_scale": 0,
        "thresholds": {
            "good": 50,
            "moderate": 100,
            "unhealthy_sensitive": 150,
            "unhealthy": 200,
            "very_unhealthy": 300,
        },
        "colors": {
            "good": "#00E400",
            "moderate": "#FFFF00",
            "unhealthy_sensitive": "#FF7E00",
            "unhealthy": "#FF0000",
            "very_unhealthy": "#8F3F97",
            "hazardous": "#7E0023",
        },
    },
    "pm10": {
        "name": "PM10",
        "unit": "µg/m³",
        "max_scale": 350,
        "min_scale": 0,
        "thresholds": {
            "good": 100,
            "moderate": 200,
            "unhealthy_sensitive": 250,
            "unhealthy": 350,
            "very_unhealthy": 430,
        },
        "colors": {
            "good": "#00E400",
            "moderate": "#FFFF00",
            "unhealthy_sensitive": "#FF7E00",
            "unhealthy": "#FF0000",
            "very_unhealthy": "#8F3F97",
            "hazardous": "#7E0023",
        },
    },
    "no2": {
        "name": "NO₂",
        "unit": "µg/m³",
        "max_scale": 200,
        "min_scale": 0,
        "thresholds": {
            "good": 40,
            "moderate": 80,
            "unhealthy_sensitive": 120,
            "unhealthy": 160,
            "very_unhealthy": 200,
        },
        "colors": {
            "good": "#00E400",
            "moderate": "#FFFF00",
            "unhealthy_sensitive": "#FF7E00",
            "unhealthy": "#FF0000",
            "very_unhealthy": "#8F3F97",
            "hazardous": "#7E0023",
        },
    },
    "so2": {
        "name": "SO₂",
        "unit": "µg/m³",
        "max_scale": 100,
        "min_scale": 0,
        "thresholds": {
            "good": 20,
            "moderate": 40,
            "unhealthy_sensitive": 60,
            "unhealthy": 80,
            "very_unhealthy": 100,
        },
        "colors": {
            "good": "#00E400",
            "moderate": "#FFFF00",
            "unhealthy_sensitive": "#FF7E00",
            "unhealthy": "#FF0000",
            "very_unhealthy": "#8F3F97",
            "hazardous": "#7E0023",
        },
    },
    "co": {
        "name": "CO",
        "unit": "mg/m³",
        "max_scale": 10,
        "min_scale": 0,
        "thresholds": {
            "good": 1,
            "moderate": 2,
            "unhealthy_sensitive": 4,
            "unhealthy": 6,
            "very_unhealthy": 10,
        },
        "colors": {
            "good": "#00E400",
            "moderate": "#FFFF00",
            "unhealthy_sensitive": "#FF7E00",
            "unhealthy": "#FF0000",
            "very_unhealthy": "#8F3F97",
            "hazardous": "#7E0023",
        },
    },
    "o3": {
        "name": "O₃",
        "unit": "µg/m³",
        "max_scale": 200,
        "min_scale": 0,
        "thresholds": {
            "good": 60,
            "moderate": 120,
            "unhealthy_sensitive": 160,
            "unhealthy": 200,
            "very_unhealthy": 240,
        },
        "colors": {
            "good": "#00E400",
            "moderate": "#FFFF00",
            "unhealthy_sensitive": "#FF7E00",
            "unhealthy": "#FF0000",
            "very_unhealthy": "#8F3F97",
            "hazardous": "#7E0023",
        },
    },
}

# -------------------------------------------------------------------
# Derived constants
# -------------------------------------------------------------------

SUPPORTED_GASES = list(GAS_CONFIG.keys())
GAS_UNITS = {gas: cfg["unit"] for gas, cfg in GAS_CONFIG.items()}

# -------------------------------------------------------------------
# Helper functions (USED BY API)
# -------------------------------------------------------------------

def get_gas_config(gas: str) -> Dict[str, Any]:
    return GAS_CONFIG.get(gas.lower(), GAS_CONFIG["pm25"])


def get_all_supported_gases():
    """Return list of supported gas parameters."""
    return SUPPORTED_GASES


def get_category_for_value(gas: str, value: float) -> str:
    thresholds = get_gas_config(gas)["thresholds"]

    if value <= thresholds["good"]:
        return "good"
    elif value <= thresholds["moderate"]:
        return "moderate"
    elif value <= thresholds["unhealthy_sensitive"]:
        return "unhealthy_sensitive"
    elif value <= thresholds["unhealthy"]:
        return "unhealthy"
    elif value <= thresholds["very_unhealthy"]:
        return "very_unhealthy"
    else:
        return "hazardous"


def get_color_for_value(gas: str, value: float) -> str:
    category = get_category_for_value(gas, value)
    return get_gas_config(gas)["colors"][category]


def validate_value_range(gas: str, value: float) -> bool:
    config = get_gas_config(gas)
    return 0 <= value <= config["max_scale"] * 2
