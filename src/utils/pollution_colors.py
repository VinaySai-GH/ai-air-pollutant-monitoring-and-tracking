"""
Utility functions for pollution color coding and categories.

Supports:
- PM2.5
- NO2
- CO
- SO2
"""

# --------------------------------------------------
# Pollution categories (CPCB-style, simplified)
# --------------------------------------------------

PM25_BREAKPOINTS = [
    (50, "Good", "#2ecc71"),
    (100, "Satisfactory", "#f1c40f"),
    (150, "Moderate", "#e67e22"),
    (200, "Poor", "#e74c3c"),
    (300, "Very Poor", "#8e44ad"),
    (float("inf"), "Severe", "#7f0000"),
]

NO2_BREAKPOINTS = [
    (40, "Good", "#2ecc71"),
    (80, "Satisfactory", "#f1c40f"),
    (180, "Moderate", "#e67e22"),
    (280, "Poor", "#e74c3c"),
    (400, "Very Poor", "#8e44ad"),
    (float("inf"), "Severe", "#7f0000"),
]

SO2_BREAKPOINTS = [
    (40, "Good", "#2ecc71"),
    (80, "Satisfactory", "#f1c40f"),
    (380, "Moderate", "#e67e22"),
    (800, "Poor", "#e74c3c"),
    (1600, "Very Poor", "#8e44ad"),
    (float("inf"), "Severe", "#7f0000"),
]

CO_BREAKPOINTS = [
    (1.0, "Good", "#2ecc71"),
    (2.0, "Satisfactory", "#f1c40f"),
    (10.0, "Moderate", "#e67e22"),
    (17.0, "Poor", "#e74c3c"),
    (34.0, "Very Poor", "#8e44ad"),
    (float("inf"), "Severe", "#7f0000"),
]

# --------------------------------------------------
# Internal helper
# --------------------------------------------------

def _lookup(value: float, breakpoints):
    for limit, category, color in breakpoints:
        if value <= limit:
            return category, color
    return "Unknown", "#95a5a6"


# --------------------------------------------------
# PUBLIC API (what your backend imports)
# --------------------------------------------------

def get_pollution_color(value: float, parameter: str) -> str:
    """
    Return hex color for a pollutant value.
    """
    if value is None:
        return "#95a5a6"

    param = parameter.lower()

    if param == "pm25":
        return _lookup(value, PM25_BREAKPOINTS)[1]
    if param == "no2":
        return _lookup(value, NO2_BREAKPOINTS)[1]
    if param == "so2":
        return _lookup(value, SO2_BREAKPOINTS)[1]
    if param == "co":
        return _lookup(value, CO_BREAKPOINTS)[1]

    return "#95a5a6"


def get_pollution_category(value: float, parameter: str) -> str:
    """
    Return air quality category for a pollutant value.
    """
    if value is None:
        return "Unknown"

    param = parameter.lower()

    if param == "pm25":
        return _lookup(value, PM25_BREAKPOINTS)[0]
    if param == "no2":
        return _lookup(value, NO2_BREAKPOINTS)[0]
    if param == "so2":
        return _lookup(value, SO2_BREAKPOINTS)[0]
    if param == "co":
        return _lookup(value, CO_BREAKPOINTS)[0]

    return "Unknown"
