"""Pure utility functions shared by the pipeline and external services."""

from math import isnan

try:
    from .config import AQI_LEVELS
except ImportError:  # Supports `python utils.py` from this directory.
    from config import AQI_LEVELS


PM25_AQI_BREAKPOINTS = (
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
)


def calculate_pm25_aqi(pm25: float | None) -> int | None:
    """Convert PM2.5 concentration in ug/m3 to an EPA AQI value."""
    if pm25 is None or (isinstance(pm25, float) and isnan(pm25)):
        return None
    concentration = int(float(pm25) * 10) / 10
    if concentration < 0:
        raise ValueError("PM2.5 concentration cannot be negative")
    for concentration_low, concentration_high, index_low, index_high in PM25_AQI_BREAKPOINTS:
        if concentration <= concentration_high:
            index = (index_high - index_low) / (concentration_high - concentration_low)
            return round(index * (concentration - concentration_low) + index_low)
    return 500


def evaluate_aqi_category(pm25: float) -> dict:
    """Return the configured category and health advice for an AQI-like value."""
    if pm25 is None or (isinstance(pm25, float) and isnan(pm25)):
        return {"category": "Unknown", "advice": "No air-quality reading is available."}
    if pm25 <= AQI_LEVELS["Good"]["max"]:
        category = "Good"
    elif pm25 <= AQI_LEVELS["Moderate"]["max"]:
        category = "Moderate"
    elif pm25 <= AQI_LEVELS["Sensitive"]["max"]:
        category = "Sensitive"
    else:
        category = "Unhealthy"
    return {"category": category, "advice": AQI_LEVELS[category]["advice"]}


def degrees_to_cardinal(deg: float) -> str:
    """Convert compass degrees to one of 16 cardinal/intercardinal points."""
    if deg is None:
        return "Unknown"
    directions = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
    return directions[int((float(deg) % 360) / 22.5 + 0.5) % 16]
